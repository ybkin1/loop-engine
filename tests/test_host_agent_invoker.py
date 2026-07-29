"""Unit tests for loop_core.host_agent_invoker — the Agent dispatch bridge.

Tests the fail-closed design, receipt serialisation, input hash computation,
and cross-verification of launch/completion receipt chains.
"""
from __future__ import annotations

import hashlib
import json
import time

import pytest

from loop_core.host_agent_invoker import (
    AgentCompletionReceipt,
    AgentLaunchReceipt,
    HostAgentInvoker,
    HostAgentInvokerError,
    ReceiptStatus,
    _canonical,
    _compute_hash,
)


# ============================================================================
# Helpers
# ============================================================================

def _build_minimal_payload(**overrides) -> dict:
    payload = {
        "task_id": "T-0001",
        "role_id": "developer",
        "prompt": "Write a function that adds two numbers.",
    }
    payload.update(overrides)
    return payload


# ============================================================================
# Fail-closed behaviour — no adapter
# ============================================================================

class TestFailClosedNoAdapter:
    """Every launch must return BLOCKED when no AgentAdapter is wired in."""

    def test_launch_returns_blocked_when_adapter_is_none(self):
        invoker = HostAgentInvoker(agent_adapter=None)
        receipt = invoker.launch(_build_minimal_payload())

        assert receipt.status == ReceiptStatus.BLOCKED
        assert receipt.is_terminal() is True
        assert receipt.is_pass() is False

    def test_launch_metadata_signals_setup_incomplete(self):
        invoker = HostAgentInvoker(agent_adapter=None)
        receipt = invoker.launch(_build_minimal_payload())

        meta = receipt.metadata
        assert meta.get("agent_takeover") is False
        assert meta.get("state") == "SETUP_INCOMPLETE"
        assert "Agent tool unavailable" in meta.get("reason", "")

    def test_launch_metadata_respects_execution_mode_hint(self):
        invoker = HostAgentInvoker(agent_adapter=None)
        receipt = invoker.launch(
            _build_minimal_payload(), execution_mode="UNIT_TEST_MODE"
        )
        assert receipt.metadata["execution_mode"] == "UNIT_TEST_MODE"

    def test_launch_generates_unique_child_session_each_call(self):
        invoker = HostAgentInvoker(agent_adapter=None)
        r1 = invoker.launch(_build_minimal_payload())
        r2 = invoker.launch(_build_minimal_payload())
        assert r1.child_session != r2.child_session
        assert r1.child_session.startswith("sim-")
        assert r2.child_session.startswith("sim-")

    def test_collect_from_blocked_launch_returns_same_status(self):
        invoker = HostAgentInvoker(agent_adapter=None)
        launch = invoker.launch(_build_minimal_payload())
        completion = invoker.collect(launch)

        assert completion.status == ReceiptStatus.BLOCKED
        assert completion.output_hash == ""
        assert completion.child_session == launch.child_session

    def test_check_agent_status_returns_blocked_without_adapter(self):
        invoker = HostAgentInvoker(agent_adapter=None)
        assert invoker.check_agent_status("any-session") == ReceiptStatus.BLOCKED

    def test_agent_available_property_is_false_when_adapter_is_none(self):
        invoker = HostAgentInvoker(agent_adapter=None)
        assert invoker.agent_available is False

    def test_active_session_count_zero_when_no_real_launches(self):
        invoker = HostAgentInvoker(agent_adapter=None)
        assert invoker.active_session_count == 0


# ============================================================================
# Receipt field validation
# ============================================================================

class TestAgentLaunchReceiptFields:
    """Ensure the frozen dataclass populates and validates all expected fields."""

    def test_all_fields_populated_for_blocked_receipt(self):
        receipt = AgentLaunchReceipt(
            host_invoker="loop-engine",
            child_session="sim-abc123",
            actor="loop-orchestrator",
            input_hash="DEADBEEF",
            status=ReceiptStatus.BLOCKED,
            metadata={"agent_takeover": False, "state": "SETUP_INCOMPLETE"},
        )
        assert receipt.host_invoker == "loop-engine"
        assert receipt.child_session == "sim-abc123"
        assert receipt.actor == "loop-orchestrator"
        assert receipt.input_hash == "DEADBEEF"
        assert receipt.status == ReceiptStatus.BLOCKED
        assert receipt.metadata["agent_takeover"] is False

    def test_metadata_defaults_to_empty_dict(self):
        receipt = AgentLaunchReceipt(
            host_invoker="loop-engine",
            child_session="sim-abc123",
            actor="loop-orchestrator",
            input_hash="DEADBEEF",
            status=ReceiptStatus.BLOCKED,
        )
        assert receipt.metadata == {}

    def test_is_pass_true_for_pass_status(self):
        receipt = AgentLaunchReceipt(
            host_invoker="loop-engine",
            child_session="sim-abc123",
            actor="loop-orchestrator",
            input_hash="DEADBEEF",
            status=ReceiptStatus.PASS,
        )
        assert receipt.is_pass() is True
        assert receipt.is_terminal() is False

    def test_is_terminal_for_blocked_and_error(self):
        for status in (ReceiptStatus.BLOCKED, ReceiptStatus.ERROR):
            receipt = AgentLaunchReceipt(
                host_invoker="loop-engine",
                child_session="sim-abc123",
                actor="loop-orchestrator",
                input_hash="DEADBEEF",
                status=status,
            )
            assert receipt.is_terminal() is True


class TestAgentCompletionReceiptFields:
    """Ensure the completion receipt dataclass is similarly sound."""

    def test_all_fields_populated(self):
        comp = AgentCompletionReceipt(
            status=ReceiptStatus.PASS,
            output_hash="ABCD1234",
            child_session="child-001",
            actor="developer",
            host_invoker="loop-engine",
            launch_input_hash="INPUT-HASH",
            metadata={"agent_takeover": True},
        )
        assert comp.status == ReceiptStatus.PASS
        assert comp.output_hash == "ABCD1234"
        assert comp.child_session == "child-001"
        assert comp.actor == "developer"
        assert comp.host_invoker == "loop-engine"
        assert comp.launch_input_hash == "INPUT-HASH"
        assert comp.metadata["agent_takeover"] is True

    def test_default_string_fields_are_empty(self):
        comp = AgentCompletionReceipt(
            status=ReceiptStatus.PASS,
            output_hash="ABCD1234",
        )
        assert comp.child_session == ""
        assert comp.actor == ""
        assert comp.host_invoker == ""
        assert comp.launch_input_hash == ""
        assert comp.metadata == {}


# ============================================================================
# Input hash computation
# ============================================================================

class TestCanonicalSerialization:
    """_canonical() must produce stable, sorted-key JSON."""

    def test_keys_are_sorted(self):
        payload = {"z": 1, "a": 2, "m": 3}
        result = _canonical(payload)
        assert result == '{"a":2,"m":3,"z":1}'

    def test_nested_dict_keys_are_sorted(self):
        payload = {"outer": {"z": 1, "a": 2}}
        result = _canonical(payload)
        assert result == '{"outer":{"a":2,"z":1}}'

    def test_lists_preserve_order(self):
        payload = {"items": [3, 1, 2]}
        result = _canonical(payload)
        assert result == '{"items":[3,1,2]}'

    def test_same_content_different_order_produces_same_canonical(self):
        a = {"role_id": "dev", "task_id": "T1"}
        b = {"task_id": "T1", "role_id": "dev"}
        assert _canonical(a) == _canonical(b)


class TestInputHashComputation:
    """_compute_hash() must produce stable SHA-256 uppercased hex."""

    def test_hash_is_uppercased_sha256_hex(self):
        h = _compute_hash({"task_id": "T-0001"})
        # SHA-256 hex is 64 characters
        assert len(h) == 64
        assert h == h.upper()
        # Verify directly
        expected = (
            hashlib.sha256(b'{"task_id":"T-0001"}')
            .hexdigest()
            .upper()
        )
        assert h == expected

    def test_same_input_produces_same_hash(self):
        h1 = _compute_hash({"task_id": "T-0001", "role_id": "dev"})
        h2 = _compute_hash({"role_id": "dev", "task_id": "T-0001"})
        assert h1 == h2

    def test_different_input_produces_different_hash(self):
        h1 = _compute_hash({"task_id": "T-0001"})
        h2 = _compute_hash({"task_id": "T-0002"})
        assert h1 != h2

    def test_launch_computes_hash_from_payload(self):
        invoker = HostAgentInvoker(agent_adapter=None)
        payload = _build_minimal_payload(task_id="T-XYZ", role_id="reviewer")
        receipt = invoker.launch(payload)

        expected_hash = _compute_hash(payload)
        assert receipt.input_hash == expected_hash


# ============================================================================
# Receipt chain verification
# ============================================================================

class TestReceiptChainVerification:
    """verify_receipt_chain() must catch mismatched receipts."""

    def test_valid_chain_returns_true(self):
        invoker = HostAgentInvoker(agent_adapter=None)
        launch = AgentLaunchReceipt(
            host_invoker=invoker.host_name,
            child_session="child-001",
            actor="loop-orchestrator",
            input_hash="SAME-HASH",
            status=ReceiptStatus.PASS,
        )
        completion = AgentCompletionReceipt(
            status=ReceiptStatus.PASS,
            output_hash="OUT-HASH",
            child_session="child-001",
            actor="loop-orchestrator",
            host_invoker=invoker.host_name,
            launch_input_hash="SAME-HASH",
        )
        assert invoker.verify_receipt_chain(launch, completion) is True

    def test_mismatched_child_session_returns_false(self):
        invoker = HostAgentInvoker(agent_adapter=None)
        launch = AgentLaunchReceipt(
            host_invoker=invoker.host_name,
            child_session="child-001",
            actor="loop-orchestrator",
            input_hash="SAME-HASH",
            status=ReceiptStatus.PASS,
        )
        completion = AgentCompletionReceipt(
            status=ReceiptStatus.PASS,
            output_hash="OUT-HASH",
            child_session="child-002",  # different
            actor="loop-orchestrator",
            host_invoker=invoker.host_name,
            launch_input_hash="SAME-HASH",
        )
        assert invoker.verify_receipt_chain(launch, completion) is False

    def test_mismatched_input_hash_returns_false(self):
        invoker = HostAgentInvoker(agent_adapter=None)
        launch = AgentLaunchReceipt(
            host_invoker=invoker.host_name,
            child_session="child-001",
            actor="loop-orchestrator",
            input_hash="HASH-A",
            status=ReceiptStatus.PASS,
        )
        completion = AgentCompletionReceipt(
            status=ReceiptStatus.PASS,
            output_hash="OUT-HASH",
            child_session="child-001",
            actor="loop-orchestrator",
            host_invoker=invoker.host_name,
            launch_input_hash="HASH-B",  # different
        )
        assert invoker.verify_receipt_chain(launch, completion) is False

    def test_mismatched_host_invoker_returns_false(self):
        invoker = HostAgentInvoker(agent_adapter=None)
        launch = AgentLaunchReceipt(
            host_invoker="host-A",
            child_session="child-001",
            actor="loop-orchestrator",
            input_hash="SAME-HASH",
            status=ReceiptStatus.PASS,
        )
        completion = AgentCompletionReceipt(
            status=ReceiptStatus.PASS,
            output_hash="OUT-HASH",
            child_session="child-001",
            actor="loop-orchestrator",
            host_invoker="host-B",  # different
            launch_input_hash="SAME-HASH",
        )
        assert invoker.verify_receipt_chain(launch, completion) is False

    def test_non_pass_launch_returns_false(self):
        invoker = HostAgentInvoker(agent_adapter=None)
        launch = AgentLaunchReceipt(
            host_invoker=invoker.host_name,
            child_session="child-001",
            actor="loop-orchestrator",
            input_hash="SAME-HASH",
            status=ReceiptStatus.BLOCKED,  # not PASS
        )
        completion = AgentCompletionReceipt(
            status=ReceiptStatus.PASS,
            output_hash="OUT-HASH",
            child_session="child-001",
            actor="loop-orchestrator",
            host_invoker=invoker.host_name,
            launch_input_hash="SAME-HASH",
        )
        assert invoker.verify_receipt_chain(launch, completion) is False


# ============================================================================
# to_dict() serialisation
# ============================================================================

class TestAgentLaunchReceiptToDict:
    """to_dict() must produce the dispatch_receipt shape."""

    def test_to_dict_includes_required_keys(self):
        receipt = AgentLaunchReceipt(
            host_invoker="loop-engine",
            child_session="sim-abc123",
            actor="loop-orchestrator",
            input_hash="DEADBEEF",
            status=ReceiptStatus.BLOCKED,
        )
        d = receipt.to_dict()
        assert d == {
            "host_invoker": "loop-engine",
            "child_session": "sim-abc123",
            "actor": "loop-orchestrator",
            "input_hash": "DEADBEEF",
            "status": "BLOCKED",
        }

    def test_to_dict_status_is_string_value_not_enum(self):
        receipt = AgentLaunchReceipt(
            host_invoker="h",
            child_session="c",
            actor="a",
            input_hash="h",
            status=ReceiptStatus.ERROR,
        )
        d = receipt.to_dict()
        assert d["status"] == "ERROR"
        assert not isinstance(d["status"], ReceiptStatus)

    def test_to_dict_does_not_include_metadata(self):
        """Metadata is internal and should NOT leak into the serialised receipt."""
        receipt = AgentLaunchReceipt(
            host_invoker="loop-engine",
            child_session="sim-abc123",
            actor="loop-orchestrator",
            input_hash="DEADBEEF",
            status=ReceiptStatus.BLOCKED,
            metadata={"secret": "do-not-leak"},
        )
        d = receipt.to_dict()
        assert "metadata" not in d

    def test_to_dict_all_status_values(self):
        for status in ReceiptStatus:
            receipt = AgentLaunchReceipt(
                host_invoker="h",
                child_session="c",
                actor="a",
                input_hash="h",
                status=status,
            )
            d = receipt.to_dict()
            assert d["status"] == status.value


class TestAgentCompletionReceiptToDict:
    """to_dict() must serialise all completion receipt fields."""

    def test_to_dict_includes_all_expected_keys(self):
        comp = AgentCompletionReceipt(
            status=ReceiptStatus.PASS,
            output_hash="OUT-ABCD",
            child_session="child-001",
            actor="developer",
            host_invoker="loop-engine",
            launch_input_hash="INPUT-ABCD",
        )
        d = comp.to_dict()
        assert d == {
            "status": "PASS",
            "output_hash": "OUT-ABCD",
            "child_session": "child-001",
            "actor": "developer",
            "host_invoker": "loop-engine",
            "launch_input_hash": "INPUT-ABCD",
        }

    def test_to_dict_defaults_produce_empty_strings(self):
        comp = AgentCompletionReceipt(
            status=ReceiptStatus.ERROR,
            output_hash="",
        )
        d = comp.to_dict()
        assert d["child_session"] == ""
        assert d["actor"] == ""
        assert d["host_invoker"] == ""
        assert d["launch_input_hash"] == ""

    def test_to_dict_does_not_include_metadata(self):
        comp = AgentCompletionReceipt(
            status=ReceiptStatus.PASS,
            output_hash="OUT-ABCD",
            metadata={"internal": "secret"},
        )
        d = comp.to_dict()
        assert "metadata" not in d


# ============================================================================
# Edge cases
# ============================================================================

class TestEdgeCases:
    """Miscellaneous edge cases and robustness checks."""

    def test_empty_payload_produces_hash(self):
        invoker = HostAgentInvoker(agent_adapter=None)
        receipt = invoker.launch({})
        assert len(receipt.input_hash) == 64

    def test_unicode_payload_is_hashed_correctly(self):
        payload = {
            "task_id": "T-0079",
            "prompt": "Realise le test avec des accents: cote, cote, cote, cote",
        }
        invoker = HostAgentInvoker(agent_adapter=None)
        receipt = invoker.launch(payload)
        assert len(receipt.input_hash) == 64

    def test_large_nested_payload_is_hashed_consistently(self):
        payload = {
            "task_id": "T-LARGE",
            "nested": [{"key": f"value-{i}"} for i in range(100)],
        }
        invoker = HostAgentInvoker(agent_adapter=None)
        r1 = invoker.launch(payload)
        r2 = invoker.launch(payload)
        assert r1.input_hash == r2.input_hash

    def test_host_name_default(self):
        invoker = HostAgentInvoker(agent_adapter=None)
        assert invoker.host_name == "loop-engine"

    def test_custom_host_name(self):
        invoker = HostAgentInvoker(agent_adapter=None, host_name="custom-host")
        assert invoker.host_name == "custom-host"

    def test_custom_actor_appears_in_receipt(self):
        invoker = HostAgentInvoker(agent_adapter=None)
        receipt = invoker.launch(
            _build_minimal_payload(), actor="ci-bot"
        )
        assert receipt.actor == "ci-bot"

    def test_receipt_is_frozen_raises_on_mutation(self):
        receipt = AgentLaunchReceipt(
            host_invoker="h",
            child_session="c",
            actor="a",
            input_hash="h",
            status=ReceiptStatus.BLOCKED,
        )
        with pytest.raises(Exception):
            receipt.status = ReceiptStatus.PASS  # type: ignore[misc]

    def test_default_timeout_is_stored(self):
        invoker = HostAgentInvoker(
            agent_adapter=None, default_timeout_seconds=123
        )
        assert invoker._default_timeout == 123


# ============================================================================
# HostAgentInvokerError
# ============================================================================

class TestHostAgentInvokerError:
    """Basic smoke test for the error type."""

    def test_is_runtime_error_subclass(self):
        assert issubclass(HostAgentInvokerError, RuntimeError)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(HostAgentInvokerError, match="test error"):
            raise HostAgentInvokerError("test error")
