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
import importlib  # noqa: F401 — 壳保留拆分前导入面（T-0110 批 C，dir() 逐名一致）
import json
import logging
import os
import re
import subprocess  # noqa: F401 — 壳保留拆分前导入面（T-0110 批 C，dir() 逐名一致）
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
from hook_common import (  # noqa: E402 — 必须先完成 sys.path 就绪
    DEFAULT_CONFIG,
    extract_target_path,
    is_governance_project,
    is_path_safe,
    is_readonly_command,
    is_readonly_exempt,
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


def _snapshot_hook_file_shas() -> dict[str, str]:
    """快照本进程判定所依赖的 hook 文件 sha256（脚本目录内）。

    T-0107 D4-7: 读取失败的文件不再静默跳过——首次跳过时记 warning
    （防篡改扫描集不完整的可见性）；同一文件仅告警一次，避免每次
    hook 调用刷屏。
    """
    shas: dict[str, str] = {}
    base = Path(__file__).resolve().parent
    for name in (
        "loop_enforcement.py", "hook_common.py", "_hook_bash.py",
        "_hook_state.py", "_hook_path.py", "_hook_config.py", "_hook_sync.py",
        # T-0110 批 C：行为等价拆分后判定逻辑分布到四个拆分模块，扫描集
        # 同步扩展（自愈机制语义零变化：改任一判定文件 → re-exec 一次）。
        "loop_contract_parser.py", "loop_command_utils.py",
        "gate_evidence_checks.py", "loop_enforcement_constants.py",
    ):
        p = base / name
        try:
            shas[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
        except OSError as exc:
            if str(p) not in _HOOK_SHA_WARNED:
                _HOOK_SHA_WARNED.add(str(p))
                logger.warning(
                    "HASH_SCAN_SKIPPED: cannot read %s (%s); tamper-scan set incomplete",
                    p, exc,
                )
    return shas


# T-0107 D4-7: 已告警过的跳过文件（进程内去重，避免每次调用刷屏）
_HOOK_SHA_WARNED: set[str] = set()


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

# ══════════════════════════════════════════════════════════════════════
# T-0110 批 C：常量表接线（loop_enforcement_constants，批 A 已建）。
# EXIT_PASS/EXIT_BLOCK（M-1）、_REEXEC_MAX（自愈重执行上限）、治理路径
# 白名单——数值与批 A 登记逐一一致（tests/test_t0110_batch_a.py 锁定）；
# 本文件不再持有这些字面量定义（唯一来源 = 常量表）。
# ══════════════════════════════════════════════════════════════════════
from loop_enforcement_constants import (  # noqa: E402 — 壳接线导入（sys.path 就绪后）
    EXIT_BLOCK,
    EXIT_PASS,
    GOVERNANCE_EXEMPT,
    MAIN_THREAD_ALLOWED,
    MINIMAL_METADATA_READ,
)
from loop_enforcement_constants import (  # noqa: E402 — 自愈上限别名接线
    REEXEC_MAX as _REEXEC_MAX,
)

# GOVERNANCE_TOOL_DIRS 双登记例外：T-0109 AC-05 门禁
# （tests/test_t0109_f5_tool_capability.py::_extract_governance_tool_dirs）
# 用 AST 断言本文件源内必须保留 GOVERNANCE_TOOL_DIRS 的 tuple 字面量；
# 数值与 loop_enforcement_constants.GOVERNANCE_TOOL_DIRS 一致（批 C
# 一致性测试锁定）。其余常量均为常量表唯一来源。
GOVERNANCE_TOOL_DIRS: tuple[str, ...] = (
    ".zcode/tools/",   # 治理工具（validate_state/repair_continuity/close_session...）
    ".ai/checkers/",   # 检查器（compile_gate/run_governance_checks...）
    ".ai/guards/",     # 守卫（policy_guard）
    "scripts/",        # 治理脚本（runtime_delivery_gate/regression_runner...）
    "hooks/",          # hook 自测
    "tools/",          # 项目 loop 工具 CLI/MCP（tool_state/tool_handoff/
                       # loop_guard_health/loop_self_audit...，与
                       # MINIMAL_METADATA_READ 中的 tools/ 治理语义一致）。
                       # T-0109 F5：36 工具 capability 化后工具清单见
                       # loop_core/capability_registry.py
                       # TOOL_CAPABILITY_MANIFEST；白名单按目录覆盖，工具
                       # 变更无需逐文件同步（一致性测试 AC-05 断言）。
)

# ══════════════════════════════════════════════════════════════════════
# T-0110 批 C：行为等价拆分 re-export（壳保持拆分前 dir()/import *
# 公开面逐名一致，含私有名；未在本文件体内使用的绑定是供测试与下游
# 直接导入的 re-export 面——与批 B-1/B-2 壳文件同模式，pyproject.toml
# per-file-ignores 登记 F401 豁免）。
# ══════════════════════════════════════════════════════════════════════
from gate_evidence_checks import (  # noqa: F401, E402 — 拆分 re-export（壳保持 dir() 逐名一致）
    _PHASE_EVIDENCE_FILES,
    _check_phase_evidence_file,
    _import_loop_core_gate,
    _self_review_block_enabled,
    check_delivery_gate_evidence,
    check_phase_gate_enforcement,
    check_quality_gate_evidence,
    check_runtime_quality_gate,
    check_second_failure_gate_evidence,
    check_security_gate_evidence,
    check_slo_gate_evidence,
    trace_review_evidence_isolation,
)
from loop_command_utils import (  # noqa: F401, E402 — 拆分 re-export（壳保持 dir() 逐名一致）
    _PYTHON_INTERPRETER_RE,
    _SIDE_EFFECT_CAPABLE,
    _command_references_outside,
    _is_governance_tool_segment,
    _is_python_interpreter,
    _is_safe_cd_segment,
    _is_safe_display_segment,
    _msys_to_windows,
    _script_in_governance_dirs,
    _split_command_segments,
    check_diff_scope,
    is_in_task_scope,
)
from loop_contract_parser import (  # noqa: F401, E402 — 拆分 re-export（壳保持 dir() 逐名一致）
    _SHARED_FRONT_MATTER_PARSER,
    _front_matter_parser,
    _parse_task_front_matter_legacy,
    _read_task_max_files,
    _task_mcp_allowed_tools,
    load_task_contract,
)


def is_loop_mode_enforced(root: Path) -> bool:
    """Check if Loop mode enforcement is active for this project.

    T-0107 D4-2: state 读取异常时 fail-closed（was fail-open）——无法确认
    loop 模式时按强制执行处理（返回 True），loop 强制不得因 state 读取
    失败而静默关闭；与同文件 runtime 投影路径（RuntimeController 不可用
    即 BLOCK）的 fail-closed 语义一致。异常显式告警。
    """
    try:
        state = load_state(root)
    except Exception as exc:
        logger.warning(
            "STATE_UNREADABLE: cannot read .ai/state.yaml (%s); "
            "treating loop mode as enforced (fail-closed)", exc,
        )
        return True

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
#
# T-0110 批 C：段级判定辅助（_split_command_segments/_is_governance_tool_segment/
# _is_safe_cd_segment/_is_safe_display_segment/_script_in_governance_dirs/
# _is_python_interpreter/_msys_to_windows/_PYTHON_INTERPRETER_RE/
# _SIDE_EFFECT_CAPABLE）外提至 loop_command_utils（本文件 re-export）。


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


# ── C11: File Write Counter ────────────────────────────────────────────


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
    # T-0110 批 C：接线批 A 常量（函数内局部导入，壳命名空间零新增绑定，
    # dir() 逐名一致要求）
    from loop_enforcement_constants import DEFAULT_MAX_FILES

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
        "max_files": max_files if max_files is not None else DEFAULT_MAX_FILES,
    }


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

        # ── 工具类型判定（T-0086，判定源统一 T-0095）：只读 ≠ 写入 ──
        tool_name = hook_input.get("tool_name", "")
        tool_input = hook_input.get("tool_input") or {}
        command = tool_input.get("command", "")
        is_readonly_op = is_readonly_exempt(tool_name, command)
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
            _GIT_COMMIT_OPS = ("git add", "git commit", "git diff")  # noqa: N806 — 主流程原样保留
            _GIT_ALL_LOCAL = _GIT_COMMIT_OPS + (  # noqa: N806 — 主流程原样保留
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
