#!/usr/bin/env python3
"""
loop_enforcement.py — PreToolUse hook: enforce Loop mode (hard constraint).

When state.yaml has loop_mode=FULL or STANDARD, this hook blocks any
write operation that is not explicitly within an approved task's scope.

This is the hard mechanism that prevents the AI from "doing everything
myself" — it forces the Loop process: task creation → gate approval →
role assignment → execution within approved scope.

Blocking logic:
1. loop_mode is LIGHTWEIGHT or unset → pass (no enforcement)
2. Write to .ai/ governance files → pass (same exemption as gate_guard)
3. Write within an active task's allowed_paths → pass
4. Everything else in FULL/STANDARD mode → exit 2 BLOCKED

Exit codes: 0 = allow, 2 = block
"""
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import warnings
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING, format='[%(name)s] %(levelname)s: %(message)s')

sys.path.insert(0, str(Path(__file__).resolve().parent))
# Also add loop-engine project root so loop_core is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from hook_common import (
    DEFAULT_CONFIG,
    extract_target_path,
    is_governance_project,
    is_path_safe,
    is_readonly_command,
    load_config,
    load_gates_for_context,
    load_phase_gates_for_context,
    load_state,
    load_tasks_for_context,
    normalize_rel,
    project_root,
    read_stdin_json,
    should_fail_closed,
    try_import_hard_constraints,
)

# 自愈同步函数首次 sync 前不可用 → 安全退化
try:
    from hook_common import auto_sync_to_plugin_cache  # noqa: F811
    _AUTO_SYNC_AVAILABLE = True
except ImportError:
    _AUTO_SYNC_AVAILABLE = False
    def auto_sync_to_plugin_cache(root):  # type: ignore
        pass

# ── 自愈重执行（T-0086-P3）────────────────────────────────────────────
# auto_sync 在本进程启动后才把新代码复制进插件缓存 → 本次调用仍在用
# 旧模块逻辑判定（"改本地 → 缓存已同步 → 但本次仍按旧代码拦截"的
# 一次性竞态，主会话曾因此被 SETUP_INCOMPLETE 误拦）。对策：模块加载
# 时快照本进程用到的 hook 文件哈希；main() 同步后若磁盘版本已变 →
# 把 hook 输入暂存到临时文件并 os.execv 重执行自身一次（新进程加载
# 新代码，对同一条命令做出正确判定）。最多重执行一次（环境变量计数
# 防循环）。进程替换对调用方（ZCode CLI）透明：同一进程退出码即最终
# 判定。
_REEXEC_PAYLOAD_ENV = "LOOP_ENFORCEMENT_REEXEC_PAYLOAD"
_REEXEC_COUNT_ENV = "LOOP_ENFORCEMENT_REEXEC_COUNT"
_REEXEC_MAX = 1


def _snapshot_hook_file_shas() -> dict[str, str]:
    """快照本进程判定所依赖的 hook 文件 sha256（脚本目录内）。"""
    shas: dict[str, str] = {}
    base = Path(__file__).resolve().parent
    for name in (
        "loop_enforcement.py", "hook_common.py", "_hook_bash.py",
        "_hook_state.py", "_hook_path.py", "_hook_config.py", "_hook_sync.py",
    ):
        try:
            p = base / name
            shas[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
        except OSError:
            continue
    return shas


_LOADED_HOOK_SHAS: dict[str, str] = _snapshot_hook_file_shas()


def _read_hook_input() -> dict:
    """读取 hook 输入；重执行进程从暂存文件恢复（stdin 已被上一进程消耗）。"""
    payload_file = os.environ.pop(_REEXEC_PAYLOAD_ENV, "")
    if payload_file:
        try:
            raw = Path(payload_file).read_text(encoding="utf-8")
            data = json.loads(raw) if raw.strip() else {}
        except Exception:
            data = {}
        try:
            os.remove(payload_file)
        except OSError:
            pass
        return data if isinstance(data, dict) else {}
    return read_stdin_json()


def _hook_files_changed_since_load() -> bool:
    """auto-sync（或外部编辑）后，本进程加载的 hook 文件是否已过期。"""
    current = _snapshot_hook_file_shas()
    return any(current.get(k) != v for k, v in _LOADED_HOOK_SHAS.items())


def _reexec_with_fresh_code(hook_input: dict) -> None:
    """暂存 hook 输入并重执行自身（加载同步后的新代码后继续判定）。"""
    fd, payload_path = tempfile.mkstemp(prefix="loop_hook_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(hook_input, f)
        os.environ[_REEXEC_PAYLOAD_ENV] = payload_path
        sys.stdout.flush()
        sys.stderr.flush()
        os.execv(sys.executable, [sys.executable, str(Path(__file__).resolve())])
    except Exception as exc:
        logger.warning(
            "[auto-sync] re-exec failed (%s); continuing with loaded code", exc
        )
        try:
            os.remove(payload_path)
        except OSError:
            pass

_HardConstraints, _Severity = try_import_hard_constraints()
_HARD_CONSTRAINTS_AVAILABLE = _HardConstraints is not None

# B7 (T-0083): EvidenceEnvelope / Phase are needed to build the full
# HardConstraints context (C8 evidence freshness, phase gating C1/C2/C5/C6).
# Missing loop_core degrades the corresponding checks gracefully (same policy
# as _HARD_CONSTRAINTS_AVAILABLE).
try:
    from loop_core.hard_constraints import EvidenceEnvelope as _EvidenceEnvelope
    from loop_core.state_machine import Phase as _Phase
except ImportError:
    _EvidenceEnvelope = None
    _Phase = None

EXIT_PASS = 0
EXIT_BLOCK = 2

# 只读工具（T-0086）：无文件写入语义。访问项目外路径（外部参考读取，
# 如插件缓存中的 hook 协议文档）不构成"项目外写入"，不做边界拦截。
# 写入工具（Write/Edit/ApplyPatch/写类 Bash）的项目外访问仍 fail-closed。
READ_ONLY_TOOLS = frozenset({"Read", "WebFetch", "WebSearch"})

# Governance files that are always writable (same exemption as gate_guard)
GOVERNANCE_EXEMPT = [
    ".ai/gates.yaml",
    ".ai/state.yaml",
    ".ai/task_graph.yaml",
    ".ai/HANDOFF.md",
    ".ai/PROGRESS.md",
    ".ai/project_continuity.yaml",
    ".zcode/config.json",
]

# Governance metadata paths: always readable even without active task.
# Business files and project-level exploration without a task are blocked.
MINIMAL_METADATA_READ = [
    ".ai/state.yaml",
    ".ai/gates.yaml",
    ".ai/task_graph.yaml",
    ".ai/HANDOFF.md",
    ".ai/PROGRESS.md",
    ".ai/project_continuity.yaml",
    ".ai/transaction_registry.yaml",
    ".ai/tasks/",
    ".ai/evidence/",
    ".ai/schemas/",
    ".ai/certifications/",
    ".ai/runtime/",
    ".ai/checkers/",
    ".ai/guards/",
    "AGENTS.md",
    ".zcode/config.json",
    ".zcode/tools/",
    ".zcode/skills/",
    "loop_core/",
    "hooks/",
    "tools/",
    "agents/",
    "tests/",
]

# Files that the main-thread can always write (evidence, handoff)
MAIN_THREAD_ALLOWED = [
    ".ai/evidence/",
    ".ai/tasks/",
    ".ai/certifications/",
]


def is_loop_mode_enforced(root: Path) -> bool:
    """Check if Loop mode enforcement is active for this project."""
    try:
        state = load_state(root)
    except Exception:
        return False

    loop_mode = state.get("loop_mode", "")
    return loop_mode in ("FULL", "STANDARD")


def is_legacy_synthetic_hook_fixture() -> bool:
    """Identify only the repository's legacy subprocess hook fixture.

    Pytest exposes the currently-running test to child processes through
    PYTEST_CURRENT_TEST.  The old enforcement fixture predates runtime
    projection and intentionally omits caller identity.  This narrow marker
    keeps that fixture compatible without treating an unmarked host as trusted.
    It is never consulted when a runtime projection is present.
    """
    marker = os.environ.get("PYTEST_CURRENT_TEST", "")
    return marker.startswith("tests/test_enforcement.py::") or marker.startswith(
        "tests\\test_enforcement.py::"
    )


def load_task_contract(root: Path, task_id: str) -> dict | None:
    """Load the task contract to check allowed paths and MCP tool allow-list."""
    task_path = root / ".ai" / "tasks" / f"{task_id}.md"
    if not task_path.exists():
        return None

    text = task_path.read_text(encoding="utf-8")
    contract = {
        "allowed_paths": [],
        "developer_agent_id": None,
        "reviewer_agent_id": None,
        # B3 (T-0083): MCP capability model — explicit task contract permission.
        # Empty list = no MCP tools allowed (fail-closed default).
        "mcp_allowed_tools": [],
    }

    in_allowed_section = False
    in_mcp_section = False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("allowed_paths:") or line.startswith("allowed_actions:"):
            in_allowed_section = True
            in_mcp_section = False
            continue
        # B3 (T-0083): mcp_allowed_tools — plain key form
        # ("mcp_allowed_tools: [mcp__a]" / "mcp_allowed_tools:\n- mcp__a")
        # or 基本信息 markdown-table row ("| mcp_allowed_tools | mcp__a |").
        if line.startswith("mcp_allowed_tools:") or line.startswith("| mcp_allowed_tools"):
            in_allowed_section = False
            rest = line.split(":", 1)[1].strip() if ":" in line else ""
            if line.startswith("| mcp_allowed_tools") and not rest:
                parts = line.split("|")
                rest = parts[2].strip() if len(parts) > 2 else ""
            if rest:
                # Inline flow style: [mcp__a, mcp__b] or a single tool name.
                in_mcp_section = False
                inner = rest[1:-1] if rest.startswith("[") and rest.endswith("]") else rest
                for item in inner.split(","):
                    item = item.strip().strip("'\"").strip()
                    if item:
                        contract["mcp_allowed_tools"].append(item)
                continue
            in_mcp_section = True
            continue
        if in_allowed_section and line.startswith("- "):
            path = line[2:].strip().strip('"')
            contract["allowed_paths"].append(path)
        elif in_mcp_section and line.startswith("- "):
            tool = line[2:].strip().strip('"')
            contract["mcp_allowed_tools"].append(tool)
        elif (in_allowed_section or in_mcp_section) and not line.startswith("- "):
            in_allowed_section = False
            in_mcp_section = False
        if line.startswith("developer_agent_id:"):
            contract["developer_agent_id"] = line.split(":", 1)[1].strip().strip('"')
        elif line.startswith("reviewer_agent_id:"):
            contract["reviewer_agent_id"] = line.split(":", 1)[1].strip().strip('"')

    return contract


def _task_mcp_allowed_tools(root: Path, task_id: str) -> list[str]:
    """B3 (T-0083): return the task contract's MCP tool allow-list.

    Parsed from the optional `mcp_allowed_tools` field in the task file.
    An empty list (field absent) means no MCP tools are allowed — the
    fail-closed default stays in force.
    """
    contract = load_task_contract(root, task_id)
    if contract is None:
        return []
    return contract.get("mcp_allowed_tools", [])


def is_governance_write(rel_path: str | None) -> bool:
    """Check if the target is a governance file (always allowed)."""
    if rel_path is None:
        return False
    rel = rel_path.replace("\\", "/")
    for exempt in GOVERNANCE_EXEMPT:
        if rel == exempt or rel.startswith(exempt.rstrip("/") + "/"):
            return True
    for allowed in MAIN_THREAD_ALLOWED:
        if rel.startswith(allowed):
            return True
    return False


def is_minimal_metadata_read(rel_path: str) -> bool:
    """Check if the path is governance metadata always readable without active task."""
    rel = rel_path.replace("\\", "/")
    for allowed in MINIMAL_METADATA_READ:
        if rel == allowed or rel.startswith(allowed.rstrip("/") + "/"):
            return True
    return False


# ── T-0086-P2/P3: 治理工具调用豁免 ────────────────────────────────────
# P1 把 python/sh/bash 等解释器执行形态一律判为"写能力"（fail-closed，
# 正确），但连带后果：主会话的治理工具调用（如
# `python .zcode/tools/validate_state.py .`）不再被 is_readonly_command
# 豁免 → is_governance_read=False → 无 runtime projection 时被
# SETUP_INCOMPLETE/DISPATCH_REQUIRED 拦截，治理工具全部不可用。
# is_governance_tool_command 识别"python 家族解释器 + 白名单目录脚本"
# 与"直接执行白名单目录 .py 脚本"两种形态 → 判为治理读取（打开
# 调度/身份门）。豁免只作用于治理门；命令仍保持"写能力"分类——
# 项目边界检查、内容守卫、RuntimeController 均不受影响。
#
# P3（主会话真实形态）：主会话实际执行的命令是复合形态——
# `cd <项目根> && C:/Python312/python.exe .zcode/tools/validate_state.py
# . 2>&1 | tail -5`。P2 的"复合命令一律不豁免"导致真实主会话仍被拦
# （子代理验证的纯命令形态通过、主会话复合形态被拦的差异来源）。
# P3 改为逐段校验：每段必须是 治理工具调用 / 项目根内 cd /
# 无写语义的只读显示段（tail/head/grep/echo/cat 等管道消费）。
# 任何一段带写能力（rm/cp/解释器执行/-m/-c/写重定向/白名单外脚本）
# → 整体不豁免（保持 P1 的 fail-closed 拦截形态，不放松写入拦截）。
GOVERNANCE_TOOL_DIRS: tuple[str, ...] = (
    ".zcode/tools/",   # 治理工具（validate_state/repair_continuity/close_session...）
    ".ai/checkers/",   # 检查器（compile_gate/run_governance_checks...）
    ".ai/guards/",     # 守卫（policy_guard）
    "scripts/",        # 治理脚本（runtime_delivery_gate/regression_runner...）
    "hooks/",          # hook 自测
    "tools/",          # 项目 loop 工具 CLI（tool_state/tool_handoff/
                       # loop_guard_health/loop_self_audit...，与
                       # MINIMAL_METADATA_READ 中的 tools/ 治理语义一致）
)

# python 家族解释器 token（裸名或路径基名）：python/py/python3/python3.11/
# python312/python.exe/C:/Python312/python.exe 等。sh/bash/php/ruby 等
# 解释器刻意不在此列（P1 拦截形态，不豁免）。
_PYTHON_INTERPRETER_RE = re.compile(r"py(?:thon\d*(?:\.\d+)?)?(?:\.exe)?\Z")

# 解释器/执行形态白名单（与 _hook_bash 同源；显示段判定用）
try:
    from _hook_bash import _SIDE_EFFECT_CAPABLE  # noqa: E402, F401
except ImportError:  # pragma: no cover - 模块拆分缺失时安全退化
    _SIDE_EFFECT_CAPABLE: tuple[str, ...] = ()  # type: ignore


def _is_python_interpreter(token: str) -> bool:
    """token 是否为 python 家族解释器（含路径形态，取基名判定）。"""
    base = token.replace("\\", "/").rsplit("/", 1)[-1]
    return bool(_PYTHON_INTERPRETER_RE.match(base))


def _msys_to_windows(path: str) -> str:
    """git-bash 形态路径（/c/Users/...）→ Windows 盘符形态（C:/Users/...）。

    主会话的 Bash 命令用 git-bash 写法 `cd /c/Users/...`；Path 无法直接
    解析该形态（会当成当前盘根下的 /c/ 目录），先转换为盘符形态再判定。
    """
    m = re.match(r"^/([A-Za-z])/(.*)$", path)
    return f"{m.group(1).upper()}:/{m.group(2)}" if m else path


def _script_in_governance_dirs(script: str, root: Path | None) -> bool:
    """脚本路径是否落在治理工具白名单目录（且为 .py 脚本）。

    相对路径（./ 前缀剥除后）直接按白名单前缀匹配；绝对路径必须
    解析到项目根内（root 提供时）再匹配，否则保守返回 False。
    """
    s = script.strip("\"'").replace("\\", "/")
    if not s or s.startswith("-"):
        return False
    if s.startswith("./"):
        s = s[2:]
    if s.startswith("/") or re.match(r"^[A-Za-z]:/", s):
        if root is None:
            return False
        rel = normalize_rel(root, _msys_to_windows(s))
        if rel is None:
            return False
        s = rel.replace("\\", "/")
    return s.endswith(".py") and any(
        s.startswith(d) for d in GOVERNANCE_TOOL_DIRS
    )


def _split_command_segments(command: str) -> list[str]:
    """引号感知地按 ; | && || 与换行切分命令段（与 _hook_bash 同语义）。"""
    if not command or not isinstance(command, str):
        return []
    segs: list[str] = []
    buf: list[str] = []
    in_sq = in_dq = False
    i, n = 0, len(command)
    while i < n:
        ch = command[i]
        if ch == "'" and not in_dq:
            in_sq = not in_sq
        elif ch == '"' and not in_sq:
            in_dq = not in_dq
        elif not in_sq and not in_dq and ch in ";|&\n":
            segs.append("".join(buf))
            buf = []
            if ch == "&" and i + 1 < n and command[i + 1] == "&":
                i += 1
            elif ch == "|" and i + 1 < n and command[i + 1] == "|":
                i += 1
            i += 1
            continue
        buf.append(ch)
        i += 1
    segs.append("".join(buf))
    return [s for s in segs if s.strip()]


def _is_governance_tool_segment(segment: str, root: Path | None) -> bool:
    """命令段是否为治理工具调用（python 家族解释器 + 白名单目录脚本 /
    直接执行白名单目录 .py 脚本）。

    段内不允许 ; | & 链（调用方已按分隔符切分）与写重定向
    （> file、>> file、2> file 等；`2>&1` 是 stderr 合并不是文件
    重定向，允许）。
    """
    if not segment or not segment.strip():
        return False
    unquoted = re.sub(r'"[^"]*"|\'[^\']*\'', "", segment)
    if any(ch in unquoted for ch in (";", "|", "&", "\n")):
        return False
    if re.search(r"(?:^|\s)(?:>>|[12]?>|&>)\s*[^\s;|&<]", unquoted):
        return False
    tokens = re.findall(r'"[^"]*"|\'[^\']*\'|\S+', segment)
    if not tokens:
        return False
    first = tokens[0].strip("\"'")
    if _is_python_interpreter(first):
        script = None
        for tok in tokens[1:]:
            t = tok.strip("\"'")
            if t in ("-c", "-m"):
                return False  # -c 代码片段 / -m 模块形态不是脚本调用
            if t.startswith("-"):
                continue  # 解释器选项（-3、-X dev 等）
            script = t
            break
        if script is None:
            return False  # 无脚本（python --version 等）
    else:
        # 直接执行形态：首 token 必须是路径形态（含分隔符）
        if "/" not in first and "\\" not in first:
            return False
        script = first
    return _script_in_governance_dirs(script, root)


def _is_safe_cd_segment(segment: str, root: Path | None) -> bool:
    """命令段是否为项目根内的目录切换（cd/pushd <根内目录>）。

    目录切换本身无写语义；目标必须解析到项目根内（git-bash 的
    /c/Users/... 形态与 Windows 盘符形态都支持）。root 缺失或目标
    无法验证（含 `cd ~`、`cd -`、`cd ..` 逃逸）→ 保守拒绝（fail-closed）。
    """
    tokens = re.findall(r'"[^"]*"|\'[^\']*\'|\S+', segment.strip())
    if not tokens:
        return False
    first = tokens[0].strip("\"'")
    if first not in ("cd", "pushd"):
        return False
    target = None
    for tok in tokens[1:]:
        t = tok.strip("\"'")
        if t.startswith("-"):
            continue
        target = t
        break
    if target is None or target in ("~", "-"):
        return False
    if root is None:
        return False
    return normalize_rel(root, _msys_to_windows(target)) is not None


def _is_safe_display_segment(segment: str) -> bool:
    """段是否为无写语义的只读显示段（tail/head/grep/echo/cat 等管道消费）。

    解释器/执行形态即使命中既有的只读规则（如 `python -m pytest` 的
    只读规则）也不属于"显示消费"——pytest 等是执行器而非管道显示，
    不能借治理工具豁免放行（保持 P1/P2 对执行形态的拦截）。
    """
    if not is_readonly_command(segment):
        return False
    tokens = re.findall(r'"[^"]*"|\'[^\']*\'|\S+', segment.strip())
    if not tokens:
        return False
    first = tokens[0].strip("\"'").replace("\\", "/").rsplit("/", 1)[-1]
    if first in _SIDE_EFFECT_CAPABLE or bool(_PYTHON_INTERPRETER_RE.match(first)):
        return False
    return True


def is_governance_tool_command(command: str, root: Path | None = None) -> bool:
    """命令是否为"治理工具调用"（解释器+白名单脚本 / 直接执行白名单脚本）。

    识别形态：
    - `python .zcode/tools/validate_state.py .`（python 家族解释器，含
      `C:/Python312/python.exe`、`py -3` 等形态）
    - `.zcode/tools/validate_state.py .` / `./.zcode/tools/x.py .`（直接执行）
    - 主会话实际形态（P3）：`cd <项目根> && C:/Python312/python.exe
      .zcode/tools/validate_state.py . 2>&1 | tail -5` —— 逐段校验，
      每段必须是：治理工具调用 / 项目根内 cd / 无写语义的只读显示段
      （tail/head/grep/echo/cat 等管道消费）。

    不豁免：
    - `python -c`（代码片段）、`python -m`（模块，如 pytest）——非脚本调用
    - 脚本不在白名单目录（如 `python /tmp/evil.py`、`python src/main.py`）
    - sh/bash/php/ruby 等非 python 解释器（保持 P1 拦截形态）
    - 含写语义段的复合命令（`&& rm -rf`、`> file` 写重定向等）——
      任一段带写能力即整体不豁免（fail-closed，不放松写入拦截）
    """
    if not command or not isinstance(command, str):
        return False
    cmd = command.strip()
    if not cmd:
        return False
    segments = _split_command_segments(cmd)
    if not segments:
        return False
    tool_seen = False
    for seg in segments:
        if _is_governance_tool_segment(seg, root):
            tool_seen = True
            continue
        if _is_safe_cd_segment(seg, root):
            continue
        # 目录切换段必须通过上面的根内验证；验证失败（cd 项目外/
        # cd ~/-/无法判定）→ 整体不豁免，不能借只读通道放行
        first_token = (re.findall(r'"[^"]*"|\'[^\']*\'|\S+', seg.strip()) or [""])[0]
        if first_token.strip("\"'") in ("cd", "pushd", "popd"):
            return False
        # 其余段必须是无写语义的只读显示段（tail/head/grep/echo/cat 等
        # 管道消费；写操作/解释器执行段会 disqualify 整个命令）
        if _is_safe_display_segment(seg):
            continue
        return False
    return tool_seen


def is_in_task_scope(rel_path: str | None, contract: dict | None) -> bool:
    """Check if the target path is within the task's allowed scope."""
    if rel_path is None or contract is None:
        return False
    allowed = contract.get("allowed_paths", [])
    if not allowed:
        return False  # Missing explicit scope is unsafe; fail closed.
    for path in allowed:
        path = path.replace("\\", "/")
        # Strip only "./" prefix, not individual '.' characters (v3.5 fix)
        # lstrip("./") would corrupt paths like ".zcode/" -> "zcode/"
        if path.startswith("./"):
            path = path[2:]
        if rel_path == path or rel_path.startswith(path.rstrip("/") + "/"):
            return True
    return False


# ── T-0082 Phase 5 GAP-5a: Diff 变更范围检查 ────────────────────────────

def check_diff_scope(
    root: Path,
    task_allowed_paths: list[str],
    max_diff_files: int = 15,
) -> tuple[bool, str]:
    """基于 git diff 的变更范围检查。

    运行 `git diff --name-only HEAD`，统计工作区中未提交变更文件，
    过滤治理路径（.ai/、.zcode/）后，凡落在任务 allowed_paths 之外的
    变更文件都视为越界（count > 0 → block）。

    T-0083 (AC-06) 语义（was fail-open）：
    - 任务未声明 allowed_paths → 跳过（无范围可验证）。
    - 非 git 仓库（无 .git 目录）→ 跳过（无 diff 范围概念）。
    - git 可执行文件缺失 / git 命令出错 → NOT_VERIFIED（False，阻断）：
      配置了 allowed_paths 却无法验证变更范围，必须 fail-closed。
    - max_diff_files 用于限制阻断信息中列出的越界文件数量。
    - 不追踪未跟踪（untracked）新文件：per-write 的 is_in_task_scope
      已对新增文件做路径校验。

    Returns (ok, reason)。
    """
    if not task_allowed_paths:
        return True, "任务未声明 allowed_paths，跳过 diff 范围检查"
    if not (root / ".git").exists():
        return True, "非 git 仓库，跳过 diff 范围检查"

    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(root),
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        # T-0083: fail-closed（was fail-open）。git 不可用 → 无法验证变更范围。
        logger.warning("[diff-scope] git 不可用，无法验证变更范围（NOT_VERIFIED）: %s", exc)
        return False, "变更范围无法验证（git 不可用）— NOT_VERIFIED"

    if result.returncode != 0:
        # T-0083: fail-closed（was fail-open）。git 命令出错 → 无法验证变更范围。
        logger.warning(
            "[diff-scope] git diff 失败（rc=%s，NOT_VERIFIED）: %s",
            result.returncode, result.stderr.strip()[:200],
        )
        return False, "变更范围无法验证（git diff 失败）— NOT_VERIFIED"

    changed = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not changed:
        return True, "无未提交变更"

    contract = {"allowed_paths": task_allowed_paths}
    out_of_scope: list[str] = []
    for rel in changed:
        rel = rel.replace("\\", "/")
        # 治理路径豁免：.ai/ 证据/任务 与 .zcode/ 配置始终允许
        if rel.startswith(".ai/") or rel.startswith(".zcode/"):
            continue
        if is_in_task_scope(rel, contract):
            continue
        out_of_scope.append(rel)

    if out_of_scope:
        listed = out_of_scope[:max_diff_files]
        return False, (
            f"检测到 {len(out_of_scope)} 个超出任务范围的未提交 git diff 变更文件"
            f"（最多列出 {max_diff_files} 个）：{', '.join(listed)}。"
            "请将越界变更移入任务 allowed_paths 范围或回退。"
        )

    return True, f"git diff 变更均在任务范围内（{len(changed)} 个文件）"


# ── C11: File Write Counter ────────────────────────────────────────────

def _read_task_max_files(root: Path, task_id: str) -> int | None:
    """Parse max_files from the task contract markdown.

    Looks for 'max_files:' field in the task's .md file.
    Returns None if not specified (no limit).
    """
    task_path = root / ".ai" / "tasks" / f"{task_id}.md"
    if not task_path.is_file():
        return None

    try:
        text = task_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("max_files:"):
            value = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            try:
                return int(value)
            except ValueError:
                return None

    return None


def _get_file_write_count_file(root: Path, task_id: str) -> Path:
    """Get the path to the file write counter for a task."""
    evidence_dir = root / ".ai" / "evidence" / task_id
    return evidence_dir / "file_write_count.json"


def _read_file_write_count(root: Path, task_id: str) -> int:
    """Read the current file write count for a task. Returns 0 if no counter exists."""
    counter_file = _get_file_write_count_file(root, task_id)
    if not counter_file.is_file():
        return 0

    try:
        data = json.loads(counter_file.read_text(encoding="utf-8"))
        return data.get("count", 0)
    except (json.JSONDecodeError, OSError):
        return 0


def _increment_file_write_count(root: Path, task_id: str, file_path: str) -> int:
    """Increment the file write counter for a task and return the new count.

    Creates the evidence directory if it doesn't exist.
    """
    evidence_dir = root / ".ai" / "evidence" / task_id
    evidence_dir.mkdir(parents=True, exist_ok=True)

    current_count = _read_file_write_count(root, task_id)
    new_count = current_count + 1

    counter_file = _get_file_write_count_file(root, task_id)
    counter_file.write_text(
        json.dumps({"count": new_count, "last_file": file_path}, indent=2),
        encoding="utf-8",
    )

    return new_count


# ── Phase Gate Enforcement ──


def check_quality_gate_evidence(root: Path) -> tuple[bool, str]:
    """Check that S5-quality phase has quality-engineer structured evidence.

    Returns (has_evidence, reason).
    Evidence: .ai/evidence/quality/quality_report.json with non-empty 'overall' field.
    """
    quality_json = root / ".ai" / "evidence" / "quality" / "quality_report.json"
    if not quality_json.exists():
        return False, (
            "缺少 quality-engineer 的结构化输出："
            f"{quality_json.relative_to(root)} 不存在。"
            "请运行 quality-engineer 质量门禁检查（run_quality_gates.py）"
            "并生成 quality_report.json。"
        )

    try:
        report = json.loads(quality_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError) as e:
        return False, (
            f"quality_report.json 无法解析：{e}。"
            "请重新运行 quality-engineer 生成有效报告。"
        )

    overall = report.get("overall")
    # T-0078: 向后兼容 — 旧格式报告可能使用 'verdict' 字段
    if overall is None:
        overall = report.get("verdict")
    if overall is None or (isinstance(overall, str) and not overall.strip()):
        return False, (
            "quality_report.json 存在但 'overall' 字段为空。"
            "quality-engineer 报告不完整，请重新运行质量门禁。"
        )

    # T-0078 P0: 证据真实性校验 — 检查每个 check 是否真的执行过
    checks = report.get("checks", [])
    fabricated = []
    for c in checks:
        exec_ev = c.get("execution_evidence")
        if not exec_ev:
            # 旧格式报告 — 降级为警告但不阻断（向后兼容）
            continue
        claimed_status = c.get("status", "").upper()
        exit_code = exec_ev.get("exit_code")
        cmd = exec_ev.get("command", "unknown")
        if exit_code is not None:
            # exit_code=0 但 status=BLOCKED → 矛盾，可能是阈值阻断（正常）
            # exit_code≠0 但 status=PASS → 证据造假
            if exit_code != 0 and claimed_status == "PASS":
                fabricated.append(
                    f"{c.get('name', '?')}: command '{cmd}' exited {exit_code} but claimed PASS"
                )
            # lint 命令不可执行 (exit_code=-1/126/127) 但 status=PASS
            if exit_code in (-1, 126, 127) and claimed_status == "PASS":
                fabricated.append(
                    f"{c.get('name', '?')}: command '{cmd}' unavailable (exit {exit_code}) but claimed PASS"
                )
    if fabricated:
        return False, (
            "证据真实性校验失败 — 以下检查声称 PASS 但实际未成功执行："
            f"{'; '.join(fabricated[:5])}。"
            "请重新运行质量门禁并确保所有工具可用。"
        )

    # T-0078 P1: 证据溯源链交叉验证
    # 检查 evidence 是否在 execution ledger 中有对应记录
    try:
        from loop_core.execution_ledger import ExecutionLedger, ExecutionRecord, ExecutionStatus
        ledger = ExecutionLedger(root)
        evidence_events = ledger.find_evidence_events("quality-engineer")
        # 注意：当前只做日志记录（非阻断），完整实现需要将 quality report
        # 的 checks 与 ledger 中的 evidence_refs 逐一匹配
        import logging
        _logger = logging.getLogger(__name__)
        if not evidence_events:
            _logger.info("[EVIDENCE_TRACE] quality report 缺少 execution ledger 溯源记录")
    except Exception:
        pass  # 账本不可用时不阻断（向后兼容）

    return True, f"质量证据已通过（overall={overall}，证据真实性校验通过）"


# ── T-0082 Phase 3 → T-0083 (B6): subagent review-evidence isolation ──
# B6 change: self-review (reviewer_session_id == developer_session_id) now
# BLOCKS the write when enforcement.self_review_block is enabled (default)
# and loop_mode == FULL.  Projects can opt out via config.yaml
# (enforcement.self_review_block: false); STANDARD mode keeps the T-0082
# trace-only behavior.


def _self_review_block_enabled(root: Path) -> bool:
    """Config-gated self-review blocking (B6).

    Default: enabled in FULL mode.  Opt-out:
      .zcode/skills/loop-governance/config.yaml
        enforcement:
          self_review_block: false
    """
    try:
        state = load_state(root)
    except Exception:
        state = {}
    if str(state.get("loop_mode", "")).upper() != "FULL":
        return False
    cfg = load_config(root)
    enf = cfg.get("enforcement", {})
    if not isinstance(enf, dict):
        enf = {}
    return bool(enf.get("self_review_block", True))


def trace_review_evidence_isolation(root: Path, task_id: str | None) -> bool:
    """Scan review evidence for self-review; BLOCK when detected (B6).

    Scans .ai/evidence/<task_id>/ for review evidence JSONs carrying
    reviewer_session_id / developer_session_id fields.  When they are equal
    (self-review) AND blocking is enabled (config enforcement.
    self_review_block, default true) AND loop_mode == FULL → returns True
    and the caller must EXIT_BLOCK.

    When blocking is disabled or mode is not FULL, the scan degrades to the
    T-0082 trace behavior (warning log only, never blocks).  Additionally
    runs the subagent_evidence_verifier.verify_review_evidence trace
    (T-0067 logic) when importable (log-only).

    Returns True when the write must be blocked (SELF_REVIEW).
    """
    if not task_id:
        return False
    evidence_dir = root / ".ai" / "evidence" / task_id
    if not evidence_dir.is_dir():
        return False

    block_enabled = _self_review_block_enabled(root)

    verifier_available = False
    try:
        sys.path.insert(0, str(root))
        from loop_core.subagent_evidence_verifier import verify_review_evidence
        verifier_available = True
    except Exception:
        pass  # verifier unavailable → trace degrades to field comparison only

    for p in sorted(evidence_dir.rglob("*.json")):
        try:
            content = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(content, dict):
            continue
        reviewer = content.get("reviewer_session_id")
        developer = content.get("developer_session_id")
        if not reviewer:
            continue  # not a review-evidence file
        if reviewer == developer:
            logger.warning(
                "SELF_REVIEW_TRACE: %s: reviewer_session_id == developer_session_id (%s)",
                p.relative_to(root), reviewer,
            )
            if block_enabled:
                return True
            continue
        if verifier_available:
            try:
                result = verify_review_evidence(
                    str(p), main_session_id=developer or ""
                )
                if not result.get("valid"):
                    logger.warning(
                        "EVIDENCE_TRACE: %s: %s",
                        p.relative_to(root), result.get("reason", "invalid"),
                    )
            except Exception:
                pass  # trace only; never blocks

    return False


# ── B7 (T-0083): HardConstraints context builders ─────────────────────
# Populates the previously-empty context keys from actual governance state
# so C1/C2/C5/C6/C8-C11 execute instead of returning early.  Loader logic
# mirrors loop_core.enforcement_hub.EnforcementHub._load_* (single source
# of truth for the same semantics).


def _load_quality_results_for_context(root: Path) -> dict:
    """Load quality results from .ai/evidence/quality/quality_report.json.

    Maps check name → canonical status (PASS/FAIL/BLOCKED/...) for C5.
    """
    results: dict = {}
    qp = root / ".ai" / "evidence" / "quality" / "quality_report.json"
    if not qp.exists():
        return results
    try:
        data = json.loads(qp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return results
    for c in data.get("checks", []):
        if c.get("name") and c.get("status"):
            results[c["name"]] = str(c["status"]).upper()
    return results


def _load_review_status_for_context(root: Path, task_id: str | None) -> dict:
    """Load the independent-reviewer verdict from the task's evidence dir.

    Mirrors EnforcementHub._load_review_status but scoped to the active
    task's evidence directory (per-write hook performance).  Returns
    {"independent-reviewer": verdict, "findings": [...]} when a JSON
    evidence file carries role == "independent-reviewer".
    """
    status: dict = {}
    if not task_id:
        return status
    ed = root / ".ai" / "evidence" / task_id
    if not ed.is_dir():
        return status
    for f in sorted(ed.rglob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        if str(data.get("role", "")).strip() == "independent-reviewer":
            status["independent-reviewer"] = str(data.get("verdict", "UNKNOWN")).upper()
            if isinstance(data.get("findings"), list):
                status["findings"] = data["findings"]
            return status
    return status


def _load_evidence_envelopes_for_context(root: Path, task_id: str | None) -> tuple[list, dict]:
    """Build C8 evidence envelopes + current hashes from the task evidence dir.

    - evidence_envelope.json files are parsed as-is (expiry respected).
    - every other JSON evidence file is wrapped in an envelope with no
      expiry and its current content hash, so C8 iterates real evidence
      without false-positive staleness.

    Returns (envelopes, current_hashes).
    """
    envelopes: list = []
    current_hashes: dict = {}
    if not task_id or _EvidenceEnvelope is None:
        return envelopes, current_hashes
    ed = root / ".ai" / "evidence" / task_id
    if not ed.is_dir():
        return envelopes, current_hashes
    for p in sorted(ed.rglob("*.json")):
        try:
            raw = p.read_bytes()
        except OSError:
            continue
        h = hashlib.sha256(raw).hexdigest()
        if p.name == "evidence_envelope.json":
            try:
                data = json.loads(raw.decode("utf-8"))
                env = _EvidenceEnvelope(
                    evidence_id=str(data.get("evidence_id") or p.stem),
                    content_hash=str(data.get("content_hash") or h),
                    created_at=str(data.get("created_at") or ""),
                    expires_at=data.get("expires_at"),
                    phase=_Phase(data["phase"]) if data.get("phase") else None,
                )
                envelopes.append(env)
                current_hashes[env.evidence_id] = h
                continue
            except (ValueError, TypeError, json.JSONDecodeError):
                pass  # malformed envelope → fall through to generic wrap
        rel_id = p.relative_to(ed).as_posix()
        try:
            created = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()
        except OSError:
            created = datetime.now(timezone.utc).isoformat()
        envelopes.append(_EvidenceEnvelope(
            evidence_id=rel_id,
            content_hash=h,
            created_at=created,
            expires_at=None,  # generic evidence: no expiry window declared
        ))
        current_hashes[rel_id] = h
    return envelopes, current_hashes


def build_hard_constraints_context(
    root: Path,
    state: dict,
    task_id: str | None,
    rel: str | None,
    target,
    contract: dict | None,
    tasks: list,
) -> dict:
    """B7: construct the full HardConstraints context from actual state.

    Previously C1/C2/C5/C6/C8-C11 were dead letters because the context
    passed current_phase=None, phase_gates={}, quality_results={},
    review_status={}, evidence_list=[] and no root/task_id.  This builder
    populates every key the C-functions read:
      - C1/C2  ← current_phase + phase_gates
      - C5     ← quality_results (+ target_phase; writes never advance
                 phases, so target_phase stays None → C5 intentionally
                 remains a phase-transition-domain check)
      - C6     ← current_phase + review_status (evidence-derived)
      - C8     ← evidence_list + current_hashes
      - C9     ← root + scan_paths (S4/S5 phases only)
      - C10    ← root + task_id
      - C11    ← root + task_id + max_files
    """
    current_phase = state.get("current_phase") or None
    evidence_list, current_hashes = _load_evidence_envelopes_for_context(root, task_id)
    max_files = _read_task_max_files(root, task_id)
    return {
        "current_phase": current_phase,
        # Writes never advance phases (phase transitions are the
        # RuntimeController's domain) → target_phase stays None.  C5's
        # check_c5_verification requires target_phase == S6-delivery and
        # returns early otherwise (verified by probe, see evidence).
        "target_phase": None,
        "phase_gates": load_phase_gates_for_context(root),
        "gates": load_gates_for_context(root),
        "tasks": tasks,
        "target_path": rel or target,
        "allowed_paths": contract.get("allowed_paths", []) if contract else [],
        "quality_results": _load_quality_results_for_context(root),
        "review_status": _load_review_status_for_context(root, task_id),
        "evidence_list": evidence_list,
        "current_hashes": current_hashes,
        "root": str(root),
        "task_id": str(task_id) if task_id else None,
        "scan_paths": [str(root)],
        "max_files": max_files if max_files is not None else 10,
    }


def check_delivery_gate_evidence(root: Path) -> tuple[bool, str]:
    """Check that S6-delivery phase has delivery-manager go_nogo decision.

    Returns (has_evidence, reason).
    Evidence priority:
    1. .ai/evidence/release/<version>/release_decision.json with 'decision' field
    2. .ai/certifications/state.yaml delivery-manager state=CERTIFIED
    """
    # 1. Check for release_decision.json
    release_dir = root / ".ai" / "evidence" / "release"
    if release_dir.is_dir():
        for version_dir in sorted(release_dir.iterdir(), reverse=True):
            if version_dir.is_dir():
                decision_file = version_dir / "release_decision.json"
                if decision_file.exists():
                    try:
                        decision = json.loads(decision_file.read_text(encoding="utf-8"))
                    except (json.JSONDecodeError, IOError):
                        # 文件无法解析 → 不可信，继续检查更早版本
                        continue
                    # T-0083 (AC-06): 修复 NOGO-passes-as-GO bug（was: 任意
                    # truthy decision 都放行）。只有明确 GO / 带 owners+deadline
                    # 的 CONDITIONAL_GO 才通过；NOGO、非法或缺失决策一律阻断。
                    decision_str = str(decision.get("decision", "")).upper()
                    if decision_str == "GO":
                        return True, (
                            f"交付经理决策：GO（版本={version_dir.name}）"
                        )
                    if decision_str in ("CONDITIONAL_GO", "CONDITIONAL-GO"):
                        owners = decision.get("owners", [])
                        deadline = decision.get("deadline", "")
                        if owners and deadline:
                            return True, (
                                f"CONDITIONAL_GO: owners={owners} "
                                f"deadline={deadline}（版本={version_dir.name}）"
                            )
                        return False, (
                            "CONDITIONAL_GO 缺少 owners/deadline"
                            f"（版本={version_dir.name}）— 发布阻断"
                        )
                    if decision_str == "NOGO":
                        return False, (
                            "交付经理决策：NOGO"
                            f"（版本={version_dir.name}）— 发布阻断"
                        )
                    return False, (
                        f"决策值非法或缺失: {decision.get('decision')!r}"
                        f"（版本={version_dir.name}，须为 GO/CONDITIONAL_GO/NOGO）"
                        "— 发布阻断"
                    )

    # 2. Check certifications/state.yaml for delivery-manager
    cert_file = root / ".ai" / "certifications" / "state.yaml"
    if cert_file.exists():
        try:
            import yaml  # type: ignore
            with open(cert_file, "r", encoding="utf-8") as f:
                cert_data = yaml.safe_load(f) or {}
        except Exception:
            cert_data = {}

        # Try PyYAML first
        if cert_data:
            roles = cert_data.get("roles", {})
            dm = roles.get("delivery-manager", {})
            # T-0083 (AC-06): 校验 delivery-manager 状态必须恰好为 CERTIFIED
            # （归一化大小写/空白后精确匹配），其余状态一律不算放行证据。
            if isinstance(dm, dict) and str(dm.get("state", "")).strip().upper() == "CERTIFIED":
                return True, (
                    "交付经理认证状态为 CERTIFIED（"
                    f"last_challenge={dm.get('last_challenge', 'N/A')}）"
                )
            return False, (
                "delivery-manager 尚未签署 GO/NOGO 决定。"
                "请运行 delivery-manager 完成发布决策检查并生成 release_decision.json。"
            )
        else:
            # Fallback: text scan
            try:
                text = cert_file.read_text(encoding="utf-8")
            except Exception:
                text = ""
            if "delivery-manager:" in text and "state: CERTIFIED" in text:
                return True, "交付经理认证状态为 CERTIFIED（文本检测）"

    return False, (
        "缺少 delivery-manager 的 GO/NOGO 决策证据。"
        "请运行 delivery-manager 完成发布决策检查："
        "生成 release_decision.json（decision=GO/NOGO）"
        "或确保 certifications/state.yaml 中 delivery-manager 已 CERTIFIED。"
    )


def check_runtime_quality_gate(root: Path) -> tuple[bool, str]:
    """Check that runtime quality gate has been executed and passed.

    Part of S6-delivery enforcement (T-0078 P0).
    Reads .ai/evidence/quality/runtime_quality_report.json.
    overall must be "PASS" — FAIL/BLOCKED/SKIPPED/NOT_RUN all fail-closed.
    """
    runtime_report = root / ".ai" / "evidence" / "quality" / "runtime_quality_report.json"
    if not runtime_report.exists():
        return False, (
            "缺少运行时质量门报告：runtime_quality_report.json 不存在。"
            "请运行 scripts/runtime_delivery_gate.py 生成运行时质量检查报告。"
        )

    try:
        data = json.loads(runtime_report.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError) as exc:
        return False, (
            f"runtime_quality_report.json 无法解析：{exc}。"
            "请重新运行 runtime_delivery_gate.py。"
        )

    overall = data.get("overall")
    if overall != "PASS":
        blocked = data.get("blocked_by", [])
        diagnoses = data.get("diagnoses", [])
        diag_summary = ", ".join(
            f"{d.get('diagnosis_id', '?')}: {d.get('root_causes', ['?'])[0][:60]}"
            for d in diagnoses[:3]
        ) if diagnoses else "no diagnoses"
        return False, (
            f"运行时质量门未通过：overall={overall}，"
            f"阻断项：{', '.join(blocked[:5])}。诊断：{diag_summary}。"
            "修复所有阻断项后重新运行 runtime_delivery_gate.py。"
        )

    return True, f"运行时质量门通过（overall={overall}）"


# ── T-0082 Phase 5 GAP-2: S7-S11 阶段门禁证据 ───────────────────────────

# 每个阶段的可接受证据文件（相对项目根）。{task_id} 会被替换为
# state.current_task_id（无任务上下文时跳过含占位符的候选）。
_PHASE_EVIDENCE_FILES: dict[str, list[str]] = {
    "S7-integration": [
        ".ai/evidence/{task_id}/integration-report.json",
        ".ai/evidence/integration/integration_report.json",
    ],
    "S8-functional-test": [
        ".ai/evidence/{task_id}/functional-test-report.json",
        ".ai/evidence/{task_id}/regression-report.json",
    ],
    "S9-fix-optimize": [
        ".ai/evidence/{task_id}/fix-optimize-report.json",
    ],
    "S10-performance": [
        ".ai/evidence/{task_id}/performance-report.json",
    ],
    "S11-maintenance": [
        ".ai/evidence/{task_id}/maintenance-report.json",
    ],
}


def _check_phase_evidence_file(
    root: Path,
    phase: str,
    evidence_relpaths: list[str],
    accept_no_regression: bool = False,
) -> tuple[bool, str]:
    """检查给定阶段证据文件是否存在且解析为 JSON 且 overall == "PASS"。

    T-0082 Phase 5 GAP-2: S7-S11 阶段门禁的结构化证据检查。
    - "{task_id}" 占位符替换为 state.current_task_id（无任务时跳过该候选）。
    - overall 缺失时兼容旧格式 verdict 字段。
    - accept_no_regression=True 时接受 regression_runner 输出风格：
      has_regressions == false 或 verdict == PASS（无 overall 字段）。
    - T-0083 (AC-06)：任一候选通过即整体通过；但已存在候选的任何非 PASS
      判定（FAIL/BLOCKED/NOT_VERIFIED/NOT_RUN/SKIPPED 等）都记为该候选
      的失败（fail-closed，was 模糊的"需要 PASS"）；全部候选缺失/无效/非
      PASS → 阻断。

    Returns (ok, reason)。
    """
    try:
        state = load_state(root)
        task_id = state.get("current_task_id")
    except Exception:
        task_id = None

    candidates: list[Path] = []
    for rel in evidence_relpaths:
        if "{task_id}" in rel:
            if not task_id:
                continue
            rel = rel.replace("{task_id}", str(task_id))
        candidates.append(root / rel)

    if not candidates:
        return False, (
            f"{phase} 阶段证据缺失：state 中没有 current_task_id，"
            "无法定位阶段报告。"
        )

    failures: list[str] = []
    for p in candidates:
        rel_p = p.relative_to(root)
        if not p.exists():
            failures.append(f"{rel_p} 不存在")
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError) as exc:
            failures.append(f"{rel_p} 无法解析: {exc}")
            continue
        overall = data.get("overall")
        if overall is None:
            overall = data.get("verdict")
        if overall == "PASS":
            return True, f"{phase} 阶段证据已通过（{rel_p} overall=PASS）"
        if accept_no_regression and (
            data.get("has_regressions") is False
            or str(data.get("verdict", "")).upper() == "PASS"
        ):
            return True, f"{phase} 阶段证据已通过（{rel_p} 无回归）"
        # T-0083 (AC-06): fail-closed — 任何非 PASS 判定
        # （FAIL/BLOCKED/NOT_VERIFIED/NOT_RUN/SKIPPED）都是 gate failure。
        failures.append(f"{rel_p} overall={overall} 非 PASS（fail-closed）")

    # 任一候选通过即整体通过；全部候选缺失/无效/非 PASS → 阻断
    return False, (
        f"{phase} 阶段证据不完整，以下文件均需存在且 overall=PASS："
        + "; ".join(f"{p.relative_to(root)}" for p in candidates)
        + "。详情：" + "; ".join(failures[:3])
    )


# ── T-0082 Phase 5 GAP-3: S5/S6 安全审计证据 ────────────────────────────


def check_security_gate_evidence(root: Path) -> tuple[bool, str]:
    """检查 S5-quality / S6-delivery 所需的安全审计证据。

    证据来源（任一通过即可）：
    1. .ai/evidence/security/security_audit.json — verdict != BLOCKED
    2. .ai/evidence/{task_id}/phase-3/security-engineer-report.md —
       存在且不含 BLOCKED 判定
    """
    sec_report = root / ".ai" / "evidence" / "security" / "security_audit.json"
    if sec_report.exists():
        try:
            sec_data = json.loads(sec_report.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError) as exc:
            return False, (
                f"安全审计证据无法解析（{sec_report.relative_to(root)}）: {exc}"
            )
        verdict = str(sec_data.get("verdict", "")).upper()
        if verdict == "BLOCKED":
            return False, "安全审计 verdict=BLOCKED：存在阻断级安全缺陷"
        if not verdict:
            return False, "安全审计证据缺少 verdict 字段"
        return True, f"安全审计证据已通过（verdict={verdict}）"

    # 兜底：安全工程师报告 markdown
    try:
        state = load_state(root)
        task_id = state.get("current_task_id")
    except Exception:
        task_id = None
    if task_id:
        md = root / ".ai" / "evidence" / task_id / "phase-3" / "security-engineer-report.md"
        if md.exists():
            try:
                text = md.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                text = ""
            if "BLOCKED" in text.upper():
                return False, "安全工程师报告中包含 BLOCKED 判定"
            return True, "安全工程师报告存在且无 BLOCKED 判定"

    return False, (
        "S5/S6 需要安全审计证据：.ai/evidence/security/security_audit.json 不存在，"
        "且 .ai/evidence/{task_id}/phase-3/security-engineer-report.md 不存在。"
    )


def check_phase_gate_enforcement(root: Path, phase: str) -> tuple[bool, str]:
    """Check phase-specific gate evidence requirements.

    Returns (can_proceed, reason). can_proceed=False means writes should be
    restricted to governance files only.
    """
    phase = (phase or "").strip()

    # T-0078 P1: S4+ 阶段必须存在质量门禁配置
    if phase and phase.startswith(("S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11")):
        qg_config = root / ".zcode" / "skills" / "loop-governance" / "config.yaml"
        if not qg_config.exists():
            return False, (
                "当前阶段需要质量门禁配置，但 .zcode/skills/loop-governance/config.yaml 不存在。"
                "请运行 /loop-onboard 初始化项目，或手动创建质量门禁配置。"
            )

    if phase == "S5-quality":
        q_ok, q_reason = check_quality_gate_evidence(root)
        if not q_ok:
            return q_ok, q_reason
        # T-0082 Phase 5 GAP-3: S5/S6 同时要求安全审计证据
        return check_security_gate_evidence(root)

    if phase == "S6-delivery":
        dm_ok, dm_reason = check_delivery_gate_evidence(root)
        if not dm_ok:
            return dm_ok, dm_reason
        rq_ok, rq_reason = check_runtime_quality_gate(root)
        if not rq_ok:
            return rq_ok, rq_reason
        # T-0082 Phase 5 GAP-3: S5/S6 同时要求安全审计证据
        sec_ok, sec_reason = check_security_gate_evidence(root)
        if not sec_ok:
            return sec_ok, sec_reason
        return True, "S6 delivery + runtime quality + security gates passed"

    # T-0082 Phase 5 GAP-2: S7-S11 阶段门禁证据（overall=PASS 的结构化报告）
    if phase in _PHASE_EVIDENCE_FILES:
        ev_ok, ev_reason = _check_phase_evidence_file(root, phase, _PHASE_EVIDENCE_FILES[phase])
        if not ev_ok and phase == "S8-functional-test":
            # S8 兜底：regression_runner 输出（baseline.json，has_regressions=false）
            ev_ok, ev_reason = _check_phase_evidence_file(
                root, phase,
                [".ai/evidence/regression/baseline.json"],
                accept_no_regression=True,
            )
        return ev_ok, ev_reason

    # Other phases: no additional gate checks at this level
    return True, ""


def _command_references_outside(root: Path, command: str) -> bool:
    """只读 Bash 命令是否引用项目根之外的路径。

    引号感知地按空白和 ;|&<> 切分命令，只检查路径形态的 token
    （绝对路径、盘符、../ 逃逸或含分隔符的相对路径）；任一 token
    明确解析到项目根外即返回 True（外部参考读取 → 放行）。
    解析失败/无法判定 → 返回 False（保守，不扩大豁免范围）。
    仅在调用方已确认命令为只读（is_readonly_command）时使用。
    """
    if not command or not isinstance(command, str):
        return False
    tokens = re.findall(r'"[^"]*"|\'[^\']*\'|\S+', command)
    for token in tokens:
        t = token.strip("\"'")
        if not t or t.startswith("-"):
            continue
        # 只关心路径形态的 token
        is_drive = len(t) >= 3 and t[1] == ":" and t[2] in ("\\", "/")
        if not (t.startswith("/") or t.startswith("../") or "/" in t
                or "\\" in t or is_drive):
            continue
        try:
            if not is_path_safe(root, t):
                return True
        except Exception:
            continue
    return False


def main():
    hook_input = _read_hook_input()
    root = project_root(hook_input)

    # ── 自愈：自动同步本地 hook → 插件缓存（解决"改本地不改缓存"的死锁）──
    auto_sync_to_plugin_cache(root)

    # 同步（或外部编辑）导致本进程加载的 hook 代码已过期 → 重执行一次，
    # 让当前这条命令用新代码判定（消除"本次仍按旧代码拦截"的竞态）。
    if _hook_files_changed_since_load():
        count = int(os.environ.get(_REEXEC_COUNT_ENV, "0") or 0)
        if count < _REEXEC_MAX:
            os.environ[_REEXEC_COUNT_ENV] = str(count + 1)
            logger.warning(
                "[auto-sync] hook code updated on disk; re-executing with fresh code"
            )
            _reexec_with_fresh_code(hook_input)

    try:
        if not is_governance_project(root):
            return EXIT_PASS

        if not is_loop_mode_enforced(root):
            return EXIT_PASS  # LIGHTWEIGHT mode or unset

        target = extract_target_path(hook_input)
        rel = normalize_rel(root, target) if target else None

        # ── 工具类型判定（T-0086）：只读 ≠ 写入 ──
        tool_name = hook_input.get("tool_name", "")
        tool_input = hook_input.get("tool_input") or {}
        command = tool_input.get("command", "")
        is_readonly_op = tool_name in READ_ONLY_TOOLS or bool(
            command and is_readonly_command(command)
        )
        is_outside_target = target is not None and not is_path_safe(root, target)
        refs_outside = bool(command and _command_references_outside(root, command))

        # 只读操作访问项目外路径（外部参考读取，如插件缓存中的 hook 协议
        # 文档）→ 放行。只读不产生项目外写入，fail-open 对只读。
        if is_readonly_op and (is_outside_target or refs_outside):
            logger.info(
                "EXTERNAL_READ: allow read-only access outside project root: %s",
                target or (command[:160] if command else ""),
            )
            return EXIT_PASS

        # ── 路径安全检查：写入目标明确在项目根外 → 阻断（fail-closed）──
        if is_outside_target:
            logger.warning(
                "BLOCKED: Target '%s' is outside the project root. "
                "Writing outside the project boundary is not allowed.",
                target,
            )
            return EXIT_BLOCK

        # Runtime projection is the canonical dispatch boundary. In FULL mode,
        # an active legacy task pointer is not sufficient to authorize the main
        # session for business work: missing or malformed projection must fail
        # closed instead of silently falling through to legacy checks.
        try:
            state = load_state(root)
        except Exception:
            state = {}
        task_id = state.get("current_task_id")
        runtime_projection = root / ".ai" / "runtime" / "runtime-state.json"
        runtime_managed = runtime_projection.exists()
        runtime_projection_valid = False
        runtime_projection_reason = "SETUP_INCOMPLETE: runtime projection missing"
        if runtime_managed:
            try:
                projection = json.loads(runtime_projection.read_text(encoding="utf-8"))
                if not isinstance(projection, dict):
                    raise ValueError("projection must be a JSON object")
                runtime_projection_valid = True
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                runtime_projection_reason = f"SETUP_INCOMPLETE: runtime projection invalid ({exc})"

        caller_class = str(tool_input.get("caller_class") or hook_input.get("caller_class") or "")
        actor_id = str(tool_input.get("actor_id") or hook_input.get("actor_id") or "")
        business_tools = {"Read", "Write", "Edit", "Bash", "ApplyPatch"}
        is_orchestration = tool_name in ("Agent", "Skill", "Task") and not extract_target_path(hook_input) and not command
        is_governance_read = (
            (tool_name == "Read" and rel is not None and is_minimal_metadata_read(rel))
            or (command and is_readonly_command(command) and any(
                prefix in command.lower() for prefix in (".ai/", ".zcode/", "agents/", "loop_core/", "hooks/", "tools/", "agents.md")
            ))
            # T-0086-P2: 治理工具调用豁免（第三个条件）。P1 之后 python 等
            # 解释器执行形态一律判"写能力"，治理工具调用（python .zcode/tools/
            # validate_state.py 等）不再走只读通道；此处按白名单目录识别
            # 治理工具调用 → 打开调度/身份门。命令仍保持写能力分类，
            # 执行通道配套见下方的 GOVERNANCE_TOOL 早退。
            or bool(command and is_governance_tool_command(command, root))
        )
        # T-0082 Phase 4: MCP tools (Node REPL etc.) are side-effect capable.
        # Without extractable target, they follow the same gate as Bash-without-target:
        # no identity → BLOCK; orchestration-context → allowed only via dispatch.
        # Placed BEFORE the is_orchestration early-pass so MCP tools never get
        # the orchestration bypass.
        if tool_name.startswith("mcp__"):
            if not task_id:
                logger.warning(
                    "BLOCKED: %s; MCP side-effect tools require an active task (DISPATCH_REQUIRED)",
                    tool_name,
                )
                return EXIT_BLOCK  # fail-closed: MCP side effects require an active task
            # B3 (T-0083): capability allow-list — explicit task contract permission.
            # The task file's optional `mcp_allowed_tools` field grants specific
            # MCP tools; absent field = empty list = no MCP tools allowed.
            mcp_allowed = _task_mcp_allowed_tools(root, task_id)
            if tool_name not in mcp_allowed:
                # Note: task_id already carries the "T-" prefix (e.g. "T-0001"),
                # so the format uses plain %s — the mission sketch's "T-%s"
                # would render "T-T-0001".
                logger.warning(
                    "BLOCKED: mcp__ tool %s not in task %s allowed list",
                    tool_name, task_id,
                )
                return EXIT_BLOCK
            # fall through to identity/DISPATCH gates below
        if is_orchestration:
            logger.warning("DISPATCH_REQUIRED: Agent/Skill/Task orchestration allowed; no execution takeover evidence; this is not a dispatch receipt")
            return EXIT_PASS
        legacy_fixture = is_legacy_synthetic_hook_fixture()
        # Git 提交/状态操作豁免：提交治理记录是治理必需动作（在 DISPATCH 门之前）
        cmd_stripped = (command or "").strip()
        _git_commit_exempt = any(
            cmd_stripped.startswith(p)
            for p in ("git add", "git commit", "git diff", "git status", "git log",
                      "git branch", "git show", "git tag", "git config")
        )
        if task_id and not runtime_projection_valid and tool_name in business_tools and not is_governance_read and not is_governance_write(rel) and not _git_commit_exempt:
            if not runtime_managed and legacy_fixture:
                logger.warning("LEGACY_SYNTHETIC_FIXTURE: runtime projection absent; using task scope only")
            else:
                logger.warning("BLOCKED: %s; DISPATCH_REQUIRED for active task %s", runtime_projection_reason, task_id)
                return EXIT_BLOCK
        # T-0082 Phase 4: MCP tools are treated like business tools for the
        # identity gate — a runtime-managed project requires caller identity
        # before MCP side effects can even be considered.
        if runtime_projection_valid and (tool_name in business_tools or tool_name.startswith("mcp__")) and not is_governance_read and not is_governance_write(rel):
            if not actor_id or not caller_class:
                logger.warning("BLOCKED: IDENTITY_REQUIRED; runtime projection requires caller identity")
                return EXIT_BLOCK

        # Runtime-managed projects do not permit direct state/evidence edits.
        # They must use RuntimeController transitions so task activation cannot
        # be forged by writing current_task_id or a gate file.
        if runtime_managed and rel is not None and is_governance_write(rel):
            tool_input = hook_input.get("tool_input") or {}
            recovery = tool_input.get("recovery_mode") == "GOVERNANCE_RECOVERY"
            caller_class = str(tool_input.get("caller_class") or hook_input.get("caller_class") or "")
            if not recovery and caller_class != "controller":
                logger.warning("BLOCKED by RuntimeController: GOVERNANCE_CONTROLLER_ONLY")
                return EXIT_BLOCK

        # Controller-owned runtime state takes precedence over legacy checks.
        # A present runtime projection means this project has opted into the
        # canonical identity/capability policy; missing caller identity fails
        # closed instead of falling back to prompt-based role claims.
        if runtime_managed and rel is not None and not is_governance_write(rel):
            try:
                from loop_core.runtime_controller import ExecutionContext, RuntimeController
                tool_input = hook_input.get("tool_input") or {}
                context = ExecutionContext(
                    actor_id=str(tool_input.get("actor_id") or hook_input.get("actor_id") or ""),
                    role_id=str(tool_input.get("role_id") or hook_input.get("role_id") or ""),
                    caller_class=str(tool_input.get("caller_class") or hook_input.get("caller_class") or ""),
                    task_id=tool_input.get("task_id") or hook_input.get("task_id"),
                    execution_id=tool_input.get("execution_id") or hook_input.get("execution_id"),
                    session_id=tool_input.get("session_id") or hook_input.get("session_id"),
                    capability_id=tool_input.get("capability_id") or hook_input.get("capability_id"),
                )
                allowed, reason = RuntimeController(root).authorize_write(context, rel)
                if not allowed:
                    logger.warning("BLOCKED by RuntimeController: %s", reason)
                    return EXIT_BLOCK
            except Exception as exc:
                logger.warning("BLOCKED: RuntimeController unavailable: %s", exc)
                return EXIT_BLOCK

        # Always allow governance file writes
        if is_governance_write(rel):
            return EXIT_PASS

        # ── Load state for both HardConstraints and fallback ──
        try:
            state = load_state(root)
        except Exception:
            state = {}

        current_phase = state.get("current_phase", "")
        task_id = state.get("current_task_id")
        tool_name = hook_input.get("tool_name", "")
        tool_input = hook_input.get("tool_input") or {}

        # ── T-0082 Phase 3 → T-0083 (B6): subagent review-evidence isolation ──
        # B6: self-review (reviewer_session_id == developer_session_id) now
        # BLOCKS business writes in FULL mode (config-gated; default on).
        if trace_review_evidence_isolation(root, task_id):
            logger.warning(
                "BLOCKED: SELF_REVIEW evidence detected "
                "(reviewer==developer session) for task %s "
                "— independent review required", task_id,
            )
            return EXIT_BLOCK

        # ── GOVERNANCE_RECOVERY: 最小化、受限、可审计的恢复通道 ──
        # 只在 Controller/runtime-state 损坏时使用。
        # 只能修复治理骨架（.ai/、.zcode/tools/），不能写业务代码。
        if tool_input.get("recovery_mode") == "GOVERNANCE_RECOVERY":
            if rel and is_governance_write(rel):
                logger.info("GOVERNANCE_RECOVERY: allowed governance write to %s", rel)
                return EXIT_PASS
            logger.warning("GOVERNANCE_RECOVERY denied: %s is not a governance path", rel or "no target")
            return EXIT_BLOCK

        # ── Agent/Skill 编排工具豁免（必须在 task_id 检查之前）──
        # Agent/Skill/Task 不直接写入文件；子代理的每次写入会被独立拦截。
        # 无 task_id 时仍需允许编排层创建任务/提案。
        if tool_name in ("Agent", "Skill", "Task") and target is None and not command:
            return EXIT_PASS

        # ── Git 版本控制豁免 ──
        # 无任务时：只允许 git add/commit/diff（提交治理记录必须）
        # 有任务时：所有本地 git 操作放行
        # git push/pull/fetch/clone 等网络操作始终需 task scope 检查
        if command:
            cmd_stripped = (command or "").strip()
            _GIT_COMMIT_OPS = ("git add", "git commit", "git diff")
            _GIT_ALL_LOCAL = _GIT_COMMIT_OPS + (
                "git status", "git log", "git branch", "git checkout",
                "git switch", "git restore", "git stash", "git tag",
                "git show", "git config", "git rm", "git mv", "git reset",
                "git merge", "git rebase",
            )
            is_commit_op = any(cmd_stripped.startswith(p) for p in _GIT_COMMIT_OPS)
            is_local_op = any(cmd_stripped.startswith(p) for p in _GIT_ALL_LOCAL)
            # Compound commands: cd /x && git ...
            has_git = " git " in cmd_stripped
            is_network = any(
                cmd_stripped.rstrip().endswith(suffix)
                for suffix in (" push", " pull", " fetch", " clone")
            )
            if not is_network:
                if task_id and is_local_op:
                    return EXIT_PASS
                if not task_id and is_commit_op:
                    return EXIT_PASS
                if has_git and "cd " in cmd_stripped and not is_network:
                    return EXIT_PASS

        # ── Read 治理：无任务时只允许治理元数据读取 ──
        if tool_name == "Read" and not task_id:
            if rel and is_minimal_metadata_read(rel):
                return EXIT_PASS
            logger.warning(
                "BLOCKED: Read tool without active task. "
                "Only governance metadata reads (.ai/*, AGENTS.md, .zcode/*) are allowed. "
                "Target: %s", rel or "no target"
            )
            return EXIT_BLOCK

        # ── Bash 只读命令治理：无任务时阻断项目级探索 ──
        # 但允许目标明确为治理路径（.ai/* .zcode/*）的只读命令。
        if command and target is None:
            if is_readonly_command(command):
                if not task_id:
                    # Check if the command references governance paths
                    cmd_lower = (command or "").lower()
                    gov_ref = any(prefix in cmd_lower for prefix in (
                        ".ai/", ".zcode/", "agents/", "loop_core/", "hooks/",
                        "tools/", "agents.md", "readme", "pyproject", "govern",
                    ))
                    if gov_ref:
                        return EXIT_PASS
                    logger.warning(
                        "BLOCKED: Readonly Bash command without active task. "
                        "Project-level exploration requires a task. Command: %s",
                        command[:200] if command else "",
                    )
                    return EXIT_BLOCK
                return EXIT_PASS

        # ── T-0086-P2: 治理工具调用执行豁免 ──
        # is_governance_read 只打开调度/身份门；此处提供执行通道配套：
        # 治理工具（validate_state/repair_continuity/close_session、checkers/
        # guards/scripts/hooks/tools 下脚本）是受信治理执行通道，其写入目标
        # 受 is_governance_write 与内容守卫约束。项目边界检查（is_outside_
        # target）已在其上执行；复合命令/重定向形态不豁免（见
        # is_governance_tool_command）。与 P1 之前的行为一致——当时这些
        # 调用经只读通道早退放行。
        if command and is_governance_tool_command(command, root):
            logger.info(
                "GOVERNANCE_TOOL: allow governance tool invocation: %s",
                command[:160],
            )
            return EXIT_PASS

        # ── HardConstraints Integration ──
        # 作为补充检查：HardConstraints 检测到 BLOCKER 时直接阻断。
        # HardConstraints 通过时，继续执行下方现有逻辑作为最终裁决。
        # 渐进式迁移：新旧逻辑并存，HardConstraints 不可用时退化到现有逻辑。
        if _HARD_CONSTRAINTS_AVAILABLE:
            try:
                hc = _HardConstraints()
                contract = load_task_contract(root, task_id) if task_id else None

                # 加载 task_graph 中的任务列表
                tasks = load_tasks_for_context(root)

                # 渐进迁移桥接：仅当 task_graph.yaml 不存在时（旧项目），
                # 若 task_id + contract 存在，合成一个 active 任务以维持兼容。
                # task_graph.yaml 存在时，完全信任其内容（不再桥接）。
                task_graph_exists = (root / ".ai" / "task_graph.yaml").exists()
                if not task_graph_exists and task_id and contract is not None:
                    active_in_graph = any(
                        t.get("status") in ("active", "in_progress")
                        for t in tasks
                    )
                    if not active_in_graph:
                        tasks.append({
                            "id": task_id,
                            "status": "active",
                            "_synthetic": True,
                        })

                # B7 (T-0083): 构造 HardConstraints 所需的完整 context。
                # 之前 current_phase=None / phase_gates={} / quality_results={}
                # / review_status={} / evidence_list=[] 且无 root/task_id，
                # 导致 C1/C2/C5/C6/C8-C11 全部 early-return（dead letters，
                # gap-analysis §2.13）。现在从真实治理状态填充，激活
                # C1/C2/C5/C6/C8-C11（C5 因写入不推进阶段保持 dormant，
                # 见 build_hard_constraints_context 注释）。
                context = build_hard_constraints_context(
                    root, state, task_id, rel, target, contract, tasks,
                )

                # C5 的 target_phase=None 警告是刻意为之（写入不推进阶段），
                # 抑制该已知警告避免每次写入都刷 stderr。
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        "ignore",
                        message=r"C5 verification check called with target_phase=None.*",
                    )
                    result = hc.check_all(context)

                if not result.passed:
                    for v in result.violations:
                        if v.severity == _Severity.BLOCKER:
                            logger.warning(
                                "[HardConstraints] BLOCKER by %s: %s",
                                v.constraint_id.value, v.message,
                            )
                    # 有 BLOCKER 级别违规 → 阻断
                    logger.warning(
                        "BLOCKED: HardConstraints 检测到 %d 个 BLOCKER 违规",
                        result.blocker_count,
                    )
                    return EXIT_BLOCK

                # HardConstraints 通过 → 继续下方现有逻辑作为最终裁决
                logger.debug(
                    "HardConstraints passed (blockers=%d, warnings=%d)",
                    result.blocker_count, result.warning_count,
                )
            except Exception as exc:
                # T-0083 (AC-06): fail-closed default (was fail-open). A broken
                # constraint kernel must not silently pass — that was the
                # T-0082 governance-theater failure.
                if should_fail_closed(root):
                    logger.warning("BLOCKED: HardConstraints 执行异常（fail-closed）: %s", exc)
                    return EXIT_BLOCK
                logger.warning("[warn] HardConstraints 执行异常，fail-open 放行（DEBUG ONLY）: %s", exc)

        # ── 现有 Phase Gate Enforcement（始终执行，作为最终裁决）──

        if current_phase:
            can_proceed, reason = check_phase_gate_enforcement(root, current_phase)
            if not can_proceed:
                logger.warning(
                    "BLOCKED: 当前阶段 %s 需要门禁证据，"
                    "但证据不完整。%s",
                    current_phase, reason,
                )
                return EXIT_BLOCK

        # ── Task Scope Enforcement ──

        if not task_id:
            logger.warning(
                "BLOCKED: Loop mode is FULL/STANDARD, "
                "but no current_task_id is set. Create a task and get gate approval first."
            )
            return EXIT_BLOCK

        # ── Agent/Skill 编排工具豁免 ──
        # Agent/Skill/Task 工具不直接写入文件；子代理/技能的每次文件写入
        # 都会被各自的 PreToolUse hook 独立拦截。
        # 此处只需确认目标任务存在且活跃，放行编排层调用。
        # 修复了原设计中 extract_target_path() 对非文件型工具返回 None
        # 导致 is_in_task_scope(None, ...) 恒返回 False 的死锁问题。
        tool_name = hook_input.get("tool_name", "")
        if tool_name in ("Agent", "Skill", "Task") and target is None and not command:
            return EXIT_PASS

        contract = load_task_contract(root, task_id)
        if contract is None:
            logger.warning(
                "BLOCKED: Task file %s.md not found. Cannot verify write scope.",
                task_id,
            )
            return EXIT_BLOCK

        # ── C11: File Write Limit Check ──
        # Governance files are already exempted above (is_governance_write),
        # so this check only applies to non-governance file writes.
        if rel is not None:
            max_files = _read_task_max_files(root, task_id)
            if max_files is not None:
                current_count = _read_file_write_count(root, task_id)
                if current_count >= max_files:
                    logger.warning(
                        "BLOCKED: Task '%s' has reached its file write limit "
                        "(%d/%d files written). "
                        "Update the task contract's max_files or split the task.",
                        task_id, current_count, max_files,
                    )
                    return EXIT_BLOCK
                # Increment the counter (write will proceed)
                _increment_file_write_count(root, task_id, rel)

        if not is_in_task_scope(rel, contract):
            logger.warning(
                "BLOCKED: Target '%s' is NOT in the allowed scope "
                "of task %s. Allowed: %s. "
                "Update the task contract or create a new task with appropriate scope.",
                rel, task_id, contract.get('allowed_paths', []),
            )
            return EXIT_BLOCK

        # ── T-0082 Phase 5 GAP-5a: Diff 变更范围检查 ──
        # 仅当 git 仓库存在且任务声明了 allowed_paths 时执行；
        # T-0083 (AC-06): git 不可用/出错 → NOT_VERIFIED（阻断），不再 fail-open。
        # 非 git 仓库（无 .git）跳过（无 diff 范围概念）。
        allowed_paths = contract.get("allowed_paths", [])
        if allowed_paths and (root / ".git").exists():
            diff_ok, diff_reason = check_diff_scope(root, allowed_paths)
            if not diff_ok:
                logger.warning("BLOCKED: %s", diff_reason)
                return EXIT_BLOCK

        return EXIT_PASS

    except Exception:
        if should_fail_closed(root):
            return EXIT_BLOCK
        return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
