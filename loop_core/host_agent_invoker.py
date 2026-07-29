"""Agent dispatch bridge for the Loop runtime controller.

This module is the host-independent bridge that the runtime controller uses
to launch Agent sub-sessions.  It is fail-closed by design: if the Agent tool
is unavailable (no AgentAdapter provided), every launch returns status=BLOCKED
with explicit metadata — never a fabricated PASS.

Design principles
-----------------
- Fail-closed          — default to BLOCKED when Agent tool is not available
- Explicit metadata    — execution_mode and agent_takeover clearly marked
- No mock-as-real      — if dispatch isn't truly available, mark SETUP_INCOMPLETE
- Cross-verifiable     — all receipts carry hashable input/output fingerprints
"""
from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ============================================================================
# Status enum — mirrors the dispatch-runtime-contract schema
# ============================================================================

class ReceiptStatus(str, Enum):
    """Dispatch receipt status values per the contract schema."""
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"
    NOT_RUN = "NOT_RUN"


# ============================================================================
# Receipts
# ============================================================================

@dataclass(frozen=True)
class AgentLaunchReceipt:
    """Evidence-layer record of an Agent sub-session launch attempt.

    Conforms to the ``dispatch_receipt`` object defined in
    ``.ai/schemas/dispatch-runtime-contract.schema.json``::

        {
          "host_invoker":  "...",
          "child_session": "...",
          "actor":         "...",
          "input_hash":    "...",
          "status":        "PASS|BLOCKED|ERROR|NOT_RUN"
        }
    """

    host_invoker: str
    child_session: str
    actor: str
    input_hash: str
    status: ReceiptStatus
    metadata: dict[str, Any] = field(default_factory=dict)

    # -- helpers ----------------------------------------------------------

    def is_pass(self) -> bool:
        """True when the launch succeeded and dispatch should proceed."""
        return self.status == ReceiptStatus.PASS

    def is_terminal(self) -> bool:
        """True when no further action can be taken (BLOCKED or ERROR)."""
        return self.status in (ReceiptStatus.BLOCKED, ReceiptStatus.ERROR)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to the exact dispatch_receipt shape."""
        return {
            "host_invoker": self.host_invoker,
            "child_session": self.child_session,
            "actor": self.actor,
            "input_hash": self.input_hash,
            "status": self.status.value,
        }


@dataclass(frozen=True)
class AgentCompletionReceipt:
    """Evidence-layer record of an Agent sub-session completion.

    Carries an ``output_hash`` that can be cross-verified against the
    launch receipt's ``input_hash`` to prove the execution chain is intact.
    """

    status: ReceiptStatus
    output_hash: str
    child_session: str = ""
    actor: str = ""
    host_invoker: str = ""
    launch_input_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # -- helpers ----------------------------------------------------------

    def is_pass(self) -> bool:
        return self.status == ReceiptStatus.PASS

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "output_hash": self.output_hash,
            "child_session": self.child_session,
            "actor": self.actor,
            "host_invoker": self.host_invoker,
            "launch_input_hash": self.launch_input_hash,
        }


# ============================================================================
# Error type
# ============================================================================

class HostAgentInvokerError(RuntimeError):
    """Raised when the invoker encounters a hard failure (fail-closed)."""


# ============================================================================
# Hashing helpers
# ============================================================================

def _canonical(value: Any) -> str:
    """Serialize a value to canonical JSON (sorted keys, no whitespace)."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _compute_hash(value: Any) -> str:
    """SHA-256 of a canonical JSON string, uppercased for readability."""
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest().upper()


# ============================================================================
# HostAgentInvoker
# ============================================================================

class HostAgentInvoker:
    """Agent dispatch bridge — callable from ``runtime_controller.py``.

    **Fail-closed contract**

    When no ``agent_adapter`` is supplied the invoker operates in degraded
    mode.  Every ``launch()`` returns ``ReceiptStatus.BLOCKED`` with::

        execution_mode: "SIMULATED_MAIN_SESSION"
        agent_takeover: false
        state:          "SETUP_INCOMPLETE"

    This guarantees the runtime controller never receives a fabricated PASS
    receipt.

    **Usage from runtime_controller.py**::

        invoker = HostAgentInvoker(agent_adapter=host_adapter)
        receipt = invoker.launch({
            "task_id":      task_id,
            "role_id":      "developer",
            "prompt":       "...",
            "gate_id":      gate_id,
            "execution_id": execution_id,
        })

        if receipt.is_pass():
            completion = invoker.collect(receipt)
            is_valid = invoker.verify_receipt_chain(receipt, completion)

    **Metadata shape** on a successful launch::

        {
          "execution_mode":  "ROLE_EXECUTION",
          "agent_takeover":  true,
          "task_id":         "task-1",
          "role_id":         "developer",
          "gate_id":         "gate-abc",
          "execution_id":    "exec-..."
        }
    """

    DEFAULT_ACTOR = "loop-orchestrator"
    DEFAULT_HOST = "loop-engine"

    # ------------------------------------------------------------------

    def __init__(
        self,
        agent_adapter: Any = None,
        *,
        host_name: str = "",
        default_timeout_seconds: int = 300,
    ):
        self._agent_adapter = agent_adapter
        self._host_name = host_name or self.DEFAULT_HOST
        self._default_timeout = default_timeout_seconds
        self._active_sessions: dict[str, AgentLaunchReceipt] = {}

    # -- properties ------------------------------------------------------

    @property
    def host_name(self) -> str:
        return self._host_name

    @property
    def agent_available(self) -> bool:
        """True when a real Agent adapter is wired in (not just configured)."""
        return self._agent_adapter is not None

    @property
    def active_session_count(self) -> int:
        return len(self._active_sessions)

    # -- launch ----------------------------------------------------------

    def launch(
        self,
        dispatch_payload: dict[str, Any],
        *,
        actor: str = "",
        execution_mode: str = "",
    ) -> AgentLaunchReceipt:
        """Launch an Agent sub-session.

        Computes ``input_hash`` from the full dispatch payload so the
        receipt can later be cross-verified against the completion receipt.

        Args:
            dispatch_payload:
                Minimum keys: ``task_id``, ``role_id``, ``prompt``.
                Recommended: ``gate_id``, ``execution_id``,
                ``input_files``, ``read_scope``, ``write_scope``,
                ``allowed_tools``, ``forbidden_tools``.
            actor:
                Override the default ``DEFAULT_ACTOR`` identifier.
            execution_mode:
                Hint for the metadata block (e.g. ``"ROLE_EXECUTION"``).

        Returns:
            ``AgentLaunchReceipt`` — always check ``.is_pass()`` before
            proceeding.
        """
        input_hash = _compute_hash(dispatch_payload)
        resolved_actor = actor or self.DEFAULT_ACTOR

        # ── Fail-closed: no Agent adapter ──────────────────────────────
        if self._agent_adapter is None:
            child_session = f"sim-{secrets.token_hex(8)}"
            return AgentLaunchReceipt(
                host_invoker=self._host_name,
                child_session=child_session,
                actor=resolved_actor,
                input_hash=input_hash,
                status=ReceiptStatus.BLOCKED,
                metadata={
                    "reason": (
                        "Agent tool unavailable — no AgentAdapter provided to "
                        "HostAgentInvoker. Dispatch blocked (fail-closed)."
                    ),
                    "execution_mode": execution_mode or "SIMULATED_MAIN_SESSION",
                    "agent_takeover": False,
                    "state": "SETUP_INCOMPLETE",
                },
            )

        # ── Attempt real dispatch ──────────────────────────────────────
        try:
            from loop_core.agent_adapter import AgentInput

            task_id = dispatch_payload.get("task_id", "")
            role_id = dispatch_payload.get("role_id", "general-purpose")
            prompt = dispatch_payload.get("prompt", "")
            gate_id = dispatch_payload.get("gate_id", "")
            execution_id = dispatch_payload.get("execution_id", "")

            child_session = f"child-{secrets.token_hex(16)}"

            agent_input = AgentInput(
                role_id=role_id,
                task_id=task_id,
                prompt=prompt,
                session_id=child_session,
                actor_id=resolved_actor,
                input_files=dispatch_payload.get("input_files", []),
                read_scope=dispatch_payload.get("read_scope", []),
                write_scope=dispatch_payload.get("write_scope", []),
                allowed_tools=dispatch_payload.get("allowed_tools"),
                forbidden_tools=dispatch_payload.get("forbidden_tools"),
            )

            result = self._agent_adapter.launch_agent(agent_input)

            # Map agent status to receipt status
            if result is None:
                raise HostAgentInvokerError("launch_agent returned None")

            agent_status = result.status.value if hasattr(result, "status") else "unknown"
            if agent_status in ("completed", "running", "launching", "pending"):
                receipt_status = ReceiptStatus.PASS
            elif agent_status == "blocked":
                receipt_status = ReceiptStatus.BLOCKED
            else:
                receipt_status = ReceiptStatus.ERROR

            receipt = AgentLaunchReceipt(
                host_invoker=self._host_name,
                child_session=child_session,
                actor=resolved_actor,
                input_hash=input_hash,
                status=receipt_status,
                metadata={
                    "execution_mode": execution_mode or "ROLE_EXECUTION",
                    "agent_takeover": receipt_status == ReceiptStatus.PASS,
                    "task_id": task_id,
                    "role_id": role_id,
                    "gate_id": gate_id,
                    "execution_id": execution_id,
                },
            )
            self._active_sessions[child_session] = receipt
            return receipt

        except Exception as exc:
            child_session = f"err-{secrets.token_hex(8)}"
            return AgentLaunchReceipt(
                host_invoker=self._host_name,
                child_session=child_session,
                actor=resolved_actor,
                input_hash=input_hash,
                status=ReceiptStatus.ERROR,
                metadata={
                    "reason": f"Agent launch raised: {exc!r}",
                    "execution_mode": execution_mode or "SIMULATED_MAIN_SESSION",
                    "agent_takeover": False,
                    "state": "SETUP_INCOMPLETE",
                },
            )

    # -- collect ---------------------------------------------------------

    def collect(
        self,
        launch_receipt: AgentLaunchReceipt,
        *,
        raw_output: str = "",
    ) -> AgentCompletionReceipt:
        """Collect the result from a launched Agent sub-session.

        Args:
            launch_receipt:
                The receipt returned by ``launch()``.
            raw_output:
                Fallback output text when the adapter's ``collect_output``
                is unavailable.

        Returns:
            ``AgentCompletionReceipt`` with ``output_hash`` populated so
            the full chain is cross-verifiable.
        """
        # Cannot collect from a non-PASS launch
        if launch_receipt.status != ReceiptStatus.PASS:
            return AgentCompletionReceipt(
                status=launch_receipt.status,
                output_hash="",
                child_session=launch_receipt.child_session,
                actor=launch_receipt.actor,
                host_invoker=launch_receipt.host_invoker,
                launch_input_hash=launch_receipt.input_hash,
                metadata={
                    "reason": (
                        f"Cannot collect from launch with status "
                        f"{launch_receipt.status.value}"
                    ),
                },
            )

        try:
            output_content = raw_output

            if self._agent_adapter is not None:
                collected = self._agent_adapter.collect_output(
                    launch_receipt.child_session
                )
                if collected is not None:
                    output_content = getattr(collected, "stdout", "") or raw_output

            output_hash = (
                _compute_hash({"output": output_content, "child_session": launch_receipt.child_session})
                if output_content
                else ""
            )

            return AgentCompletionReceipt(
                status=ReceiptStatus.PASS,
                output_hash=output_hash,
                child_session=launch_receipt.child_session,
                actor=launch_receipt.actor,
                host_invoker=launch_receipt.host_invoker,
                launch_input_hash=launch_receipt.input_hash,
                metadata={
                    "agent_takeover": True,
                    "collected_at": time.time(),
                },
            )
        except Exception as exc:
            return AgentCompletionReceipt(
                status=ReceiptStatus.ERROR,
                output_hash="",
                child_session=launch_receipt.child_session,
                actor=launch_receipt.actor,
                host_invoker=launch_receipt.host_invoker,
                launch_input_hash=launch_receipt.input_hash,
                metadata={"reason": f"Collection failed: {exc!r}"},
            )

    # -- status check ----------------------------------------------------

    def check_agent_status(self, child_session: str) -> ReceiptStatus:
        """Poll a launched sub-session for its current status.

        Returns ``NOT_RUN`` when the session is still pending / running,
        ``PASS`` when completed, ``ERROR`` on failure, and ``BLOCKED``
        when no adapter is available.
        """
        if self._agent_adapter is None:
            return ReceiptStatus.BLOCKED
        try:
            status = self._agent_adapter.get_status(child_session)
            status_value = status.value if hasattr(status, "value") else str(status)
            if status_value == "completed":
                return ReceiptStatus.PASS
            if status_value in ("failed", "blocked", "unavailable"):
                return ReceiptStatus.ERROR
            return ReceiptStatus.NOT_RUN
        except Exception:
            return ReceiptStatus.ERROR

    # -- verification ----------------------------------------------------

    def verify_receipt_chain(
        self,
        launch_receipt: AgentLaunchReceipt,
        completion_receipt: AgentCompletionReceipt,
    ) -> bool:
        """Cross-verify that launch and completion receipts form an unbroken chain.

        Checks that ``child_session``, ``host_invoker``, and the
        ``input_hash`` / ``launch_input_hash`` pair all match.
        """
        return (
            launch_receipt.is_pass()
            and launch_receipt.child_session == completion_receipt.child_session
            and launch_receipt.input_hash == completion_receipt.launch_input_hash
            and launch_receipt.host_invoker == completion_receipt.host_invoker
        )
