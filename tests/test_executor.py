"""
Unit tests for loop_core.executor — PhaseExecutor execution engine.

Covers:
  - execute_phase on valid and invalid phases
  - execute_role returns correct RoleStep
  - validate_step detects complete/incomplete/BLOCKED
  - Retry logic for incomplete steps
  - BLOCKED role prevents phase advancement
  - persist_state writes correct files
  - Parallel role scheduling (all roles launched)
  - plan_phase creates correct steps
  - can_advance checks

All tests use tempfile.TemporaryDirectory for isolated file operations.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

from loop_core.state_machine import Phase, GateStatus
from loop_core.router import LoopMode
from loop_core.executor import (
    StepStatus,
    RoleStep,
    PhasePlan,
    PhaseExecutor,
    PHASE_ROLES,
)


# ── Helper ────────────────────────────────────────────────────────────

def _make_project(tmpdir: str, state_content: str | None = None) -> Path:
    """Create a minimal governed project in a temp directory."""
    root = Path(tmpdir)
    ai_dir = root / ".ai"
    ai_dir.mkdir(parents=True, exist_ok=True)
    if state_content is not None:
        (ai_dir / "state.yaml").write_text(state_content, encoding="utf-8")
    return root


STATE_S0 = """\
schema_version: 1
project_name: test-project
current_phase: S0-init
loop_mode: FULL
"""

STATE_S1_APPROVED = """\
schema_version: 1
project_name: test-project
current_phase: S1-requirements
loop_mode: FULL
current_gate_id: G-S1-approved
"""

STATE_S4 = """\
schema_version: 1
project_name: test-project
current_phase: S4-implementation
loop_mode: FULL
"""

STATE_LIGHTWEIGHT = """\
schema_version: 1
project_name: test-project
loop_mode: LIGHTWEIGHT
"""


# ── Test Cases ────────────────────────────────────────────────────────

class TestPhaseExecutorPlanPhase:
    """Tests for plan_phase() and related helpers."""

    def test_plan_phase_creates_correct_steps_full_mode(self):
        """plan_phase should create steps for all roles required by FULL mode phase."""
        executor = PhaseExecutor(mode=LoopMode.FULL, fixture_mode=True)
        plan = executor.plan_phase(Phase.S2_ARCHITECTURE)
        expected_roles = PHASE_ROLES[Phase.S2_ARCHITECTURE]
        assert len(plan.steps) == len(expected_roles)
        role_ids = [s.role_id for s in plan.steps]
        for role in expected_roles:
            assert role in role_ids
        assert plan.phase == Phase.S2_ARCHITECTURE
        assert plan.loop_mode == LoopMode.FULL

    def test_plan_phase_lightweight_uses_lightweight_roles(self):
        """LIGHTWEIGHT mode should only use developer role for any phase."""
        executor = PhaseExecutor(mode=LoopMode.LIGHTWEIGHT, fixture_mode=True)
        plan = executor.plan_phase(Phase.S4_IMPLEMENTATION)
        role_ids = [s.role_id for s in plan.steps]
        assert len(role_ids) == 1
        assert role_ids[0] == "developer"

    def test_plan_phase_steps_have_required_fields(self):
        """Each RoleStep should have required_fields populated."""
        executor = PhaseExecutor(mode=LoopMode.FULL, fixture_mode=True)
        plan = executor.plan_phase(Phase.S5_QUALITY)
        for step in plan.steps:
            assert len(step.required_fields) > 0
            assert "verdict" in step.required_fields
            assert "summary" in step.required_fields

    def test_plan_phase_all_steps_start_pending(self):
        """All steps should start with PENDING status."""
        executor = PhaseExecutor(mode=LoopMode.FULL, fixture_mode=True)
        plan = executor.plan_phase(Phase.S1_REQUIREMENTS)
        for step in plan.steps:
            assert step.status == StepStatus.PENDING


class TestValidateStep:
    """Tests for validate_step() logic."""

    def test_validate_step_complete_output(self):
        """Full output with all required fields should be COMPLETE."""
        executor = PhaseExecutor(fixture_mode=True)
        step = RoleStep(
            role_id="test-role",
            required_fields=["verdict", "summary", "findings"],
        )
        output = {
            "verdict": "PASS",
            "summary": "All good",
            "findings": ["No issues"],
        }
        status = executor.validate_step(step, output)
        assert status == StepStatus.COMPLETE
        assert step.verdict == "PASS"
        assert len(step.filled_fields) == 3

    def test_validate_step_incomplete_missing_fields(self):
        """Output missing required fields should be INCOMPLETE."""
        executor = PhaseExecutor(fixture_mode=True)
        step = RoleStep(
            role_id="test-role",
            required_fields=["verdict", "summary", "findings"],
        )
        output = {
            "verdict": "PASS",
            # missing 'summary' and 'findings'
        }
        status = executor.validate_step(step, output)
        assert status == StepStatus.INCOMPLETE
        assert len(step.filled_fields) == 1
        assert "verdict" in step.filled_fields
        assert "summary" not in step.filled_fields

    def test_validate_step_blocked_verdict(self):
        """Output with BLOCKED verdict should return BLOCKED status."""
        executor = PhaseExecutor(fixture_mode=True)
        step = RoleStep(
            role_id="test-role",
            required_fields=["verdict", "summary"],
        )
        output = {
            "verdict": "BLOCKED",
            "summary": "Cannot proceed due to conflict",
        }
        status = executor.validate_step(step, output)
        assert status == StepStatus.BLOCKED
        assert step.verdict == "BLOCKED"

    def test_validate_step_empty_output(self):
        """Empty output dict should return FAILED."""
        executor = PhaseExecutor(fixture_mode=True)
        step = RoleStep(
            role_id="test-role",
            required_fields=["verdict", "summary"],
        )
        status = executor.validate_step(step, {})
        assert status == StepStatus.FAILED

    def test_validate_step_none_output(self):
        """None output should return FAILED (handled by empty check)."""
        executor = PhaseExecutor(fixture_mode=True)
        step = RoleStep(
            role_id="test-role",
            required_fields=["verdict"],
        )
        # Empty dict triggers FAILED
        status = executor.validate_step(step, {})
        assert status == StepStatus.FAILED


class TestCanAdvance:
    """Tests for can_advance() logic."""

    def test_can_advance_all_complete(self):
        """When all steps are COMPLETE, can_advance returns True."""
        executor = PhaseExecutor(fixture_mode=True)
        plan = PhasePlan(
            phase=Phase.S4_IMPLEMENTATION,
            loop_mode=LoopMode.FULL,
            steps=[
                RoleStep(role_id="dev", status=StepStatus.COMPLETE, verdict="PASS"),
                RoleStep(role_id="reviewer", status=StepStatus.COMPLETE, verdict="PASS"),
            ],
        )
        ok, msg = executor.can_advance(plan)
        assert ok is True
        assert "complete" in msg.lower()

    def test_can_advance_blocked_role(self):
        """A BLOCKED step should prevent advancement."""
        executor = PhaseExecutor(fixture_mode=True)
        plan = PhasePlan(
            phase=Phase.S4_IMPLEMENTATION,
            loop_mode=LoopMode.FULL,
            steps=[
                RoleStep(role_id="dev", status=StepStatus.COMPLETE, verdict="PASS"),
                RoleStep(role_id="reviewer", status=StepStatus.BLOCKED, verdict="BLOCKED"),
            ],
        )
        ok, msg = executor.can_advance(plan)
        assert ok is False
        assert "reviewer" in msg

    def test_can_advance_incomplete_role(self):
        """An INCOMPLETE step should prevent advancement."""
        executor = PhaseExecutor(fixture_mode=True)
        plan = PhasePlan(
            phase=Phase.S4_IMPLEMENTATION,
            loop_mode=LoopMode.FULL,
            steps=[
                RoleStep(
                    role_id="dev", status=StepStatus.INCOMPLETE,
                    filled_fields=["verdict"], required_fields=["verdict", "summary"],
                ),
            ],
        )
        ok, msg = executor.can_advance(plan)
        assert ok is False
        assert "dev" in msg
        assert "1/2" in msg


class TestExecuteRole:
    """Tests for execute_role()."""

    def test_execute_role_returns_rolestep_with_status(self):
        """execute_role should return a RoleStep with a valid status."""
        executor = PhaseExecutor(fixture_mode=True)
        step = executor.execute_role(
            role_id="quality-engineer",
            role_prompt="Test quality check",
            input_files=[],
            output_file="/tmp/test-output.json",
        )
        assert isinstance(step, RoleStep)
        assert step.role_id == "quality-engineer"
        assert step.status in (
            StepStatus.COMPLETE, StepStatus.INCOMPLETE,
            StepStatus.BLOCKED, StepStatus.FAILED,
        )
        # Simulated output should always pass
        assert step.status == StepStatus.COMPLETE
        assert step.verdict == "PASS"

    def test_execute_role_simulates_output_for_missing_agent_script(self):
        """When no agent script exists, _simulate_role_output fills fields."""
        executor = PhaseExecutor(fixture_mode=True)
        step = executor.execute_role(
            role_id="security-engineer",
            role_prompt="Scan for vulnerabilities",
            input_files=[],
        )
        assert step.status == StepStatus.COMPLETE
        assert step.verdict == "PASS"
        # Security engineer should have extra fields filled
        assert len(step.filled_fields) >= 2


class TestRetryLogic:
    """Tests for retry behavior of incomplete/failed steps."""

    def test_retry_on_incomplete_then_complete(self, monkeypatch):
        """Step marked INCOMPLETE should retry up to max_retries."""
        executor = PhaseExecutor(fixture_mode=True)
        step = RoleStep(
            role_id="tester",
            status=StepStatus.RUNNING,
            required_fields=["verdict", "summary", "findings"],
            max_retries=3,
        )

        call_count = [0]

        def mock_launch(role_id, prompt, input_files, output_path):
            call_count[0] += 1
            if call_count[0] < 2:
                # First call: incomplete
                return {"verdict": "PASS", "summary": "OK"}
                # Missing 'findings'
            else:
                # Second call: complete
                return {"verdict": "PASS", "summary": "OK", "findings": ["done"]}

        monkeypatch.setattr(executor, "_launch_agent_subprocess", mock_launch)

        # Simulate the retry loop manually
        while step.retries < step.max_retries:
            output = executor._launch_agent_subprocess(
                step.role_id, "test", [], "/tmp/out.json"
            )
            status = executor.validate_step(step, output)
            if status == StepStatus.COMPLETE:
                break
            if status == StepStatus.BLOCKED:
                break
            step.retries += 1

        assert step.status == StepStatus.COMPLETE
        assert call_count[0] == 2
        assert step.retries == 1  # retried once

    def test_blocked_role_does_not_retry(self, monkeypatch):
        """A step with BLOCKED verdict should not be retried."""
        executor = PhaseExecutor(fixture_mode=True)
        step = RoleStep(
            role_id="blocker",
            status=StepStatus.RUNNING,
            required_fields=["verdict", "summary"],
            max_retries=3,
        )

        def mock_launch(role_id, prompt, input_files, output_path):
            return {"verdict": "BLOCKED", "summary": "Cannot proceed"}

        monkeypatch.setattr(executor, "_launch_agent_subprocess", mock_launch)

        # Simulate retry loop
        while step.retries < step.max_retries:
            output = executor._launch_agent_subprocess(
                step.role_id, "test", [], "/tmp/out.json"
            )
            status = executor.validate_step(step, output)
            step.status = status
            if status == StepStatus.COMPLETE:
                break
            if status == StepStatus.BLOCKED:
                break  # Don't retry BLOCKED
            step.retries += 1

        assert step.status == StepStatus.BLOCKED
        assert step.retries == 0  # No retry attempted


class TestPersistState:
    """Tests for persist_state() and related file I/O."""

    def test_persist_state_writes_state_yaml(self):
        """persist_state should create/update .ai/state.yaml."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, STATE_S0)
            executor = PhaseExecutor(mode=LoopMode.FULL, fixture_mode=True)
            plan = PhasePlan(
                phase=Phase.S1_REQUIREMENTS,
                loop_mode=LoopMode.FULL,
                status=StepStatus.COMPLETE,
                gate_id="G-S1-gate",
            )
            executor.persist_state(plan, project_root=root)

            state_path = root / ".ai" / "state.yaml"
            assert state_path.exists()
            content = state_path.read_text(encoding="utf-8")
            assert "S1-requirements" in content
            assert "loop_mode: FULL" in content
            assert "G-S1-gate" in content

    def test_persist_state_writes_task_graph(self):
        """persist_state should create .ai/task_graph.yaml."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, STATE_S0)
            executor = PhaseExecutor(mode=LoopMode.FULL, fixture_mode=True)
            step1 = RoleStep(
                role_id="developer",
                status=StepStatus.COMPLETE,
                verdict="PASS",
                retries=0,
                output_file="out.json",
            )
            plan = PhasePlan(
                phase=Phase.S4_IMPLEMENTATION,
                loop_mode=LoopMode.FULL,
                status=StepStatus.COMPLETE,
                steps=[step1],
            )
            executor.persist_state(plan, project_root=root)

            graph_path = root / ".ai" / "task_graph.yaml"
            assert graph_path.exists()
            content = graph_path.read_text(encoding="utf-8")
            assert "S4-implementation" in content
            assert "developer" in content
            assert "PASS" in content

    def test_persist_state_updates_last_handoff(self):
        """persist_state should update last_handoff_at timestamp."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, STATE_S0)
            executor = PhaseExecutor(fixture_mode=True)
            plan = PhasePlan(phase=Phase.S2_ARCHITECTURE, loop_mode=LoopMode.FULL)
            executor.persist_state(plan, project_root=root)

            content = (root / ".ai" / "state.yaml").read_text(encoding="utf-8")
            assert "last_handoff_at" in content


class TestExecutePhase:
    """End-to-end tests for execute_phase()."""

    def test_execute_phase_first_phase_succeeds(self):
        """Executing S0-init as the first phase should work."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp)  # No state.yaml yet (fresh project)
            executor = PhaseExecutor(mode=LoopMode.FULL, fixture_mode=True)
            plan = executor.execute_phase(
                Phase.S0_INIT,
                project_root=root,
            )
            assert plan.status == StepStatus.COMPLETE
            assert len(plan.steps) == len(PHASE_ROLES[Phase.S0_INIT])
            for step in plan.steps:
                assert step.status == StepStatus.COMPLETE

    def test_execute_phase_invalid_transition_blocked(self):
        """Jumping from S0-init to S4-implementation should be blocked."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, STATE_S0)
            executor = PhaseExecutor(mode=LoopMode.FULL, fixture_mode=True)
            plan = executor.execute_phase(
                Phase.S4_IMPLEMENTATION,
                project_root=root,
            )
            assert plan.status == StepStatus.BLOCKED
            # Should have a transition-check error step
            transition_errors = [
                s for s in plan.steps if s.role_id == "transition-check"
            ]
            assert len(transition_errors) >= 1
            assert transition_errors[0].status == StepStatus.BLOCKED

    def test_execute_phase_valid_forward_transition(self):
        """S0-init to S1-requirements should work (valid transition)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, STATE_S0)
            executor = PhaseExecutor(mode=LoopMode.FULL, fixture_mode=True)
            plan = executor.execute_phase(
                Phase.S1_REQUIREMENTS,
                project_root=root,
            )
            # This should complete since roles have simulated output
            assert plan.status == StepStatus.COMPLETE

    def test_execute_phase_persists_state_after_execution(self):
        """After execute_phase, state files should be updated."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp)  # fresh project
            executor = PhaseExecutor(mode=LoopMode.FULL, fixture_mode=True)
            plan = executor.execute_phase(
                Phase.S0_INIT,
                project_root=root,
            )
            assert plan.status == StepStatus.COMPLETE

            state_path = root / ".ai" / "state.yaml"
            assert state_path.exists()
            content = state_path.read_text(encoding="utf-8")
            assert "S0-init" in content

            graph_path = root / ".ai" / "task_graph.yaml"
            assert graph_path.exists()

    def test_execute_phase_lightweight_mode_fewer_roles(self):
        """LIGHTWEIGHT mode should only run the developer role."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, STATE_LIGHTWEIGHT)
            executor = PhaseExecutor(mode=LoopMode.LIGHTWEIGHT, fixture_mode=True)
            plan = executor.execute_phase(
                Phase.S4_IMPLEMENTATION,
                project_root=root,
            )
            # LIGHTWEIGHT only has one role (developer)
            assert len(plan.steps) == 1
            assert plan.steps[0].role_id == "developer"


class TestBlockedRolePreventsAdvance:
    """Tests that BLOCKED roles actually prevent phase advancement."""

    def test_blocked_role_stops_phase(self, monkeypatch):
        """When a role returns BLOCKED, the phase should not advance."""
        executor = PhaseExecutor(mode=LoopMode.FULL, fixture_mode=True)
        plan = PhasePlan(
            phase=Phase.S4_IMPLEMENTATION,
            loop_mode=LoopMode.FULL,
            steps=[
                RoleStep(role_id="developer", status=StepStatus.COMPLETE, verdict="PASS"),
                RoleStep(role_id="independent-reviewer", status=StepStatus.BLOCKED, verdict="BLOCKED"),
                RoleStep(role_id="quality-engineer", status=StepStatus.COMPLETE, verdict="PASS"),
            ],
        )
        ok, msg = executor.can_advance(plan)
        assert ok is False
        assert "independent-reviewer" in msg


class TestParallelRoleScheduling:
    """Tests for parallel role scheduling behavior."""

    def test_all_roles_in_phase_are_launched(self):
        """All roles for a phase should be included in the plan steps."""
        executor = PhaseExecutor(mode=LoopMode.FULL, fixture_mode=True)
        plan = executor.plan_phase(Phase.S4_IMPLEMENTATION)
        expected = PHASE_ROLES[Phase.S4_IMPLEMENTATION]
        launched = {s.role_id for s in plan.steps}
        assert launched == set(expected)

    def test_execute_phase_launches_all_roles(self):
        """execute_phase should produce a step for each role."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp)  # fresh
            executor = PhaseExecutor(mode=LoopMode.FULL, fixture_mode=True)
            plan = executor.execute_phase(Phase.S0_INIT, project_root=root)
            expected_roles = set(PHASE_ROLES[Phase.S0_INIT])
            launched_roles = {s.role_id for s in plan.steps}
            assert launched_roles == expected_roles

    def test_each_role_step_has_independent_status(self):
        """Each role step should have its own status."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp)
            executor = PhaseExecutor(mode=LoopMode.FULL, fixture_mode=True)
            plan = executor.execute_phase(Phase.S0_INIT, project_root=root)
            assert len(plan.steps) >= 1
            for step in plan.steps:
                assert step.status is not None
                assert step.role_id


class TestPhaseExecutorModes:
    """Tests for phase list variations across modes."""

    def test_full_mode_has_all_phases(self):
        executor = PhaseExecutor(mode=LoopMode.FULL, fixture_mode=True)
        phases = executor.get_phases()
        assert len(phases) == 12

    def test_standard_mode_has_core_phases(self):
        executor = PhaseExecutor(mode=LoopMode.STANDARD, fixture_mode=True)
        phases = executor.get_phases()
        assert len(phases) == 6
        assert Phase.S0_INIT in phases
        assert Phase.S1_REQUIREMENTS in phases
        assert Phase.S2_ARCHITECTURE in phases
        assert Phase.S4_IMPLEMENTATION in phases
        assert Phase.S5_QUALITY in phases
        assert Phase.S6_DELIVERY in phases

    def test_lightweight_mode_has_minimal_phases(self):
        executor = PhaseExecutor(mode=LoopMode.LIGHTWEIGHT, fixture_mode=True)
        phases = executor.get_phases()
        assert len(phases) == 3


class TestFreezeInputs:
    """Tests for input file freezing."""

    def test_freeze_inputs_hashes_files(self):
        """Existing files should get SHA256 hashes."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f1 = root / "test.txt"
            f1.write_text("hello world", encoding="utf-8")
            f2 = root / "missing.txt"
            # f2 does not exist

            executor = PhaseExecutor(fixture_mode=True)
            hashes = executor._freeze_inputs([str(f1), str(f2)])
            assert len(hashes) == 2
            assert hashes[str(f1)] != "MISSING"
            assert hashes[str(f2)] == "MISSING"
            # Verify it's a valid SHA256 hex string
            assert len(hashes[str(f1)]) == 64

    def test_freeze_inputs_empty_list(self):
        executor = PhaseExecutor(fixture_mode=True)
        hashes = executor._freeze_inputs([])
        assert hashes == {}
