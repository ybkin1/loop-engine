"""
Gate Decision Feedback Loop — structured lessons from gate decisions.

U4 (T-0089): when a gate is rejected or a repair is requested, the
experience is recorded as a structured, searchable lesson so that future
Human Review Packets can reference past history instead of repeating the
same mistakes. Modeled on StaffDeck feedback/service.py attribution
buckets → skill health feedback (see .ai/evidence/T-0086/staffdeck-benchmark.md
U4).

Design:
- Lessons are appended to ``.ai/evidence/feedback/gate-lessons.yaml``
  (append-only: historical gate records in gates.yaml are never modified).
- Recording is idempotent: same gate + same decision + same normalized
  reason fingerprint records at most once (dedup key is a deterministic
  SHA-256 lesson id).
- Retrieval: by_gate_id / by_reason_category / recent / search, plus
  suggest_related_lessons() for decision-packet integration.
- Integration with human_review_packet is optional: the packet builder
  accepts a ``related_experience`` summary string; rendering only adds a
  section when the string is non-empty, so default behavior is unchanged.

Referenced by:
- human_review_packet.py — optional related_experience field / builder param
- tests/test_gate_feedback.py — AC-01 recording + dedup + retrieval + integration
"""
from __future__ import annotations

import hashlib
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

GATE_LESSONS_SCHEMA = "gate_lessons"
GATE_LESSONS_SCHEMA_VERSION = 1
DEFAULT_LESSONS_RELATIVE_PATH = ".ai/evidence/feedback/gate-lessons.yaml"

# T-0095: process-internal lock serializing record_gate_lesson's
# read-modify-write (load_lessons -> append -> _save_lessons).  Without it,
# concurrent threads recording different lessons can overwrite each other's
# append and silently drop records.  The lock is process-local by design
# (跨进程并发仍由 _save_lessons 的 tmp+rename 原子写兜底，同一进程内
# 完全串行化)。
_RECORD_LOCK = threading.Lock()

# Decision outcomes that produce a lesson. "approved" is recordable too
# (positive experience), but the loop focuses on rejected / repair_requested.
DECISION_REJECTED = "rejected"
DECISION_REPAIR_REQUESTED = "repair_requested"
DECISION_APPROVED = "approved"
DECISIONS = (
    DECISION_REJECTED,
    DECISION_REPAIR_REQUESTED,
    DECISION_APPROVED,
)

# Reason attribution buckets — mirrors StaffDeck feedback attribution buckets.
REASON_CATEGORIES = ("scope", "evidence", "risk", "wording", "other")

DEFAULT_RECENT_LIMIT = 10
DEFAULT_SUGGEST_LIMIT = 5


class GateLessonError(Exception):
    """Base error for gate-lesson record / retrieval failures."""


class InvalidLessonError(GateLessonError):
    """Raised when a lesson record is malformed or violates the schema."""


# ── Data Model ─────────────────────────────────────────────────────────────


@dataclass
class GateLesson:
    """One structured lesson captured from a gate decision.

    Fields:
        lesson_id: Deterministic id — SHA-256 over
            gate_id|decision|reason_category|normalized_reason_text.
            Same fingerprint → same lesson (dedup key).
        gate_id: The gate that produced this lesson (e.g. G-T-0005-CLOSEOUT-REVIEW).
        task_id: The task the gate belongs to.
        decision: rejected | repair_requested | approved.
        reason_category: scope | evidence | risk | wording | other.
        reason_text: The rejection / repair reason (free text, verbatim).
        repair_suggestion: Optional suggested fix direction.
        source: Optional origin of the lesson (e.g. decision packet id).
        recorded_at: ISO-8601 UTC timestamp of when the lesson was recorded.
        schema_version: Lesson schema version (GATE_LESSONS_SCHEMA_VERSION).
    """
    lesson_id: str
    gate_id: str
    task_id: str
    decision: str
    reason_category: str
    reason_text: str
    repair_suggestion: str | None = None
    source: str | None = None
    recorded_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    schema_version: int = GATE_LESSONS_SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "lesson_id": self.lesson_id,
            "gate_id": self.gate_id,
            "task_id": self.task_id,
            "decision": self.decision,
            "reason_category": self.reason_category,
            "reason_text": self.reason_text,
            "repair_suggestion": self.repair_suggestion,
            "source": self.source,
            "recorded_at": self.recorded_at,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GateLesson:
        if not isinstance(data, dict):
            raise InvalidLessonError(f"lesson 记录格式错误: {data!r}")
        required = (
            "lesson_id", "gate_id", "task_id", "decision",
            "reason_category", "reason_text", "recorded_at",
        )
        for key in required:
            if key not in data or data[key] in (None, ""):
                raise InvalidLessonError(f"lesson 记录缺少必需字段 '{key}'")
        decision = str(data["decision"])
        category = str(data["reason_category"])
        if decision not in DECISIONS:
            raise InvalidLessonError(
                f"decision 非法: {decision!r}（允许 {DECISIONS}）"
            )
        if category not in REASON_CATEGORIES:
            raise InvalidLessonError(
                f"reason_category 非法: {category!r}（允许 {REASON_CATEGORIES}）"
            )
        schema_version = int(data.get("schema_version", GATE_LESSONS_SCHEMA_VERSION))
        if schema_version != GATE_LESSONS_SCHEMA_VERSION:
            raise InvalidLessonError(
                f"不支持的 lesson schema_version: {schema_version}"
            )
        return cls(
            lesson_id=str(data["lesson_id"]),
            gate_id=str(data["gate_id"]),
            task_id=str(data["task_id"]),
            decision=decision,
            reason_category=category,
            reason_text=str(data["reason_text"]),
            repair_suggestion=(
                str(data["repair_suggestion"])
                if data.get("repair_suggestion") is not None
                else None
            ),
            source=str(data["source"]) if data.get("source") is not None else None,
            recorded_at=str(data["recorded_at"]),
            schema_version=schema_version,
        )


# ── Fingerprint / Lesson Id ────────────────────────────────────────────────


def _normalize_reason(text: str) -> str:
    """Normalize reason text for fingerprinting: collapse whitespace + casefold."""
    return " ".join(str(text).strip().split()).casefold()


def make_lesson_id(
    gate_id: str,
    decision: str,
    reason_category: str,
    reason_text: str,
) -> str:
    """Deterministic lesson id for the given reason fingerprint.

    Same (gate_id, decision, reason_category, normalized reason_text)
    always yields the same lesson id — this is the dedup key.
    """
    fingerprint = "|".join([
        str(gate_id),
        str(decision),
        str(reason_category),
        _normalize_reason(reason_text),
    ])
    digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
    return f"GL-{digest[:16].upper()}"


# ── Storage ────────────────────────────────────────────────────────────────


def lessons_path(
    project_root: str | Path,
    relative_path: str | None = None,
) -> Path:
    """Absolute path of the lessons file under the project root."""
    return Path(project_root) / (
        relative_path or DEFAULT_LESSONS_RELATIVE_PATH
    )


def load_lessons(
    project_root: str | Path,
    relative_path: str | None = None,
) -> list[GateLesson]:
    """Load all recorded lessons. Missing / empty file → empty list.

    Malformed entries fail closed: any record that violates the schema
    raises InvalidLessonError instead of being silently dropped — the
    machine never guesses about its own memory.
    """
    path = lessons_path(project_root, relative_path)
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        raise GateLessonError(
            f"无法解析 lessons 文件 {path}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise GateLessonError(f"lessons 文件格式错误（非 mapping）: {path}")
    if data.get("schema") not in (None, GATE_LESSONS_SCHEMA):
        raise GateLessonError(
            f"不支持的 lessons schema: {data.get('schema')!r}（{path}）"
        )
    raw_lessons = data.get("lessons", [])
    if not isinstance(raw_lessons, list):
        raise GateLessonError(f"lessons 文件格式错误（lessons 非列表）: {path}")
    return [GateLesson.from_dict(rec) for rec in raw_lessons]


def _save_lessons(path: Path, lessons: list[GateLesson]) -> None:
    """Write all lessons atomically (tmp file + rename), append-style log."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": GATE_LESSONS_SCHEMA,
        "schema_version": GATE_LESSONS_SCHEMA_VERSION,
        "lessons": [lesson.to_dict() for lesson in lessons],
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.dump(
            payload,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )
    os.replace(tmp, path)


def record_gate_lesson(
    project_root: str | Path,
    *,
    gate_id: str,
    task_id: str,
    decision: str,
    reason_category: str,
    reason_text: str,
    repair_suggestion: str | None = None,
    source: str | None = None,
    recorded_at: str | None = None,
    relative_path: str | None = None,
) -> tuple[GateLesson, bool]:
    """Record one gate lesson; idempotent for identical fingerprints.

    Args:
        project_root: Project root that contains the .ai/ governance tree.
        gate_id: Gate that produced the lesson (e.g. G-T-0005-CLOSEOUT-REVIEW).
        task_id: Task the gate belongs to.
        decision: rejected | repair_requested | approved.
        reason_category: scope | evidence | risk | wording | other.
        reason_text: Rejection / repair reason (free text).
        repair_suggestion: Optional suggested fix direction.
        source: Optional origin, e.g. decision packet id ("HRP-...").
        recorded_at: Optional ISO timestamp; defaults to now (UTC).
        relative_path: Override for the lessons file location (tests).

    Returns:
        (lesson, created): lesson is the stored record — either freshly
        created or the existing duplicate; created is True only when a new
        record was appended.
    """
    if not isinstance(gate_id, str) or not gate_id.strip():
        raise InvalidLessonError("gate_id 不能为空")
    if not isinstance(task_id, str) or not task_id.strip():
        raise InvalidLessonError("task_id 不能为空")
    if decision not in DECISIONS:
        raise InvalidLessonError(f"decision 非法: {decision!r}（允许 {DECISIONS}）")
    if reason_category not in REASON_CATEGORIES:
        raise InvalidLessonError(
            f"reason_category 非法: {reason_category!r}"
            f"（允许 {REASON_CATEGORIES}）"
        )
    if not isinstance(reason_text, str) or not reason_text.strip():
        raise InvalidLessonError("reason_text 不能为空")

    lesson_id = make_lesson_id(gate_id, decision, reason_category, reason_text)

    # T-0095: the read-modify-write below is serialized by a process-internal
    # lock so concurrent recorders never lose records (load->append->save is
    # not atomic without it).  Validation above stays outside the lock.
    with _RECORD_LOCK:
        lessons = load_lessons(project_root, relative_path)
        for existing in lessons:
            if existing.lesson_id == lesson_id:
                # Same gate + same decision + same reason fingerprint → idempotent.
                return existing, False

        lesson = GateLesson(
            lesson_id=lesson_id,
            gate_id=gate_id.strip(),
            task_id=task_id.strip(),
            decision=decision,
            reason_category=reason_category,
            reason_text=reason_text.strip(),
            repair_suggestion=(
                repair_suggestion.strip()
                if isinstance(repair_suggestion, str) and repair_suggestion.strip()
                else None
            ),
            source=source.strip() if isinstance(source, str) and source.strip() else None,
            recorded_at=recorded_at or datetime.now(timezone.utc).isoformat(),
        )
        _save_lessons(lessons_path(project_root, relative_path), lessons + [lesson])
        return lesson, True


# ── Retrieval ──────────────────────────────────────────────────────────────


def by_gate_id(
    project_root: str | Path,
    gate_id: str,
    relative_path: str | None = None,
) -> list[GateLesson]:
    """All lessons for one gate, in recording order."""
    return [
        lesson for lesson in load_lessons(project_root, relative_path)
        if lesson.gate_id == gate_id
    ]


def by_reason_category(
    project_root: str | Path,
    category: str,
    relative_path: str | None = None,
) -> list[GateLesson]:
    """All lessons attributed to one reason bucket (scope/evidence/risk/...)."""
    if category not in REASON_CATEGORIES:
        raise InvalidLessonError(
            f"reason_category 非法: {category!r}（允许 {REASON_CATEGORIES}）"
        )
    return [
        lesson for lesson in load_lessons(project_root, relative_path)
        if lesson.reason_category == category
    ]


def recent(
    project_root: str | Path,
    limit: int = DEFAULT_RECENT_LIMIT,
    relative_path: str | None = None,
) -> list[GateLesson]:
    """Most recent lessons, newest first (stable on equal timestamps)."""
    lessons = sorted(
        load_lessons(project_root, relative_path),
        key=lambda lesson: lesson.recorded_at,
        reverse=True,
    )
    return lessons[: max(0, limit)]


def search(
    project_root: str | Path,
    keyword: str,
    relative_path: str | None = None,
) -> list[GateLesson]:
    """Case-insensitive substring search over lesson content.

    Matches reason_text, repair_suggestion, gate_id, task_id, decision,
    reason_category and source. Empty keyword returns everything.
    """
    needle = str(keyword).casefold()
    if not needle:
        return load_lessons(project_root, relative_path)
    results: list[GateLesson] = []
    for lesson in load_lessons(project_root, relative_path):
        haystack = " ".join([
            lesson.gate_id,
            lesson.task_id,
            lesson.decision,
            lesson.reason_category,
            lesson.reason_text,
            lesson.repair_suggestion or "",
            lesson.source or "",
        ]).casefold()
        if needle in haystack:
            results.append(lesson)
    return results


def suggest_related_lessons(
    project_root: str | Path,
    *,
    gate_id: str | None = None,
    reason_category: str | None = None,
    limit: int = DEFAULT_SUGGEST_LIMIT,
    relative_path: str | None = None,
) -> list[GateLesson]:
    """Related history for a decision packet: same gate or same reason bucket.

    Combines by_gate_id + by_reason_category, de-duplicates by lesson_id,
    sorts newest first, and caps at ``limit``. Missing gate_id or category
    simply contributes nothing (no error) — used for optional enhancement.
    """
    seen: dict[str, GateLesson] = {}
    if gate_id:
        for lesson in by_gate_id(project_root, gate_id, relative_path):
            seen[lesson.lesson_id] = lesson
    if reason_category:
        for lesson in by_reason_category(project_root, reason_category, relative_path):
            seen[lesson.lesson_id] = lesson
    ordered = sorted(seen.values(), key=lambda lesson: lesson.recorded_at, reverse=True)
    return ordered[: max(0, limit)]


# ── Decision Packet Integration (optional, default unchanged) ──────────────


def related_lessons_summary(
    lessons: list[GateLesson],
    limit: int | None = None,
) -> str:
    """Render lessons as a compact markdown summary for a decision packet.

    One bullet per lesson: gate id — decision (reason bucket): reason text,
    plus repair suggestion and source when present. Empty input → "".
    """
    lines: list[str] = []
    for lesson in lessons[:limit] if limit is not None else lessons:
        header = (
            f"- **{lesson.gate_id}** — {lesson.decision} "
            f"({lesson.reason_category}): {lesson.reason_text}"
        )
        lines.append(header)
        if lesson.repair_suggestion:
            lines.append(f"  - 修复建议: {lesson.repair_suggestion}")
        if lesson.source:
            lines.append(f"  - 来源: {lesson.source}")
    return "\n".join(lines)
