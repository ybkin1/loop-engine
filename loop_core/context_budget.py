"""
context_budget.py — Token budget calculator for context packing (F6, T-0108).

T-0107 introduced the budgeted task-card formatting directly inside
``loop_core/context_packager.py`` (D1-1).  T-0108 (F6) extracts the pure
budget/allocation logic into this dedicated module so it can be unit-tested
and reused independently of the packager:

- ``estimate_tokens`` — character → token heuristic (no tokenizer dependency).
- ``split_sections`` — markdown ``## `` section splitting.
- ``is_ac_section`` — AC/acceptance heading recognition (priority retention).
- ``slice_with_marker`` — truncation that is never silent (explicit marker).
- ``format_task_card`` — token-budget allocation: AC sections are preserved
  unconditionally, remaining sections are filled in document order, any
  drop/truncation appends a structured ``…[task card truncated ...]`` marker
  (P3 D1-3: truncation markers are structured, not bare slices).

Design constraints (design-bh-integration.md F6 必须保持):
- fail-closed: nothing here writes files; pure functions of their input.
- No tokenizer dependency: the heuristic is a constant-tunable approximation.
- The marker format is a stable contract (consumed by tests and by
  sub-agents that need to know the context was truncated).

Behavior note: ``format_task_card`` is byte-for-byte equivalent to the
T-0107 implementation previously inlined in context_packager.py (golden
snapshot preserved; context_packager now delegates here).
"""
from __future__ import annotations

# ── Tunable budget constants ─────────────────────────────────────────────

# 任务卡 token 预算（D1-1）：替代原固定 1000 字符切片。token 估算用
# 字符/token 启发式（无 tokenizer 依赖，见 estimate_tokens）。
TASK_CARD_TOKEN_BUDGET = 1500
CHARS_PER_TOKEN = 4                       # ~4 字符/token 估算启发式
TASK_CARD_BUDGET_CHARS = TASK_CARD_TOKEN_BUDGET * CHARS_PER_TOKEN
TASK_CARD_HEADER_MAX_CHARS = 400          # 任务卡 `# 标题` 前头部上限

# AC/验收节优先保留（D1-1）：标题包含下列任一关键词即视为验收节，
# 该节永不截断（其余节先被丢弃）。
TASK_CARD_AC_HEADING_MARKERS = ("可验证验收标准", "验收标准")

# 截断标记契约（D1-3 结构化标记）：任何截断/丢弃必须追加显式标记，
# 绝不静默裁剪。
TRUNCATED_MARKER = "…[truncated N chars]"
TASK_CARD_TRUNCATED_MARKER_PREFIX = "…[task card truncated: "


def estimate_tokens(text: str) -> int:
    """字符 → token 估算（≈CHARS_PER_TOKEN 字符/token 启发式，无外部依赖）。

    Args:
        text: 任意文本。

    Returns:
        int，至少为 1（空串也返回 1，避免除零/零预算歧义）。
    """
    return max(1, len(text) // CHARS_PER_TOKEN)


def slice_with_marker(text: str, limit: int) -> str:
    """截断并追加显式省略标记（D1-2/D1-3：截断绝不静默）。

    Args:
        text: 原始文本。
        limit: 保留的字符上限（不含标记）。

    Returns:
        未超限时原样返回；超限时返回 ``text[:limit] + 标记``。
    """
    if len(text) <= limit:
        return text
    marker = f"\n…[truncated {len(text) - limit} chars]"
    return text[:limit] + marker


def split_sections(text: str) -> list[tuple[str | None, str]]:
    """按 markdown ``## `` 标题把文本切分为 (标题行, 节内容) 序列。

    标题之前的全部内容作为 (None, preamble) 首元素返回（无前导内容时
    preamble 为空串）；无任何 ``## `` 标题时返回 [(None, 全文)]。
    """
    lines = text.splitlines()
    sections: list[tuple[str | None, str]] = []
    preamble: list[str] = []
    current_heading: str | None = None
    current: list[str] = []
    for line in lines:
        if line.startswith("## "):
            if current_heading is None:
                sections.append((None, "\n".join(preamble)))
            else:
                sections.append((current_heading, "\n".join(current)))
            current_heading = line
            current = []
        else:
            if current_heading is None:
                preamble.append(line)
            else:
                current.append(line)
    if current_heading is None:
        return [(None, text)]
    sections.append((current_heading, "\n".join(current)))
    return sections


def is_ac_section(heading: str | None) -> bool:
    """标题是否属于 AC/验收节（D1-1：验收节优先保留、不被切）。"""
    if heading is None:
        return False
    return any(marker in heading for marker in TASK_CARD_AC_HEADING_MARKERS)


def format_task_card(text: str, *, budget: int | None = None) -> str:
    """任务卡按 token 预算截断 + AC 节优先保留 + truncated 标记（D1-1）。

    替代原 ``read_text()[:1000]`` 固定字符切片：
    - 按 markdown 节（``## `` 标题）解析任务卡
    - AC/验收节（``## 可验证验收标准`` 等）永远完整保留（不被切）
    - 头部（标题行及 ``## `` 前的正文）保留（超长则带标记截断）
    - 其余节按文档顺序填充，超出 token 预算的节整体丢弃
    - 任何丢弃/截断都追加显式 ``…[task card truncated ...]`` 标记

    Args:
        text: 任务卡全文。
        budget: 可选字符预算（默认 ``TASK_CARD_BUDGET_CHARS``，即
            ``TASK_CARD_TOKEN_BUDGET × CHARS_PER_TOKEN``）。

    Returns:
        格式化后的任务卡文本（含截断标记，若发生丢弃/截断）。
    """
    budget_chars = TASK_CARD_BUDGET_CHARS if budget is None else budget
    sections = split_sections(text)
    header, *body = sections

    out: list[str] = []
    used = 0
    dropped = 0
    truncated_header = False

    if header[1].strip():
        # 前导标题/元信息（无 `## ` 节时即整文）：有节时上限小，
        # 无节时按 token 预算截断。
        header_cap = budget_chars if not body else TASK_CARD_HEADER_MAX_CHARS
        h = header[1]
        if len(h) > header_cap:
            truncated_header = True
            h = slice_with_marker(h, header_cap)
        out.append(h)
        used += len(h)

    ac_sections: list[tuple[str, str]] = []
    others: list[tuple[str, str]] = []
    for heading, content in body:
        (ac_sections if is_ac_section(heading) else others).append((heading, content))

    # AC 节永远完整保留（D1-1 硬约束：AC 不被切）
    for heading, content in ac_sections:
        out.append(heading)
        out.append(content)
        used += len(heading) + len(content) + 1

    # 其余节按文档顺序填充预算
    for heading, content in others:
        size = len(heading) + len(content) + 1
        if used + size > budget_chars:
            dropped += 1
            continue
        out.append(heading)
        out.append(content)
        used += size

    if dropped or truncated_header:
        marker = (
            f"\n\n{TASK_CARD_TRUNCATED_MARKER_PREFIX}"
            f"{dropped} section(s) dropped, "
            f"{used} of {len(text)} chars included, "
            f"token budget ≈{TASK_CARD_TOKEN_BUDGET} (AC section preserved)]"
        )
        out.append(marker)
    return "\n".join(out)
