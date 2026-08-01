"""
Tests for loop_core.gate_feedback — gate decision feedback loop (U4, T-0089).

Covers T-0089 AC-01:
- AC-01a: structured lesson recording — all fields present (gate_id,
  task_id, decision, reason_category, reason_text, repair_suggestion,
  source, recorded_at) + schema version, deterministic lesson_id
- AC-01b: dedup / idempotency — same gate + same decision + same reason
  fingerprint records at most once
- AC-01c: retrieval — by_gate_id / by_reason_category / recent(limit) /
  search(keyword)
- AC-01d: HumanReviewPacket integration — optional related_experience
  param effective, default behavior unchanged

Plus fail-closed validation: invalid decision / category / empty fields
raise InvalidLessonError; malformed lessons file raises instead of being
silently dropped.
"""
from __future__ import annotations

from datetime import datetime

import pytest
import yaml

from loop_core.gate_feedback import (
    DECISION_APPROVED,
    DECISION_REJECTED,
    DECISION_REPAIR_REQUESTED,
    DEFAULT_LESSONS_RELATIVE_PATH,
    GATE_LESSONS_SCHEMA,
    GATE_LESSONS_SCHEMA_VERSION,
    GateLesson,
    GateLessonError,
    InvalidLessonError,
    by_gate_id,
    by_reason_category,
    load_lessons,
    make_lesson_id,
    recent,
    record_gate_lesson,
    related_lessons_summary,
    search,
    suggest_related_lessons,
)
from loop_core.human_review_packet import HumanReviewPacketBuilder

GATE_ID = "G-T-0005-CLOSEOUT-REVIEW"
TASK_ID = "T-0005"


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def project(tmp_path):
    """A scratch project root; lessons are recorded under tmp_path/.ai."""
    return tmp_path


def _sample_kwargs(**overrides):
    kwargs = {
        "gate_id": GATE_ID,
        "task_id": TASK_ID,
        "decision": DECISION_REJECTED,
        "reason_category": "evidence",
        "reason_text": (
            "Closeout review failed because CONTRACTS.md and KNOWN_ISSUES.md "
            "still contain stale pre-installation statements."
        ),
        "repair_suggestion": (
            "Repair stale installation-state wording in CONTRACTS.md and "
            "KNOWN_ISSUES.md, then rerun the closeout review."
        ),
        "source": "HRP-00000001",
    }
    kwargs.update(overrides)
    return kwargs


def _record(project, **overrides):
    return record_gate_lesson(project, **_sample_kwargs(**overrides))


# ── AC-01a: Structured recording ───────────────────────────────────────────


class TestAC01aStructuredRecording:
    """A recorded lesson is fully structured with all schema fields."""

    def test_record_creates_lessons_file(self, project):
        lesson, created = _record(project)
        assert created is True
        path = project / DEFAULT_LESSONS_RELATIVE_PATH
        assert path.exists()
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["schema"] == GATE_LESSONS_SCHEMA
        assert data["schema_version"] == GATE_LESSONS_SCHEMA_VERSION
        assert len(data["lessons"]) == 1
        assert data["lessons"][0]["lesson_id"] == lesson.lesson_id

    def test_record_fields_complete(self, project):
        lesson, _ = _record(project)
        assert lesson.lesson_id.startswith("GL-")
        assert lesson.gate_id == GATE_ID
        assert lesson.task_id == TASK_ID
        assert lesson.decision == DECISION_REJECTED
        assert lesson.reason_category == "evidence"
        assert lesson.reason_text
        assert lesson.repair_suggestion
        assert lesson.source == "HRP-00000001"
        assert lesson.schema_version == GATE_LESSONS_SCHEMA_VERSION
        # recorded_at is a parseable ISO-8601 UTC timestamp
        datetime.fromisoformat(lesson.recorded_at)
        assert lesson.recorded_at.endswith("+00:00")

    def test_lesson_id_deterministic(self, project):
        lesson1, created1 = _record(project)
        lesson2, created2 = _record(project)
        assert created1 is True and created2 is False
        assert lesson1.lesson_id == lesson2.lesson_id
        # Deterministic across processes: recompute the id and compare
        assert lesson1.lesson_id == make_lesson_id(
            GATE_ID, DECISION_REJECTED, "evidence",
            _sample_kwargs()["reason_text"],
        )

    def test_repair_suggestion_and_source_optional(self, project):
        lesson, created = record_gate_lesson(
            project,
            gate_id="G-T-0009-X",
            task_id="T-0009",
            decision=DECISION_REPAIR_REQUESTED,
            reason_category="wording",
            reason_text="Scope wording conflicts with the registry.",
        )
        assert created is True
        assert lesson.repair_suggestion is None
        assert lesson.source is None

    def test_record_approved_decision_allowed(self, project):
        lesson, created = record_gate_lesson(
            project,
            gate_id="G-T-0003-SYNC-STATE",
            task_id="T-0003",
            decision=DECISION_APPROVED,
            reason_category="other",
            reason_text="State sync approved with legacy pre-field record.",
        )
        assert created is True
        assert lesson.decision == DECISION_APPROVED

    def test_roundtrip_load_keeps_fields(self, project):
        lesson, _ = _record(project)
        loaded = load_lessons(project)
        assert len(loaded) == 1
        assert loaded[0].to_dict() == lesson.to_dict()
        # from_dict validation round-trip
        assert GateLesson.from_dict(lesson.to_dict()).to_dict() == lesson.to_dict()

    def test_invalid_decision_raises(self, project):
        with pytest.raises(InvalidLessonError):
            _record(project, decision="maybe")

    def test_invalid_reason_category_raises(self, project):
        with pytest.raises(InvalidLessonError):
            _record(project, reason_category="process")

    def test_empty_reason_raises(self, project):
        with pytest.raises(InvalidLessonError):
            _record(project, reason_text="   ")

    def test_empty_gate_id_raises(self, project):
        with pytest.raises(InvalidLessonError):
            _record(project, gate_id="")

    def test_by_category_unknown_raises(self, project):
        with pytest.raises(InvalidLessonError):
            by_reason_category(project, "process")

    def test_malformed_lessons_file_fails_closed(self, project):
        path = project / DEFAULT_LESSONS_RELATIVE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("lessons: [not-a-dict]\n", encoding="utf-8")
        with pytest.raises(InvalidLessonError):
            load_lessons(project)

    def test_unsupported_schema_fails_closed(self, project):
        path = project / DEFAULT_LESSONS_RELATIVE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.dump({"schema": "other", "lessons": []}), encoding="utf-8"
        )
        with pytest.raises(GateLessonError):
            load_lessons(project)

    def test_missing_file_loads_empty(self, project):
        assert load_lessons(project) == []


# ── AC-01b: Dedup / idempotency ────────────────────────────────────────────


class TestAC01bDedup:
    """Same gate + same decision + same reason fingerprint records once."""

    def test_identical_record_is_idempotent(self, project):
        lesson1, created1 = _record(project)
        lesson2, created2 = _record(project)
        lesson3, created3 = _record(project)
        assert (created1, created2, created3) == (True, False, False)
        assert lesson1.lesson_id == lesson2.lesson_id == lesson3.lesson_id
        assert len(load_lessons(project)) == 1

    def test_fingerprint_ignores_whitespace_and_case(self, project):
        _record(project, reason_text="  Evidence   Missing. ")
        lesson2, created2 = _record(project, reason_text="evidence missing.")
        assert created2 is False
        assert lesson2.reason_text.strip() == "Evidence   Missing."
        assert len(load_lessons(project)) == 1

    def test_different_reason_text_records_separately(self, project):
        _record(project)
        lesson2, created2 = _record(
            project,
            reason_text="A completely different rejection reason.",
        )
        assert created2 is True
        assert lesson2.lesson_id != load_lessons(project)[0].lesson_id
        assert len(load_lessons(project)) == 2

    def test_different_decision_records_separately(self, project):
        _record(project, decision=DECISION_REJECTED)
        lesson2, created2 = _record(
            project, decision=DECISION_REPAIR_REQUESTED,
            reason_text="User requested repairs to the candidate.",
        )
        assert created2 is True
        assert len(load_lessons(project)) == 2

    def test_different_category_records_separately(self, project):
        _record(project, reason_category="evidence")
        lesson2, created2 = _record(
            project, reason_category="wording",
            reason_text="Stale wording in KNOWN_ISSUES.md.",
        )
        assert created2 is True
        assert len(load_lessons(project)) == 2

    def test_different_gate_records_separately(self, project):
        _record(project, gate_id=GATE_ID)
        lesson2, created2 = _record(
            project, gate_id="G-T-0005-CLOSEOUT-REVIEW-RERUN",
        )
        assert created2 is True
        assert len(load_lessons(project)) == 2

    def test_duplicate_across_append_generations(self, project):
        """Re-recording after other lessons were appended still dedups."""
        _record(project)
        _record(
            project, gate_id="G-T-0009-X", task_id="T-0009",
            decision=DECISION_REPAIR_REQUESTED, reason_category="wording",
            reason_text="Another lesson in between.",
        )
        lesson, created = _record(project)
        assert created is False
        assert lesson.gate_id == GATE_ID
        assert len(load_lessons(project)) == 2


# ── AC-01c: Retrieval ──────────────────────────────────────────────────────


class TestAC01cRetrieval:
    """by_gate_id / by_reason_category / recent / search work as specified."""

    def _seed(self, project):
        """Four lessons across two gates and two categories, with explicit
        recorded_at timestamps so ordering is deterministic."""
        timestamps = {
            "t1": "2026-07-01T01:00:00+00:00",
            "t2": "2026-07-02T01:00:00+00:00",
            "t3": "2026-07-03T01:00:00+00:00",
            "t4": "2026-07-04T01:00:00+00:00",
        }
        record_gate_lesson(
            project, gate_id=GATE_ID, task_id=TASK_ID,
            decision=DECISION_REJECTED, reason_category="evidence",
            reason_text="Stale memory blocked closeout.",
            repair_suggestion="Repair stale memory then rerun.",
            recorded_at=timestamps["t1"],
        )
        record_gate_lesson(
            project, gate_id=GATE_ID, task_id=TASK_ID,
            decision=DECISION_REPAIR_REQUESTED, reason_category="wording",
            reason_text="Registry wording conflicts with AGENTS.md.",
            recorded_at=timestamps["t2"],
        )
        record_gate_lesson(
            project, gate_id="G-T-0009-X", task_id="T-0009",
            decision=DECISION_REJECTED, reason_category="evidence",
            reason_text="Missing evidence attachments.",
            recorded_at=timestamps["t3"],
        )
        record_gate_lesson(
            project, gate_id="G-T-0009-X", task_id="T-0009",
            decision=DECISION_REJECTED, reason_category="risk",
            reason_text="Unmitigated deployment risk.",
            repair_suggestion="Add rollback plan.",
            recorded_at=timestamps["t4"],
        )
        return timestamps

    def test_by_gate_id(self, project):
        self._seed(project)
        lessons = by_gate_id(project, GATE_ID)
        assert [lesson.gate_id for lesson in lessons] == [GATE_ID, GATE_ID]
        assert len(lessons) == 2

    def test_by_gate_id_no_match(self, project):
        self._seed(project)
        assert by_gate_id(project, "G-NOPE") == []

    def test_by_reason_category(self, project):
        self._seed(project)
        lessons = by_reason_category(project, "evidence")
        assert [lesson.reason_category for lesson in lessons] == ["evidence", "evidence"]
        assert len(lessons) == 2

    def test_recent_orders_newest_first(self, project):
        timestamps = self._seed(project)
        lessons = recent(project, limit=10)
        assert [lesson.recorded_at for lesson in lessons] == [
            timestamps["t4"], timestamps["t3"], timestamps["t2"], timestamps["t1"],
        ]

    def test_recent_honors_limit(self, project):
        self._seed(project)
        assert len(recent(project, limit=2)) == 2
        assert len(recent(project, limit=0)) == 0

    def test_recent_default_limit(self, project):
        self._seed(project)
        assert len(recent(project)) == 4

    def test_search_reason_text_case_insensitive(self, project):
        self._seed(project)
        assert len(search(project, "STALE")) == 1
        assert search(project, "stale")[0].gate_id == GATE_ID

    def test_search_repair_suggestion(self, project):
        self._seed(project)
        assert len(search(project, "rollback plan")) == 1

    def test_search_gate_id(self, project):
        self._seed(project)
        assert len(search(project, "G-T-0009-X")) == 2

    def test_search_no_match_empty(self, project):
        self._seed(project)
        assert search(project, "nonexistent-keyword") == []

    def test_search_empty_keyword_returns_all(self, project):
        self._seed(project)
        assert len(search(project, "")) == 4

    def test_suggest_related_lessons_combines_and_dedups(self, project):
        self._seed(project)
        suggested = suggest_related_lessons(
            project, gate_id=GATE_ID, reason_category="evidence", limit=10
        )
        # gate_id lessons (2) + evidence lessons (2, one already counted)
        assert len(suggested) == 3
        # newest first
        assert suggested[0].recorded_at == "2026-07-03T01:00:00+00:00"
        assert {lesson.gate_id for lesson in suggested} == {GATE_ID, "G-T-0009-X"}

    def test_suggest_related_lessons_limit(self, project):
        self._seed(project)
        assert len(suggest_related_lessons(
            project, gate_id=GATE_ID, reason_category="evidence", limit=1
        )) == 1

    def test_suggest_related_lessons_no_filters(self, project):
        self._seed(project)
        assert suggest_related_lessons(project) == []


# ── AC-01d: Decision packet integration ────────────────────────────────────


class TestAC01dPacketIntegration:
    """related_experience is optional; default packets are unchanged."""

    def _packet_data(self):
        return {
            "phase": "S5-quality",
            "task_id": "T-0005",
            "artifacts": {"closeout_report": "Closeout review report"},
            "review_results": {"independent-reviewer": "PASS"},
            "quality_report": {"pass": True, "checks": ["OK"], "warnings": []},
        }

    def test_default_packet_unchanged(self, project):
        """No related_experience → no field content, no rendered section."""
        packet = HumanReviewPacketBuilder.from_phase_completion(
            **self._packet_data()
        )
        assert packet.related_experience == ""
        assert "Related Past Experience" not in packet.to_markdown()
        assert "RELATED PAST EXPERIENCE" not in packet.to_plain_text()
        # The standard sections are still all present
        md = packet.to_markdown()
        for section in ("## What We Did", "## Main Risks", "## You Need to Decide"):
            assert section in md

    def test_phase_completion_attaches_related_experience(self, project):
        summary = related_lessons_summary([_record(project)[0]])
        packet = HumanReviewPacketBuilder.from_phase_completion(
            **self._packet_data(), related_experience=summary
        )
        assert packet.related_experience == summary
        md = packet.to_markdown()
        assert "## Related Past Experience" in md
        assert GATE_ID in md
        assert DECISION_REJECTED in md
        assert "evidence" in md
        assert "stale" in md.lower()
        text = packet.to_plain_text()
        assert "RELATED PAST EXPERIENCE" in text
        assert GATE_ID in text

    def test_veto_escalation_attaches_related_experience(self, project):
        summary = related_lessons_summary([_record(project)[0]])
        packet = HumanReviewPacketBuilder.from_veto_escalation(
            vetoes=[{"vetoed_by": "reviewer", "reason": "Concern"}],
            task_id=TASK_ID,
            related_experience=summary,
        )
        assert packet.related_experience == summary
        assert "## Related Past Experience" in packet.to_markdown()

    def test_related_lessons_summary_content(self, project):
        lesson, _ = _record(project)
        summary = related_lessons_summary([lesson])
        assert GATE_ID in summary
        assert DECISION_REJECTED in summary
        assert "evidence" in summary
        assert "stale pre-installation" in summary
        assert "修复建议" in summary
        assert "HRP-00000001" in summary  # source

    def test_related_lessons_summary_empty_input(self, project):
        assert related_lessons_summary([]) == ""

    def test_related_lessons_summary_limit(self, project):
        _record(project)
        record_gate_lesson(
            project, gate_id="G-T-0009-X", task_id="T-0009",
            decision=DECISION_REPAIR_REQUESTED, reason_category="wording",
            reason_text="Second lesson.",
        )
        summary = related_lessons_summary(load_lessons(project), limit=1)
        assert summary.count("**G-") == 1

    def test_end_to_end_feedback_loop(self, project):
        """Record rejection → suggest related → attach to next packet."""
        record_gate_lesson(
            project, gate_id=GATE_ID, task_id=TASK_ID,
            decision=DECISION_REJECTED, reason_category="evidence",
            reason_text="Stale memory blocked the first closeout review.",
            repair_suggestion="Narrow stale-memory repair gate, then rerun.",
            source="HRP-00000001",
        )
        related = suggest_related_lessons(
            project, gate_id=GATE_ID, reason_category="evidence"
        )
        assert len(related) == 1
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S5-quality",
            task_id=TASK_ID,
            artifacts={"closeout_report": "Closeout review report"},
            review_results={"independent-reviewer": "PASS"},
            quality_report={"pass": True, "checks": ["OK"], "warnings": []},
            related_experience=related_lessons_summary(related),
        )
        md = packet.to_markdown()
        assert "## Related Past Experience" in md
        assert "Stale memory blocked the first closeout review." in md
        assert "Narrow stale-memory repair gate" in md

    def test_recorded_at_explicit_timestamp_respected(self, project):
        ts = "2026-08-01T06:00:00+00:00"
        lesson, _ = record_gate_lesson(
            project, gate_id="G-T-0090-X", task_id="T-0090",
            decision=DECISION_REJECTED, reason_category="scope",
            reason_text="Scope exceeded approved gate.",
            recorded_at=ts,
        )
        assert lesson.recorded_at == ts
        assert datetime.fromisoformat(lesson.recorded_at).tzinfo is not None
