"""
Tests for resume payload (U6, T-0088) in loop_core.human_review_packet.

Covers T-0088 AC-05:
- AC-05a: payload generation — all snapshot fields present, recovery data
  taken verbatim from authoritative sources (state.yaml / task_graph.yaml /
  gates.yaml), JSON-serializable
- AC-05b: resume succeeds when payload matches current state
- AC-05c: state drift (task/gate/phase mismatch) raises an explicit
  StateDriftError ("状态已漂移") — the machine never guesses
- AC-05d: backward compatibility — existing packet interface unchanged,
  default packets carry no payload

Plus fail-closed validation: missing sources, field inconsistency at build
time, gate already decided, task removed, unsupported schema versions.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from loop_core.human_review_packet import (
    RESUME_PAYLOAD_SCHEMA,
    RESUME_PAYLOAD_SCHEMA_VERSION,
    DecisionPoint,
    HumanReviewPacket,
    HumanReviewPacketBuilder,
    PacketType,
    ResumeContext,
    ResumePayload,
    ResumePayloadError,
    ResumeSnapshot,
    StateDriftError,
    build_resume_payload,
    resume_from_payload,
)

TASK_ID = "T-0090"
GATE_ID = "G-T-0090-DELIVERY"
PHASE = "S6-delivery"


# ── Fixtures ───────────────────────────────────────────────────────────────


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )


@pytest.fixture
def project(tmp_path):
    """A minimal authoritative governance state for a paused delivery gate."""
    state = {
        "schema_version": 1,
        "project_name": "Resume Test Project",
        "current_phase": PHASE,
        "current_task_id": TASK_ID,
        "current_gate_id": GATE_ID,
        "loop_mode": "FULL",
        "last_handoff_at": "2026-08-01T00:00:00+08:00",
    }
    task_graph = {
        "schema_version": 1,
        "tasks": [
            {"id": "T-0089", "title": "Previous task", "status": "completed",
             "phase": PHASE},
            {"id": TASK_ID, "title": "Paused delivery task",
             "status": "in_progress", "phase": PHASE, "priority": "P0",
             "depends_on": ["T-0089"], "gates": [GATE_ID],
             "note": "paused at delivery gate"},
            {"id": "T-0091", "title": "Next task", "status": "pending",
             "phase": PHASE, "priority": "P1"},
            {"id": "T-0092", "title": "Blocked task", "status": "blocked",
             "phase": PHASE},
        ],
        "edges": [
            {"from": "T-0089", "to": TASK_ID},
            {"from": TASK_ID, "to": "T-0091"},
        ],
    }
    gates = {
        "schema_version": 1,
        "gates": [
            {"id": GATE_ID, "task_id": TASK_ID, "gate_type": "user-approval",
             "status": "pending", "decision": None,
             "recorded_at": None,
             "evidence": f".ai/evidence/{TASK_ID}/approval-evidence.json"},
        ],
    }
    _write_yaml(tmp_path / ".ai" / "state.yaml", state)
    _write_yaml(tmp_path / ".ai" / "task_graph.yaml", task_graph)
    _write_yaml(tmp_path / ".ai" / "gates.yaml", gates)
    tasks_dir = tmp_path / ".ai" / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / f"{TASK_ID}.md").write_text("# T-0090\n", encoding="utf-8")
    evidence_dir = tmp_path / ".ai" / "evidence" / TASK_ID
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "approval-evidence.json").write_text("{}", encoding="utf-8")
    return tmp_path


def _rewrite_state(project: Path, **overrides) -> None:
    path = project / ".ai" / "state.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data.update(overrides)
    _write_yaml(path, data)


def _rewrite_gate_status(project: Path, status: str) -> None:
    path = project / ".ai" / "gates.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for gate in data["gates"]:
        if gate["id"] == GATE_ID:
            gate["status"] = status
    _write_yaml(path, data)


def _build(project, **kwargs) -> ResumePayload:
    params = {
        "task_id": TASK_ID,
        "gate_id": GATE_ID,
        "phase": PHASE,
        "decision_type": PacketType.GATE_APPROVAL,
        "presentation_version": 2,
        "packet_id": "HRP-TEST0001",
    }
    params.update(kwargs)
    return build_resume_payload(project, **params)


def _sample_phase_data():
    """Minimal phase-completion inputs for the builder."""
    artifacts = {"architecture_diagram": "A visual map of the system parts"}
    review_results = {"system-architect": "Well-structured. PASS."}
    quality_report = {"pass": True, "checks": ["All rules satisfied"], "warnings": []}
    return artifacts, review_results, quality_report


# ── AC-05a: payload generation ─────────────────────────────────────────────


class TestAC05aPayloadGeneration:
    def test_snapshot_fields_complete(self, project):
        payload = _build(project)
        assert payload.schema == RESUME_PAYLOAD_SCHEMA
        assert payload.schema_version == RESUME_PAYLOAD_SCHEMA_VERSION
        assert payload.generated_at  # generation timestamp present

        snap = payload.snapshot
        assert isinstance(snap, ResumeSnapshot)
        assert snap.task_id == TASK_ID
        assert snap.gate_id == GATE_ID
        assert snap.phase == PHASE

        # Decision point: decision type + presentation version
        assert isinstance(snap.decision_point, DecisionPoint)
        assert snap.decision_point.decision_type == PacketType.GATE_APPROVAL.value
        assert snap.decision_point.presentation_version == 2
        assert snap.decision_point.packet_id == "HRP-TEST0001"

    def test_context_pointers_all_real(self, project):
        payload = _build(project)
        pointers = payload.snapshot.context_pointers
        assert len(pointers) >= 5  # 3 sources + task file + evidence dir
        for pointer in pointers:
            assert Path(pointer).exists(), f"context pointer is not real: {pointer}"
        assert str(project / ".ai" / "state.yaml") in pointers
        assert str(project / ".ai" / "task_graph.yaml") in pointers
        assert str(project / ".ai" / "gates.yaml") in pointers
        assert str(project / ".ai" / "tasks" / f"{TASK_ID}.md") in pointers
        assert str(project / ".ai" / "evidence" / TASK_ID) in pointers

    def test_recovery_data_comes_from_authoritative_sources(self, project):
        payload = _build(project)
        recovery = payload.recovery
        # task record verbatim from task_graph.yaml
        assert recovery["task"]["id"] == TASK_ID
        assert recovery["task"]["title"] == "Paused delivery task"
        assert recovery["task"]["status"] == "in_progress"
        assert recovery["task"]["priority"] == "P0"
        assert recovery["task"]["depends_on"] == ["T-0089"]
        assert recovery["task"]["gates"] == [GATE_ID]
        # gate record verbatim from gates.yaml
        assert recovery["gate"]["id"] == GATE_ID
        assert recovery["gate"]["task_id"] == TASK_ID
        assert recovery["gate"]["status"] == "pending"
        assert recovery["gate"]["gate_type"] == "user-approval"
        # pending tasks: only pending/in_progress/active, blocked excluded
        pending_ids = [t["id"] for t in recovery["pending_tasks"]]
        assert pending_ids == [TASK_ID, "T-0091"]
        assert all(
            t["status"] in ("pending", "in_progress", "active")
            for t in recovery["pending_tasks"]
        )

    def test_payload_is_json_serializable(self, project):
        payload = _build(project)
        as_dict = payload.to_dict()
        json.dumps(as_dict)  # must not raise
        assert as_dict["snapshot"]["task_id"] == TASK_ID
        # JSON string round-trip
        restored = ResumePayload.from_json(payload.to_json())
        assert restored.snapshot.task_id == TASK_ID
        assert restored.snapshot.gate_id == GATE_ID
        assert restored.snapshot.phase == PHASE
        assert restored.recovery == payload.recovery

    def test_decision_type_accepts_plain_string(self, project):
        payload = _build(project, decision_type="veto_escalation")
        assert payload.snapshot.decision_point.decision_type == "veto_escalation"


# ── AC-05b: resume success ─────────────────────────────────────────────────


class TestAC05bResumeSuccess:
    def test_resume_returns_resumable_context(self, project):
        payload = _build(project)
        ctx = resume_from_payload(payload, project)
        assert isinstance(ctx, ResumeContext)
        assert ctx.task_id == TASK_ID
        assert ctx.gate_id == GATE_ID
        assert ctx.phase == PHASE
        assert ctx.decision_point.decision_type == "gate_approval"
        assert ctx.decision_point.presentation_version == 2
        assert ctx.decision_point.packet_id == "HRP-TEST0001"
        assert ctx.task["status"] == "in_progress"
        assert ctx.gate["status"] == "pending"
        assert [t["id"] for t in ctx.pending_tasks] == [TASK_ID, "T-0091"]
        assert ctx.resumed_at  # resume timestamp present
        assert ctx.sources["state.yaml"] == str(project / ".ai" / "state.yaml")

    def test_resume_accepts_payload_dict_from_json(self, project):
        payload = _build(project)
        ctx = resume_from_payload(payload.to_dict(), project)
        assert ctx.task_id == TASK_ID
        assert ctx.gate_id == GATE_ID

    def test_pause_resume_full_cycle(self, project):
        """Gate pause -> payload -> (state unchanged) -> resume works."""
        payload = _build(project)
        # Simulate the pause period: state files are untouched, then resume.
        ctx = resume_from_payload(payload, project)
        assert ctx.gate_id == GATE_ID
        assert ctx.phase == PHASE
        # The resumed context still carries the original decision point.
        assert ctx.decision_point.packet_id == "HRP-TEST0001"


# ── AC-05c: state drift → explicit error, never guess ─────────────────────


class TestAC05cStateDrift:
    def test_drift_on_task_mismatch(self, project):
        payload = _build(project)
        _rewrite_state(project, current_task_id="T-0091")
        with pytest.raises(StateDriftError, match="状态已漂移"):
            resume_from_payload(payload, project)

    def test_drift_on_gate_mismatch(self, project):
        payload = _build(project)
        _rewrite_state(project, current_gate_id="G-OTHER-GATE")
        with pytest.raises(StateDriftError, match="状态已漂移"):
            resume_from_payload(payload, project)

    def test_drift_on_phase_mismatch(self, project):
        payload = _build(project)
        _rewrite_state(project, current_phase="S5-quality")
        with pytest.raises(StateDriftError, match="状态已漂移"):
            resume_from_payload(payload, project)

    def test_drift_error_carries_expected_and_actual(self, project):
        payload = _build(project)
        _rewrite_state(project, current_task_id="T-0091")
        with pytest.raises(StateDriftError) as excinfo:
            resume_from_payload(payload, project)
        message = str(excinfo.value)
        assert "T-0091" in message and TASK_ID in message

    def test_drift_when_task_removed_from_graph(self, project):
        payload = _build(project)
        path = project / ".ai" / "task_graph.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["tasks"] = [t for t in data["tasks"] if t["id"] != TASK_ID]
        _write_yaml(path, data)
        with pytest.raises(StateDriftError, match="状态已漂移"):
            resume_from_payload(payload, project)

    def test_drift_when_gate_removed(self, project):
        payload = _build(project)
        path = project / ".ai" / "gates.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["gates"] = [g for g in data["gates"] if g["id"] != GATE_ID]
        _write_yaml(path, data)
        with pytest.raises(StateDriftError, match="状态已漂移"):
            resume_from_payload(payload, project)

    def test_drift_when_gate_rebound_to_other_task(self, project):
        payload = _build(project)
        path = project / ".ai" / "gates.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["gates"][0]["task_id"] = "T-0091"
        _write_yaml(path, data)
        with pytest.raises(StateDriftError, match="状态已漂移"):
            resume_from_payload(payload, project)

    def test_drift_when_gate_already_decided(self, project):
        payload = _build(project)
        _rewrite_gate_status(project, "approved")
        with pytest.raises(StateDriftError, match="状态已漂移"):
            resume_from_payload(payload, project)


# ── AC-05d: backward compatibility ────────────────────────────────────────


class TestAC05dBackwardCompatibility:
    def test_default_packet_has_no_resume_payload(self):
        artifacts, review_results, quality_report = _sample_phase_data()
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S2-architecture",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        assert packet.resume_payload is None
        # Rendered output is unchanged in structure
        assert packet.to_markdown().startswith("# Phase Delivery Decision Packet")
        assert packet.to_plain_text().startswith("PHASE DELIVERY DECISION PACKET")

    def test_default_veto_packet_has_no_resume_payload(self):
        packet = HumanReviewPacketBuilder.from_veto_escalation(
            vetoes=[{"vetoed_by": "quality-engineer", "reason": "Blocked"}],
            task_id="T-0001",
        )
        assert packet.resume_payload is None
        assert "VETOES RAISED" in packet.to_plain_text()

    def test_packet_can_carry_resume_payload_optional(self, project):
        payload = _build(project)
        artifacts, review_results, quality_report = _sample_phase_data()
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S2-architecture",
            task_id=TASK_ID,
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
            resume_payload=payload,
        )
        assert isinstance(packet, HumanReviewPacket)
        assert packet.resume_payload is payload
        assert packet.resume_payload.snapshot.task_id == TASK_ID
        # Human-facing rendering still works with payload attached
        assert packet.to_markdown().startswith("# Phase Delivery Decision Packet")

    def test_veto_packet_can_carry_resume_payload_optional(self, project):
        payload = _build(project)
        packet = HumanReviewPacketBuilder.from_veto_escalation(
            vetoes=[{"vetoed_by": "quality-engineer", "reason": "Blocked"}],
            task_id=TASK_ID,
            resume_payload=payload,
        )
        assert packet.resume_payload is payload

    def test_existing_builder_signature_unchanged(self):
        """Five positional args still work — nothing shifted."""
        artifacts, review_results, quality_report = _sample_phase_data()
        packet = HumanReviewPacketBuilder.from_phase_completion(
            "S2-architecture", "T-0001", artifacts, review_results, quality_report
        )
        assert packet.resume_payload is None
        assert packet.task_id == "T-0001"


# ── Fail-closed validation (build + resume) ───────────────────────────────


class TestFailClosedValidation:
    def test_build_fails_closed_on_missing_source(self, tmp_path):
        with pytest.raises(ResumePayloadError, match="来源文件缺失"):
            build_resume_payload(
                tmp_path, task_id=TASK_ID, gate_id=GATE_ID, phase=PHASE,
                decision_type="gate_approval",
            )

    def test_build_fails_closed_on_task_mismatch_in_state(self, project):
        _rewrite_state(project, current_task_id="T-0091")
        with pytest.raises(ResumePayloadError, match="字段不一致"):
            _build(project)

    def test_build_fails_closed_on_gate_mismatch_in_state(self, project):
        _rewrite_state(project, current_gate_id="G-OTHER")
        with pytest.raises(ResumePayloadError, match="字段不一致"):
            _build(project)

    def test_build_fails_closed_on_phase_mismatch_in_state(self, project):
        _rewrite_state(project, current_phase="S7-integration")
        with pytest.raises(ResumePayloadError, match="字段不一致"):
            _build(project)

    def test_build_fails_closed_on_unknown_task(self, project):
        # state.yaml must point at the requested ID so the check reaches
        # task_graph.yaml (which lacks the task).
        _rewrite_state(project, current_task_id="T-9999")
        with pytest.raises(ResumePayloadError, match="不存在任务"):
            _build(project, task_id="T-9999")

    def test_build_fails_closed_on_unknown_gate(self, project):
        _rewrite_state(project, current_gate_id="G-NOPE")
        with pytest.raises(ResumePayloadError, match="不存在 gate"):
            _build(project, gate_id="G-NOPE")

    def test_build_fails_closed_on_gate_task_binding_mismatch(self, project):
        path = project / ".ai" / "gates.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["gates"][0]["task_id"] = "T-0091"
        _write_yaml(path, data)
        with pytest.raises(ResumePayloadError, match="字段不一致"):
            _build(project)

    def test_resume_fails_closed_on_missing_source(self, project):
        payload = _build(project)
        (project / ".ai" / "state.yaml").unlink()
        with pytest.raises(ResumePayloadError, match="来源文件缺失"):
            resume_from_payload(payload, project)

    def test_resume_rejects_unsupported_schema(self):
        with pytest.raises(ResumePayloadError, match="unsupported payload schema"):
            ResumePayload.from_dict(
                {"schema": "other", "schema_version": 1,
                 "snapshot": {"task_id": TASK_ID}}
            )

    def test_resume_rejects_unsupported_schema_version(self, project):
        payload = _build(project)
        data = payload.to_dict()
        data["schema_version"] = 99
        with pytest.raises(ResumePayloadError, match="schema_version"):
            resume_from_payload(data, project)

    def test_resume_rejects_missing_snapshot(self):
        with pytest.raises(ResumePayloadError, match="snapshot"):
            resume_from_payload(
                {"schema": RESUME_PAYLOAD_SCHEMA,
                 "schema_version": RESUME_PAYLOAD_SCHEMA_VERSION},
                project_root=".",
            )

    def test_from_dict_rejects_malformed_snapshot(self):
        with pytest.raises(ResumePayloadError, match="missing 'task_id'"):
            ResumePayload.from_dict(
                {"schema": RESUME_PAYLOAD_SCHEMA,
                 "schema_version": RESUME_PAYLOAD_SCHEMA_VERSION,
                 "snapshot": {"gate_id": GATE_ID, "phase": PHASE,
                              "decision_point": {"decision_type": "gate_approval",
                                                 "presentation_version": 1}}}
            )

    def test_to_dict_from_dict_roundtrip(self, project):
        payload = _build(project)
        restored = ResumePayload.from_dict(payload.to_dict())
        assert restored.snapshot.task_id == TASK_ID
        assert restored.snapshot.decision_point.packet_id == "HRP-TEST0001"
        assert restored.recovery == payload.recovery
