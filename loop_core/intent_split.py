"""
Intent Router — 意图切分与切换信号辅助（T-0110 批 B-1 拆分产物）。

从 loop_core/intent_router.py 外提（design-common-weakness.md 1.3 边界：
"意图切分/切换辅助（split_intents/_INTENT_SPLIT_RE/detect_intent_switch/
_other_task_refs/_active_task_completion_signal）:1127-1235"，含其专属
常量：_MAX_TASK_FRAMES / INTENT_SWITCH_KEYWORDS / _TASK_ID_RE /
_COMPLETION_VERBS）。

内容（原文件逐字迁移，行为零变化）：split_intents / detect_intent_switch /
_other_task_refs / _active_task_completion_signal + 正则/词表。

依赖：仅标准库 re（叶子模块）。public 面由 intent_router 壳 re-export
保持（from loop_core.intent_router import * 兼容）。
"""
from __future__ import annotations

import re

# Max task frames produced in one round (defensive cap)
_MAX_TASK_FRAMES: int = 5

# Explicit invalidation conditions for sticky routing: a new-task marker
# or a task-completion/closure marker overrides the default "continue the
# active task" behaviour.  Heuristic list — kept explicit and documented.
INTENT_SWITCH_KEYWORDS: list[str] = [
    # --- new-task markers ---
    "new task", "start a new task", "start another task", "another task",
    "other task", "different task", "separate task", "unrelated task",
    "next task", "switch task", "switch to",
    "新任务", "开始新任务", "换个任务", "另一个任务", "其他任务",
    "别的任务", "下一个任务", "切换任务", "换一个任务", "换一项工作",
    # --- completion / closure markers ---
    "task is done", "task is complete", "task done", "task completed",
    "mark complete", "mark as complete", "mark completed",
    "mark as completed", "close the task", "close task",
    "cancel the task", "abort the task",
    "任务完成", "任务已完成", "任务结束", "结束任务", "关闭任务",
    "取消任务", "终止任务", "收尾任务", "已完成", "完成了",
]

_TASK_ID_RE = re.compile(r"\bT-\d{4}\b", re.IGNORECASE)


def split_intents(description: str, max_frames: int = _MAX_TASK_FRAMES) -> list[str]:
    """Heuristically split one user input into multiple intents (U5).

    Conservative, explicit-marker-only splitting (no sentence-level
    splitting) to avoid fragmenting a single intent into noise:

    - semicolons (``；`` / ``;``)
    - numbered task lists (``1. ... 2. ...``)
    - English sequential/additive connectors (``then``, ``after that``,
      ``afterwards``, ``next``, ``finally``, ``also``, ``additionally``,
      ``moreover``, ``meanwhile``)
    - Chinese connectors when preceded by punctuation (``，然后``,
      ``。接下来``, ``；之后``, ...): ``然后/接下来/之后/接着/其次/再次/
      最后/同时/另外/此外/除此之外``
    - a sentence break followed by an action starter (``。新增``,
      ``。修复``, ``。写``, ...)

    Returns the ordered intents (max ``max_frames``), or ``[]`` for
    empty/invalid input.
    """
    if not isinstance(description, str) or not description.strip():
        return []
    parts: list[str] = []
    for raw in _INTENT_SPLIT_RE.split(description):
        part = re.sub(r"^\d+\.\s*", "", raw.strip())
        # Drop leading Chinese connectors left over from a split (e.g. a
        # segment that began right after a semicolon).
        part = re.sub(
            r"^(?:然后|接下来|之后|接着|其次|再次|最后|同时|另外|此外|除此之外)\s*",
            "", part,
        )
        part = part.strip(" \t，。；;,.：:、")
        if part:
            parts.append(part)
        if len(parts) >= max_frames:
            break
    return parts


# Split markers — see split_intents() docstring.  The Chinese connector
# branch requires a preceding punctuation char (lookbehind) so phrases
# like "登录之后" (temporal reference inside one intent) are NOT split;
# the sentence-break branch uses a zero-width lookahead so the action
# verb ("新增" in "。新增...") stays attached to the follow-up frame.
_INTENT_SPLIT_RE = re.compile(
    r"[；;]"
    r"|(?:\s+\d+\.\s+)"
    r"|(?i:\s+(?:then|after\s+that|afterwards|next|finally|also|additionally|moreover|meanwhile)\s*[,，]?\s+)"
    r"|(?<=[，。；,.;：:、])(?:然后|接下来|之后|接着|其次|再次|最后|同时|另外|此外|除此之外)"
    r"|(?<=。)(?=新增|添加|加|修复|重构|实现|部署|优化|更新|写|创建|移除|删除|升级|支持|增加|设计)"
)


def detect_intent_switch(description: str) -> tuple[bool, str]:
    """Detect explicit intent-switch / task-completion signals (U5).

    These are the explicit invalidation conditions for sticky routing:
    a new-task marker or a completion/closure marker overrides the
    default "continue the active task" behaviour, allowing the route to
    cut out of the active task domain.

    Returns ``(switched, reason)``.
    """
    desc_lower = description.lower()
    for kw in INTENT_SWITCH_KEYWORDS:
        if kw in desc_lower:
            return True, f"intent-switch marker {kw!r} detected"
    return False, ""


def _other_task_refs(desc_lower: str, active_task_id: str) -> list[str]:
    """Task ids mentioned in the input that differ from the active task."""
    seen: list[str] = []
    for m in _TASK_ID_RE.finditer(desc_lower):
        tid = m.group(0).upper()
        if tid != active_task_id.upper() and tid not in seen:
            seen.append(tid)
    return seen


# Completion/closure verbs used by _active_task_completion_signal()
_COMPLETION_VERBS: list[str] = [
    "complete", "completed", "done", "finished", "close", "closed",
    "abort", "cancel", "canceled", "cancelled",
    "结束", "完成", "关闭", "取消", "终止", "收尾",
]


def _active_task_completion_signal(desc_lower: str, active_task_id: str) -> str:
    """Detect "mark <active task> complete"-style closure signals.

    When the active task id is mentioned together with a
    completion/closure verb in its vicinity (proximity window), the
    active task is being closed and stickiness must not apply.  Returns
    the evidence string, or "" when no signal is found.
    """
    upper = desc_lower.upper()
    task_pos = upper.find(active_task_id.upper())
    if task_pos < 0:
        return ""
    window = desc_lower[max(0, task_pos - 20): task_pos + len(active_task_id) + 40]
    for verb in _COMPLETION_VERBS:
        if verb in window:
            return (
                f"active task {active_task_id} referenced together with "
                f"completion/closure marker {verb!r}"
            )
    return ""
