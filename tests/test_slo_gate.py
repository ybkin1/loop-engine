"""T-0093 (AC-01..AC-05): SLO gate wave 2 — error budget exhaustion freezes
releases (B2 §1.4/§1.5 ``slo_budget_available`` wiring).

Covers:
- AC-01: gate decision — HEALTHY → PASS; FREEZE → BLOCK
  (ERROR_BUDGET_EXHAUSTED); CONSUMING → PASS + warning; missing/unparseable
  required source → fail-closed BLOCK listing the missing sources.
- AC-02: release-chain wiring — loop_enforcement S6-delivery branch calls the
  gate (hook subprocess tests: FREEZE blocks, HEALTHY passes); checker CLI
  exit codes 0/1/2; toggle default-enabled, config/env disable → PASS + note.
- AC-03: exemptions — append-only record; valid exemption overrides FREEZE →
  PASS; expired exemption ineffective (re-BLOCK); approver/reason missing
  rejected; unreadable ledger cannot override (fail-closed).
- AC-04: recovery — window rollover resets the budget; gate auto-passes when
  the current window is healthy (slo.yaml window honored by default).
- AC-05: backward compatibility — the new gate only adds blocking conditions;
  existing S6 checks (NOGO still blocks, GO+healthy still passes) keep their
  exact semantics.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import pytest

from loop_core.governance_metrics import build_report
from loop_core.slo_gate import (
    GATE_BLOCK_CODE,
    GATE_DECISION_BLOCK,
    GATE_DECISION_PASS,
    GATE_STATUS_DISABLED,
    GATE_STATUS_NOT_AVAILABLE,
    record_slo_exemption,
    check_slo_gate,
    load_exemptions,
    slo_gate_enabled,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHECKERS = PROJECT_ROOT / ".ai" / "checkers"
SCRIPTS = PROJECT_ROOT / "hooks" / "scripts"
PYTHON = sys.executable

NOW = datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
ISO_NOW = "2026-08-01T00:00:00+00:00"
FUTURE = "2026-12-31T00:00:00+00:00"
PAST = "2026-06-30T00:00:00+00:00"


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


def _write_slo(root: Path, doc: dict) -> Path:
    path = root / ".ai" / "slo.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return path


def _gate(gate_id: str, task_id: str = "T-X", status: str = "approved",
          requested: str | None = None, recorded: str | None = None,
          evidence: str | None = None, gate_type: str = "user-approval") -> dict:
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


def _pass_event(event_id: str, timestamp: str = ISO_NOW) -> dict:
    return {
        "event_id": event_id, "guard_id": "g_alpha", "capability_id": None,
        "check_type": "death", "result": "PASS", "duration_ms": 5.0,
        "failure_reason": None, "timestamp": timestamp, "source": "registry:t",
    }


@pytest.fixture
def healthy_project(tmp_path: Path) -> Path:
    """All-clean fixture: approved gates only -> HEALTHY budget (AC-01)."""
    gates = [
        _gate("G-T-3000-REQUIREMENTS", "T-300", requested="2026-07-01T09:00:00+08:00",
              recorded="2026-07-01T10:00:00+08:00", evidence=".ai/evidence/T-300/a.md"),
        _gate("G-T-3001-QUALITY", "T-300", gate_type="user-quality"),
    ]
    tasks = [
        {"id": "T-300", "status": "completed", "phase": "S6-delivery",
         "created_at": "2026-07-01T00:00:00+08:00",
         "updated_at": "2026-07-03T00:00:00+08:00"},
    ]
    events = [_pass_event("e1")]
    _write_gates(tmp_path, gates)
    _write_tasks(tmp_path, tasks)
    _write_guard_events(tmp_path, events)
    return tmp_path


@pytest.fixture
def consuming_project(tmp_path: Path) -> Path:
    """2 rejected S1 gates (2 units) + 2 rework (2 units) + 1 guard FAIL
    (1 unit) = 5 units consumed of 100 -> CONSUMING (AC-01)."""
    gates = [
        _gate("G-T-3100-REQUIREMENTS", "T-310", requested="2026-07-01T09:00:00+08:00",
              recorded="2026-07-01T10:00:00+08:00", evidence=".ai/evidence/T-310/a.md"),
        _gate("G-T-3101-REQUIREMENTS", "T-311", requested="2026-07-02T09:00:00+08:00",
              recorded="2026-07-02T10:00:00+08:00", evidence=".ai/evidence/T-311/a.md"),
        _gate("G-T-3102-REQUIREMENTS", "T-312", status="rejected",
              requested="2026-07-03T09:00:00+08:00", recorded="2026-07-03T10:00:00+08:00"),
        _gate("G-T-3103-REQUIREMENTS", "T-313", status="rejected",
              requested="2026-07-04T09:00:00+08:00", recorded="2026-07-04T10:00:00+08:00"),
    ]
    tasks = [
        {"id": "T-310", "status": "completed", "phase": "S6-delivery",
         "created_at": "2026-07-01T00:00:00+08:00",
         "updated_at": "2026-07-03T00:00:00+08:00"},
    ]
    events = [
        _pass_event("e1"), _pass_event("e2", "2026-08-01T00:00:01+00:00"),
        {"event_id": "e3", "guard_id": "g_alpha", "capability_id": None,
         "check_type": "death", "result": "FAIL", "duration_ms": 6.0,
         "failure_reason": "DORMANT", "timestamp": "2026-08-01T00:00:02+00:00",
         "source": "registry:t"},
    ]
    _write_gates(tmp_path, gates)
    _write_tasks(tmp_path, tasks)
    _write_guard_events(tmp_path, events)
    return tmp_path


@pytest.fixture
def freeze_project(tmp_path: Path) -> Path:
    """60 rejected S1 gates: 60 (rejection) + 60 (rework) = 120 > 100 ->
    FREEZE (AC-01)."""
    gates = [
        _gate(f"G-T-3200-REQUIREMENTS-{i}", "T-320", status="rejected",
              requested="2026-07-01T09:00:00+08:00",
              recorded="2026-07-01T10:00:00+08:00")
        for i in range(60)
    ]
    tasks = [
        {"id": "T-320", "status": "completed", "phase": "S4-implementation",
         "created_at": "2026-07-01T00:00:00+08:00",
         "updated_at": "2026-07-02T00:00:00+08:00"},
    ]
    events = [_pass_event("e1")]
    _write_gates(tmp_path, gates)
    _write_tasks(tmp_path, tasks)
    _write_guard_events(tmp_path, events)
    return tmp_path


@pytest.fixture
def missing_source_project(tmp_path: Path) -> Path:
    """Only the gates register exists — task graph and guard events are
    missing -> fail-closed BLOCK with the missing sources listed (AC-01)."""
    _write_gates(tmp_path, [_gate("G-T-3300-REQUIREMENTS", "T-330")])
    return tmp_path


# ── AC-01: gate decision ─────────────────────────────────────────────────


class TestSloGateDecision:
    def test_healthy_budget_passes(self, healthy_project: Path):
        result = check_slo_gate(healthy_project)
        assert result.decision == GATE_DECISION_PASS
        assert result.passed
        assert result.status == "HEALTHY"
        assert result.budget["remaining_units"] == 100.0
        assert "release allowed" in result.reason

    def test_freeze_budget_blocks(self, freeze_project: Path):
        result = check_slo_gate(freeze_project)
        assert result.decision == GATE_DECISION_BLOCK
        assert not result.passed
        assert result.status == "FREEZE_RECOMMENDED"
        assert GATE_BLOCK_CODE in result.reason
        assert "release frozen" in result.reason
        assert result.budget["consumed_units"] == 120.0
        assert result.budget["remaining_units"] == -20.0
        assert result.missing == []

    def test_consuming_budget_passes_with_warning(self, consuming_project: Path):
        result = check_slo_gate(consuming_project)
        assert result.decision == GATE_DECISION_PASS
        assert result.status == "CONSUMING"
        assert any("CONSUMING" in w for w in result.warnings)
        assert result.budget["consumed_units"] == 5.0

    def test_missing_source_fails_closed_with_detail(self, missing_source_project: Path):
        result = check_slo_gate(missing_source_project)
        assert result.decision == GATE_DECISION_BLOCK
        assert result.status == GATE_STATUS_NOT_AVAILABLE
        assert result.budget is None
        # every missing required source is listed — never a silent zero
        assert any("task graph" in m for m in result.missing)
        assert any("guard events" in m for m in result.missing)
        assert "fail-closed" in result.reason
        assert "cannot determine the error budget" in result.reason

    def test_empty_project_fails_closed(self, tmp_path: Path):
        result = check_slo_gate(tmp_path)
        assert result.decision == GATE_DECISION_BLOCK
        assert result.status == GATE_STATUS_NOT_AVAILABLE
        assert len(result.missing) == 3  # gates + task graph + guard events

    def test_unparseable_source_fails_closed(self, healthy_project: Path):
        (healthy_project / ".ai" / "gates.yaml").write_text(
            "gates: [unclosed", encoding="utf-8")
        result = check_slo_gate(healthy_project)
        assert result.decision == GATE_DECISION_BLOCK
        assert result.status == GATE_STATUS_NOT_AVAILABLE
        assert any("gates register" in m for m in result.missing)

    def test_precomputed_budget_param(self, freeze_project: Path):
        # caller-provided D2 budget (e.g. build_report().budget) is honored
        report_budget = build_report(freeze_project).budget
        assert report_budget["status"] == "FREEZE_RECOMMENDED"
        result = check_slo_gate(freeze_project, budget=report_budget)
        assert result.decision == GATE_DECISION_BLOCK
        healthy = {
            "status": "HEALTHY", "total_units": 100.0, "consumed_units": 0.0,
            "remaining_units": 100.0, "release_fee_units": 5.0,
            "release_count": 0, "breach_consumption": 0.0,
            "release_consumption": 0.0, "note": "n",
        }
        assert check_slo_gate(freeze_project, budget=healthy).decision == GATE_DECISION_PASS

    def test_unwired_sources_are_not_gate_blocking(self, healthy_project: Path):
        # guard_decisions.jsonl / phase_transitions.jsonl / runtime-events.jsonl
        # are documented not-yet-wired wave-2 sources: they surface as
        # NOT_AVAILABLE warnings but cannot deadlock the gate (D2 accounting
        # treats them as zero consumption; blocking on them would make the
        # freeze mechanism permanently unreachable).
        result = check_slo_gate(healthy_project)
        assert result.decision == GATE_DECISION_PASS
        assert any("sli:guard_block_rate NOT_AVAILABLE" in w for w in result.warnings)


# ── AC-02: toggle + release-chain wiring ─────────────────────────────────


class TestSloGateToggle:
    def test_default_enabled(self, healthy_project: Path):
        assert slo_gate_enabled(healthy_project) is True
        result = check_slo_gate(healthy_project)
        assert result.gate_enabled is True
        assert result.status != GATE_STATUS_DISABLED

    def test_env_var_disables(self, healthy_project: Path):
        env = {"LOOP_SLO_GATE_ENABLED": "0"}
        assert slo_gate_enabled(healthy_project, env=env) is False
        assert slo_gate_enabled(healthy_project, env={"LOOP_SLO_GATE_ENABLED": "false"}) is False
        result = check_slo_gate(healthy_project)
        assert result.decision == GATE_DECISION_PASS  # sanity: base is PASS anyway
        # even a FREEZE budget must not block while disabled
        disabled = _check_disabled(healthy_project, env)
        assert disabled.decision == GATE_DECISION_PASS
        assert disabled.status == GATE_STATUS_DISABLED
        assert "disabled" in disabled.reason

    def test_config_file_disables(self, healthy_project: Path):
        cfg = healthy_project / ".zcode" / "skills" / "loop-governance" / "config.yaml"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text("slo_gate:\n  enabled: false\n", encoding="utf-8")
        assert slo_gate_enabled(healthy_project) is False
        result = check_slo_gate(healthy_project)
        assert result.decision == GATE_DECISION_PASS
        assert result.status == GATE_STATUS_DISABLED
        assert "disabled" in result.reason

    def test_env_value_wins_over_config(self, healthy_project: Path):
        cfg = healthy_project / ".zcode" / "skills" / "loop-governance" / "config.yaml"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text("slo_gate:\n  enabled: false\n", encoding="utf-8")
        env = {"LOOP_SLO_GATE_ENABLED": "1"}
        assert slo_gate_enabled(healthy_project, env=env) is True

    def test_corrupt_config_falls_back_to_default(self, healthy_project: Path):
        cfg = healthy_project / ".zcode" / "skills" / "loop-governance" / "config.yaml"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text("slo_gate: [unclosed", encoding="utf-8")
        assert slo_gate_enabled(healthy_project) is True


def _check_disabled(root: Path, env: dict[str, str]):
    """Run check_slo_gate with a disabled env in a subprocess-safe way (the
    gate reads os.environ, so we set it around the call)."""
    old = os.environ.get("LOOP_SLO_GATE_ENABLED")
    try:
        os.environ["LOOP_SLO_GATE_ENABLED"] = env["LOOP_SLO_GATE_ENABLED"]
        return check_slo_gate(root)
    finally:
        if old is None:
            os.environ.pop("LOOP_SLO_GATE_ENABLED", None)
        else:
            os.environ["LOOP_SLO_GATE_ENABLED"] = old


class TestSloGateCheckerCli:
    """AC-02: checker CLI — compile_gate-style JSON report + exit codes."""

    CHECKER = CHECKERS / "slo_gate_checker.py"

    def _run(self, root: Path, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [PYTHON, str(self.CHECKER), str(root), *extra],
            capture_output=True, text=True, env=dict(os.environ), timeout=60,
        )

    def test_cli_pass_exit_0(self, healthy_project: Path):
        r = self._run(healthy_project)
        assert r.returncode == 0, r.stderr
        payload = json.loads(r.stdout)
        assert payload["checker_id"] == "slo_gate"
        assert payload["decision"] == "PASS"
        assert payload["exit_code"] == 0
        assert payload["budget"]["status"] == "HEALTHY"

    def test_cli_block_exit_1(self, freeze_project: Path):
        r = self._run(freeze_project)
        assert r.returncode == 1, r.stderr
        payload = json.loads(r.stdout)
        assert payload["decision"] == "BLOCK"
        assert payload["exit_code"] == 1
        assert GATE_BLOCK_CODE in payload["reason"]

    def test_cli_missing_data_block_exit_1(self, tmp_path: Path):
        r = self._run(tmp_path)
        assert r.returncode == 1, r.stderr
        payload = json.loads(r.stdout)
        assert payload["decision"] == "BLOCK"
        assert payload["missing"]

    def test_cli_error_exit_2_bad_root(self):
        r = self._run(Path("Z:/definitely/not/a/project"))
        assert r.returncode == 2
        assert json.loads(r.stdout)["status"] == "error"

    def test_cli_error_exit_2_bad_window(self, healthy_project: Path):
        r = self._run(healthy_project, "--window", "garbage")
        assert r.returncode == 2
        assert json.loads(r.stdout)["status"] == "error"

    def test_cli_disabled_exit_0(self, healthy_project: Path):
        env = dict(os.environ)
        env["LOOP_SLO_GATE_ENABLED"] = "0"
        r = subprocess.run(
            [PYTHON, str(self.CHECKER), str(healthy_project)],
            capture_output=True, text=True, env=env, timeout=60,
        )
        assert r.returncode == 0, r.stderr
        assert json.loads(r.stdout)["status_detail"] == "DISABLED"


# ── AC-02: hook wiring (loop_enforcement S6-delivery branch) ─────────────

GOVERNANCE_CONFIG_YAML = """\
# loop-governance behavior config (synthetic test fixture)
version: 1
gate_guard:
  enabled: true
  fail_on_state_error: closed
path_guard:
  enabled: true
  decision: ask
session_brief:
  enabled: true
  max_pending_listed: 10
"""

STATE_S6 = """\
schema_version: 1
project_name: test-s6
current_phase: S6-delivery
loop_mode: FULL
current_task_id: T-0001
"""

TASK_CONTRACT = """\
# Task T-0001: Implement feature X
allowed_paths:
- src/
- tests/

developer_agent_id: "agent-001"
reviewer_agent_id: "agent-002"
"""

RELEASE_DECISION_GO = '{"decision": "GO"}'
RELEASE_DECISION_NOGO = '{"decision": "NOGO"}'
RUNTIME_QUALITY_PASS = '{"overall": "PASS"}'
SECURITY_AUDIT_PASS = '{"verdict": "PASS"}'


def _make_s6_project(tmp: str, budget: str = "healthy",
                     release_decision: str = RELEASE_DECISION_GO) -> Path:
    """Minimal governed project in S6-delivery with full release evidence.

    ``budget`` selects the SLO data: "healthy" (approved gates only) or
    "freeze" (60 rejected gates -> 120 units consumed)."""
    root = Path(tmp)
    (root / ".ai" / "tasks").mkdir(parents=True, exist_ok=True)
    (root / ".ai" / "state.yaml").write_text(STATE_S6, encoding="utf-8")
    (root / ".ai" / "tasks" / "T-0001.md").write_text(TASK_CONTRACT, encoding="utf-8")
    qg = root / ".zcode" / "skills" / "loop-governance"
    qg.mkdir(parents=True, exist_ok=True)
    (qg / "config.yaml").write_text(GOVERNANCE_CONFIG_YAML, encoding="utf-8")
    release = root / ".ai" / "evidence" / "release" / "1.0.0"
    release.mkdir(parents=True, exist_ok=True)
    (release / "release_decision.json").write_text(release_decision, encoding="utf-8")
    quality = root / ".ai" / "evidence" / "quality"
    quality.mkdir(parents=True, exist_ok=True)
    (quality / "runtime_quality_report.json").write_text(RUNTIME_QUALITY_PASS, encoding="utf-8")
    security = root / ".ai" / "evidence" / "security"
    security.mkdir(parents=True, exist_ok=True)
    (security / "security_audit.json").write_text(SECURITY_AUDIT_PASS, encoding="utf-8")
    if budget == "freeze":
        gates = [
            _gate(f"G-T-3400-REQUIREMENTS-{i}", "T-340", status="rejected",
                  requested="2026-07-01T09:00:00+08:00",
                  recorded="2026-07-01T10:00:00+08:00")
            for i in range(60)
        ]
        tasks = [{"id": "T-340", "status": "completed", "phase": "S4-implementation",
                  "created_at": "2026-07-01T00:00:00+08:00",
                  "updated_at": "2026-07-02T00:00:00+08:00"}]
    else:
        gates = [
            _gate("G-T-3400-REQUIREMENTS", "T-340",
                  requested="2026-07-01T09:00:00+08:00",
                  recorded="2026-07-01T10:00:00+08:00",
                  evidence=".ai/evidence/T-340/a.md"),
        ]
        tasks = [{"id": "T-340", "status": "completed", "phase": "S6-delivery",
                  "created_at": "2026-07-01T00:00:00+08:00",
                  "updated_at": "2026-07-03T00:00:00+08:00"}]
    _write_gates(root, gates)
    _write_tasks(root, tasks)
    _write_guard_events(root, [_pass_event("e1")])
    return root


def _load_enforcement_module():
    """Import hooks/scripts/loop_enforcement.py by file path (the PreToolUse
    hook).  We exercise ``check_phase_gate_enforcement`` directly — the exact
    function the hook's main() calls for phase evidence (line ~1815) — which
    keeps the wiring test free of the runtime-dispatch machinery."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "loop_enforcement_t0093", SCRIPTS / "loop_enforcement.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestSloGateHookWiring:
    """AC-02: the S6 release verification path calls the SLO gate.

    ``check_phase_gate_enforcement(root, "S6-delivery")`` is the S6 branch the
    PreToolUse hook invokes on every S6 write; the new SLO check sits after
    the delivery/runtime-quality/security checks, same level as
    ``check_delivery_gate_evidence``."""

    def _s6_gate(self, root: Path) -> tuple[bool, str]:
        return _load_enforcement_module().check_phase_gate_enforcement(
            root, "S6-delivery")

    def test_s6_freeze_budget_blocks_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_s6_project(tmp, budget="freeze")
            ok, reason = self._s6_gate(root)
            assert ok is False
            assert "SLO 门禁阻断" in reason
            assert GATE_BLOCK_CODE in reason

    def test_s6_healthy_budget_passes_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_s6_project(tmp, budget="healthy")
            ok, reason = self._s6_gate(root)
            assert ok is True, reason
            assert "SLO 门禁通过" in reason

    def test_s6_disabled_gate_passes_even_with_freeze(self):
        old = os.environ.get("LOOP_SLO_GATE_ENABLED")
        try:
            os.environ["LOOP_SLO_GATE_ENABLED"] = "0"
            with tempfile.TemporaryDirectory() as tmp:
                root = _make_s6_project(tmp, budget="freeze")
                ok, reason = self._s6_gate(root)
                assert ok is True, reason
                assert "SLO 门禁通过" in reason
                assert "disabled" in reason
        finally:
            if old is None:
                os.environ.pop("LOOP_SLO_GATE_ENABLED", None)
            else:
                os.environ["LOOP_SLO_GATE_ENABLED"] = old

    def test_s6_config_disables_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_s6_project(tmp, budget="freeze")
            cfg = root / ".zcode" / "skills" / "loop-governance" / "config.yaml"
            cfg.write_text(
                GOVERNANCE_CONFIG_YAML + "slo_gate:\n  enabled: false\n",
                encoding="utf-8",
            )
            ok, reason = self._s6_gate(root)
            assert ok is True, reason
            assert "disabled" in reason

    def test_s6_gate_requires_slo_data_fail_closed(self):
        # full release evidence present, but the SLO budget sources are
        # incomplete -> the new gate fails closed with the missing source
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_s6_project(tmp, budget="healthy")
            (root / ".ai" / "task_graph.yaml").unlink()
            ok, reason = self._s6_gate(root)
            assert ok is False
            assert "SLO 门禁阻断" in reason
            assert "task graph" in reason


# ── AC-03: exemptions ────────────────────────────────────────────────────


class TestSloExemption:
    def test_record_appends_to_ledger(self, tmp_path: Path):
        entry = record_slo_exemption(
            tmp_path, reason="user-approved freeze waiver", expires_at=FUTURE,
            approver="user",
        )
        assert entry["id"] == "SLO-EX-0001"
        assert entry["approver"] == "user"
        path = tmp_path / ".ai" / "evidence" / "observability" / "slo-exemptions.json"
        assert path.exists()
        records = load_exemptions(tmp_path)
        assert len(records) == 1
        # append-only: a second record appends, never overwrites
        entry2 = record_slo_exemption(
            tmp_path, reason="second waiver", expires_at=FUTURE, approver="delivery-manager",
        )
        assert entry2["id"] == "SLO-EX-0002"
        assert len(load_exemptions(tmp_path)) == 2
        assert load_exemptions(tmp_path)[0] == entry

    def test_valid_exemption_overrides_freeze(self, freeze_project: Path):
        record_slo_exemption(
            freeze_project, reason="user-approved release waiver",
            expires_at=FUTURE, approver="user",
        )
        result = check_slo_gate(freeze_project, now=NOW)
        assert result.decision == GATE_DECISION_PASS
        assert result.exemption is not None
        assert result.exemption["id"] == "SLO-EX-0001"
        assert "exemption SLO-EX-0001 in effect" in result.reason
        # the gate never mutates the ledger (read-only)
        before = (freeze_project / ".ai" / "evidence" / "observability"
                  / "slo-exemptions.json").read_bytes()
        check_slo_gate(freeze_project, now=NOW)
        after = (freeze_project / ".ai" / "evidence" / "observability"
                 / "slo-exemptions.json").read_bytes()
        assert before == after

    def test_expired_exemption_is_ineffective(self, freeze_project: Path):
        record_slo_exemption(
            freeze_project, reason="stale waiver", expires_at=PAST,
            approver="user",
        )
        result = check_slo_gate(freeze_project, now=NOW)
        assert result.decision == GATE_DECISION_BLOCK  # re-BLOCK
        assert GATE_BLOCK_CODE in result.reason
        assert any("expired" in w for w in result.warnings)

    def test_approver_missing_rejected(self, tmp_path: Path):
        with pytest.raises(ValueError, match="approver"):
            record_slo_exemption(tmp_path, reason="r", expires_at=FUTURE, approver="")

    def test_reason_missing_rejected(self, tmp_path: Path):
        with pytest.raises(ValueError, match="reason"):
            record_slo_exemption(tmp_path, reason="  ", expires_at=FUTURE, approver="user")

    def test_unparseable_expiry_rejected(self, tmp_path: Path):
        with pytest.raises(ValueError, match="expires_at"):
            record_slo_exemption(tmp_path, reason="r", expires_at="not-a-date",
                                 approver="user")

    def test_unreadable_ledger_cannot_override(self, freeze_project: Path):
        path = freeze_project / ".ai" / "evidence" / "observability" / "slo-exemptions.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{corrupt", encoding="utf-8")
        result = check_slo_gate(freeze_project, now=NOW)
        # fail-closed: an unreadable override cannot override the freeze
        assert result.decision == GATE_DECISION_BLOCK
        assert any("unparseable" in w for w in result.warnings)

    def test_no_exemption_file_is_normal(self, freeze_project: Path):
        result = check_slo_gate(freeze_project, now=NOW)
        assert result.exemption is None
        assert result.decision == GATE_DECISION_BLOCK

    def test_exemption_entry_without_approver_is_invalid(self, freeze_project: Path):
        path = freeze_project / ".ai" / "evidence" / "observability" / "slo-exemptions.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "schema_version": 1,
            "exemptions": [{"id": "SLO-EX-0001", "reason": "no approver",
                            "expires_at": FUTURE, "approver": ""}],
        }), encoding="utf-8")
        result = check_slo_gate(freeze_project, now=NOW)
        assert result.decision == GATE_DECISION_BLOCK
        assert any("no approver" in w for w in result.warnings)


# ── AC-04: recovery (window rollover) ────────────────────────────────────


class TestSloRecovery:
    @pytest.fixture
    def rollover_project(self, tmp_path: Path) -> Path:
        """Breaches all sit in the July window; August is clean.  A window
        rollover therefore resets the budget and the gate auto-passes."""
        july_rejected = [
            _gate(f"G-T-3500-REQUIREMENTS-{i}", "T-350", status="rejected",
                  requested="2026-07-01T09:00:00+08:00",
                  recorded="2026-07-01T10:00:00+08:00")
            for i in range(60)
        ]
        august_clean = [
            _gate("G-T-3501-REQUIREMENTS", "T-351",
                  requested="2026-08-05T09:00:00+08:00",
                  recorded="2026-08-05T10:00:00+08:00",
                  evidence=".ai/evidence/T-351/a.md"),
        ]
        tasks = [
            {"id": "T-350", "status": "completed", "phase": "S4-implementation",
             "created_at": "2026-07-01T00:00:00+08:00",
             "updated_at": "2026-07-02T00:00:00+08:00"},
            {"id": "T-351", "status": "completed", "phase": "S6-delivery",
             "created_at": "2026-08-01T00:00:00+08:00",
             "updated_at": "2026-08-06T00:00:00+08:00"},
        ]
        events = [
            _pass_event("e1", "2026-07-05T00:00:00+00:00"),
            _pass_event("e2", "2026-08-05T00:00:00+00:00"),
        ]
        _write_gates(tmp_path, july_rejected + august_clean)
        _write_tasks(tmp_path, tasks)
        _write_guard_events(tmp_path, events)
        return tmp_path

    def test_full_data_freeze(self, rollover_project: Path):
        # without a window, all data counts: 120 units -> FREEZE
        result = check_slo_gate(rollover_project, now=NOW)
        assert result.decision == GATE_DECISION_BLOCK
        assert result.budget["remaining_units"] <= 0

    def test_window_rollover_recovers(self, rollover_project: Path):
        # July window: breaches count -> frozen
        july = check_slo_gate(rollover_project, window=("2026-07-01", "2026-07-31"),
                              now=NOW)
        assert july.decision == GATE_DECISION_BLOCK
        assert july.budget["remaining_units"] <= 0
        # August window: budget resets -> auto-pass (recovery, AC-04)
        august = check_slo_gate(rollover_project, window=("2026-08-01", "2026-08-31"),
                                now=NOW)
        assert august.decision == GATE_DECISION_PASS
        assert august.status == "HEALTHY"
        assert august.budget["remaining_units"] == 100.0

    def test_slo_yaml_window_applies_by_default(self, rollover_project: Path):
        _write_slo(rollover_project, {
            "schema_version": 1,
            "window_start": "2026-08-01",
            "window_end": "2026-08-31",
        })
        result = check_slo_gate(rollover_project, now=NOW)
        assert result.decision == GATE_DECISION_PASS  # window from slo.yaml


# ── AC-05: backward compatibility (constraints only strengthened) ────────


class TestSloGateBackwardCompat:
    def test_existing_s6_checks_unchanged_no_go_still_blocks(self):
        """A NOGO release decision still blocks even with a healthy SLO
        budget — the new gate never weakens the existing checks."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_s6_project(tmp, budget="healthy",
                                    release_decision=RELEASE_DECISION_NOGO)
            ok, reason = _load_enforcement_module().check_phase_gate_enforcement(
                root, "S6-delivery")
            assert ok is False
            assert "NOGO" in reason  # existing check, unchanged semantics

    def test_existing_s6_checks_unchanged_full_evidence_passes(self):
        """GO + runtime quality PASS + security PASS + healthy budget ->
        release allowed (all existing checks and the new gate align)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_s6_project(tmp, budget="healthy")
            ok, reason = _load_enforcement_module().check_phase_gate_enforcement(
                root, "S6-delivery")
            assert ok is True, reason

    def test_gate_only_adds_blocking_conditions(self, healthy_project: Path):
        # same data shape, only the budget differs: healthy passes, freeze
        # blocks — the delta is exactly the new constraint.  (Two fixtures
        # would share pytest's per-test tmp_path, so the freeze variant is
        # built in its own directory.)
        assert check_slo_gate(healthy_project).decision == GATE_DECISION_PASS
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gates = [
                _gate(f"G-T-3200-REQUIREMENTS-{i}", "T-320", status="rejected",
                      requested="2026-07-01T09:00:00+08:00",
                      recorded="2026-07-01T10:00:00+08:00")
                for i in range(60)
            ]
            _write_gates(root, gates)
            _write_tasks(root, [
                {"id": "T-320", "status": "completed", "phase": "S4-implementation",
                 "created_at": "2026-07-01T00:00:00+08:00",
                 "updated_at": "2026-07-02T00:00:00+08:00"},
            ])
            _write_guard_events(root, [_pass_event("e1")])
            assert check_slo_gate(root).decision == GATE_DECISION_BLOCK

    def test_non_s6_phases_unaffected(self):
        """S5/S7 branches keep their exact behavior (no SLO check added):
        S5 with quality+security evidence passes; S7 without evidence blocks."""
        enforcement = _load_enforcement_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_s6_project(tmp, budget="freeze")  # SLO data would block S6
            # S5: quality + security evidence -> passes (SLO gate is S6-only)
            q = root / ".ai" / "evidence" / "quality"
            (q / "quality_report.json").write_text(
                '{"schema": "quality_report/v1", "overall": "PASS"}',
                encoding="utf-8")
            ok, reason = enforcement.check_phase_gate_enforcement(root, "S5-quality")
            assert ok is True, reason
            # S7: no integration report -> still blocks with the S7 message
            ok, reason = enforcement.check_phase_gate_enforcement(root, "S7-integration")
            assert ok is False
            assert "S7-integration" in reason


if __name__ == "__main__":
    unittest.main()
