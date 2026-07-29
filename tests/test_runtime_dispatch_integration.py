"""Integration tests for RuntimeController + HostAgentInvoker + DispatchLease.

Tests the full dispatch pipeline: lease conflict detection, fail-closed
behaviour without an adapter, and runtime projection file creation on
successful dispatch with a mock adapter.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from loop_core.agent_adapter import AgentAdapter, AgentInput, AgentOutput, AgentStatus
from loop_core.dispatch_lease import DispatchLease, LeaseStatus
from loop_core.host_agent_invoker import ReceiptStatus
from loop_core.runtime_controller import (
    ExecutionCapability,
    ExecutionContext,
    RuntimeController,
    RuntimeControllerError,
    RuntimeState,
)


# ============================================================================
# Mock AgentAdapter — simulates Agent dispatch for testing
# ============================================================================


class MockPassAdapter(AgentAdapter):
    """An AgentAdapter stub that always returns COMPLETED (PASS)."""

    def launch_agent(self, agent_input: AgentInput) -> AgentOutput:
        return AgentOutput(
            actor_id=agent_input.actor_id or "mock-actor",
            session_id=agent_input.session_id or "mock-session",
            role_id=agent_input.role_id,
            task_id=agent_input.task_id,
            status=AgentStatus.COMPLETED,
        )

    def get_status(self, session_id: str) -> AgentStatus:
        return AgentStatus.COMPLETED

    def collect_output(self, session_id: str) -> AgentOutput:
        return AgentOutput(
            actor_id="mock-actor",
            session_id=session_id,
            role_id="developer",
            task_id="T-1",
            status=AgentStatus.COMPLETED,
            stdout="mock output",
        )

    @property
    def host_name(self) -> str:
        return "mock-host"


class MockBlockedAdapter(AgentAdapter):
    """An AgentAdapter stub that always returns BLOCKED."""

    def launch_agent(self, agent_input: AgentInput) -> AgentOutput:
        return AgentOutput(
            actor_id=agent_input.actor_id or "mock-actor",
            session_id=agent_input.session_id or "mock-session",
            role_id=agent_input.role_id,
            task_id=agent_input.task_id,
            status=AgentStatus.BLOCKED,
        )

    def get_status(self, session_id: str) -> AgentStatus:
        return AgentStatus.BLOCKED

    def collect_output(self, session_id: str) -> AgentOutput:
        return AgentOutput(
            actor_id="mock-actor",
            session_id=session_id,
            role_id="developer",
            task_id="T-1",
            status=AgentStatus.BLOCKED,
        )

    @property
    def host_name(self) -> str:
        return "mock-host"


# ============================================================================
# Helpers
# ============================================================================


@pytest.fixture(autouse=True)
def _clean_leases():
    """Ensure the global DispatchLease registry is empty before/after each test."""
    DispatchLease.release_all()
    yield
    DispatchLease.release_all()


def _make_capability(
    task_id: str = "T-0001",
    execution_id: str = "exec-test",
    allowed_paths: tuple[str, ...] = ("src/",),
) -> ExecutionCapability:
    """Build a minimal ExecutionCapability for testing."""
    return ExecutionCapability(
        capability_id="cap-test",
        task_id=task_id,
        execution_id=execution_id,
        assigned_actor_id="developer:T-0001",
        allowed_paths=allowed_paths,
        issued_at="2026-07-29T00:00:00Z",
        idempotency_key="test-key",
    )


def _make_context(
    actor_id: str = "dev-agent",
    role_id: str = "developer",
    caller_class: str = "agent",
    task_id: str = "T-0001",
    execution_id: str = "exec-test",
    session_id: str = "test-session",
) -> ExecutionContext:
    """Build a minimal ExecutionContext for testing."""
    return ExecutionContext(
        actor_id=actor_id,
        role_id=role_id,
        caller_class=caller_class,
        task_id=task_id,
        execution_id=execution_id,
        session_id=session_id,
        capability_id="cap-test",
    )


def _setup_onboarded_controller(root: Path) -> RuntimeController:
    """Create a controller on a temp directory and onboard the project."""
    controller = RuntimeController(root)
    controller.onboard_project("integration test")
    return controller


# ============================================================================
# Test: Dispatch without adapter → BLOCKED, SETUP_INCOMPLETE
# ============================================================================


class TestDispatchWithoutAdapter:
    """Dispatch must return BLOCKED when no agent_adapter is wired in."""

    def test_dispatch_without_adapter_returns_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)

            capability = _make_capability()
            context = _make_context()

            snapshot = controller.dispatch_execution(capability, context)

            # The dispatch should complete without raising, but the receipt
            # status should be BLOCKED because no adapter is available.
            assert snapshot.lease_status == ReceiptStatus.BLOCKED.value
            assert snapshot.child_session is not None
            # Simulated child session for blocked dispatch
            assert snapshot.child_session.startswith("sim-")
            # Actor should be populated from the context
            assert snapshot.actor == context.actor_id

    def test_dispatch_without_adapter_does_not_create_projection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)

            capability = _make_capability()
            context = _make_context()

            controller.dispatch_execution(capability, context)

            # Projection file must NOT exist — only written on PASS
            assert not controller.projection_path.exists()

    def test_dispatch_without_adapter_sets_expected_runtime_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)

            capability = _make_capability()
            context = _make_context()

            snapshot = controller.dispatch_execution(capability, context)

            # BLOCKED dispatch transitions to USER_APPROVAL_REQUIRED
            assert snapshot.runtime_state == RuntimeState.USER_APPROVAL_REQUIRED.value

    def test_dispatch_without_adapter_preserves_execution_ids_in_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)

            capability = _make_capability()
            context = _make_context()

            snapshot = controller.dispatch_execution(capability, context)

            assert snapshot.task_id == capability.task_id
            assert snapshot.execution_id == capability.execution_id
            assert snapshot.capability_id == capability.capability_id


# ============================================================================
# Test: DispatchLease conflict → second dispatch blocked
# ============================================================================


class TestDispatchLeaseConflict:
    """Only one active dispatch per (task_id, role_id)."""

    def test_second_dispatch_same_task_role_returns_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)

            capability1 = _make_capability(execution_id="exec-1")
            context1 = _make_context(execution_id="exec-1")

            # First dispatch — should succeed (or be BLOCKED without adapter)
            first = controller.dispatch_execution(capability1, context1)

            # Second dispatch with same (task_id, role_id) but different execution
            capability2 = _make_capability(execution_id="exec-2")
            context2 = _make_context(execution_id="exec-2")

            second = controller.dispatch_execution(capability2, context2)

            # Second dispatch should be CONFLICT
            assert second.lease_status == LeaseStatus.CONFLICT.value
            assert second.child_session is None

    def test_conflict_does_not_alter_first_lease(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)

            capability1 = _make_capability(execution_id="exec-1")
            context1 = _make_context(execution_id="exec-1")

            first = controller.dispatch_execution(capability1, context1)

            # Second dispatch with same (task_id, role_id)
            capability2 = _make_capability(execution_id="exec-2")
            context2 = _make_context(execution_id="exec-2")
            controller.dispatch_execution(capability2, context2)

            # The original lease should still be in the registry
            lease = DispatchLease.lookup("T-0001", "developer")
            assert lease is not None
            assert lease.status in (LeaseStatus.ACTIVE,)

    def test_different_role_id_no_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)

            cap_dev = _make_capability(execution_id="exec-1")
            ctx_dev = _make_context(role_id="developer", execution_id="exec-1")

            cap_rev = _make_capability(execution_id="exec-2")
            ctx_rev = _make_context(role_id="reviewer", execution_id="exec-2",
                                     actor_id="rev-agent")

            first = controller.dispatch_execution(cap_dev, ctx_dev)
            second = controller.dispatch_execution(cap_rev, ctx_rev)

            # Different role_id → no conflict
            assert second.lease_status != LeaseStatus.CONFLICT.value

    def test_different_task_id_no_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)

            cap_a = _make_capability(task_id="T-A", execution_id="exec-1")
            ctx_a = _make_context(task_id="T-A", execution_id="exec-1")

            cap_b = _make_capability(task_id="T-B", execution_id="exec-2")
            ctx_b = _make_context(task_id="T-B", execution_id="exec-2")

            first = controller.dispatch_execution(cap_a, ctx_a)
            second = controller.dispatch_execution(cap_b, ctx_b)

            # Different task_id → no conflict
            assert second.lease_status != LeaseStatus.CONFLICT.value

    def test_release_then_redispatch_succeeds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)

            cap1 = _make_capability(execution_id="exec-1")
            ctx1 = _make_context(execution_id="exec-1")

            first = controller.dispatch_execution(cap1, ctx1)

            # Manually release the lease
            lease = DispatchLease.lookup("T-0001", "developer")
            if lease is not None:
                lease.release()

            # Now re-dispatch should succeed (no conflict)
            cap2 = _make_capability(execution_id="exec-2")
            ctx2 = _make_context(execution_id="exec-2")

            second = controller.dispatch_execution(cap2, ctx2)
            assert second.lease_status != LeaseStatus.CONFLICT.value


# ============================================================================
# Test: Runtime projection file created on successful dispatch
# ============================================================================


class TestRuntimeProjectionOnSuccess:
    """When dispatch passes (mock adapter), a projection.json must be written."""

    def test_projection_file_created_with_mock_pass_adapter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)

            capability = _make_capability(task_id="T-PROJ", execution_id="exec-proj")
            context = _make_context(task_id="T-PROJ", execution_id="exec-proj")

            adapter = MockPassAdapter()
            snapshot = controller.dispatch_execution(
                capability, context, agent_adapter=adapter,
                gate_id="G-PROJ",
            )

            # Dispatch should have PASS lease_status
            assert snapshot.lease_status == LeaseStatus.ACTIVE.value
            assert snapshot.child_session is not None
            assert snapshot.child_session.startswith("child-")

            # Projection file must exist
            assert controller.projection_path.exists()

    def test_projection_contains_required_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)

            capability = _make_capability(task_id="T-PROJ", execution_id="exec-proj")
            context = _make_context(task_id="T-PROJ", execution_id="exec-proj")

            adapter = MockPassAdapter()
            controller.dispatch_execution(
                capability, context, agent_adapter=adapter,
                gate_id="G-PROJ",
            )

            # Read and validate projection
            projection = json.loads(controller.projection_path.read_text(encoding="utf-8"))

            # Required fields
            assert projection["execution_id"] == "exec-proj"
            assert projection["task_id"] == "T-PROJ"
            assert projection["gate_id"] == "G-PROJ"
            assert projection["child_session"].startswith("child-")
            assert projection["actor"] == "dev-agent"
            assert projection["state"] == "ROLE_EXECUTION"
            assert "timestamp" in projection
            assert isinstance(projection["timestamp"], (int, float))

    def test_projection_fields_match_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)

            capability = _make_capability(execution_id="exec-match")
            context = _make_context(execution_id="exec-match",
                                     actor_id="custom-actor")

            adapter = MockPassAdapter()
            snapshot = controller.dispatch_execution(
                capability, context, agent_adapter=adapter,
                gate_id="G-MATCH",
            )

            projection = json.loads(controller.projection_path.read_text(encoding="utf-8"))

            # Cross-verify projection with snapshot
            assert projection["child_session"] == snapshot.child_session
            assert projection["actor"] == snapshot.actor
            assert projection["execution_id"] == snapshot.execution_id
            assert projection["task_id"] == snapshot.task_id

    def test_projection_only_written_on_pass_not_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)

            capability = _make_capability()
            context = _make_context()

            # Dispatch with blocked adapter
            adapter = MockBlockedAdapter()
            controller.dispatch_execution(
                capability, context, agent_adapter=adapter,
            )

            # Projection must NOT exist for BLOCKED receipt
            assert not controller.projection_path.exists()

    def test_projection_atomic_write(self):
        """The projection must be readable after write (atomic JSON write)."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)

            capability = _make_capability()
            context = _make_context()

            adapter = MockPassAdapter()
            controller.dispatch_execution(
                capability, context, agent_adapter=adapter,
                gate_id="G-ATOMIC",
            )

            # File must exist and be valid JSON
            assert controller.projection_path.exists()
            data = json.loads(controller.projection_path.read_text(encoding="utf-8"))
            assert isinstance(data, dict)
            assert len(data) >= 7


# ============================================================================
# Test: Runtime projection validation (required fields)
# ============================================================================


class TestRuntimeProjectionValidation:
    """Detailed validation of the projection file shape and contents."""

    REQUIRED_FIELDS = {
        "execution_id",
        "task_id",
        "gate_id",
        "child_session",
        "actor",
        "state",
        "timestamp",
    }

    def test_all_required_fields_present(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)

            capability = _make_capability()
            context = _make_context()

            adapter = MockPassAdapter()
            controller.dispatch_execution(
                capability, context, agent_adapter=adapter,
                gate_id="G-FIELDS",
            )

            projection = json.loads(controller.projection_path.read_text(encoding="utf-8"))

            for field in self.REQUIRED_FIELDS:
                assert field in projection, f"Missing required field: {field}"
                assert projection[field] is not None or field == "gate_id", \
                    f"Field {field} should not be None"

    def test_state_is_always_role_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)

            capability = _make_capability()
            context = _make_context()

            adapter = MockPassAdapter()
            controller.dispatch_execution(
                capability, context, agent_adapter=adapter,
                gate_id="G-STATE",
            )

            projection = json.loads(controller.projection_path.read_text(encoding="utf-8"))
            assert projection["state"] == "ROLE_EXECUTION"

    def test_child_session_is_non_empty_string(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)

            capability = _make_capability()
            context = _make_context()

            adapter = MockPassAdapter()
            controller.dispatch_execution(
                capability, context, agent_adapter=adapter,
                gate_id="G-CS",
            )

            projection = json.loads(controller.projection_path.read_text(encoding="utf-8"))
            assert isinstance(projection["child_session"], str)
            assert len(projection["child_session"]) > 0
            assert projection["child_session"].startswith("child-")

    def test_timestamp_is_recent(self):
        import time

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)

            before = time.time()

            capability = _make_capability()
            context = _make_context()

            adapter = MockPassAdapter()
            controller.dispatch_execution(
                capability, context, agent_adapter=adapter,
                gate_id="G-TS",
            )

            after = time.time()

            projection = json.loads(controller.projection_path.read_text(encoding="utf-8"))
            ts = projection["timestamp"]
            assert before <= ts <= after + 0.5, \
                f"timestamp {ts} not in [{before}, {after + 0.5}]"

    def test_gate_id_can_be_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)

            capability = _make_capability()
            context = _make_context()

            adapter = MockPassAdapter()
            # No gate_id passed, and snapshot has no gate_id
            controller.dispatch_execution(
                capability, context, agent_adapter=adapter,
            )

            projection = json.loads(controller.projection_path.read_text(encoding="utf-8"))
            assert projection["gate_id"] == "" or projection["gate_id"] is not None


# ============================================================================
# Test: Backward compatibility
# ============================================================================


class TestBackwardCompatibility:
    """Existing RuntimeController methods must still work unchanged."""

    def test_onboard_still_works(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = RuntimeController(root)
            snapshot = controller.onboard_project("backward compat test")
            assert snapshot.runtime_state == RuntimeState.NO_ACTIVE_TASK.value
            # New fields should default to None for backward compat
            assert snapshot.child_session is None
            assert snapshot.actor is None
            assert snapshot.lease_status is None

    def test_proposal_still_works(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)
            snapshot = controller.create_work_package_proposal(
                "T-BC", "G-BC", "backward compat proposal", ["src/"]
            )
            assert snapshot.runtime_state == RuntimeState.USER_APPROVAL_REQUIRED.value
            assert snapshot.child_session is None
            assert snapshot.lease_status is None

    def test_approve_and_execute_still_works(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)
            controller.create_work_package_proposal(
                "T-BC2", "G-BC2", "backward compat", ["src/"]
            )
            snapshot = controller.approve_and_execute("G-BC2", approval="approved")
            assert snapshot.runtime_state == RuntimeState.DEVELOPER_EXECUTION.value
            # approve_and_execute doesn't populate new dispatch fields
            assert snapshot.child_session is None
            assert snapshot.lease_status is None

    def test_authorize_write_still_works(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)
            controller.create_work_package_proposal(
                "T-BC3", "G-BC3", "backward compat", ["src/"]
            )
            snapshot = controller.approve_and_execute("G-BC3", approval="approved")
            developer = ExecutionContext(
                "developer:T-BC3", "developer", "agent",
                "T-BC3", snapshot.execution_id,
                capability_id=snapshot.capability_id,
            )
            allowed, reason = controller.authorize_write(developer, "src/app.py")
            assert allowed is True
            assert reason == "AUTHORIZED"

    def test_inspect_still_works(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)
            state = controller.inspect()
            assert state == RuntimeState.NO_ACTIVE_TASK

    def test_checkpoint_still_works(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_onboarded_controller(root)
            path = controller.checkpoint("next step", summary="test")
            assert path.exists()
            assert path.name == "checkpoint.json"
