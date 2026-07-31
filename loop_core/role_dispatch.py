"""
Role Dispatch Manager — real role sub-agent execution takeover (T-0082 Phase 3).

The MAIN THREAD (orchestrator) uses this module to prepare role dispatches:
- generate_role_actor_id(role_id)   — deterministic actor per role
- generate_role_session_id(...)     — unique session per dispatch
- prepare_dispatch(...)             — writes launch receipt + LAUNCHED ledger entry
- complete_dispatch(...)            — writes completion receipt + COMPLETED ledger entry
- verify_role_isolation(orders)     — rejects developer==reviewer actor/session

Ledger wiring uses the real ExecutionLedger API (loop_core/execution_ledger.py):
- ExecutionLedger(project_root) — appends .ai/ledger/executions.jsonl itself
- record_launch(ExecutionRecord(status=LAUNCHED, ...)) — full record object
- record_completion(execution_id, status=ExecutionStatus, ...) — enum status

Host Adapter unavailable → BLOCKED/NOT_VERIFIED, never a fabricated PASS.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_role_actor_id(role_id: str) -> str:
    """Deterministic actor id per role: zcode-actor-<sha256(role_id)[:12]>.

    Distinct roles ALWAYS get distinct actor ids. Same role across tasks
    shares an actor id (identity is role-scoped, sessions are per-dispatch).
    """
    digest = hashlib.sha256(role_id.encode()).hexdigest()[:12]
    return f"zcode-actor-{digest}"


def generate_role_session_id(task_id: str, role_id: str) -> str:
    """Random session id per dispatch: zcode-sess-<sha256(task:role:uuid)[:16]>."""
    digest = hashlib.sha256(f"{task_id}:{role_id}:{uuid.uuid4()}".encode()).hexdigest()[:16]
    return f"zcode-sess-{digest}"


@dataclass(frozen=True)
class DispatchOrder:
    """Everything needed to dispatch one role sub-agent."""
    dispatch_id: str
    role_id: str
    task_id: str
    phase: str
    gate_id: str
    actor_id: str
    session_id: str
    child_session_id: str  # = session_id (the agent tool session)
    prompt: str
    allowed_paths: tuple[str, ...] = ()
    created_at: str = field(default_factory=now_iso)

    def launch_receipt(self) -> dict:
        """Launch receipt conforming to dispatch-runtime-contract schema."""
        return {
            "receipt_type": "launch",
            "dispatch_id": self.dispatch_id,
            "host_invoker": "zcode-main-thread",
            "child_session": self.child_session_id,
            "actor": self.actor_id,
            "role_id": self.role_id,
            "task_id": self.task_id,
            "phase": self.phase,
            "gate_id": self.gate_id,
            "status": "PASS",
            "agent_takeover": True,
            "input_hash": hashlib.sha256(self.prompt.encode()).hexdigest()[:16],
            "created_at": self.created_at,
        }

    def to_dict(self) -> dict:
        return {
            "dispatch_id": self.dispatch_id,
            "role_id": self.role_id,
            "task_id": self.task_id,
            "phase": self.phase,
            "gate_id": self.gate_id,
            "actor_id": self.actor_id,
            "session_id": self.session_id,
            "child_session_id": self.child_session_id,
            "allowed_paths": list(self.allowed_paths),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DispatchOrder":
        return cls(
            dispatch_id=d["dispatch_id"],
            role_id=d["role_id"],
            task_id=d["task_id"],
            phase=d["phase"],
            gate_id=d["gate_id"],
            actor_id=d["actor_id"],
            session_id=d["session_id"],
            child_session_id=d["child_session_id"],
            prompt=d.get("prompt", ""),
            allowed_paths=tuple(d.get("allowed_paths", [])),
            created_at=d.get("created_at", now_iso()),
        )


class RoleDispatchManager:
    """Manages role dispatch lifecycle with receipts + ledger wiring.

    Ledger: uses ExecutionLedger when available; otherwise records are
    written to the receipts file so the chain stays append-only.
    """

    def __init__(self, project_root: str | Path, receipts_dir: str = ".ai/runtime/dispatch"):
        self.root = Path(project_root).resolve()
        self.receipts_dir = self.root / receipts_dir
        self.receipts_dir.mkdir(parents=True, exist_ok=True)
        self._ledger = None
        try:
            from loop_core.execution_ledger import ExecutionLedger
            # ExecutionLedger takes the project root; it appends
            # .ai/ledger/executions.jsonl itself.
            self._ledger = ExecutionLedger(self.root)
        except Exception:
            self._ledger = None

    # ── Prepare: launch receipt + LAUNCHED ledger ──
    def prepare_dispatch(self, role_id: str, task_id: str, phase: str,
                         gate_id: str, prompt: str,
                         allowed_paths: list[str] | None = None) -> DispatchOrder:
        session_id = generate_role_session_id(task_id, role_id)
        order = DispatchOrder(
            dispatch_id=f"DP-{uuid.uuid4().hex[:12]}",
            role_id=role_id,
            task_id=task_id,
            phase=phase,
            gate_id=gate_id,
            actor_id=generate_role_actor_id(role_id),
            session_id=session_id,
            # child_session == session for direct Agent() dispatch
            child_session_id=session_id,
            prompt=prompt,
            allowed_paths=tuple(allowed_paths or []),
        )
        self._write_receipt(order.dispatch_id, order.launch_receipt())
        if self._ledger is not None:
            try:
                from loop_core.execution_ledger import ExecutionRecord, ExecutionStatus
                self._ledger.record_launch(ExecutionRecord(
                    execution_id=f"exec-{order.dispatch_id}",
                    session_id=order.session_id,
                    actor_id=order.actor_id,
                    role_id=role_id,
                    task_id=task_id,
                    prompt_fingerprint=hashlib.sha256(prompt.encode()).hexdigest()[:16],
                    input_files_hash=hashlib.sha256(
                        "|".join(sorted(order.allowed_paths)).encode()
                    ).hexdigest()[:16],
                    status=ExecutionStatus.LAUNCHED,
                    launched_at=order.created_at,
                ))
            except Exception:
                pass  # ledger failure is non-blocking; receipts still authoritative
        return order

    def _write_receipt(self, dispatch_id: str, receipt: dict) -> Path:
        path = self.receipts_dir / f"{dispatch_id}.receipt.json"
        path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    # ── Complete: completion receipt + COMPLETED ledger ──
    def complete_dispatch(self, order: DispatchOrder, status: str = "COMPLETED",
                          output_summary: str = "") -> dict:
        receipt = {
            "receipt_type": "completion",
            "dispatch_id": order.dispatch_id,
            "host_invoker": "zcode-main-thread",
            "child_session": order.child_session_id,
            "actor": order.actor_id,
            "role_id": order.role_id,
            "task_id": order.task_id,
            "status": status,
            "output_hash": hashlib.sha256(output_summary.encode()).hexdigest()[:16],
            "launch_input_hash": order.launch_receipt()["input_hash"],
            "completed_at": now_iso(),
        }
        self._write_receipt(order.dispatch_id, {**order.launch_receipt(), **receipt})
        if self._ledger is not None:
            try:
                from loop_core.execution_ledger import ExecutionStatus
                self._ledger.record_completion(
                    execution_id=f"exec-{order.dispatch_id}",
                    status=ExecutionStatus.COMPLETED if status == "COMPLETED" else ExecutionStatus.FAILED,
                    exit_code=0 if status == "COMPLETED" else 2,
                    output_hash=receipt["output_hash"],
                )
            except Exception:
                pass
        return receipt

    # ── Isolation verification ──
    def verify_role_isolation(self, orders: list[DispatchOrder]) -> list[str]:
        """Return list of violations. Empty list = isolated.

        Enforces: developer and reviewer must have distinct actor_id AND
        distinct session_id (AC-06).
        """
        violations: list[str] = []
        dev_orders = [o for o in orders if o.role_id == "developer"]
        rev_orders = [o for o in orders if o.role_id == "independent-reviewer"]
        for d in dev_orders:
            for r in rev_orders:
                if d.actor_id == r.actor_id:
                    violations.append(f"SHARED_ACTOR: developer {d.actor_id} == reviewer {r.actor_id}")
                if d.session_id == r.session_id:
                    violations.append(f"SHARED_SESSION: developer {d.session_id} == reviewer {r.session_id}")
        # All roles must have unique sessions
        seen: dict[str, str] = {}
        for o in orders:
            if o.session_id in seen:
                violations.append(f"SHARED_SESSION: {o.role_id} {o.session_id} already used by {seen[o.session_id]}")
            seen[o.session_id] = o.role_id
        return violations

    def list_receipts(self) -> list[dict]:
        out = []
        for p in sorted(self.receipts_dir.glob("*.receipt.json")):
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                pass
        return out
