"""
Loader key-field extraction — regex constants and field inference helpers.

T-0110 批 B-2 拆分（行为等价，纯外提 re-export）：
- 原 loop_core/context_loader.py 的正则常量族 + key 字段提取（_TASK_ID_RE 等、
  extract_key_fields / _format_key_fields）逐字迁移至此（design-common-weakness.md
  1.5 拆分边界表 :186-209,318-363）。
- 本模块是依赖图叶子：仅标准库 re，零 loop_core 内部依赖。
- 壳文件通过 ``from loop_core.loader_fields import ...`` re-export 保持公开面
  （含私有名）逐名一致，行为不变。
"""
from __future__ import annotations

import re

_TASK_ID_RE = re.compile(r"\bT-\d{4}\b")
_GATE_ID_RE = re.compile(r"\bG-T-\d{4}-[A-Z0-9-]+\b")
_PHASE_RE = re.compile(r"\bS(?:0|[1-9]\d?)\b")
_DECISION_RE = re.compile(
    r"\b(APPROVED|PASS|FAIL|NOGO|BLOCKED|REJECTED|ACCEPTED|COMPLETED|"
    r"approved|passed|failed|blocked|rejected|accepted|completed|"
    r"in_progress)\b"
)
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+\S")
# Lines that carry key context fields verbatim (kept at every summary level).
# Also matches the "- task_ids: ..." field lines of previous summary headers
# so that "summary of the summary" keeps the full key-field trail.
_KEY_FIELD_LINE_RE = re.compile(
    r"^\s*(?:-?\s*)?(?:task[_ -]?id|task_ids|gate|gates|phase|phases|decision|decisions)"
    r"\s*[:：]",
    re.IGNORECASE,
)
# Whitespace-delimited path-like tokens that look like evidence citations.
_CITATION_TOKEN_RE = re.compile(
    r"[^\s\"'(),;\[\]]*(?:\.ai/|evidence/|T-\d{4}/|…/)[^\s\"'(),;\[\]]*"
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。．！？!?])\s*|(?<=\.)\s+")
# Common abbreviations after which a period is not a sentence boundary.
_ABBREV_RE = re.compile(r"\b(?:e\.g|i\.e|etc|vs|Mr|Ms|Dr|St|No)\.$")


def extract_key_fields(text: str) -> dict[str, list[str]]:
    """Extract key context fields (task IDs / gates / phases / decisions).

    These fields are what every summary level preserves, so that even the
    deepest "summary of the summary" stays traceable to its task/gate/phase
    and to the decision points recorded in the original context.
    """
    fields: dict[str, list[str]] = {
        "task_ids": [],
        "gate_ids": [],
        "phases": [],
        "decisions": [],
    }

    def _add(key: str, value: str) -> None:
        if value and value not in fields[key] and len(fields[key]) < 5:
            fields[key].append(value)

    for m in _GATE_ID_RE.finditer(text):
        _add("gate_ids", m.group(0))
    # Strip gate spans first so "T-0088" inside "G-T-0088-REQUIREMENTS"
    # is not double-counted as a task ID.
    text_without_gates = _GATE_ID_RE.sub(" ", text)
    for m in _TASK_ID_RE.finditer(text_without_gates):
        _add("task_ids", m.group(0))
    for m in _PHASE_RE.finditer(text):
        _add("phases", m.group(0))
    for m in _DECISION_RE.finditer(text):
        _add("decisions", m.group(0))
    return fields


def _format_key_fields(fields: dict[str, list[str]], level: int) -> str:
    """Render the key-field header prepended to every summary level."""
    lines = [f"[CONTEXT SUMMARY L{level}]"]
    for label, key in (
        ("task_ids", "task_ids"),
        ("gates", "gate_ids"),
        ("phases", "phases"),
        ("decisions", "decisions"),
    ):
        values = fields[key]
        if values:
            lines.append(f"- {label}: {', '.join(values)}")
    return "\n".join(lines)
