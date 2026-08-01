"""T-0097 (AC-01..AC-04): B2 learning loop — incident records, retrospectives,
second-failure doctrine, gate_lessons integration.

Covers:
- AC-01: incident schema (all fields + deterministic IN- id), idempotent
  recording (same source + same fingerprint + same occurrence), append-style
  atomic persistence to .ai/evidence/observability/incidents.yaml, retrieval
  by_category / by_status / by_severity / keyword / by_source, fail-closed
  validation, concurrent RMW safety.
- AC-02: retrospective schema (RT- id linked to an incident, action items
  with owner + deadline + status), open -> done tracking, auto-close when all
  items are done, closed retro immutable.
- AC-03: second-failure detection (same category + same root-cause
  fingerprint recurrence -> task draft), persistence (report level),
  second_failure_block: unresolved -> BLOCK with details; open action item ->
  PASS; closed loop -> PASS; exemption -> PASS; corrupt evidence -> fail-closed
  BLOCK; toggle (env + config, default off).
- AC-04: gate_lessons bridge — >= 2 rejections at the same gate register a
  gate_rejection incident; re-running is idempotent; a new rejection is a new
  occurrence (recurrence).
- Checker CLI (.ai/checkers/second_failure_checker.py): exit 0/1/2.
- S6 hook wiring (loop_enforcement): default-off, opt-in via config, only
  adds blocking conditions.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from loop_core.incidents import (
    CATEGORIES,
    DEFAULT_INCIDENTS_RELATIVE_PATH,
    INCIDENTS_SCHEMA,
    INCIDENTS_SCHEMA_VERSION,
    IncidentError,
    IncidentRecord,
    InvalidIncidentError,
    by_category,
    by_severity,
    by_source,
    by_status,
    load_incidents,
    make_incident_id,
    record_incident,
    register_gate_rejection_incident,
    search,
)
from loop_core.gate_feedback import (
    DECISION_APPROVED,
    DECISION_REJECTED,
    DECISION_REPAIR_REQUESTED,
    record_gate_lesson,
)
from loop_core.retrospectives import (
    DEFAULT_RETROS_RELATIVE_PATH,
    RETROS_SCHEMA,
    RETROS_SCHEMA_VERSION,
    RETRO_STATUS_CLOSED,
    RETRO_STATUS_OPEN,
    ActionItem,
    InvalidRetrospectiveError,
    RetrospectiveError,
    add_action_item,
    by_incident,
    create_retrospective,
    load_retrospectives,
    update_action_item,
)
from loop_core.second_failure import (
    DEFAULT_SECOND_FAILURES_RELATIVE_PATH,
    ENV_ENABLED,
    GATE_BLOCK_CODE,
    SECOND_FAILURES_SCHEMA,
    SECOND_FAILURES_SCHEMA_VERSION,
    InvalidSecondFailureError,
    SecondFailureError,
    SecondFailureGateResult,
    SecondFailureRecord,
    detect_second_failure,
    load_exemptions,
    load_second_failures,
    record_second_failure,
    record_second_failure_exemption,
    resolve_second_failure,
    root_cause_fingerprint,
    second_failure_block,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHECKERS = PROJECT_ROOT / ".ai" / "checkers"
SCRIPTS = PROJECT_ROOT / "hooks" / "scripts"
PYTHON = sys.executable

CATEGORY = "gate_rejection"
SOURCE_ID = "G-T-0005-CLOSEOUT-REVIEW"
OCCURRED_1 = "2026-07-01T09:00:00+00:00"
OCCURRED_2 = "2026-07-10T09:00:00+00:00"

FUTURE = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
PAST = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

# ── shared fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def project(tmp_path):
    """A scratch project root; governance files land under tmp_path/.ai."""
    return tmp_path


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Never leak the second-failure gate toggle between tests."""
    monkeypatch.delenv(ENV_ENABLED, raising=False)


def _incident_kwargs(**overrides):
    kwargs = {
        "category": CATEGORY,
        "severity": "high",
        "scope": "closeout review rejected on stale evidence",
        "source_type": "gate",
        "source_id": SOURCE_ID,
        "root_cause": "stale evidence",
        "title": "Closeout review rejected on stale evidence",
    }
    kwargs.update(overrides)
    return kwargs


def _record(project, occurred_at=OCCURRED_1, **overrides):
    return record_incident(
        project, occurred_at=occurred_at, **_incident_kwargs(**overrides)
    )


def _second_failure_pair(project):
    """Two incidents of the same class (two occurrences) + persisted report."""
    _record(project, occurred_at=OCCURRED_1)
    _record(project, occurred_at=OCCURRED_2)
    return record_second_failure(project)


# ═══════════════════════════════════════════════════════════════════════
# AC-01: incident records
# ═══════════════════════════════════════════════════════════════════════


class TestAC01Incidents:
    def test_record_creates_incidents_file(self, project):
        incident, created = _record(project)
        assert created is True
        path = project / DEFAULT_INCIDENTS_RELATIVE_PATH
        assert path.exists()
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["schema"] == INCIDENTS_SCHEMA
        assert data["schema_version"] == INCIDENTS_SCHEMA_VERSION
        assert len(data["incidents"]) == 1
        assert data["incidents"][0]["incident_id"] == incident.incident_id

    def test_record_fields_complete(self, project):
        incident, _ = _record(project, occurred_at=OCCURRED_1)
        assert incident.incident_id.startswith("IN-")
        assert incident.category == CATEGORY
        assert incident.severity == "high"
        assert incident.scope
        assert incident.occurred_at == OCCURRED_1
        assert incident.discovered_at
        assert incident.status == "open"
        assert incident.source_type == "gate"
        assert incident.source_id == SOURCE_ID
        assert incident.title
        assert incident.root_cause == "stale evidence"
        assert incident.schema_version == INCIDENTS_SCHEMA_VERSION
        datetime.fromisoformat(incident.recorded_at)
        assert incident.recorded_at.endswith("+00:00")

    def test_incident_id_deterministic(self, project):
        incident1, created1 = _record(project, occurred_at=OCCURRED_1)
        incident2, created2 = _record(project, occurred_at=OCCURRED_1)
        assert (created1, created2) == (True, False)
        assert incident1.incident_id == incident2.incident_id
        assert incident1.incident_id == make_incident_id(
            CATEGORY, "gate", SOURCE_ID, "stale evidence",
            _incident_kwargs()["scope"], OCCURRED_1,
        )

    def test_same_occurrence_idempotent(self, project):
        _record(project, occurred_at=OCCURRED_1)
        incident, created = _record(
            project, occurred_at=OCCURRED_1, scope="different wording same event"
        )
        assert created is False
        assert len(load_incidents(project)) == 1

    def test_different_occurrence_records_separately(self, project):
        i1, c1 = _record(project, occurred_at=OCCURRED_1)
        i2, c2 = _record(project, occurred_at=OCCURRED_2)
        assert (c1, c2) == (True, True)
        assert i1.incident_id != i2.incident_id
        assert len(load_incidents(project)) == 2

    def test_different_source_or_category_records_separately(self, project):
        _record(project, occurred_at=OCCURRED_1)
        other, created = record_incident(
            project, category="guard_failure", severity="critical",
            scope="guard DORMANT silent pass", source_type="guard",
            source_id="bash_content_guard", occurred_at=OCCURRED_1,
            root_cause="dormant",
        )
        assert created is True
        assert other.incident_id != load_incidents(project)[0].incident_id
        assert len(load_incidents(project)) == 2

    def test_roundtrip_load_keeps_fields(self, project):
        incident, _ = _record(project, occurred_at=OCCURRED_1)
        loaded = load_incidents(project)
        assert len(loaded) == 1
        assert loaded[0].to_dict() == incident.to_dict()
        assert IncidentRecord.from_dict(incident.to_dict()).to_dict() == (
            incident.to_dict()
        )

    def test_invalid_category_raises(self, project):
        with pytest.raises(InvalidIncidentError):
            _record(project, category="explosion")

    def test_invalid_severity_raises(self, project):
        with pytest.raises(InvalidIncidentError):
            _record(project, severity="P1")

    def test_invalid_status_raises(self, project):
        with pytest.raises(InvalidIncidentError):
            _record(project, status="in_progress")

    def test_invalid_source_type_raises(self, project):
        with pytest.raises(InvalidIncidentError):
            _record(project, source_type="hook")

    def test_empty_scope_raises(self, project):
        with pytest.raises(InvalidIncidentError):
            _record(project, scope="   ")

    def test_empty_source_id_raises(self, project):
        with pytest.raises(InvalidIncidentError):
            _record(project, source_id="")

    def test_by_category_unknown_raises(self, project):
        with pytest.raises(InvalidIncidentError):
            by_category(project, "explosion")

    def test_malformed_file_fails_closed(self, project):
        path = project / DEFAULT_INCIDENTS_RELATIVE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("incidents: [not-a-dict]\n", encoding="utf-8")
        with pytest.raises(InvalidIncidentError):
            load_incidents(project)

    def test_unsupported_schema_fails_closed(self, project):
        path = project / DEFAULT_INCIDENTS_RELATIVE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.dump({"schema": "other", "incidents": []}),
                        encoding="utf-8")
        with pytest.raises(IncidentError):
            load_incidents(project)

    def test_missing_file_loads_empty(self, project):
        assert load_incidents(project) == []

    def test_retrieval_axes(self, project):
        _record(project, occurred_at=OCCURRED_1, severity="high")
        record_incident(
            project, category="slo_breach", severity="critical",
            scope="error budget exhausted at S6", source_type="slo",
            source_id="quality_gate_rejection_rate", occurred_at=OCCURRED_1,
            root_cause="budget exhausted",
        )
        _record(project, occurred_at=OCCURRED_2, severity="medium")
        assert len(by_category(project, CATEGORY)) == 2
        assert len(by_category(project, "slo_breach")) == 1
        assert len(by_status(project, "open")) == 3
        assert len(by_severity(project, "medium")) == 1
        assert len(by_severity(project, "critical")) == 1
        assert len(search(project, "BUDGET")) == 1
        assert len(search(project, "stale")) == 2
        assert len(by_source(project, "gate", SOURCE_ID)) == 2
        assert len(by_source(project, "slo")) == 1
        assert len(by_source(project, "gate", "G-NOPE")) == 0

    def test_search_matches_title_and_source(self, project):
        _record(project, occurred_at=OCCURRED_1, title="Dormant Guard X")
        _record(project, occurred_at=OCCURRED_2, title=None)
        assert len(search(project, "dormant")) == 1
        assert len(search(project, SOURCE_ID)) == 2
        assert len(search(project, "")) == 2

    def test_resolution_field_optional_and_searchable(self, project):
        incident, _ = _record(
            project, occurred_at=OCCURRED_1,
            resolution="repair the stale-memory gate, then rerun",
        )
        assert incident.resolution
        assert len(search(project, "repair the stale-memory")) == 1

    def test_concurrent_distinct_records_not_lost(self, project):
        n = 12
        created_flags = [False] * n
        errors: list[Exception] = []

        def worker(i: int):
            try:
                _, created = record_incident(
                    project, category="other", severity="low",
                    scope=f"concurrent incident {i:03d}",
                    source_type="manual", source_id=f"src-{i:03d}",
                    occurred_at=f"2026-08-0{1 + i % 9}T09:00:00+00:00",
                    root_cause=f"cause {i:03d}",
                )
                created_flags[i] = created
            except Exception as exc:  # noqa: BLE001 — surfaced in the test
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        assert errors == []
        incidents = load_incidents(project)
        assert len(incidents) == n
        assert all(created_flags)
        assert len({inc.incident_id for inc in incidents}) == n


# ═══════════════════════════════════════════════════════════════════════
# AC-02: retrospectives + action items
# ═══════════════════════════════════════════════════════════════════════


class TestAC02Retrospectives:
    def test_create_retro_creates_file(self, project):
        incident, _ = _record(project, occurred_at=OCCURRED_1)
        retro, created = create_retrospective(
            project, incident_id=incident.incident_id,
            root_cause="no freshness verification step",
            action_items=[{
                "owner": "quality-engineer",
                "deadline": "2026-08-15",
                "description": "add a freshness fixture",
            }],
        )
        assert created is True
        path = project / DEFAULT_RETROS_RELATIVE_PATH
        assert path.exists()
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["schema"] == RETROS_SCHEMA
        assert data["schema_version"] == RETROS_SCHEMA_VERSION
        assert len(data["retrospectives"]) == 1
        assert data["retrospectives"][0]["retro_id"] == retro.retro_id

    def test_retro_fields_complete(self, project):
        incident, _ = _record(project, occurred_at=OCCURRED_1)
        retro, _ = create_retrospective(
            project, incident_id=incident.incident_id,
            root_cause="stale memory blocks closeout",
            action_items=[{
                "owner": "quality-engineer",
                "deadline": "2026-08-15",
                "description": "add freshness fixture",
            }],
        )
        assert retro.retro_id.startswith("RT-")
        assert retro.incident_id == incident.incident_id
        assert retro.root_cause == "stale memory blocks closeout"
        assert retro.status == RETRO_STATUS_OPEN
        assert len(retro.action_items) == 1
        item = retro.action_items[0]
        assert item.id.startswith("AI-")
        assert item.owner == "quality-engineer"
        assert item.deadline == "2026-08-15"
        assert item.status == "open"
        assert item.description
        assert item.done_at is None
        datetime.fromisoformat(retro.created_at)
        assert retro.schema_version == RETROS_SCHEMA_VERSION

    def test_retro_id_deterministic_dedup(self, project):
        incident, _ = _record(project, occurred_at=OCCURRED_1)
        retro1, created1 = create_retrospective(
            project, incident_id=incident.incident_id,
            root_cause="same root cause",
            action_items=[{"owner": "qe", "deadline": "2026-08-15",
                           "description": "fix"}],
        )
        retro2, created2 = create_retrospective(
            project, incident_id=incident.incident_id,
            root_cause="Same  Root Cause",
            action_items=[{"owner": "qe", "deadline": "2026-08-15",
                           "description": "fix"}],
        )
        assert (created1, created2) == (True, False)
        assert retro1.retro_id == retro2.retro_id
        assert len(load_retrospectives(project)) == 1

    def test_action_item_owner_required(self, project):
        incident, _ = _record(project, occurred_at=OCCURRED_1)
        with pytest.raises(InvalidRetrospectiveError, match="owner"):
            create_retrospective(
                project, incident_id=incident.incident_id,
                root_cause="rc", action_items=[{
                    "owner": "  ", "deadline": "2026-08-15",
                    "description": "fix",
                }],
            )

    def test_action_item_deadline_required_and_parseable(self, project):
        incident, _ = _record(project, occurred_at=OCCURRED_1)
        with pytest.raises(InvalidRetrospectiveError, match="deadline"):
            create_retrospective(
                project, incident_id=incident.incident_id, root_cause="rc",
                action_items=[{"owner": "qe", "deadline": "",
                               "description": "fix"}],
            )
        with pytest.raises(InvalidRetrospectiveError, match="deadline"):
            create_retrospective(
                project, incident_id=incident.incident_id, root_cause="rc",
                action_items=[{"owner": "qe", "deadline": "not-a-date",
                               "description": "fix"}],
            )

    def test_action_item_description_required(self, project):
        incident, _ = _record(project, occurred_at=OCCURRED_1)
        with pytest.raises(InvalidRetrospectiveError, match="description"):
            create_retrospective(
                project, incident_id=incident.incident_id, root_cause="rc",
                action_items=[{"owner": "qe", "deadline": "2026-08-15",
                               "description": "  "}],
            )

    def test_add_action_item_appends_and_dedups(self, project):
        incident, _ = _record(project, occurred_at=OCCURRED_1)
        retro, _ = create_retrospective(
            project, incident_id=incident.incident_id, root_cause="rc"
        )
        retro, item, created = add_action_item(
            project, retro.retro_id, owner="delivery-manager",
            deadline="2026-08-20", description="triage next occurrence",
        )
        assert created is True
        assert item.id.startswith("AI-")
        retro, item2, created2 = add_action_item(
            project, retro.retro_id, owner="delivery-manager",
            deadline="2026-08-20", description="Triage Next Occurrence",
        )
        assert created2 is False
        assert item.id == item2.id
        assert len(retro.action_items) == 1

    def test_add_action_item_to_closed_retro_raises(self, project):
        incident, _ = _record(project, occurred_at=OCCURRED_1)
        retro, _ = create_retrospective(
            project, incident_id=incident.incident_id, root_cause="rc",
            action_items=[{"owner": "qe", "deadline": "2026-08-15",
                           "description": "fix"}],
        )
        update_action_item(project, retro.retro_id, retro.action_items[0].id)
        with pytest.raises(RetrospectiveError, match="closed"):
            add_action_item(project, retro.retro_id, owner="qe",
                            deadline="2026-08-30", description="more")

    def test_update_action_item_open_to_done(self, project):
        incident, _ = _record(project, occurred_at=OCCURRED_1)
        retro, _ = create_retrospective(
            project, incident_id=incident.incident_id, root_cause="rc",
            action_items=[{"owner": "qe", "deadline": "2026-08-15",
                           "description": "fix"}],
        )
        item = retro.action_items[0]
        retro, item = update_action_item(project, retro.retro_id, item.id)
        assert item.status == "done"
        assert item.done_at is not None
        datetime.fromisoformat(item.done_at)

    def test_retro_closes_when_all_items_done(self, project):
        incident, _ = _record(project, occurred_at=OCCURRED_1)
        retro, _ = create_retrospective(
            project, incident_id=incident.incident_id, root_cause="rc",
            action_items=[
                {"owner": "qe", "deadline": "2026-08-15", "description": "a"},
                {"owner": "dm", "deadline": "2026-08-16", "description": "b"},
            ],
        )
        retro, _ = update_action_item(project, retro.retro_id,
                                      retro.action_items[0].id)
        assert retro.status == RETRO_STATUS_OPEN  # one still open
        retro, _ = update_action_item(project, retro.retro_id,
                                      retro.action_items[1].id)
        assert retro.status == RETRO_STATUS_CLOSED  # all done -> closed
        assert retro.open_action_items == []
        loaded = load_retrospectives(project)[0]
        assert loaded.status == RETRO_STATUS_CLOSED

    def test_closed_retro_immutable(self, project):
        incident, _ = _record(project, occurred_at=OCCURRED_1)
        retro, _ = create_retrospective(
            project, incident_id=incident.incident_id, root_cause="rc",
            action_items=[{"owner": "qe", "deadline": "2026-08-15",
                           "description": "fix"}],
        )
        update_action_item(project, retro.retro_id, retro.action_items[0].id)
        with pytest.raises(RetrospectiveError, match="closed"):
            update_action_item(project, retro.retro_id,
                               retro.action_items[0].id, status="open")

    def test_update_unknown_item_or_retro_raises(self, project):
        incident, _ = _record(project, occurred_at=OCCURRED_1)
        retro, _ = create_retrospective(
            project, incident_id=incident.incident_id, root_cause="rc",
            action_items=[{"owner": "qe", "deadline": "2026-08-15",
                           "description": "fix"}],
        )
        with pytest.raises(RetrospectiveError, match="action_item"):
            update_action_item(project, retro.retro_id, "AI-NOPE")
        with pytest.raises(RetrospectiveError, match="retro"):
            update_action_item(project, "RT-NOPE", "AI-X")

    def test_noop_same_status(self, project):
        incident, _ = _record(project, occurred_at=OCCURRED_1)
        retro, _ = create_retrospective(
            project, incident_id=incident.incident_id, root_cause="rc",
            action_items=[{"owner": "qe", "deadline": "2026-08-15",
                           "description": "fix"}],
        )
        item = retro.action_items[0]
        update_action_item(project, retro.retro_id, item.id)
        retro2, item2 = update_action_item(
            project, retro.retro_id, item.id, status="done"
        )
        assert item2.status == "done"
        assert retro2.status == RETRO_STATUS_CLOSED

    def test_by_incident(self, project):
        incident, _ = _record(project, occurred_at=OCCURRED_1)
        create_retrospective(
            project, incident_id=incident.incident_id, root_cause="rc-a"
        )
        create_retrospective(
            project, incident_id=incident.incident_id, root_cause="rc-b"
        )
        assert len(by_incident(project, incident.incident_id)) == 2
        assert by_incident(project, "IN-NOPE") == []

    def test_malformed_retros_file_fails_closed(self, project):
        path = project / DEFAULT_RETROS_RELATIVE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("retrospectives: [{broken]\n", encoding="utf-8")
        with pytest.raises(RetrospectiveError):
            load_retrospectives(project)

    def test_action_item_from_dict_validation(self, project):
        with pytest.raises(InvalidRetrospectiveError):
            ActionItem.from_dict({"id": "AI-1", "owner": "qe",
                                  "deadline": "2026-08-15",
                                  "status": "maybe",
                                  "description": "x"})


# ═══════════════════════════════════════════════════════════════════════
# AC-03: second-failure doctrine
# ═══════════════════════════════════════════════════════════════════════


class TestAC03SecondFailure:
    def test_detect_pairs_recurrence(self, project):
        i1, _ = _record(project, occurred_at=OCCURRED_1)
        i2, _ = _record(project, occurred_at=OCCURRED_2)
        records = detect_second_failure(load_incidents(project))
        assert len(records) == 1
        rec = records[0]
        assert rec.second_failure_id.startswith("SF-")
        assert rec.first_incident_id == i1.incident_id
        assert rec.second_incident_id == i2.incident_id
        assert rec.category == CATEGORY
        assert rec.source_id == SOURCE_ID
        assert "stale evidence" in rec.root_cause_fingerprint
        assert rec.status == "open"
        # task draft: title/scope/reason, never auto-registered
        assert rec.task_draft["title"].startswith("[draft]")
        assert rec.task_draft["scope"]
        assert i1.incident_id in rec.task_draft["reason"]
        assert i2.incident_id in rec.task_draft["reason"]

    def test_detect_no_recurrence_single(self, project):
        _record(project, occurred_at=OCCURRED_1)
        assert detect_second_failure(load_incidents(project)) == []

    def test_detect_no_recurrence_different_cause(self, project):
        _record(project, occurred_at=OCCURRED_1, root_cause="stale evidence")
        _record(project, occurred_at=OCCURRED_2, root_cause="scope creep")
        assert detect_second_failure(load_incidents(project)) == []

    def test_detect_no_recurrence_different_category(self, project):
        _record(project, occurred_at=OCCURRED_1)
        record_incident(
            project, category="slo_breach", severity="high",
            scope="budget exhausted", source_type="slo",
            source_id="delivery_gate_rejection_rate",
            occurred_at=OCCURRED_2, root_cause="budget exhausted",
        )
        assert detect_second_failure(load_incidents(project)) == []

    def test_detect_third_occurrence_two_records(self, project):
        _record(project, occurred_at=OCCURRED_1)
        _record(project, occurred_at=OCCURRED_2)
        _record(project, occurred_at="2026-07-20T09:00:00+00:00")
        records = detect_second_failure(load_incidents(project))
        assert len(records) == 2
        assert records[0].second_incident_id == records[1].first_incident_id

    def test_detect_min_recurrences_validation(self, project):
        with pytest.raises(InvalidSecondFailureError):
            detect_second_failure([], min_recurrences=1)
        with pytest.raises(InvalidSecondFailureError):
            detect_second_failure([], min_recurrences="x")

    def test_record_second_failure_persists_and_idempotent(self, project):
        records, flags = _second_failure_pair(project)
        assert len(records) == 1 and flags == [True]
        path = project / DEFAULT_SECOND_FAILURES_RELATIVE_PATH
        assert path.exists()
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["schema"] == SECOND_FAILURES_SCHEMA
        assert data["schema_version"] == SECOND_FAILURES_SCHEMA_VERSION
        records2, flags2 = record_second_failure(project)
        assert len(records2) == 1 and flags2 == [False]
        assert len(load_second_failures(project)) == 1

    def test_root_cause_fingerprint_ignores_whitespace_case(self, project):
        _record(project, occurred_at=OCCURRED_1)
        i2, _ = _record(project, occurred_at=OCCURRED_2,
                        root_cause="  Stale   EVIDENCE ")
        first = load_incidents(project)[0]
        assert root_cause_fingerprint(first) == root_cause_fingerprint(i2)

    def test_block_no_records_pass(self, project, monkeypatch):
        monkeypatch.setenv(ENV_ENABLED, "1")
        result = second_failure_block(project)
        assert result.decision == "PASS"
        assert result.passed
        assert result.blocking == []

    def test_block_unresolved_blocks(self, project, monkeypatch):
        monkeypatch.setenv(ENV_ENABLED, "1")
        _second_failure_pair(project)
        result = second_failure_block(project)
        assert result.decision == "BLOCK"
        assert result.status == "BLOCKED"
        assert GATE_BLOCK_CODE in result.reason
        assert len(result.blocking) == 1
        detail = result.blocking[0]
        assert detail["first_incident_id"]
        assert detail["second_incident_id"]
        assert detail["category"] == CATEGORY
        assert "task_draft" in detail
        assert "no retrospective yet" in detail["reason"]

    def test_block_retro_with_zero_items_blocks(self, project, monkeypatch):
        monkeypatch.setenv(ENV_ENABLED, "1")
        records, _ = _second_failure_pair(project)
        create_retrospective(
            project, incident_id=records[0].second_incident_id,
            root_cause="rc"
        )  # retro without any action item
        result = second_failure_block(project)
        assert result.decision == "BLOCK"
        assert "no open action item" in result.blocking[0]["reason"]

    def test_block_open_action_item_passes(self, project, monkeypatch):
        monkeypatch.setenv(ENV_ENABLED, "1")
        records, _ = _second_failure_pair(project)
        retro, _ = create_retrospective(
            project, incident_id=records[0].second_incident_id,
            root_cause="stale evidence process gap",
            action_items=[{
                "owner": "quality-engineer", "deadline": "2026-08-15",
                "description": "add freshness fixture",
            }],
        )
        result = second_failure_block(project)
        assert result.decision == "PASS"
        assert any(retro.retro_id in note for note in result.notes)
        assert result.blocking == []

    def test_block_retro_closed_passes(self, project, monkeypatch):
        """All action items done -> loop closed -> the recurrence no longer
        blocks (completion is the closure path of the doctrine)."""
        monkeypatch.setenv(ENV_ENABLED, "1")
        records, _ = _second_failure_pair(project)
        retro, _ = create_retrospective(
            project, incident_id=records[0].second_incident_id,
            root_cause="rc",
            action_items=[{"owner": "qe", "deadline": "2026-08-15",
                           "description": "fix"}],
        )
        update_action_item(project, retro.retro_id, retro.action_items[0].id)
        result = second_failure_block(project)
        assert result.decision == "PASS"
        assert any("closed" in note for note in result.notes)

    def test_block_explicit_resolve_passes(self, project, monkeypatch):
        monkeypatch.setenv(ENV_ENABLED, "1")
        records, _ = _second_failure_pair(project)
        result = second_failure_block(project)
        assert result.decision == "BLOCK"
        resolve_second_failure(project, records[0].second_failure_id)
        result = second_failure_block(project)
        assert result.decision == "PASS"
        assert any("explicitly resolved" in note for note in result.notes)

    def test_exemption_overrides_block(self, project, monkeypatch):
        monkeypatch.setenv(ENV_ENABLED, "1")
        _second_failure_pair(project)
        assert second_failure_block(project).decision == "BLOCK"
        entry = record_second_failure_exemption(
            project, reason="user-approved waiver", expires_at=FUTURE,
            approver="user",
        )
        result = second_failure_block(project)
        assert result.decision == "PASS"
        assert result.exemption is not None
        assert result.exemption["id"] == entry["id"]
        assert "exemption SF-EX-0001 in effect" in result.reason

    def test_expired_exemption_ineffective(self, project, monkeypatch):
        monkeypatch.setenv(ENV_ENABLED, "1")
        _second_failure_pair(project)
        record_second_failure_exemption(
            project, reason="stale waiver", expires_at=PAST, approver="user"
        )
        result = second_failure_block(project)
        assert result.decision == "BLOCK"
        assert any("expired" in w for w in result.warnings)

    def test_exemption_missing_approver_invalid(self, project, monkeypatch):
        monkeypatch.setenv(ENV_ENABLED, "1")
        _second_failure_pair(project)
        path = project / ".ai" / "evidence" / "observability" / \
            "second-failure-exemptions.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "schema_version": 1,
            "exemptions": [{"id": "SF-EX-0001", "reason": "r",
                            "expires_at": FUTURE, "approver": ""}],
        }), encoding="utf-8")
        result = second_failure_block(project)
        assert result.decision == "BLOCK"
        assert any("no approver" in w for w in result.warnings)

    def test_exemption_validation(self, project):
        with pytest.raises(ValueError, match="reason"):
            record_second_failure_exemption(project, reason="  ",
                                            expires_at=FUTURE, approver="user")
        with pytest.raises(ValueError, match="approver"):
            record_second_failure_exemption(project, reason="r",
                                            expires_at=FUTURE, approver="")
        with pytest.raises(ValueError, match="expires_at"):
            record_second_failure_exemption(project, reason="r",
                                            expires_at="not-a-date",
                                            approver="user")

    def test_exemption_ledger_append_only(self, project):
        e1 = record_second_failure_exemption(
            project, reason="first", expires_at=FUTURE, approver="user")
        e2 = record_second_failure_exemption(
            project, reason="second", expires_at=FUTURE,
            approver="delivery-manager")
        assert (e1["id"], e2["id"]) == ("SF-EX-0001", "SF-EX-0002")
        assert len(load_exemptions(project)) == 2
        assert load_exemptions(project)[0] == e1

    def test_block_corrupt_evidence_fail_closed(self, project, monkeypatch):
        monkeypatch.setenv(ENV_ENABLED, "1")
        path = project / DEFAULT_INCIDENTS_RELATIVE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{corrupt", encoding="utf-8")
        result = second_failure_block(project)
        assert result.decision == "BLOCK"
        assert result.status == "NOT_AVAILABLE"
        assert "unparseable" in result.reason
        assert any("incidents.yaml" in m for m in result.blocking[0].values())

    def test_toggle_env_disabled_passes(self, project, monkeypatch):
        monkeypatch.setenv(ENV_ENABLED, "0")
        _second_failure_pair(project)
        result = second_failure_block(project)
        assert result.decision == "PASS"
        assert result.status == "DISABLED"
        assert result.gate_enabled is False

    def test_toggle_env_enabled(self, project, monkeypatch):
        monkeypatch.setenv(ENV_ENABLED, "true")
        _second_failure_pair(project)
        result = second_failure_block(project)
        assert result.decision == "BLOCK"
        assert result.gate_enabled is True

    def test_toggle_config_enabled(self, project, monkeypatch):
        monkeypatch.delenv(ENV_ENABLED, raising=False)
        cfg = project / ".zcode" / "skills" / "loop-governance" / "config.yaml"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text("second_failure_gate:\n  enabled: true\n",
                       encoding="utf-8")
        _second_failure_pair(project)
        result = second_failure_block(project)
        assert result.decision == "BLOCK"

    def test_toggle_config_default_disabled(self, project, monkeypatch):
        monkeypatch.delenv(ENV_ENABLED, raising=False)
        _second_failure_pair(project)
        result = second_failure_block(project)
        assert result.decision == "PASS"
        assert result.status == "DISABLED"

    def test_second_failure_record_validation(self, project):
        with pytest.raises(InvalidSecondFailureError):
            SecondFailureRecord.from_dict({
                "second_failure_id": "SF-1", "first_incident_id": "IN-1",
                "second_incident_id": "IN-2", "category": "x",
                "root_cause_fingerprint": "f", "source_type": "gate",
                "source_id": "g", "task_draft": {"title": "t"},
                "status": "open", "detected_at": "2026-07-01T00:00:00+00:00",
            })
        with pytest.raises(InvalidSecondFailureError):
            SecondFailureRecord.from_dict({
                "second_failure_id": "SF-1", "first_incident_id": "IN-1",
                "second_incident_id": "IN-2", "category": "x",
                "root_cause_fingerprint": "f", "source_type": "gate",
                "source_id": "g",
                "task_draft": {"title": "t", "scope": "s", "reason": "r"},
                "status": "maybe", "detected_at": "2026-07-01T00:00:00+00:00",
            })

    def test_resolve_unknown_record_raises(self, project):
        with pytest.raises(SecondFailureError, match="不存在"):
            resolve_second_failure(project, "SF-NOPE")


# ═══════════════════════════════════════════════════════════════════════
# AC-04: gate_lessons integration
# ═══════════════════════════════════════════════════════════════════════


class TestAC04GateLessonsBridge:
    def test_below_threshold_no_incident(self, project):
        record_gate_lesson(
            project, gate_id=SOURCE_ID, task_id="T-0005",
            decision=DECISION_REJECTED, reason_category="evidence",
            reason_text="stale memory",
        )
        incident, created = register_gate_rejection_incident(project, SOURCE_ID)
        assert incident is None and created is False
        assert load_incidents(project) == []

    def test_two_rejections_registers_incident(self, project):
        record_gate_lesson(
            project, gate_id=SOURCE_ID, task_id="T-0005",
            decision=DECISION_REJECTED, reason_category="evidence",
            reason_text="stale memory",
        )
        record_gate_lesson(
            project, gate_id=SOURCE_ID, task_id="T-0006",
            decision=DECISION_REPAIR_REQUESTED, reason_category="wording",
            reason_text="conflicting wording",
        )
        incident, created = register_gate_rejection_incident(project, SOURCE_ID)
        assert created is True
        assert incident is not None
        assert incident.incident_id.startswith("IN-")
        assert incident.category == "gate_rejection"
        assert incident.source_type == "gate"
        assert incident.source_id == SOURCE_ID
        assert "2" in incident.root_cause

    def test_bridge_idempotent_rerun(self, project):
        record_gate_lesson(
            project, gate_id=SOURCE_ID, task_id="T-0005",
            decision=DECISION_REJECTED, reason_category="evidence",
            reason_text="stale memory",
        )
        record_gate_lesson(
            project, gate_id=SOURCE_ID, task_id="T-0006",
            decision=DECISION_REJECTED, reason_category="scope",
            reason_text="scope creep",
        )
        incident, created = register_gate_rejection_incident(project, SOURCE_ID)
        incident2, created2 = register_gate_rejection_incident(project, SOURCE_ID)
        assert (created, created2) == (True, False)
        assert incident.incident_id == incident2.incident_id
        assert len(load_incidents(project)) == 1

    def test_third_rejection_new_occurrence_new_incident(self, project):
        """A new rejection moves the occurrence time -> a new incident, which
        the second-failure detector can pair (recurrence across counts)."""
        for i, reason in enumerate(["stale memory", "scope creep"], start=1):
            record_gate_lesson(
                project, gate_id=SOURCE_ID, task_id=f"T-000{i}",
                decision=DECISION_REJECTED, reason_category="evidence",
                reason_text=reason,
                recorded_at=f"2026-07-0{i}T09:00:00+00:00",
            )
        incident, _ = register_gate_rejection_incident(project, SOURCE_ID)
        record_gate_lesson(
            project, gate_id=SOURCE_ID, task_id="T-0003",
            decision=DECISION_REJECTED, reason_category="evidence",
            reason_text="third distinct reason",
            recorded_at="2026-07-03T09:00:00+00:00",
        )
        incident2, created = register_gate_rejection_incident(project, SOURCE_ID)
        assert created is True
        assert incident2.incident_id != incident.incident_id

    def test_approved_lessons_do_not_count(self, project):
        record_gate_lesson(
            project, gate_id=SOURCE_ID, task_id="T-0005",
            decision=DECISION_APPROVED, reason_category="other",
            reason_text="all good",
        )
        incident, created = register_gate_rejection_incident(project, SOURCE_ID)
        assert incident is None and created is False

    def test_min_rejections_parameter(self, project):
        for i in range(3):
            record_gate_lesson(
                project, gate_id=SOURCE_ID, task_id=f"T-{i}",
                decision=DECISION_REJECTED, reason_category="evidence",
                reason_text=f"reason {i}",
            )
        incident, created = register_gate_rejection_incident(
            project, SOURCE_ID, min_rejections=3
        )
        assert created is True
        assert "3" in incident.root_cause

    def test_min_rejections_below_2_raises(self, project):
        with pytest.raises(InvalidIncidentError, match="min_rejections"):
            register_gate_rejection_incident(project, SOURCE_ID,
                                             min_rejections=1)

    def test_bridge_rejects_empty_gate_id(self, project):
        with pytest.raises(InvalidIncidentError, match="gate_id"):
            register_gate_rejection_incident(project, "  ")


# ═══════════════════════════════════════════════════════════════════════
# Checker CLI (.ai/checkers/second_failure_checker.py)
# ═══════════════════════════════════════════════════════════════════════

CHECKER = CHECKERS / "second_failure_checker.py"


class TestSecondFailureCheckerCli:
    def _run(self, root: Path, *extra: str, env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [PYTHON, str(CHECKER), str(root), *extra],
            capture_output=True, text=True,
            env=env if env is not None else dict(os.environ), timeout=60,
        )

    def _enabled_env(self) -> dict:
        env = dict(os.environ)
        env[ENV_ENABLED] = "1"
        return env

    def test_cli_pass_exit_0(self, project):
        r = self._run(project, env=self._enabled_env())
        assert r.returncode == 0, r.stderr
        payload = json.loads(r.stdout)
        assert payload["checker_id"] == "second_failure"
        assert payload["decision"] == "PASS"
        assert payload["exit_code"] == 0

    def test_cli_block_exit_1(self, project):
        _second_failure_pair(project)
        r = self._run(project, env=self._enabled_env())
        assert r.returncode == 1, r.stderr
        payload = json.loads(r.stdout)
        assert payload["decision"] == "BLOCK"
        assert payload["exit_code"] == 1
        assert GATE_BLOCK_CODE in payload["reason"]
        assert payload["blocking"]

    def test_cli_error_exit_2_bad_root(self):
        r = self._run(Path("Z:/definitely/not/a/project"))
        assert r.returncode == 2
        assert json.loads(r.stdout)["status"] == "error"

    def test_cli_disabled_exit_0(self, project):
        _second_failure_pair(project)
        r = self._run(project)  # no env -> default disabled
        assert r.returncode == 0, r.stderr
        payload = json.loads(r.stdout)
        assert payload["status_detail"] == "DISABLED"

    def test_cli_detect_flag_persists_report(self, project):
        """--detect runs detection first and persists the report before
        evaluating; without the flag the gate is read-only."""
        _record(project, occurred_at=OCCURRED_1)
        _record(project, occurred_at=OCCURRED_2)
        path = project / DEFAULT_SECOND_FAILURES_RELATIVE_PATH
        assert not path.exists()  # recording incidents never writes the report
        r = self._run(project, "--detect", env=self._enabled_env())
        assert r.returncode == 1, r.stderr
        assert path.exists()
        assert len(load_second_failures(project)) == 1

    def test_cli_output_file(self, project):
        out = project / "sf_result.json"
        r = self._run(project, "--output", str(out), env=self._enabled_env())
        assert r.returncode == 0, r.stderr
        assert json.loads(out.read_text(encoding="utf-8"))["checker_id"] == (
            "second_failure"
        )


# ═══════════════════════════════════════════════════════════════════════
# S6 hook wiring (loop_enforcement check_phase_gate_enforcement)
# ═══════════════════════════════════════════════════════════════════════

GOVERNANCE_CONFIG_YAML = """\
version: 1
gate_guard:
  enabled: true
  fail_on_state_error: closed
path_guard:
  enabled: true
  decision: ask
"""

STATE_S6 = """\
schema_version: 1
project_name: test-s6
current_phase: S6-delivery
loop_mode: FULL
current_task_id: T-0001
"""

TASK_CONTRACT = """\
# Task T-0001
allowed_paths:
- src/
- tests/
developer_agent_id: "agent-001"
reviewer_agent_id: "agent-002"
"""


def _write_slo_sources(root: Path) -> None:
    """Healthy error-budget sources so the SLO gate passes."""
    gates = [{
        "id": "G-T-9000-REQUIREMENTS", "task_id": "T-900",
        "gate_type": "user-approval", "status": "approved",
        "decision": "approved",
        "requested_at": "2026-07-01T09:00:00+08:00",
        "recorded_at": "2026-07-01T10:00:00+08:00",
        "evidence": ".ai/evidence/T-900/a.md",
    }]
    path = root / ".ai" / "gates.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "schema_version: 1\n" + "gates:\n"
        + "\n".join(f"- {json.dumps(g)}" for g in gates), encoding="utf-8",
    )
    tasks = [{
        "id": "T-900", "status": "completed", "phase": "S6-delivery",
        "created_at": "2026-07-01T00:00:00+08:00",
        "updated_at": "2026-07-03T00:00:00+08:00",
    }]
    task_path = root / ".ai" / "task_graph.yaml"
    task_path.write_text(
        "schema_version: 1\n" + "tasks:\n"
        + "\n".join(f"- {json.dumps(t)}" for t in tasks), encoding="utf-8",
    )
    events = root / ".ai" / "evidence" / "observability" / "guard-events.jsonl"
    events.parent.mkdir(parents=True, exist_ok=True)
    events.write_text(json.dumps({
        "event_id": "e1", "guard_id": "g_alpha", "capability_id": None,
        "check_type": "death", "result": "PASS", "duration_ms": 5.0,
        "failure_reason": None, "timestamp": "2026-07-01T00:00:00+00:00",
        "source": "registry:t",
    }) + "\n", encoding="utf-8")


def _make_s6_project(tmp: str, enable_second_failure: bool = False) -> Path:
    """Minimal governed project in S6-delivery with full release evidence."""
    root = Path(tmp)
    (root / ".ai" / "tasks").mkdir(parents=True, exist_ok=True)
    (root / ".ai" / "state.yaml").write_text(STATE_S6, encoding="utf-8")
    (root / ".ai" / "tasks" / "T-0001.md").write_text(TASK_CONTRACT,
                                                      encoding="utf-8")
    qg = root / ".zcode" / "skills" / "loop-governance"
    qg.mkdir(parents=True, exist_ok=True)
    config = GOVERNANCE_CONFIG_YAML
    if enable_second_failure:
        config += "second_failure_gate:\n  enabled: true\n"
    (qg / "config.yaml").write_text(config, encoding="utf-8")
    release = root / ".ai" / "evidence" / "release" / "1.0.0"
    release.mkdir(parents=True, exist_ok=True)
    (release / "release_decision.json").write_text(
        '{"decision": "GO"}', encoding="utf-8")
    quality = root / ".ai" / "evidence" / "quality"
    quality.mkdir(parents=True, exist_ok=True)
    (quality / "runtime_quality_report.json").write_text(
        '{"overall": "PASS"}', encoding="utf-8")
    security = root / ".ai" / "evidence" / "security"
    security.mkdir(parents=True, exist_ok=True)
    (security / "security_audit.json").write_text(
        '{"verdict": "PASS"}', encoding="utf-8")
    _write_slo_sources(root)
    return root


def _load_enforcement_module():
    """Import hooks/scripts/loop_enforcement.py by file path (the PreToolUse
    hook) — the exact function the hook's main() calls for phase evidence."""
    spec = importlib.util.spec_from_file_location(
        "loop_enforcement_t0097", SCRIPTS / "loop_enforcement.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestS6HookWiring:
    def _s6_gate(self, root: Path) -> tuple[bool, str]:
        return _load_enforcement_module().check_phase_gate_enforcement(
            root, "S6-delivery")

    def test_s6_default_disabled_passes(self):
        """Default (wave 1 advisory): existing S6 checks unchanged, no new
        block even with an unresolved second failure present."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_s6_project(tmp)
            _second_failure_pair(root)
            ok, reason = self._s6_gate(root)
            assert ok is True, reason
            assert "S6 delivery + runtime quality + security + SLO" in reason

    def test_s6_enabled_blocks_unresolved(self):
        """Opt-in: with second_failure_gate.enabled=true an unresolved
        recurrence blocks the release path."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_s6_project(tmp, enable_second_failure=True)
            _second_failure_pair(root)
            ok, reason = self._s6_gate(root)
            assert ok is False
            assert "Second-failure 门禁阻断" in reason
            assert GATE_BLOCK_CODE in reason

    def test_s6_enabled_passes_with_open_action_item(self):
        """Opt-in + owned action item: the release path passes."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_s6_project(tmp, enable_second_failure=True)
            records, _ = _second_failure_pair(root)
            create_retrospective(
                root, incident_id=records[0].second_incident_id,
                root_cause="stale evidence process gap",
                action_items=[{
                    "owner": "quality-engineer", "deadline": "2026-08-15",
                    "description": "add freshness fixture",
                }],
            )
            ok, reason = self._s6_gate(root)
            assert ok is True, reason
            assert "Second-failure 门禁通过" in reason

    def test_s6_existing_checks_unchanged_no_go_still_blocks(self):
        """The new gate never weakens existing checks: NOGO still blocks."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_s6_project(tmp, enable_second_failure=True)
            (root / ".ai" / "evidence" / "release" / "1.0.0" /
             "release_decision.json").write_text(
                '{"decision": "NOGO"}', encoding="utf-8")
            ok, reason = self._s6_gate(root)
            assert ok is False
            assert "NOGO" in reason
