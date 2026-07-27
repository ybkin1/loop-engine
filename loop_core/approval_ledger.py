"""
Approval Ledger — Structured approval records with integrity hash, TTL, and scope fingerprint.

Provides ApprovalRecord (per-user-approval dataclass) and ApprovalLedger (CRUD + validation
against gates.yaml). Does not replace gates.yaml; adds `approval` sub-records to existing gates.

Key design:
- scope_hash = SHA256(sorted allowed_paths + allowed_actions concatenated).
  If allowed_paths change after approval, hash changes -> approval invalidated (scope creep).
- is_valid() = decision==APPROVED AND not is_expired()
- Default TTL: 30 days from recorded_at.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import uuid
from pathlib import Path


# ── Enums ──────────────────────────────────────────────────────────────────


class Decision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    REPAIR_REQUESTED = "repair_requested"


class Source(str, Enum):
    EXPLICIT_MESSAGE = "explicit_user_message"
    INTERACTIVE_DIALOG = "interactive_dialog"


# ── Helpers ────────────────────────────────────────────────────────────────


def _short_uuid() -> str:
    """Generate a 12-character hex UUID fragment."""
    return uuid.uuid4().hex[:12]


def _sha256(content: str) -> str:
    """Return SHA-256 hex digest of the given content string."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _parse_datetime(dt_str: str) -> datetime:
    """Parse an ISO-8601 datetime string, normalising to UTC."""
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ── Approval Record ────────────────────────────────────────────────────────


@dataclass
class ApprovalRecord:
    """A single user-approval record bound to a gate.

    10 required fields: approval_id, gate_id, human_actor, decision, source,
    packet_hash, scope_hash, input_fingerprint, recorded_at, expiration.

    3 optional fields: approval_text, task_id, previous_approval_id.
    """

    approval_id: str          # "AR-{uuid12}"
    gate_id: str              # Linked gate ID (e.g. "G-T-0012-...")
    human_actor: str          # Always "user"
    decision: Decision
    source: Source
    packet_hash: str          # SHA-256 of the decision packet content
    scope_hash: str           # SHA-256 of sorted allowed_paths + allowed_actions
    input_fingerprint: str    # SHA-256 of de-identified user input
    recorded_at: str          # ISO-8601 with timezone
    expiration: str           # ISO-8601 with timezone (default +30 days)

    # Optional
    approval_text: str | None = None
    task_id: str | None = None
    previous_approval_id: str | None = None

    # ── Validity ──────────────────────────────────────────────────────

    def is_expired(self) -> bool:
        """Return True if the approval record has passed its expiration time."""
        now = datetime.now(timezone.utc)
        exp = _parse_datetime(self.expiration)
        return now >= exp

    def is_valid(self) -> bool:
        """Return True if the approval is both APPROVED and not expired."""
        return self.decision == Decision.APPROVED and not self.is_expired()

    # ── Factory ───────────────────────────────────────────────────────

    @staticmethod
    def create(
        gate_id: str,
        decision: Decision,
        source: Source,
        packet_content: str,
        scope_content: str,
        user_input: str,
        approval_text: str | None = None,
        task_id: str | None = None,
        ttl_days: int = 30,
    ) -> "ApprovalRecord":
        """Create a new ApprovalRecord with auto-computed hashes and timestamps.

        Args:
            gate_id: The gate this approval is for.
            decision: The user's decision (approved/rejected/repair_requested).
            source: How the decision was collected.
            packet_content: Full decision packet text (hashed into packet_hash).
            scope_content: Sorted allowed_paths + allowed_actions concatenated
                           (hashed into scope_hash).
            user_input: De-identified user input text (hashed into input_fingerprint).
            approval_text: Optional verbatim approval text from the user.
            task_id: Optional task ID for context.
            ttl_days: Number of days until expiration (default 30).
        """
        now = datetime.now(timezone.utc)
        approval_id = f"AR-{_short_uuid()}"
        recorded_at = now.isoformat()
        expiration = (now + timedelta(days=ttl_days)).isoformat()

        return ApprovalRecord(
            approval_id=approval_id,
            gate_id=gate_id,
            human_actor="user",
            decision=decision,
            source=source,
            packet_hash=_sha256(packet_content),
            scope_hash=_sha256(scope_content),
            input_fingerprint=_sha256(user_input),
            recorded_at=recorded_at,
            expiration=expiration,
            approval_text=approval_text,
            task_id=task_id,
            previous_approval_id=None,
        )


# ── Approval Ledger ────────────────────────────────────────────────────────


class ApprovalLedger:
    """Manages ApprovalRecord creation, validation, and persistence into gates.yaml.

    Each gate in gates.yaml may carry an optional ``approval`` sub-dict.
    ApprovalLedger reads/writes those sub-records without replacing the gates file.

    Usage::

        ledger = ApprovalLedger()
        record = ApprovalRecord.create(...)
        ledger.record_approval(record, Path(".ai/gates.yaml"))
        same = ledger.get_approval("G-T-0012-...", Path(".ai/gates.yaml"))
        expired = ledger.find_expired(Path(".ai/gates.yaml"))
    """

    # ── Persistence ───────────────────────────────────────────────────

    def record_approval(self, record: ApprovalRecord, gates_path: Path) -> None:
        """Write *record* into the ``approval`` sub-field of the matching gate.

        Reads gates.yaml, finds the gate by ``id``, adds/overwrites its
        ``approval`` key, then writes the entire document back.

        Raises:
            FileNotFoundError: if gates_path does not exist.
            ValueError: if no gate with ``record.gate_id`` is found.
        """
        import yaml

        if not gates_path.exists():
            raise FileNotFoundError(f"gates.yaml not found at {gates_path}")

        with open(gates_path, "r", encoding="utf-8") as fh:
            doc = yaml.safe_load(fh) or {}

        gates: list[dict] = doc.get("gates", [])
        found = False

        approval_block: dict[str, str | None] = {
            "approval_id": record.approval_id,
            "human_actor": record.human_actor,
            "decision": record.decision.value,
            "source": record.source.value,
            "packet_hash": record.packet_hash,
            "scope_hash": record.scope_hash,
            "input_fingerprint": record.input_fingerprint,
            "recorded_at": record.recorded_at,
            "expiration": record.expiration,
        }
        if record.approval_text is not None:
            approval_block["approval_text"] = record.approval_text
        if record.task_id is not None:
            approval_block["task_id"] = record.task_id
        if record.previous_approval_id is not None:
            approval_block["previous_approval_id"] = record.previous_approval_id

        for gate in gates:
            if gate.get("id") == record.gate_id:
                gate["approval"] = approval_block
                found = True
                break

        if not found:
            raise ValueError(
                f"Gate '{record.gate_id}' not found in {gates_path}"
            )

        doc["gates"] = gates
        with open(gates_path, "w", encoding="utf-8") as fh:
            yaml.dump(
                doc,
                fh,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

    def get_approval(
        self, gate_id: str, gates_path: Path
    ) -> ApprovalRecord | None:
        """Read the approval record for *gate_id* from gates.yaml.

        Returns None if the gate does not exist or has no ``approval`` sub-record.
        """
        import yaml

        if not gates_path.exists():
            return None

        with open(gates_path, "r", encoding="utf-8") as fh:
            doc = yaml.safe_load(fh) or {}

        gates: list[dict] = doc.get("gates", [])
        for gate in gates:
            if gate.get("id") == gate_id:
                approval_data = gate.get("approval")
                if not isinstance(approval_data, dict):
                    return None
                return ApprovalRecord(
                    approval_id=approval_data["approval_id"],
                    gate_id=gate_id,
                    human_actor=approval_data["human_actor"],
                    decision=Decision(approval_data["decision"]),
                    source=Source(approval_data["source"]),
                    packet_hash=approval_data["packet_hash"],
                    scope_hash=approval_data["scope_hash"],
                    input_fingerprint=approval_data["input_fingerprint"],
                    recorded_at=approval_data["recorded_at"],
                    expiration=approval_data["expiration"],
                    approval_text=approval_data.get("approval_text"),
                    task_id=approval_data.get("task_id"),
                    previous_approval_id=approval_data.get("previous_approval_id"),
                )
        return None

    # ── Validation ────────────────────────────────────────────────────

    def validate_scope(
        self, record: ApprovalRecord, current_scope: str
    ) -> bool:
        """Check whether *current_scope* matches the approved scope fingerprint.

        Returns True when the SHA-256 of *current_scope* equals
        ``record.scope_hash`` (no scope creep). Returns False on mismatch.
        """
        current_hash = _sha256(current_scope)
        return current_hash == record.scope_hash

    # ── Expiry scan ───────────────────────────────────────────────────

    def find_expired(self, gates_path: Path) -> list[str]:
        """Return a list of gate IDs whose approval records have expired.

        Scans every gate in gates.yaml and checks the ``expiration`` field
        of each embedded ``approval`` sub-record.
        """
        import yaml

        if not gates_path.exists():
            return []

        with open(gates_path, "r", encoding="utf-8") as fh:
            doc = yaml.safe_load(fh) or {}

        gates: list[dict] = doc.get("gates", [])
        now = datetime.now(timezone.utc)
        expired_ids: list[str] = []

        for gate in gates:
            approval_data = gate.get("approval")
            if not isinstance(approval_data, dict):
                continue
            exp_str = approval_data.get("expiration")
            if not exp_str:
                continue
            try:
                exp = _parse_datetime(exp_str)
                if now >= exp:
                    expired_ids.append(gate.get("id", ""))
            except (ValueError, TypeError):
                # Unparseable expiration — skip
                continue

        return expired_ids
