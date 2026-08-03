"""loop_command_utils.py — 命令/路径判定与子进程执行辅助（T-0110 批 C 外提）。

T-0110 批 C 从 ``hooks/scripts/loop_enforcement.py`` 外提的命令/路径判定与
子进程执行辅助（design-common-weakness.md §1.1 行 2 + 任务卡批 C
"命令工具/子进程执行辅助类（subprocess timeout 等，接入批 A 常量）"）：

- 解释器识别：``_PYTHON_INTERPRETER_RE`` / ``_is_python_interpreter``
- 路径形态转换：``_msys_to_windows``（git-bash /c/... → C:/...）
- 命令段切分/校验：``_split_command_segments`` / ``_is_governance_tool_segment`` /
  ``_is_safe_cd_segment`` / ``_is_safe_display_segment`` / ``_script_in_governance_dirs``
- 只读命令外部引用判定：``_command_references_outside``
- 任务范围判定：``is_in_task_scope``（check_diff_scope 依赖，随迁避免循环导入）
- 子进程执行：``check_diff_scope``（git diff --name-only HEAD，timeout 接线
  批 A ``COMMAND_TIMEOUT_SECONDS``，阻断信息列出上限接线 ``MAX_DIFF_FILES``）

全部代码逐字迁移自 loop_enforcement.py（行为等价拆分，语义零变化）；
依赖仅 hook_common（is_path_safe/is_readonly_command/normalize_rel）+
loop_enforcement_constants（批 A 常量表）+ _hook_bash（_SIDE_EFFECT_CAPABLE，
与 hook 同源判定）。本模块不依赖 loop_enforcement（依赖图叶子方向）。
"""
from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

from hook_common import (
    is_path_safe,
    is_readonly_command,
    normalize_rel,
)
from loop_enforcement_constants import (
    COMMAND_TIMEOUT_SECONDS,
    GOVERNANCE_TOOL_DIRS,
    MAX_DIFF_FILES,
)

logger = logging.getLogger(__name__)


# ── T-0086-P2/P3: 治理工具调用豁免的段级判定辅助 ───────────────────────
# P1 把 python/sh/bash 等解释器执行形态一律判为"写能力"（fail-closed，
# 正确），但连带后果：主会话的治理工具调用（如
# `python .zcode/tools/validate_state.py .`）不再被 is_readonly_command
# 豁免 → is_governance_read=False → 无 runtime projection 时被
# SETUP_INCOMPLETE/DISPATCH_REQUIRED 拦截，治理工具全部不可用。
# is_governance_tool_command（保留在 loop_enforcement 主文件）识别
# "python 家族解释器 + 白名单目录脚本"与"直接执行白名单目录 .py 脚本"
# 两种形态 → 判为治理读取（打开调度/身份门）。豁免只作用于治理门；
# 命令仍保持"写能力"分类——项目边界检查、内容守卫、RuntimeController
# 均不受影响。P3 逐段校验（治理工具调用 / 项目根内 cd / 只读显示段），
# 任何一段带写能力 → 整体不豁免（保持 P1 的 fail-closed 拦截形态）。

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
    max_diff_files: int = MAX_DIFF_FILES,
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
            timeout=COMMAND_TIMEOUT_SECONDS,
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
