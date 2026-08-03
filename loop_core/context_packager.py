"""context_packager.py — Build code context for role sub-agents."""
import json
import logging
import subprocess, sys
from pathlib import Path

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════
# T-0107 集中命名常量（D2-1 截断字面量 / D2-8 git timeout 字面量）
# ══════════════════════════════════════════════════════════════════════

# T-0108（F6）：token 预算/AC 节解析/截断标记逻辑外提到 context_budget.py
# （纯函数、可独立单测）；此处 re-export 常量与工具，保持既有调用方与
# 测试（TASK_CARD_TOKEN_BUDGET 等直接属性访问）零改动。
from loop_core.context_budget import (  # noqa: E402
    CHARS_PER_TOKEN,
    TASK_CARD_AC_HEADING_MARKERS,
    TASK_CARD_BUDGET_CHARS,
    TASK_CARD_HEADER_MAX_CHARS,
    TASK_CARD_TOKEN_BUDGET,
    TASK_CARD_TRUNCATED_MARKER_PREFIX,
    TRUNCATED_MARKER,
    estimate_tokens,
    format_task_card,
    is_ac_section,
    slice_with_marker,
    split_sections,
)

EXTRA_FILE_MAX_CHARS = 2000               # extra_files 单文件上限（原字面量 2000）
MAX_EXTRA_FILES = 5                       # extra_files 数量上限（原字面量 5）
KNOWLEDGE_CASES_MAX_CHARS = 3000          # knowledge cases JSON 上限（原字面量 3000）
MAX_KNOWLEDGE_CASES = 3                   # knowledge cases 数量上限（原字面量 3）

# 全上下文总字符护栏（D3-2）：原 MAX=15000 因 total 从不递增而恒真（死代码）。
# 现在 total 真实累计、护栏真实执行；超限节被丢弃/截断并带标记。
MAX_TOTAL_CHARS = 15000

# git 命令 timeout（D2-8）：按命令类型集中命名，替代散落字面量 5/10/5。
GIT_TIMEOUT_DIFF_STAT = 5
GIT_TIMEOUT_DIFF_CODE = 10
GIT_TIMEOUT_DIFF_NAME = 5
GIT_TIMEOUT_REV_PARSE = 5

# 进程内 git diff 缓存（D4-4 diff 缓存）：同一项目根 + 同一 HEAD 下
# 重复 build_context 不重跑 git diff（子代理批量派发场景）。
# key = (project_root_str, head_sha, kind)；仅成功结果入缓存。
_DIFF_CACHE: dict[tuple[str, str, str], str] = {}
_DIFF_CACHE_MAX_ENTRIES = 64

ROLE_CONTEXT = {
    "developer": {"files": ["docs/02-architecture.md", "docs/03-interface-contract.md"], "git_diff": True, "max_content": 5000},
    "independent-reviewer": {"files": ["docs/02-architecture.md", ".ai/CODING_STANDARDS.md"], "git_diff": True, "max_content": 8000},
    "test-engineer": {"files": ["docs/03-interface-contract.md"], "git_diff_name_only": True, "max_content": 3000},
    "quality-engineer": {"files": [], "git_diff_name_only": True, "max_content": 2000},
    "system-architect": {"files": ["docs/02-architecture.md", "docs/01-requirements.md"], "git_diff_name_only": True, "max_content": 5000},
    "module-architect": {"files": ["docs/03-interface-contract.md"], "git_diff": True, "max_content": 4000},
    "product-manager": {"files": ["docs/01-requirements.md"], "git_diff_name_only": True, "max_content": 3000},
    "project-manager": {"files": [".ai/task_graph.yaml"], "git_diff": True, "max_content": 4000},
    "delivery-manager": {"files": ["docs/06-delivery.md", "docs/07-phase-specification.md"], "git_diff": True, "max_content": 5000},
    "release-engineer": {"files": ["docs/06-delivery.md", "pyproject.toml"], "git_diff": True, "max_content": 5000},
    "security-engineer": {"files": ["pyproject.toml"], "git_diff": True, "max_content": 6000},
}


# ── 截断工具（T-0108 F6：实现外提 context_budget.py，别名保持兼容）────

# 兼容别名：既有内部调用方（build_context）与潜在外部引用继续可用。
# 实现见 loop_core/context_budget.py（纯函数、单测独立覆盖）。
_estimate_tokens = estimate_tokens
_slice_with_marker = slice_with_marker
_split_task_sections = split_sections
_is_ac_section = is_ac_section
_format_task_card = format_task_card


# ── T-0107 git diff 缓存（D4-4）────────────────────────────────────────

def _git_head(root: Path) -> str | None:
    """当前 HEAD 短 sha；git 不可用/非 git 仓库返回 None（不缓存）。"""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=str(root),
            timeout=GIT_TIMEOUT_REV_PARSE,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()[:40]
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _git_diff(root: Path, args: list[str], timeout: int, head: str | None,
              kind: str) -> tuple[str | None, str | None]:
    """运行 git 命令；返回 (stdout, error)。成功结果按 (root, head, kind)
    缓存（D4-4 diff 缓存）；失败返回错误信息供调用方标记，不缓存失败。"""
    if head is not None:
        key = (str(root), head, kind)
        if key in _DIFF_CACHE:
            return _DIFF_CACHE[key], None
    try:
        r = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, cwd=str(root), timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"git {' '.join(args)} unavailable: {type(exc).__name__}: {exc}"
    if r.returncode != 0:
        err = f"git {' '.join(args)} failed (rc={r.returncode})"
        if r.stderr.strip():
            err += f": {r.stderr.strip()[:200]}"
        return None, err
    if head is not None:
        key = (str(root), head, kind)
        if len(_DIFF_CACHE) >= _DIFF_CACHE_MAX_ENTRIES:
            _DIFF_CACHE.clear()
        _DIFF_CACHE[key] = r.stdout
    return r.stdout, None


def _format_knowledge_cases(selected: list) -> str:
    """D1-4：knowledge cases 序列化为语法完整的 JSON；超限时按 case 边界
    截断（丢弃尾部 case），绝不产出语法无效的 JSON 片段；截断带标记。"""
    budget = KNOWLEDGE_CASES_MAX_CHARS
    keep = list(selected)
    while keep:
        rendered = json.dumps(keep, ensure_ascii=False, indent=2)
        if len(rendered) <= budget:
            if len(keep) < len(selected):
                rendered += f"\n…[truncated {len(selected) - len(keep)} cases]"
            return rendered
        keep = keep[:-1]
    return "…[truncated: no case fits budget]"


def build_context(project_root, role_id, task_id="", extra_files=None,
                  *, include_memories: bool = False, memory_limit: int = 5,
                  memory_gate_id: str | None = None, memory_tag: str | None = None):
    """Build code context for a role sub-agent.

    T-0104 设计-5: ``include_memories=True`` 时追加"相关经验（Related
    Memories）"节（memory_service recall，top-N = memory_limit，渲染格式
    与 context_loader 一致）。默认 False 保持现状（零行为变化）。

    T-0105 B-4-1: 记忆召回透传过滤参数——``task_id``（复用位置参数）、
    ``memory_gate_id``、``memory_tag`` 按 AND 组合传给 recall，消除跨任务
    不相关记忆注入；任一过滤参数为 None/空 即不过滤，与 T-0104 现状一致
    （fail-closed：空召回 no-op、损坏抛异常不变）。

    T-0107（正确性修复）：
    - D1-1 任务卡按 token 预算截断、AC 节优先保留、带 truncated 标记
    - D1-2/D1-3 角色文件/extra_files 截断带 ``…[truncated N chars]`` 标记
    - D1-4 knowledge cases 截断到完整 JSON（按 case 边界）并带标记
    - D2-1/D2-8 字面量与 timeout 集中命名常量
    - D3-2 MAX_TOTAL_CHARS 全局护栏真实执行（total 递增 + 超限标记）
    - D4-1 git diff 失败不再静默吞错（warning + "diff unavailable" 占位节）
    - D4-4 knowledge cases 损坏不再静默丢弃（warning）；git diff 增加
      进程内缓存（同 HEAD 不重跑）
    """
    root = Path(project_root)
    spec = ROLE_CONTEXT.get(role_id, {"files": [], "git_diff_name_only": True, "max_content": 2000})
    parts: list[str] = []
    total = 0
    budget_truncated = False

    def _add(text: str, *, budgeted: bool = True) -> None:
        """追加一节；budgeted=True 时受 MAX_TOTAL_CHARS 全局护栏约束（D3-2）。"""
        nonlocal total, budget_truncated
        if budgeted:
            if total >= MAX_TOTAL_CHARS:
                budget_truncated = True
                return
            remaining = MAX_TOTAL_CHARS - total
            if len(text) > remaining:
                budget_truncated = True
                text = _slice_with_marker(text, remaining)
        parts.append(text)
        total += len(text)

    if task_id:
        tf = root / ".ai/tasks" / (task_id + ".md")
        if tf.exists():
            try:
                tc = _format_task_card(tf.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError) as exc:
                logger.warning("[context_packager] 任务卡 %s 读取失败: %s", tf, exc)
                tc = f"## Task Context\n…[task card unreadable: {type(exc).__name__}]"
            else:
                tc = "## Task Context\n" + tc
            _add(tc)

    # git diff 段（D4-1：失败记 warning + "diff unavailable" 占位，不再静默）
    git_errors: list[str] = []
    try:
        head = _git_head(root)
        if spec.get("git_diff"):
            stat_out, stat_err = _git_diff(
                root, ["diff", "--stat", "HEAD~1"], GIT_TIMEOUT_DIFF_STAT, head, "stat")
            if stat_err:
                git_errors.append(stat_err)
            elif stat_out.strip():
                _add("## Changed Files\n" + stat_out.strip())
            code_out, code_err = _git_diff(
                root, ["diff", "HEAD~1", "--", "*.py"], GIT_TIMEOUT_DIFF_CODE, head, "code")
            if code_err:
                git_errors.append(code_err)
            elif code_out.strip():
                dt = _slice_with_marker(code_out, spec["max_content"])
                _add("## Code Diff\n```diff\n" + dt + "\n```")
        elif spec.get("git_diff_name_only"):
            name_out, name_err = _git_diff(
                root, ["diff", "--name-only", "HEAD~1"], GIT_TIMEOUT_DIFF_NAME, head, "names")
            if name_err:
                git_errors.append(name_err)
            elif name_out.strip():
                _add("## Changed Files\n" + name_out.strip())
    except Exception as exc:  # 防御性兜底（D4-1：不再静默吞错）
        git_errors.append(f"unexpected error: {type(exc).__name__}: {exc}")
    for err in git_errors:
        logger.warning("[context_packager] git diff unavailable: %s", err)
        _add("## Git Diff Status\n(diff unavailable: " + err + ")")

    for f in spec.get("files", []):
        fp = root / f
        if fp.exists():
            try:
                c = fp.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                logger.warning("[context_packager] 角色文件 %s 读取失败: %s", f, exc)
                continue
            _add("## " + f + "\n" + _slice_with_marker(c, spec["max_content"]))
    if extra_files:
        for f in extra_files[:MAX_EXTRA_FILES]:
            fp = root / f
            if fp.exists():
                try:
                    c = fp.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError) as exc:
                    logger.warning("[context_packager] extra_file %s 读取失败: %s", f, exc)
                    continue
                _add("## " + f + "\n```\n" + _slice_with_marker(c, EXTRA_FILE_MAX_CHARS) + "\n```")
    knowledge = root / ".ai" / "knowledge" / "cases.json"
    if knowledge.exists():
        try:
            cases = json.loads(knowledge.read_text(encoding="utf-8"))
            selected = cases[:MAX_KNOWLEDGE_CASES] if isinstance(cases, list) else []
            if selected:
                _add("## Knowledge Cases\n" + _format_knowledge_cases(selected))
        except (OSError, json.JSONDecodeError) as exc:
            # D4-4（audit 表）：损坏的 knowledge cases 不再静默丢弃
            logger.warning("[context_packager] knowledge cases 读取失败（%s）: %s", knowledge, exc)
    if include_memories:
        # T-0104 设计-5: 记忆注入（S4+ 调用点显式开启）。空召回 = 无节 = no-op；
        # store 损坏时 fail-closed（与 context_loader 语义一致，不静默猜记忆）。
        from loop_core.memory_service import memories_to_context, recall
        if isinstance(memory_limit, int) and memory_limit > 0:
            # T-0105 B-4-1: 透传 task_id/gate_id/tag 过滤（None = 不过滤，
            # 与 context_loader._apply_memory_injection 的 recall 用法一致）。
            entries = recall(
                root,
                limit=memory_limit,
                task_id=task_id or None,
                gate_id=memory_gate_id,
                tag=memory_tag,
            )
            section = memories_to_context(entries)
            if section:
                _add(section)
    if budget_truncated:
        _add("…[context truncated: total budget exceeded]", budgeted=False)
    parts.append("execution_mode: SIMULATED_MAIN_SESSION\nagent_takeover: false")
    parts.append("\n---\nUse the above context to complete your role duties.")
    return "\n\n".join(parts)


if __name__ == "__main__":
    r = sys.argv[1] if len(sys.argv) > 1 else "."
    role = sys.argv[2] if len(sys.argv) > 2 else "developer"
    tid = sys.argv[3] if len(sys.argv) > 3 else ""
    print(build_context(r, role, tid))
