"""T-0090 D2 AC-04: SLO/error budget + Loop-DORA metrics (B2 design §1/§2).

Covers:
- AC-04a: SLI computation from fixture data (rejection rates, approval
  latency, rework, guard anomaly rate, dwell/cycle times) and NOT_AVAILABLE
  marking when a data source is missing or unparseable (no guessing).
- AC-04b: SLO/error-budget accounting — budget exhaustion yields
  FREEZE_RECOMMENDED (advisory only, never a block), within-budget stays
  HEALTHY/CONSUMING, slo.yaml overrides, release fee.
- AC-04c: DORA metrics report — >= 3 metrics, structured JSON output with
  ReportBinding-style fields, human-readable markdown.
- AC-04d: read-only aggregation — data source files are byte-identical
  (sha256) before and after report building.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from loop_core.governance_metrics import (
    BUDGET_CONSUMING,
    BUDGET_FREEZE_RECOMMENDED,
    BUDGET_HEALTHY,
    NOT_AVAILABLE,
    REPORT_NOT_VERIFIED,
    REPORT_PASS,
    DataSourceUnavailableError,
    GateMetric,
    approval_latency_stats,
    build_report,
    classify_gate_phase,
    compute_error_budget,
    evaluate_sli,
    gate_decision_coverage,
    gate_rejection_rate,
    guard_anomaly_rates,
    load_gates,
    load_slo_config,
    phase_dwell_stats,
    render_markdown,
    rework_cycles_from_gates,
    rework_cycles_from_transitions,
    task_cycle_time_stats,
)
from loop_core.observability import GuardCheckEvent

# ── Fixture writers ──────────────────────────────────────────────────────


def _write_gates(root: Path, gates: list[dict]) -> Path:
    path = root / ".ai" / "gates.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "schema_version: 1\n" + "gates:\n"
        + "\n".join(f"- {json.dumps(g, ensure_ascii=False)}" for g in gates),
        encoding="utf-8",
    )
    return path


def _write_tasks(root: Path, tasks: list[dict]) -> Path:
    path = root / ".ai" / "task_graph.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "schema_version: 1\n" + "tasks:\n"
        + "\n".join(f"- {json.dumps(t, ensure_ascii=False)}" for t in tasks),
        encoding="utf-8",
    )
    return path


def _write_guard_events(root: Path, events: list[dict]) -> Path:
    path = root / ".ai" / "evidence" / "observability" / "guard-events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n",
        encoding="utf-8",
    )
    return path


def _write_transitions(root: Path, transitions: list[dict]) -> Path:
    path = root / ".ai" / "ledger" / "phase_transitions.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(t, ensure_ascii=False) for t in transitions) + "\n",
        encoding="utf-8",
    )
    return path


def _write_slo(root: Path, doc: dict) -> Path:
    path = root / ".ai" / "slo.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return path


def _guard_event(guard_id: str, result: str, check_type: str = "death",
                 timestamp: str = "2026-08-01T00:00:00+00:00") -> GuardCheckEvent:
    return GuardCheckEvent(
        guard_id=guard_id, check_type=check_type, result=result,
        duration_ms=1.0, timestamp=timestamp, source="registry:test",
    )


def _basic_gate(gate_id: str, task_id: str = "T-X", status: str = "approved",
                gate_type: str = "user-approval", requested: str | None = None,
                recorded: str | None = None, evidence: str | None = None) -> dict:
    gate: dict = {
        "id": gate_id, "task_id": task_id, "gate_type": gate_type,
        "status": status, "decision": status,
    }
    if requested:
        gate["requested_at"] = requested
    if recorded:
        gate["recorded_at"] = recorded
    if evidence:
        gate["evidence"] = evidence
    return gate


@pytest.fixture
def full_project(tmp_path: Path) -> Path:
    """A fixture repository with all data sources populated and healthy:
    S1 gate with a small over-target rejection rate, latency samples,
    guard events with a couple of FAILs, tasks, and a transition journal."""
    gates = [
        # S1-requirements: 4 approved + 2 rejected -> rate 2/6 = 0.333
        _basic_gate("G-T-1000-REQUIREMENTS", "T-100", requested="2026-07-01T09:00:00+08:00",
                    recorded="2026-07-01T10:00:00+08:00", evidence=".ai/evidence/T-100/a.md"),
        _basic_gate("G-T-1001-REQUIREMENTS", "T-101", requested="2026-07-02T09:00:00+08:00",
                    recorded="2026-07-02T10:00:00+08:00", evidence=".ai/evidence/T-101/a.md"),
        _basic_gate("G-T-1002-REQUIREMENTS", "T-102", requested="2026-07-03T09:00:00+08:00",
                    recorded="2026-07-03T10:00:00+08:00", evidence=".ai/evidence/T-102/a.md"),
        _basic_gate("G-T-1003-REQUIREMENTS", "T-103", requested="2026-07-04T09:00:00+08:00",
                    recorded="2026-07-04T10:00:00+08:00"),
        _basic_gate("G-T-1004-REQUIREMENTS", "T-104", status="rejected",
                    requested="2026-07-05T09:00:00+08:00", recorded="2026-07-05T10:00:00+08:00"),
        _basic_gate("G-T-1005-REQUIREMENTS", "T-105", status="rejected",
                    requested="2026-07-06T09:00:00+08:00", recorded="2026-07-06T10:00:00+08:00"),
        # S5-quality: 1 approved -> 0.0
        _basic_gate("G-T-1006-QUALITY", "T-100", gate_type="user-quality",
                    evidence=".ai/evidence/T-100/q.md"),
        # unmapped token: participates in overall rate only
        _basic_gate("G-T-1007-SOMETHING-ELSE", "T-106"),
        # pending gate: not decided, excluded from rates
        _basic_gate("G-T-1008-REQUIREMENTS", "T-107", status="pending"),
    ]
    tasks = [
        {"id": "T-100", "status": "completed", "phase": "S6-delivery",
         "created_at": "2026-07-01T00:00:00+08:00", "updated_at": "2026-07-03T00:00:00+08:00"},
        {"id": "T-101", "status": "completed", "phase": "S6-delivery",
         "created_at": "2026-07-01T00:00:00+08:00", "updated_at": "2026-07-02T00:00:00+08:00"},
    ]
    events = [
        {"event_id": "e1", "guard_id": "g_alpha", "capability_id": None,
         "check_type": "health", "result": "PASS", "duration_ms": 5.0,
         "failure_reason": None, "timestamp": "2026-08-01T00:00:00+00:00",
         "source": "registry:t"},
        {"event_id": "e2", "guard_id": "g_alpha", "capability_id": None,
         "check_type": "death", "result": "FAIL", "duration_ms": 6.0,
         "failure_reason": "DORMANT", "timestamp": "2026-08-01T00:00:01+00:00",
         "source": "registry:t"},
        {"event_id": "e3", "guard_id": "g_beta", "capability_id": None,
         "check_type": "death", "result": "PASS", "duration_ms": 7.0,
         "failure_reason": None, "timestamp": "2026-08-01T00:00:02+00:00",
         "source": "registry:t"},
    ]
    transitions = [
        {"task_id": "T-100", "from_phase": "S4-implementation",
         "to_phase": "S5-quality", "at": "2026-07-01T10:00:00+08:00"},
        {"task_id": "T-100", "from_phase": "S5-quality",
         "to_phase": "S4-implementation", "at": "2026-07-01T11:00:00+08:00"},
        {"task_id": "T-100", "from_phase": "S4-implementation",
         "to_phase": "S5-quality", "at": "2026-07-01T12:00:00+08:00"},
    ]
    _write_gates(tmp_path, gates)
    _write_tasks(tmp_path, tasks)
    _write_guard_events(tmp_path, events)
    _write_transitions(tmp_path, transitions)
    return tmp_path


@pytest.fixture
def clean_project(tmp_path: Path) -> Path:
    """All-clean fixture: no rejections, no guard FAILs -> HEALTHY budget."""
    gates = [
        _basic_gate("G-T-1100-REQUIREMENTS", "T-110", requested="2026-07-01T09:00:00+08:00",
                    recorded="2026-07-01T10:00:00+08:00", evidence=".ai/evidence/T-110/a.md"),
        _basic_gate("G-T-1101-REQUIREMENTS", "T-111", requested="2026-07-02T09:00:00+08:00",
                    recorded="2026-07-02T10:00:00+08:00", evidence=".ai/evidence/T-111/a.md"),
        _basic_gate("G-T-1102-QUALITY", "T-110", gate_type="user-quality"),
    ]
    tasks = [
        {"id": "T-110", "status": "completed", "phase": "S6-delivery",
         "created_at": "2026-07-01T00:00:00+08:00", "updated_at": "2026-07-03T00:00:00+08:00"},
    ]
    events = [
        {"event_id": "e1", "guard_id": "g_alpha", "capability_id": None,
         "check_type": "death", "result": "PASS", "duration_ms": 5.0,
         "failure_reason": None, "timestamp": "2026-08-01T00:00:00+00:00",
         "source": "registry:t"},
    ]
    _write_gates(tmp_path, gates)
    _write_tasks(tmp_path, tasks)
    _write_guard_events(tmp_path, events)
    return tmp_path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── AC-04a: SLI computation ──────────────────────────────────────────────


class TestSliComputation:
    def test_rejection_rate_slis_from_fixture(self, full_project: Path):
        report = build_report(full_project)
        by_id = {r["sli_id"]: r for r in report.sli_eval}

        req = by_id["req_gate_rejection_rate"]
        assert req["status"] == "computed"
        assert req["value"] == pytest.approx(2 / 6)
        assert req["over_target"] is False          # 0.333 <= 0.35
        assert req["breach_events"] == 2
        assert req["consumed_units"] == pytest.approx(2.0)

        quality = by_id["quality_gate_rejection_rate"]
        assert quality["value"] == 0.0
        assert quality["breach_events"] == 0

        # delivery / design phases have no decided gates -> NOT_AVAILABLE
        assert by_id["delivery_gate_rejection_rate"]["status"] == NOT_AVAILABLE
        assert by_id["design_review_rejection_rate"]["status"] == NOT_AVAILABLE

    def test_rework_cycle_rate_and_guard_anomaly(self, full_project: Path):
        report = build_report(full_project)
        by_id = {r["sli_id"]: r for r in report.sli_eval}

        rework = by_id["rework_cycle_rate"]
        # 2 rejected gates / 2 completed tasks
        assert rework["status"] == "computed"
        assert rework["value"] == pytest.approx(1.0)
        assert rework["breach_events"] == 2

        guard = by_id["guard_anomaly_rate"]
        assert guard["status"] == "computed"
        assert guard["value"] == pytest.approx(1 / 3, abs=1e-3)
        assert guard["breach_events"] == 1

        assert by_id["guard_block_rate"]["status"] == NOT_AVAILABLE

    def test_approval_latency_sli(self, full_project: Path):
        report = build_report(full_project)
        by_id = {r["sli_id"]: r for r in report.sli_eval}
        latency = by_id["approval_latency_p95"]
        # all fixture latencies are exactly 1h -> p95 == 1.0h
        assert latency["status"] == "computed"
        assert latency["value"] == pytest.approx(1.0)
        assert latency["breach_events"] == 0
        assert latency["over_target"] is False

    def test_missing_source_is_not_available(self, tmp_path: Path):
        # No data sources at all -> every SLI is NOT_AVAILABLE, never a zero
        report = build_report(tmp_path)
        by_id = {r["sli_id"]: r for r in report.sli_eval}
        for sli_id in ("req_gate_rejection_rate", "rework_cycle_rate",
                       "guard_anomaly_rate", "approval_latency_p95",
                       "gate_decision_coverage"):
            assert by_id[sli_id]["status"] == NOT_AVAILABLE
            assert by_id[sli_id]["value"] == NOT_AVAILABLE
            assert by_id[sli_id]["reason"] is not None
        assert report.status == REPORT_NOT_VERIFIED
        assert any("gates" in m for m in report.missing)

    def test_partial_sources_missing(self, tmp_path: Path):
        _write_gates(tmp_path, [_basic_gate("G-T-1000-REQUIREMENTS")])
        report = build_report(tmp_path)
        by_id = {r["sli_id"]: r for r in report.sli_eval}
        # gates present: rejection rate computable
        assert by_id["req_gate_rejection_rate"]["status"] == "computed"
        # guard events absent: anomaly rate NOT_AVAILABLE
        assert by_id["guard_anomaly_rate"]["status"] == NOT_AVAILABLE
        # task graph absent: rework denominator unknown -> NOT_AVAILABLE
        assert by_id["rework_cycle_rate"]["status"] == NOT_AVAILABLE

    def test_unparseable_source_is_not_available(self, tmp_path: Path):
        _write_gates(tmp_path, [_basic_gate("G-T-1000-REQUIREMENTS")])
        path = tmp_path / ".ai" / "gates.yaml"
        path.write_text("gates: [unclosed", encoding="utf-8")
        with pytest.raises(DataSourceUnavailableError):
            load_gates(tmp_path)
        report = build_report(tmp_path)
        by_id = {r["sli_id"]: r for r in report.sli_eval}
        assert by_id["req_gate_rejection_rate"]["status"] == NOT_AVAILABLE

    def test_corrupt_guard_events_are_not_available(self, full_project: Path):
        path = full_project / ".ai" / "evidence" / "observability" / "guard-events.jsonl"
        path.write_text("{not json}\n", encoding="utf-8")
        report = build_report(full_project)
        by_id = {r["sli_id"]: r for r in report.sli_eval}
        assert by_id["guard_anomaly_rate"]["status"] == NOT_AVAILABLE
        assert report.dora["guard_anomaly_rate"]["status"] == NOT_AVAILABLE

    def test_pure_metric_functions(self, full_project: Path):
        gates = load_gates(full_project)
        # overall rate: 2 rejected / 8 decided (pending excluded)
        assert gate_rejection_rate(gates) == pytest.approx(2 / 8)
        assert gate_rejection_rate(gates, phase="S1-requirements") == pytest.approx(2 / 6)
        assert gate_rejection_rate(gates, phase="S6-delivery") is None
        # decision coverage: 4 gates with evidence / 8 decided
        assert gate_decision_coverage(gates) == pytest.approx(4 / 8)
        # rework from gates: 2 rejected
        assert sum(rework_cycles_from_gates(gates).values()) == 2
        # approval latency stats: all 1h -> p95 3600s
        stats = approval_latency_stats(gates)
        assert stats["count"] == 6
        assert stats["p95_seconds"] == 3600.0

    def test_phase_dwell_and_rework_from_transitions(self, full_project: Path):
        from loop_core.governance_metrics import load_phase_transitions

        transitions = load_phase_transitions(full_project)
        dwell = phase_dwell_stats(transitions)
        assert dwell["S4-implementation"]["count"] == 1
        assert dwell["S4-implementation"]["p50_hours"] == pytest.approx(1.0)
        assert dwell["S5-quality"]["p50_hours"] == pytest.approx(1.0)
        # S4 -> S5 -> S4 = exactly 1 bounce (B2 AC-MET)
        bounces = rework_cycles_from_transitions(transitions)
        assert bounces == {"T-100": 1}

    def test_guard_anomaly_rates_pure(self, full_project: Path):
        from loop_core.governance_metrics import load_guard_events

        events = load_guard_events(full_project)
        rates = guard_anomaly_rates(events)
        assert rates["total_events"] == 3
        assert rates["anomaly_rate"] == pytest.approx(1 / 3, abs=1e-3)
        assert rates["by_guard"]["g_alpha"]["anomaly_rate"] == pytest.approx(0.5)
        assert rates["by_guard"]["g_beta"]["anomaly_rate"] == 0.0

    def test_task_cycle_time_pure(self, full_project: Path):
        from loop_core.governance_metrics import load_tasks

        stats = task_cycle_time_stats(load_tasks(full_project))
        assert stats["count"] == 2
        assert stats["p50_days"] == pytest.approx(1.0)
        assert stats["p95_days"] == pytest.approx(2.0)

    def test_phase_classification(self):
        assert classify_gate_phase("G-T-0090-REQUIREMENTS") == "S1-requirements"
        assert classify_gate_phase("G-T-0023-ARCHITECTURE-DESIGN") == "S2-architecture"
        assert classify_gate_phase("G-T-0025-IMPLEMENTATION") == "S4-implementation"
        assert classify_gate_phase("G-T-0026-QUALITY-GATES") == "S5-quality"
        assert classify_gate_phase("G-T-0027-DELIVERY") == "S6-delivery"
        assert classify_gate_phase("G-T-1007-SOMETHING-ELSE") is None
        assert classify_gate_phase(None) is None


# ── AC-04b: SLO / error budget ───────────────────────────────────────────


class TestErrorBudget:
    def test_within_budget_is_healthy(self, clean_project: Path):
        report = build_report(clean_project)
        budget = report.budget
        assert budget["status"] == BUDGET_HEALTHY
        assert budget["consumed_units"] == 0.0
        assert budget["remaining_units"] == 100.0

    def test_consumption_within_budget_is_consuming(self, full_project: Path):
        # 2 rejected S1 gates (2 units) + 2 rework (2 units) + 1 guard FAIL
        # (1 unit) = 5 units consumed, 95 remaining -> CONSUMING
        report = build_report(full_project)
        budget = report.budget
        assert budget["status"] == BUDGET_CONSUMING
        assert budget["consumed_units"] == pytest.approx(5.0)
        assert budget["remaining_units"] == pytest.approx(95.0)
        # per-SLI consumption is itemized in the SLI evaluation
        consumed_by_sli = {r["sli_id"]: r["consumed_units"] for r in report.sli_eval}
        assert consumed_by_sli["req_gate_rejection_rate"] == pytest.approx(2.0)
        assert consumed_by_sli["rework_cycle_rate"] == pytest.approx(2.0)
        assert consumed_by_sli["guard_anomaly_rate"] == pytest.approx(1.0)

    def test_consumption_within_budget_is_consuming_units(self):
        # direct function check: 5 units consumed, 95 remaining
        budget = compute_error_budget([
            {"consumed_units": 2.0}, {"consumed_units": 2.0}, {"consumed_units": 1.0},
        ])
        assert budget["status"] == BUDGET_CONSUMING
        assert budget["remaining_units"] == pytest.approx(95.0)

    def test_budget_exhausted_reports_freeze_recommended(self, tmp_path: Path):
        # 60 rejected S1 gates: 60 (rejection SLI) + 60 (rework) = 120 > 100
        gates = [_basic_gate(f"G-T-2000-REQUIREMENTS-{i}", "T-200", status="rejected",
                             requested="2026-07-01T09:00:00+08:00",
                             recorded="2026-07-01T10:00:00+08:00")
                 for i in range(60)]
        _write_gates(tmp_path, gates)
        _write_tasks(tmp_path, [{"id": "T-200", "status": "completed",
                                 "phase": "S4-implementation",
                                 "created_at": "2026-07-01T00:00:00+08:00",
                                 "updated_at": "2026-07-02T00:00:00+08:00"}])
        report = build_report(tmp_path)
        budget = report.budget
        assert budget["status"] == BUDGET_FREEZE_RECOMMENDED
        assert budget["consumed_units"] == pytest.approx(120.0)
        assert budget["remaining_units"] == pytest.approx(-20.0)
        # advisory only: the report never claims a block was applied
        assert "no release path is blocked" in budget["note"]

    def test_budget_share_scales_consumption(self):
        # 10 breach events with budget_share 0.5 -> 5 units
        result = evaluate_sli(
            {"sli_id": "req_gate_rejection_rate", "phase": "S1-requirements",
             "target": {"op": "<=", "value": 0.35}, "severity": "error-budget-slo",
             "budget_share": 0.5},
            SliContextStub(gates=_gates_with_rejections(10)),
        )
        assert result["consumed_units"] == pytest.approx(5.0)

    def test_release_fee_consumes_budget(self):
        budget = compute_error_budget([], total_units=100.0,
                                      release_fee_units=5.0, releases=3)
        assert budget["release_consumption"] == pytest.approx(15.0)
        assert budget["consumed_units"] == pytest.approx(15.0)
        assert budget["remaining_units"] == pytest.approx(85.0)
        assert budget["status"] == BUDGET_CONSUMING

    def test_slo_config_override_via_slo_yaml(self, tmp_path: Path):
        _write_gates(tmp_path, [_basic_gate("G-T-1000-REQUIREMENTS")])
        _write_slo(tmp_path, {
            "schema_version": 1,
            "slos": [{"sli_id": "req_gate_rejection_rate",
                      "target": {"op": "<=", "value": 0.99},
                      "severity": "error-budget-slo", "budget_share": 0.25}],
            "budget_total_units": 50,
            "release_fee_units": 2,
        })
        config = load_slo_config(tmp_path)
        assert config["budget_total_units"] == 50.0
        assert config["release_fee_units"] == 2.0
        slo = next(s for s in config["slos"]
                   if s["sli_id"] == "req_gate_rejection_rate")
        assert slo["target"]["value"] == 0.99
        assert slo["budget_share"] == 0.25
        report = build_report(tmp_path)
        assert report.budget["total_units"] == 50.0
        assert report.slo_source.endswith("slo.yaml")

    def test_absent_slo_yaml_uses_defaults(self, tmp_path: Path):
        config = load_slo_config(tmp_path)
        assert "absent" in config["source"]
        assert config["budget_total_units"] == 100.0
        assert any(s["sli_id"] == "req_gate_rejection_rate" for s in config["slos"])


class SliContextStub:
    """Minimal context for evaluate_sli unit tests (gates-only)."""

    def __init__(self, gates: list[GateMetric]):
        self.gates = gates
        self.tasks = None
        self.transitions = None
        self.guard_events = None
        self.executions = None
        self.drift_events = None
        self.guard_decisions = None
        self.rework_by_task = {}
        self.rework_total = 0
        self.completed_tasks = 0


def _gates_with_rejections(n: int) -> list[GateMetric]:
    return [GateMetric(
        gate_id=f"G-T-3{i:04d}-REQUIREMENTS", task_id=f"T-{i}", gate_type="user-approval",
        status="rejected", decision="rejected", phase="S1-requirements",
        requested_at=None, recorded_at=None, evidence=None,
    ) for i in range(n)]


# ── AC-04c: DORA metrics report ──────────────────────────────────────────


class TestDoraReport:
    def test_report_has_at_least_three_computed_metrics(self, full_project: Path):
        report = build_report(full_project)
        computed = [m for m in report.dora.values()
                    if m.get("status") == "computed"]
        assert len(computed) >= 3
        names = {n for n, m in report.dora.items() if m.get("status") == "computed"}
        assert {"gate_rejection_rate", "gate_decision_coverage",
                "guard_anomaly_rate", "task_rework_cycles"} <= names

    def test_report_is_structured_json(self, full_project: Path):
        report = build_report(full_project)
        payload = report.to_dict()
        # ReportBinding-style fields
        assert payload["binding"]["task_id"] == "T-0090"
        assert payload["binding"]["tool_name"] == "loop_metrics"
        assert payload["binding"]["timestamp"]
        assert payload["window"]["start"] <= payload["window"]["end"]
        assert payload["error_budget"]["status"]
        assert payload["status"] in (REPORT_PASS, REPORT_NOT_VERIFIED)
        # JSON-serializable round-trip
        dumped = json.dumps(payload, ensure_ascii=False)
        assert json.loads(dumped)["dora_metrics"]["gate_rejection_rate"]["value"] == 0.25

    def test_markdown_render(self, full_project: Path):
        report = build_report(full_project)
        md = render_markdown(report)
        assert "# Loop-DORA Metrics Report" in md
        assert "## Error budget" in md
        assert "## DORA metrics" in md
        assert "## SLI / SLO evaluation" in md
        assert "NOT_AVAILABLE" in md  # missing-data transparency surfaces in text

    def test_report_not_verified_when_data_missing(self, tmp_path: Path):
        # only guard events exist: many metrics cannot be computed
        _write_guard_events(tmp_path, [
            {"event_id": "e1", "guard_id": "g", "capability_id": None,
             "check_type": "death", "result": "PASS", "duration_ms": 1.0,
             "failure_reason": None, "timestamp": "2026-08-01T00:00:00+00:00",
             "source": "registry:t"},
        ])
        report = build_report(tmp_path)
        assert report.status == REPORT_NOT_VERIFIED
        assert report.dora["gate_rejection_rate"]["status"] == NOT_AVAILABLE
        assert report.dora["phase_dwell_time"]["status"] == NOT_AVAILABLE

    def test_explicit_window_is_bound(self, full_project: Path):
        report = build_report(full_project, window=("2026-07-01", "2026-09-30"))
        assert report.window == ("2026-07-01", "2026-09-30")


# ── AC-04d: data sources are never modified ──────────────────────────────


class TestReadOnly:
    def test_data_sources_byte_identical_after_report(self, full_project: Path):
        sources = [
            full_project / ".ai" / "gates.yaml",
            full_project / ".ai" / "task_graph.yaml",
            full_project / ".ai" / "evidence" / "observability" / "guard-events.jsonl",
            full_project / ".ai" / "ledger" / "phase_transitions.jsonl",
        ]
        before = {p: _sha256(p) for p in sources}
        for _ in range(3):
            report = build_report(full_project)
            assert report.dora  # report built
            report.to_dict()
        after = {p: _sha256(p) for p in sources}
        assert before == after

    def test_missing_sources_are_not_created(self, tmp_path: Path):
        # report over an empty repo must not create any data source files
        build_report(tmp_path)
        assert not (tmp_path / ".ai" / "gates.yaml").exists()
        assert not (tmp_path / ".ai" / "ledger").exists()


# ═══════════════════════════════════════════════════════════════════════
# T-0095 item 2: .ai/slo.yaml 显式化 + fail-closed 校验
# ═══════════════════════════════════════════════════════════════════════

_REPO_ROOT = Path(__file__).resolve().parent.parent


class TestT0095SloConfigExplicitAndValidated:
    """AC-02: repo .ai/slo.yaml mirrors the B2 defaults exactly; an invalid
    slo.yaml raises DataSourceUnavailableError (fail-closed, field named)."""

    def test_repo_slo_yaml_matches_builtin_defaults(self):
        """The checked-in .ai/slo.yaml must not drift from DEFAULT_SLOS."""
        from loop_core.governance_metrics import (
            DEFAULT_BUDGET_TOTAL_UNITS,
            DEFAULT_RELEASE_FEE_UNITS,
            DEFAULT_SLOS,
        )

        config = load_slo_config(_REPO_ROOT)
        assert (config["slo_path"] == str(_REPO_ROOT / ".ai" / "slo.yaml"))
        assert config["budget_total_units"] == DEFAULT_BUDGET_TOTAL_UNITS
        assert config["release_fee_units"] == DEFAULT_RELEASE_FEE_UNITS
        assert config["window"] == (None, None)  # null window == all data
        assert [s["sli_id"] for s in config["slos"]] == [
            s["sli_id"] for s in DEFAULT_SLOS
        ]
        for actual, default in zip(config["slos"], DEFAULT_SLOS):
            for key in ("phase", "target", "severity", "budget_share"):
                assert actual[key] == default[key], (
                    f"sli {actual['sli_id']} field {key} drifted from defaults"
                )

    def test_invalid_budget_total_units_rejected(self, tmp_path: Path):
        _write_slo(tmp_path, {"budget_total_units": "not-a-number"})
        with pytest.raises(DataSourceUnavailableError, match="budget_total_units"):
            load_slo_config(tmp_path)

    def test_non_positive_budget_total_units_rejected(self, tmp_path: Path):
        for bad in (0, -5):
            _write_slo(tmp_path, {"budget_total_units": bad})
            with pytest.raises(DataSourceUnavailableError, match="budget_total_units"):
                load_slo_config(tmp_path)

    def test_negative_release_fee_rejected(self, tmp_path: Path):
        _write_slo(tmp_path, {"release_fee_units": -1})
        with pytest.raises(DataSourceUnavailableError, match="release_fee_units"):
            load_slo_config(tmp_path)

    def test_half_set_window_rejected(self, tmp_path: Path):
        _write_slo(tmp_path, {"window_start": "2026-08-01"})
        with pytest.raises(DataSourceUnavailableError, match="window_start"):
            load_slo_config(tmp_path)

    def test_unparseable_window_bound_rejected(self, tmp_path: Path):
        _write_slo(tmp_path, {"window_start": "garbage", "window_end": "2026-08-31"})
        with pytest.raises(DataSourceUnavailableError, match="window_start"):
            load_slo_config(tmp_path)

    def test_invalid_target_op_rejected(self, tmp_path: Path):
        _write_slo(tmp_path, {"slos": [
            {"sli_id": "req_gate_rejection_rate",
             "target": {"op": "<>", "value": 0.35}},
        ]})
        with pytest.raises(DataSourceUnavailableError, match="target op"):
            load_slo_config(tmp_path)

    def test_non_numeric_target_value_rejected(self, tmp_path: Path):
        _write_slo(tmp_path, {"slos": [
            {"sli_id": "req_gate_rejection_rate",
             "target": {"op": "<=", "value": "high"}},
        ]})
        with pytest.raises(DataSourceUnavailableError, match="target value"):
            load_slo_config(tmp_path)

    def test_unknown_severity_rejected(self, tmp_path: Path):
        _write_slo(tmp_path, {"slos": [
            {"sli_id": "req_gate_rejection_rate", "severity": "urgent"},
        ]})
        with pytest.raises(DataSourceUnavailableError, match="severity"):
            load_slo_config(tmp_path)

    def test_invalid_budget_share_rejected(self, tmp_path: Path):
        _write_slo(tmp_path, {"slos": [
            {"sli_id": "req_gate_rejection_rate", "budget_share": "lots"},
        ]})
        with pytest.raises(DataSourceUnavailableError, match="budget_share"):
            load_slo_config(tmp_path)

    def test_valid_partial_override_still_applies(self, tmp_path: Path):
        # existing override semantics unchanged: partial configs merge over
        # defaults and keep working
        _write_slo(tmp_path, {
            "schema_version": 1,
            "slos": [{"sli_id": "req_gate_rejection_rate",
                      "target": {"op": "<=", "value": 0.99}}],
            "budget_total_units": 50,
        })
        config = load_slo_config(tmp_path)
        assert config["budget_total_units"] == 50.0
        assert config["window"] == (None, None)
        slo = next(s for s in config["slos"]
                   if s["sli_id"] == "req_gate_rejection_rate")
        assert slo["target"]["value"] == 0.99
