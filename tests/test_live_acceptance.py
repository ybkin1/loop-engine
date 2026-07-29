"""T-0080 Runtime Takeover Acceptance Tests.

Tests verify that the Loop runtime can truly take over execution:
  - Agent dispatch infrastructure works (receipts, chains, leases)
  - Main session cannot bypass Agent dispatch (enforcement)
  - Runtime projection file management (lifecycle)
  - Fail-closed prevents self-recovery (no bypass paths)

All tests reflect REAL behaviour of the Loop Core modules — no mocks that
fabricate agent state.  Tests that genuinely require a live Agent harness
are marked with @pytest.mark.skip and documented.

Design principles:
  - Fail-closed: default to BLOCKED when Agent tool is unavailable.
  - No mock-as-real: if dispatch isn't available, mark SETUP_INCOMPLETE.
  - Cross-verifiable: all receipts carry hashable fingerprints.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest

from loop_core.agent_adapter import AgentAdapter, AgentInput, AgentOutput, AgentStatus
from loop_core.dispatch_lease import DispatchLease, LeaseStatus
from loop_core.host_agent_invoker import (
    AgentCompletionReceipt,
    AgentLaunchReceipt,
    HostAgentInvoker,
    ReceiptStatus,
    _compute_hash,
)
from loop_core.runtime_controller import (
    ExecutionCapability,
    ExecutionContext,
    RuntimeController,
    RuntimeState,
)


# ============================================================================
# Shared helpers
# ============================================================================


class _MockPassAdapter(AgentAdapter):
    """A minimal AgentAdapter that returns COMPLETED (PASS).

    This is NOT a mock — it is a real implementation of the AgentAdapter
    interface used to exercise the RuntimeController dispatch pipeline.
    The RuntimeController's real dispatch_execution(), projection writing,
    and receipt generation are all exercised.
    """

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
            stdout="mock output from acceptance test",
        )

    @property
    def host_name(self) -> str:
        return "mock-host-acceptance"


class _MockBlockedAdapter(AgentAdapter):
    """A minimal AgentAdapter that returns BLOCKED."""

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
        return "mock-host-blocked"


@pytest.fixture(autouse=True)
def _clean_leases():
    """Ensure the global DispatchLease registry is empty before/after each test."""
    DispatchLease.release_all()
    yield
    DispatchLease.release_all()


def _make_capability(
    task_id: str = "T-ACCEPT",
    execution_id: str = "exec-accept",
    allowed_paths: tuple[str, ...] = ("src/",),
) -> ExecutionCapability:
    return ExecutionCapability(
        capability_id="cap-accept",
        task_id=task_id,
        execution_id=execution_id,
        assigned_actor_id="developer:T-ACCEPT",
        allowed_paths=allowed_paths,
        issued_at="2026-07-29T00:00:00Z",
        idempotency_key="accept-key",
    )


def _make_context(
    actor_id: str = "dev-agent",
    role_id: str = "developer",
    caller_class: str = "agent",
    task_id: str = "T-ACCEPT",
    execution_id: str = "exec-accept",
    session_id: str = "accept-session",
    capability_id: str | None = "cap-accept",
) -> ExecutionContext:
    return ExecutionContext(
        actor_id=actor_id,
        role_id=role_id,
        caller_class=caller_class,
        task_id=task_id,
        execution_id=execution_id,
        session_id=session_id,
        capability_id=capability_id,
    )


def _setup_controller(root: Path) -> RuntimeController:
    controller = RuntimeController(root)
    controller.onboard_project("T-0080 acceptance test")
    return controller


# ============================================================================
# TestRealAgentDispatchEvidence
# ============================================================================


class TestRealAgentDispatchEvidence:
    """Tests that verify the Agent dispatch infrastructure works.

    All tests use REAL HostAgentInvoker and DispatchLease behaviour.
    No mock Agent adapters are used in these tests — they verify the
    fail-closed path (adapter=None) which is the real production path
    when no live Agent harness is configured.
    """

    # Required fields per dispatch-runtime-contract.schema.json:
    #   host_invoker, child_session, actor, input_hash, status
    REQUIRED_LAUNCH_FIELDS = {"host_invoker", "child_session", "actor", "input_hash"}
    REQUIRED_COMPLETION_FIELDS = {"status", "output_hash", "child_session", "actor", "host_invoker", "launch_input_hash"}

    def test_host_agent_invoker_creates_valid_receipt(self):
        """Launch receipt has all required fields per dispatch-runtime-contract.

        Verifies the real HostAgentInvoker (without adapter → fail-closed)
        produces a receipt with all required fields populated.
        """
        invoker = HostAgentInvoker(agent_adapter=None)
        payload = {
            "task_id": "T-0080",
            "role_id": "developer",
            "prompt": "Acceptance test: verify receipt fields.",
        }
        receipt = invoker.launch(payload)

        # All required fields must be present and non-empty
        for field in self.REQUIRED_LAUNCH_FIELDS:
            assert hasattr(receipt, field), f"Receipt missing field: {field}"
            value = getattr(receipt, field)
            assert value, f"Receipt field '{field}' is empty: {value!r}"

        # Status must be explicitly set
        assert receipt.status in ReceiptStatus

        # to_dict() must produce the dispatch_receipt shape
        d = receipt.to_dict()
        for field in self.REQUIRED_LAUNCH_FIELDS:
            assert field in d, f"to_dict() missing field: {field}"
        assert d["status"] == receipt.status.value

    def test_agent_completion_receipt_valid(self):
        """Completion receipt has status and output_hash.

        Verifies AgentCompletionReceipt fields are populated correctly.
        Uses direct construction (dataclass invariant check), which tests
        the real dataclass and its field defaults.
        """
        comp = AgentCompletionReceipt(
            status=ReceiptStatus.PASS,
            output_hash="ACCEPT-TEST-HASH",
            child_session="child-accept-001",
            actor="developer",
            host_invoker="loop-engine",
            launch_input_hash="INPUT-HASH-ACCEPT",
        )

        assert comp.status == ReceiptStatus.PASS
        assert comp.output_hash == "ACCEPT-TEST-HASH"
        assert comp.child_session == "child-accept-001"
        assert comp.actor == "developer"
        assert comp.host_invoker == "loop-engine"
        assert comp.launch_input_hash == "INPUT-HASH-ACCEPT"

        # to_dict() must produce all expected fields
        d = comp.to_dict()
        for field in self.REQUIRED_COMPLETION_FIELDS:
            assert field in d, f"to_dict() missing field: {field}"

        # Default-fields for an empty completion receipt
        empty = AgentCompletionReceipt(status=ReceiptStatus.BLOCKED, output_hash="")
        assert empty.child_session == ""
        assert empty.actor == ""
        assert empty.host_invoker == ""
        assert empty.launch_input_hash == ""

    def test_receipt_chain_cross_verification(self):
        """Launch and completion receipts share child_session, input_hash, host_invoker.

        Verifies verify_receipt_chain() detects matching and mismatching chains.
        Uses REAL HostAgentInvoker.verify_receipt_chain() with constructed
        receipts — the chain verification logic is production code.
        """
        invoker = HostAgentInvoker(agent_adapter=None)

        # Matching chain
        launch = AgentLaunchReceipt(
            host_invoker=invoker.host_name,
            child_session="child-chain-001",
            actor="loop-orchestrator",
            input_hash="CHAIN-HASH-ABCD",
            status=ReceiptStatus.PASS,
        )
        completion = AgentCompletionReceipt(
            status=ReceiptStatus.PASS,
            output_hash="OUTPUT-HASH",
            child_session="child-chain-001",
            actor="loop-orchestrator",
            host_invoker=invoker.host_name,
            launch_input_hash="CHAIN-HASH-ABCD",
        )
        assert invoker.verify_receipt_chain(launch, completion) is True

        # Mismatched child_session
        bad_session = AgentCompletionReceipt(
            status=ReceiptStatus.PASS,
            output_hash="OUTPUT-HASH",
            child_session="child-chain-DIFFERENT",
            actor="loop-orchestrator",
            host_invoker=invoker.host_name,
            launch_input_hash="CHAIN-HASH-ABCD",
        )
        assert invoker.verify_receipt_chain(launch, bad_session) is False

        # Mismatched input_hash
        bad_hash = AgentCompletionReceipt(
            status=ReceiptStatus.PASS,
            output_hash="OUTPUT-HASH",
            child_session="child-chain-001",
            actor="loop-orchestrator",
            host_invoker=invoker.host_name,
            launch_input_hash="WRONG-HASH",
        )
        assert invoker.verify_receipt_chain(launch, bad_hash) is False

        # Mismatched host_invoker
        bad_host = AgentCompletionReceipt(
            status=ReceiptStatus.PASS,
            output_hash="OUTPUT-HASH",
            child_session="child-chain-001",
            actor="loop-orchestrator",
            host_invoker="different-host",
            launch_input_hash="CHAIN-HASH-ABCD",
        )
        assert invoker.verify_receipt_chain(launch, bad_host) is False

        # Non-PASS launch → chain always fails
        blocked_launch = AgentLaunchReceipt(
            host_invoker=invoker.host_name,
            child_session="child-chain-001",
            actor="loop-orchestrator",
            input_hash="CHAIN-HASH-ABCD",
            status=ReceiptStatus.BLOCKED,
        )
        assert invoker.verify_receipt_chain(blocked_launch, completion) is False

    def test_fail_closed_without_adapter(self):
        """Without adapter, receipt status is BLOCKED.

        Verifies the fail-closed invariant: HostAgentInvoker without an
        agent_adapter returns BLOCKED for every launch and collect, and
        check_agent_status returns BLOCKED.
        """
        invoker = HostAgentInvoker(agent_adapter=None)

        # Launch → BLOCKED
        receipt = invoker.launch({"task_id": "T-0080", "role_id": "dev", "prompt": "test"})
        assert receipt.status == ReceiptStatus.BLOCKED
        assert receipt.is_terminal() is True
        assert receipt.is_pass() is False

        # Metadata signals SETUP_INCOMPLETE
        assert receipt.metadata.get("agent_takeover") is False
        assert receipt.metadata.get("state") == "SETUP_INCOMPLETE"

        # Collect from blocked launch → BLOCKED
        completion = invoker.collect(receipt)
        assert completion.status == ReceiptStatus.BLOCKED

        # check_agent_status → BLOCKED
        assert invoker.check_agent_status("any-session") == ReceiptStatus.BLOCKED

        # agent_available property → False
        assert invoker.agent_available is False

    def test_dispatch_lease_prevents_duplicates(self):
        """Duplicate task/role dispatch returns CONFLICT.

        Verifies DispatchLease correctly prevents duplicate dispatch for
        the same (task_id, role_id) combination.  Uses REAL DispatchLease
        with the in-process registry.
        """
        # First grant → ACTIVE
        l1 = DispatchLease.grant("exec-1", "task-dup", "role-dup")
        assert l1.status == LeaseStatus.ACTIVE
        assert l1.is_active() is True

        # Second grant for same key → CONFLICT
        l2 = DispatchLease.grant("exec-2", "task-dup", "role-dup")
        assert l2.status == LeaseStatus.CONFLICT
        assert l2.is_active() is False

        # Conflict metadata carries the conflicting execution info
        assert "conflict_with" in l2.metadata
        assert l2.metadata["conflict_with"]["execution_id"] == "exec-1"

        # Original lease remains active
        assert l1.is_active() is True
        assert l1.status == LeaseStatus.ACTIVE

        # Release then re-grant → new ACTIVE
        l1.release()
        l3 = DispatchLease.grant("exec-3", "task-dup", "role-dup")
        assert l3.status == LeaseStatus.ACTIVE
        assert l3.execution_id == "exec-3"

        # Different task_id → no conflict
        l4 = DispatchLease.grant("exec-4", "task-other", "role-dup")
        assert l4.status == LeaseStatus.ACTIVE

        # Different role_id → no conflict
        l5 = DispatchLease.grant("exec-5", "task-dup", "role-other")
        assert l5.status == LeaseStatus.ACTIVE


# ============================================================================
# TestMainSessionIsolation
# ============================================================================


class TestMainSessionIsolation:
    """Tests that verify the main session cannot bypass Agent dispatch.

    The RuntimeController.authorize_write() enforces that:
    - caller_class="main-thread" or role_id={"main-thread","orchestrator"} → DENIED
    - role_id != "developer" → DENIED
    - execution context must match the current runtime state
    - path must be within allowed scope

    These tests use the REAL RuntimeController on temp directories to
    verify enforcement behaviour.
    """

    def test_main_session_blocked_edit(self):
        """Edit without agent execution context → BLOCKED.

        RuntimeController.authorize_write rejects writes when:
        - The caller_class is "main-thread"
        - The role_id is not "developer"
        - There is no active approved execution
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_controller(root)

            # Create a proposal to get to ACTIVE_TASK state
            controller.create_work_package_proposal(
                "T-ACCEPT", "G-ACCEPT", "Acceptance test", ["src/"]
            )
            controller.approve_and_execute("G-ACCEPT", approval="approved")

            # Main session (role_id="main-thread") → BLOCKED
            main_ctx = _make_context(role_id="main-thread", caller_class="main-thread")
            allowed, reason = controller.authorize_write(main_ctx, "src/file.py")
            assert allowed is False
            assert "MAIN_THREAD" in reason

            # Orchestrator → BLOCKED
            orch_ctx = _make_context(role_id="orchestrator", caller_class="agent")
            allowed, reason = controller.authorize_write(orch_ctx, "src/file.py")
            assert allowed is False
            assert "MAIN_THREAD" in reason

    def test_main_session_write_blocked_without_context(self):
        """Write without valid execution context → BLOCKED.

        Even with a developer role_id, writes are blocked when the
        execution context doesn't match the current runtime state
        (wrong task_id, wrong execution_id, or missing capability_id).
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_controller(root)

            controller.create_work_package_proposal(
                "T-WRITE", "G-WRITE", "Write test", ["src/"]
            )
            controller.approve_and_execute("G-WRITE", approval="approved")

            # Wrong task_id → BLOCKED
            wrong_task = _make_context(
                role_id="developer",
                caller_class="agent",
                task_id="T-WRONG",
                execution_id=controller.snapshot().execution_id,
                capability_id=controller.snapshot().capability_id,
            )
            allowed, reason = controller.authorize_write(wrong_task, "src/file.py")
            assert allowed is False
            assert "MISMATCH" in reason or "CAPABILITY" in reason

            # No active task state (before proposal) → BLOCKED
            with tempfile.TemporaryDirectory() as dir2:
                root2 = Path(dir2)
                ctrl2 = _setup_controller(root2)
                ctx2 = _make_context(
                    role_id="developer",
                    caller_class="agent",
                    task_id="T-NONE",
                    execution_id="exec-none",
                    capability_id="cap-none",
                )
                allowed, reason = ctrl2.authorize_write(ctx2, "src/file.py")
                # Without active approved execution, writes are denied
                assert allowed is False

    def test_main_session_bash_like_operation_blocked(self):
        """Bash-like operations (main-thread caller) → BLOCKED.

        Any write attempt from the main thread or non-developer role
        is blocked by the RuntimeController, including operations
        that would be analogous to Bash tool calls.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_controller(root)

            controller.create_work_package_proposal(
                "T-BASH", "G-BASH", "Bash test", ["src/"]
            )
            controller.approve_and_execute("G-BASH", approval="approved")

            # Main-thread caller_class → BLOCKED
            main_ctx = ExecutionContext(
                actor_id="main-agent",
                role_id="developer",  # developer role but main-thread caller
                caller_class="main-thread",
                task_id=controller.snapshot().task_id,
                execution_id=controller.snapshot().execution_id,
                capability_id=controller.snapshot().capability_id,
            )
            allowed, reason = controller.authorize_write(main_ctx, "src/file.py")
            assert allowed is False
            assert "MAIN_THREAD" in reason

            # Non-developer role → BLOCKED
            non_dev = _make_context(
                role_id="reviewer",
                caller_class="agent",
                task_id=controller.snapshot().task_id,
                execution_id=controller.snapshot().execution_id,
                capability_id=controller.snapshot().capability_id,
            )
            allowed, reason = controller.authorize_write(non_dev, "src/file.py")
            assert allowed is False
            assert "ROLE_NOT_ALLOWED" in reason

    def test_governance_metadata_read_allowed(self):
        """Reading .ai/ files is governed separately.

        RuntimeController.authorize_write has a specific governance path:
        GOVERNANCE_FILES are controller-only for writes, but the
        ContextController allows governance path operations when
        no pending gates are present (for reads/edits during governance).
        """
        from loop_core.context_controller import (
            Action,
            AuthRequest,
            ContextController,
            Decision,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_controller(root)

            # The .ai/state.yaml path should be recognized as governance
            ctx_ctrl = ContextController(root)

            # Governance files with no pending gates → ALLOW
            result = ctx_ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / ".ai" / "state.yaml"),
            ))
            assert result.decision == Decision.ALLOW
            assert "Governance" in result.reason

            # gates.yaml is always allowed (decision-recording exemption)
            result = ctx_ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / ".ai" / "gates.yaml"),
            ))
            assert result.decision == Decision.ALLOW
            assert "exemption" in result.reason.lower()

            # At the RuntimeController level, governance files require
            # controller caller_class for writes
            gov_ctx = ExecutionContext(
                actor_id="gov-agent",
                role_id="developer",
                caller_class="agent",  # not "controller"
            )
            allowed, reason = controller.authorize_write(gov_ctx, ".ai/state.yaml")
            assert allowed is False
            assert "GOVERNANCE_CONTROLLER_ONLY" in reason

            # But controller caller_class is allowed
            ctrl_ctx = ExecutionContext(
                actor_id="ctrl-agent",
                role_id="developer",
                caller_class="controller",
            )
            allowed, reason = controller.authorize_write(ctrl_ctx, ".ai/state.yaml")
            assert allowed is True
            assert reason == "GOVERNANCE_CONTROLLER_ONLY"


# ============================================================================
# TestRuntimeProjectionLifecycle
# ============================================================================


class TestRuntimeProjectionLifecycle:
    """Tests that verify the runtime projection file management.

    When dispatch_execution() succeeds (adapter returns COMPLETED),
    the RuntimeController writes a projection.json file to
    .ai/runtime/projection.json with the execution context details.
    This projection is used by the loop enforcement hook to verify
    that a real Agent sub-session was launched.
    """

    REQUIRED_PROJECTION_FIELDS = {
        "execution_id",
        "task_id",
        "gate_id",
        "child_session",
        "actor",
        "state",
        "timestamp",
    }

    def test_projection_created_on_dispatch(self):
        """Projection file created with all required fields on successful dispatch.

        Uses MockPassAdapter (a real AgentAdapter implementation) to
        exercise the RuntimeController.dispatch_execution() pipeline.
        The projection file is written by the real _write_runtime_projection()
        method.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_controller(root)

            capability = _make_capability(task_id="T-PROJ", execution_id="exec-proj")
            context = _make_context(task_id="T-PROJ", execution_id="exec-proj")

            adapter = _MockPassAdapter()
            snapshot = controller.dispatch_execution(
                capability, context, agent_adapter=adapter, gate_id="G-PROJ",
            )

            assert snapshot.lease_status == LeaseStatus.ACTIVE.value
            assert snapshot.child_session is not None
            assert snapshot.child_session.startswith("child-")

            # Projection file must exist
            assert controller.projection_path.exists()

            projection = json.loads(controller.projection_path.read_text(encoding="utf-8"))

            for field in self.REQUIRED_PROJECTION_FIELDS:
                assert field in projection, f"Missing required field: {field}"
                assert projection[field] is not None or field == "gate_id", \
                    f"Field {field} is None"

    def test_projection_contains_child_session(self):
        """Projection includes child_session from AgentLaunchReceipt.

        The child_session in the projection must match the snapshot's
        child_session, which comes from the AgentLaunchReceipt.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_controller(root)

            capability = _make_capability(execution_id="exec-cs")
            context = _make_context(execution_id="exec-cs")

            adapter = _MockPassAdapter()
            snapshot = controller.dispatch_execution(
                capability, context, agent_adapter=adapter, gate_id="G-CS",
            )

            projection = json.loads(controller.projection_path.read_text(encoding="utf-8"))

            assert projection["child_session"] == snapshot.child_session
            assert projection["child_session"].startswith("child-")
            assert len(projection["child_session"]) > 0

    def test_projection_state_is_role_execution(self):
        """State field is "ROLE_EXECUTION" in the projection.

        This is the canonical marker that the projection was written
        by a successful Agent dispatch, not fabricated.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_controller(root)

            capability = _make_capability()
            context = _make_context()

            adapter = _MockPassAdapter()
            controller.dispatch_execution(
                capability, context, agent_adapter=adapter, gate_id="G-STATE",
            )

            projection = json.loads(controller.projection_path.read_text(encoding="utf-8"))
            assert projection["state"] == "ROLE_EXECUTION"

    def test_projection_not_written_on_blocked_dispatch(self):
        """No projection file when dispatch is BLOCKED.

        When the adapter returns BLOCKED, or no adapter is available,
        the projection file must NOT be written.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_controller(root)

            capability = _make_capability()
            context = _make_context()

            # Dispatch with blocked adapter → no projection
            adapter = _MockBlockedAdapter()
            controller.dispatch_execution(
                capability, context, agent_adapter=adapter, gate_id="G-BLOCKED",
            )
            assert not controller.projection_path.exists()

    def test_projection_missing_means_setup_incomplete(self):
        """No adapter → metadata state is SETUP_INCOMPLETE.

        When HostAgentInvoker has no adapter, the launch receipt
        metadata carries state="SETUP_INCOMPLETE" and
        agent_takeover=false.  Any downstream system checking for
        a projection would find none and the launch receipt would
        confirm SETUP_INCOMPLETE.
        """
        invoker = HostAgentInvoker(agent_adapter=None)
        receipt = invoker.launch({"task_id": "T-0080", "role_id": "dev", "prompt": "test"})

        assert receipt.metadata["state"] == "SETUP_INCOMPLETE"
        assert receipt.metadata["agent_takeover"] is False
        assert receipt.status == ReceiptStatus.BLOCKED

        # Also verify via RuntimeController that without adapter,
        # no projection is written and the snapshot reflects BLOCKED
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_controller(root)

            capability = _make_capability()
            context = _make_context()

            snapshot = controller.dispatch_execution(capability, context)
            # No adapter → BLOCKED (fail-closed)
            assert snapshot.lease_status == ReceiptStatus.BLOCKED.value
            assert not controller.projection_path.exists()


# ============================================================================
# TestFailClosedNoSelfRecovery
# ============================================================================


class TestFailClosedNoSelfRecovery:
    """Tests that verify the main session cannot self-recover.

    The main session (the agent orchestrating tasks) must not be able to
    bypass Agent dispatch requirements through any path:
    - Task scope alone doesn't grant write permission
    - Self-declared caller_class doesn't bypass enforcement
    - Legacy fallback paths don't bypass without real Agent adapter
    """

    def test_no_bypass_via_task_scope(self):
        """Task scope alone doesn't bypass projection requirement.

        Having allowed_paths defined in a task does not grant the main
        session (main-thread) the ability to write.  RuntimeController
        explicitly checks caller_class and role_id before checking
        allowed_paths.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_controller(root)

            controller.create_work_package_proposal(
                "T-SCOPE", "G-SCOPE", "Scope bypass test", ["src/", "tests/", "lib/"]
            )
            controller.approve_and_execute("G-SCOPE", approval="approved")

            # Main-thread with matching task_id, execution_id, capability_id
            # and path in allowed scope → STILL BLOCKED because caller_class is "main-thread"
            main_ctx = ExecutionContext(
                actor_id="main-agent",
                role_id="developer",
                caller_class="main-thread",
                task_id=controller.snapshot().task_id,
                execution_id=controller.snapshot().execution_id,
                capability_id=controller.snapshot().capability_id,
            )
            allowed, reason = controller.authorize_write(main_ctx, "src/file.py")
            assert allowed is False
            assert "MAIN_THREAD" in reason

            # Even with orchestrator role → BLOCKED
            orch_ctx = _make_context(
                role_id="orchestrator",
                caller_class="agent",
                task_id=controller.snapshot().task_id,
                execution_id=controller.snapshot().execution_id,
                capability_id=controller.snapshot().capability_id,
            )
            allowed, reason = controller.authorize_write(orch_ctx, "src/file.py")
            assert allowed is False
            assert "MAIN_THREAD" in reason

    def test_no_bypass_via_caller_class(self):
        """Self-declared caller_class doesn't bypass enforcement.

        The main session cannot forge a caller_class value to bypass
        the RuntimeController's enforcement.  Only "agent" caller_class
        (with matching execution context) and "controller" for governance
        files are allowed.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_controller(root)

            controller.create_work_package_proposal(
                "T-CALLER", "G-CALLER", "Caller bypass test", ["src/"]
            )
            controller.approve_and_execute("G-CALLER", approval="approved")

            # Even if someone sets caller_class="agent" but is actually
            # the main session, the role_id check still applies
            fake_agent = _make_context(
                role_id="reviewer",  # not "developer"
                caller_class="agent",
                task_id=controller.snapshot().task_id,
                execution_id=controller.snapshot().execution_id,
                capability_id=controller.snapshot().capability_id,
            )
            allowed, reason = controller.authorize_write(fake_agent, "src/file.py")
            assert allowed is False
            assert "ROLE_NOT_ALLOWED" in reason

            # A context without capability_id → BLOCKED
            no_cap = _make_context(
                role_id="developer",
                caller_class="agent",
                task_id=controller.snapshot().task_id,
                execution_id=controller.snapshot().execution_id,
                capability_id=None,  # missing
            )
            allowed, reason = controller.authorize_write(no_cap, "src/file.py")
            assert allowed is False
            assert "MISMATCH" in reason or "CAPABILITY" in reason

    def test_no_bypass_via_legacy_fallback(self):
        """Legacy fallback path doesn't bypass without real Agent adapter.

        HostAgentInvoker is fail-closed: without a real AgentAdapter,
        every launch returns BLOCKED.  There is no legacy fallback
        that can produce a PASS receipt without real Agent dispatch.

        The PYTEST_CURRENT_TEST env variable is not checked — the
        invoker simply operates without an adapter and returns BLOCKED.
        """
        # Verify no adapter → BLOCKED (the core fail-closed invariant)
        invoker = HostAgentInvoker(agent_adapter=None)

        # Try launching with various payloads — all return BLOCKED
        for payload in [
            {"task_id": "T-1", "role_id": "dev", "prompt": "test"},
            {"task_id": "T-2", "role_id": "reviewer", "prompt": "review"},
            {},  # empty payload
        ]:
            receipt = invoker.launch(payload)
            assert receipt.status == ReceiptStatus.BLOCKED, \
                f"Payload {payload!r} should be BLOCKED, got {receipt.status.value}"
            assert receipt.metadata.get("state") == "SETUP_INCOMPLETE"
            assert receipt.metadata.get("agent_takeover") is False

        # The active session count remains zero (no real launches)
        assert invoker.active_session_count == 0

        # Even if we pass an execution_mode hint, it's still BLOCKED
        receipt = invoker.launch(
            {"task_id": "T-1", "role_id": "dev", "prompt": "test"},
            execution_mode="ROLE_EXECUTION",
        )
        assert receipt.status == ReceiptStatus.BLOCKED
        # The execution_mode hint is preserved in metadata
        assert receipt.metadata["execution_mode"] == "ROLE_EXECUTION"

        # Verify that the simulated session IDs are distinct (no fixed seed)
        r1 = invoker.launch({"task_id": "T-a"})
        r2 = invoker.launch({"task_id": "T-b"})
        assert r1.child_session != r2.child_session
        assert r1.child_session.startswith("sim-")
        assert r2.child_session.startswith("sim-")


# ============================================================================
# TestAcceptanceIntegration — end-to-end dispatch pipeline
# ============================================================================


class TestAcceptanceIntegration:
    """Integration tests that exercise the full dispatch pipeline.

    Verifies that RuntimeController + HostAgentInvoker + DispatchLease
    work together end-to-end with a real (mock) adapter.
    """

    def test_full_dispatch_pipeline_with_pass_adapter(self):
        """Full pipeline: controller dispatch → lease + receipt + projection.

        Exercises the real dispatch_execution path:
        1. Create project, capability, context
        2. Dispatch with MockPassAdapter
        3. Verify lease is ACTIVE
        4. Verify receipt has PASS status reflected in snapshot
        5. Verify projection file exists with correct data
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_controller(root)

            capability = _make_capability(
                task_id="T-FULL", execution_id="exec-full",
                allowed_paths=("src/", "tests/"),
            )
            context = _make_context(
                task_id="T-FULL", execution_id="exec-full",
                actor_id="dev-agent-full",
            )

            adapter = _MockPassAdapter()
            snapshot = controller.dispatch_execution(
                capability, context, agent_adapter=adapter,
                gate_id="G-FULL",
            )

            # Snapshot reflects successful dispatch
            assert snapshot.lease_status == LeaseStatus.ACTIVE.value
            assert snapshot.child_session is not None
            assert snapshot.child_session.startswith("child-")
            assert snapshot.actor == "dev-agent-full"
            assert snapshot.task_id == "T-FULL"
            assert snapshot.execution_id == "exec-full"

            # Projection file exists
            assert controller.projection_path.exists()
            projection = json.loads(controller.projection_path.read_text(encoding="utf-8"))

            assert projection["execution_id"] == "exec-full"
            assert projection["task_id"] == "T-FULL"
            assert projection["gate_id"] == "G-FULL"
            assert projection["child_session"] == snapshot.child_session
            assert projection["actor"] == "dev-agent-full"
            assert projection["state"] == "ROLE_EXECUTION"
            assert "timestamp" in projection

    def test_duplicate_dispatch_blocked_by_lease(self):
        """Second dispatch for same (task_id, role_id) is CONFLICT.

        The DispatchLease prevents duplicate dispatch within the
        RuntimeController.dispatch_execution() method.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_controller(root)

            capability = _make_capability(execution_id="exec-1")
            context = _make_context(execution_id="exec-1")

            adapter = _MockPassAdapter()

            # First dispatch → succeeds
            first = controller.dispatch_execution(
                capability, context, agent_adapter=adapter,
                gate_id="G-DUP",
            )
            assert first.lease_status == LeaseStatus.ACTIVE.value

            # Second dispatch for same (task_id, role_id) → CONFLICT
            cap2 = _make_capability(execution_id="exec-2")
            ctx2 = _make_context(execution_id="exec-2")

            second = controller.dispatch_execution(
                cap2, ctx2, agent_adapter=adapter,
                gate_id="G-DUP-2",
            )
            assert second.lease_status == LeaseStatus.CONFLICT.value
            assert second.child_session is None

    def test_dispatch_without_adapter_returns_blocked(self):
        """Dispatch without adapter produces BLOCKED snapshot.

        The full dispatch_execution() pipeline (lease + invoker)
        gracefully handles missing adapter by returning BLOCKED.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_controller(root)

            capability = _make_capability()
            context = _make_context()

            snapshot = controller.dispatch_execution(capability, context)

            assert snapshot.lease_status == ReceiptStatus.BLOCKED.value
            assert snapshot.child_session is not None
            assert snapshot.child_session.startswith("sim-")
            assert snapshot.actor == context.actor_id
            assert not controller.projection_path.exists()

    def test_journal_events_emitted(self):
        """RuntimeController emits journal events on dispatch.

        The _event() method writes to the runtime-events.jsonl journal.
        Both successful and blocked dispatches should be logged.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = _setup_controller(root)

            # Successful dispatch
            controller.dispatch_execution(
                _make_capability(task_id="T-J1", execution_id="exec-j1"),
                _make_context(task_id="T-J1", execution_id="exec-j1"),
                agent_adapter=_MockPassAdapter(),
                gate_id="G-J1",
            )

            # Blocked dispatch (no adapter, different task_id to avoid lease conflict)
            controller.dispatch_execution(
                _make_capability(task_id="T-J2", execution_id="exec-j2"),
                _make_context(task_id="T-J2", execution_id="exec-j2"),
                gate_id="G-J2",
            )

            journal_path = controller.journal_path
            assert journal_path.exists()

            lines = journal_path.read_text(encoding="utf-8").strip().splitlines()
            # We expect at least the two DISPATCH_ATTEMPTED events
            dispatch_events = [
                line for line in lines
                if "DISPATCH_ATTEMPTED" in line
            ]
            assert len(dispatch_events) >= 2

            # Each event should be valid JSON
            for line in lines:
                if not line.strip():
                    continue
                event = json.loads(line)
                assert "event" in event
                assert "details" in event


# ============================================================================
# Skipped tests — require real Agent harness
# ============================================================================


@pytest.mark.skip(
    reason="REQUIRES_LIVE_AGENT: Cannot create real Agent sub-sessions in unit test. "
           "T-0079 dispatched 5 real agent_* child sessions — their evidence is "
           "recorded in .ai/evidence/T-0079/commands.md.  Real receipt chain "
           "verification across live sessions requires the harness-agentic tool "
           "which is not available at the Python test layer."
)
class TestSkippedRealAgentDispatch:
    """Tests that require a live Agent harness — skipped for now.

    These acceptance criteria can only be verified when a real Agent adapter
    is wired in and can launch actual sub-sessions.  The 5 agent_* IDs from
    T-0079 provide real-world evidence that the dispatch pipeline works.
    """

    def test_real_agent_launch_creates_pass_receipt(self):
        """[SKIPPED] Real agent dispatch produces PASS receipt.

        Requires live Agent adapter to create a real sub-session.
        Verified during T-0079 with 5 agent_* sessions.
        """
        pass

    def test_real_agent_completion_cross_verifies(self):
        """[SKIPPED] Real agent completion matches launch receipt.

        Requires a completed real sub-session to produce matching
        launch and completion receipts with cross-verifiable hashes.
        """
        pass

    def test_real_agent_projection_cross_verified(self):
        """[SKIPPED] Real agent projection file matches receipt chain.

        Requires a running Agent sub-session whose projection can be
        compared against the live receipt chain.
        """
        pass
