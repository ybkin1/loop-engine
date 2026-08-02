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

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Any


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


def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


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
    # T-0104 设计-4：用户理解确认（Human Review Packet"理解确认"节答对全部问题 → True；
    # 拒绝回答 → False；存量记录无此键 → None = 未采集）。USER_ACCEPTED 前须为 True。
    user_comprehension_confirmed: bool | None = None

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
        user_comprehension_confirmed: bool | None = None,
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
            user_comprehension_confirmed=user_comprehension_confirmed,
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
        if record.user_comprehension_confirmed is not None:
            approval_block["user_comprehension_confirmed"] = (
                record.user_comprehension_confirmed
            )

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
                    user_comprehension_confirmed=approval_data.get(
                        "user_comprehension_confirmed"
                    ),
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


# ── AI Decision Record (T-0104 设计-3 §3.3.4) ─────────────────────────────


@dataclass
class AiDecisionRecord:
    """AI 自决决策记录——[AI判断] 的结构化落盘位。

    D-03 设计-3 §3.3.4 候选代码。与 ApprovalRecord 语义严格隔离：
    ApprovalRecord 记录"用户批准"（human_actor 恒为 "user"）；本记录记录
    "AI 替用户做的关键决定"，不混入 human_actor 语义（evidence ≠ approval）。
    """

    decision_id: str        # "AD-{uuid12}"（与 ApprovalRecord approval_id 同风格）
    task_id: str            # T-XXXX
    phase: str              # S4-implementation
    role_id: str            # 做出决策的角色（developer/main-thread）
    decision: str           # [AI判断] 内容
    why_not_ask: str        # R10 判断依据（为什么没有问用户）
    impact_if_wrong: str    # 错误影响与回滚路径
    reason_ref: str | None = None   # 关联 deviation_id（D-03 §3.3.1）或 gate_id
    recorded_at: str = field(default_factory=_utc_now_iso)  # ISO-8601 UTC

    @staticmethod
    def create(
        task_id: str,
        phase: str,
        role_id: str,
        decision: str,
        why_not_ask: str,
        impact_if_wrong: str,
        reason_ref: str | None = None,
    ) -> "AiDecisionRecord":
        """Create a new AiDecisionRecord with auto-generated id and timestamp."""
        return AiDecisionRecord(
            decision_id=f"AD-{_short_uuid()}",
            task_id=task_id,
            phase=phase,
            role_id=role_id,
            decision=decision,
            why_not_ask=why_not_ask,
            impact_if_wrong=impact_if_wrong,
            reason_ref=reason_ref,
            recorded_at=_utc_now_iso(),
        )

    def to_json_row(self) -> str:
        """Serialize to the JSONL row (without chain_hash)."""
        return json.dumps({
            "decision_id": self.decision_id,
            "task_id": self.task_id,
            "phase": self.phase,
            "role_id": self.role_id,
            "decision": self.decision,
            "why_not_ask": self.why_not_ask,
            "impact_if_wrong": self.impact_if_wrong,
            "reason_ref": self.reason_ref,
            "recorded_at": self.recorded_at,
        }, sort_keys=True, ensure_ascii=False)

    @classmethod
    def from_json_row(cls, data: dict[str, Any]) -> "AiDecisionRecord":
        return cls(
            decision_id=data["decision_id"],
            task_id=data["task_id"],
            phase=data["phase"],
            role_id=data["role_id"],
            decision=data["decision"],
            why_not_ask=data["why_not_ask"],
            impact_if_wrong=data["impact_if_wrong"],
            reason_ref=data.get("reason_ref"),
            recorded_at=data["recorded_at"],
        )


class AiDecisionLedger:
    """AI 决策记录账本：链式 JSONL 追加写（.ai/ledger/ai-decisions.jsonl）。

    与 executions.jsonl 完全相同的链契约（D-03 §3.3.4 第一层）：
    chain_hash = SHA256(上一条.chain_hash || 本条不含 chain_hash 的 JSON 行)。
    Root seed 与 ExecutionLedger / ledger_guard 相同——ledger_guard 对
    .ai/ledger/ 全目录的追加+链校验（hooks/scripts/ledger_guard.py）自动覆盖
    本文件，零 hook 改动。空文件 = 空链 = 合法（空链 verify 返回 True）。
    """

    CHAIN_HASH_KEY = "chain_hash"
    _ROOT_SEED = b"LOOP_ENGINE_EXECUTION_LEDGER_V1_ROOT"  # 与 execution_ledger 一致

    def __init__(self, project_root: Path | str) -> None:
        self._root = Path(project_root)
        self._ledger_path = self._root / ".ai" / "ledger" / "ai-decisions.jsonl"

    @property
    def exists(self) -> bool:
        return self._ledger_path.exists()

    @property
    def path(self) -> Path:
        return self._ledger_path

    def _ensure_dir(self) -> None:
        self._ledger_path.parent.mkdir(parents=True, exist_ok=True)

    def _root_hash(self) -> str:
        return hashlib.sha256(self._ROOT_SEED).hexdigest()

    def _last_chain_hash(self) -> str:
        entries = self.read_all()
        if entries:
            return entries[-1][self.CHAIN_HASH_KEY]
        return self._root_hash()

    def _compute_chain_hash(self, prev_hash: str, row_json: str) -> str:
        return hashlib.sha256(
            prev_hash.encode() + row_json.encode("utf-8")
        ).hexdigest()

    # ── 读取 ──────────────────────────────────────────────────────────

    def read_all(self) -> list[dict[str, Any]]:
        if not self.exists:
            return []
        entries: list[dict[str, Any]] = []
        with open(self._ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entries.append(json.loads(line))
        return entries

    def read_records(self) -> list[AiDecisionRecord]:
        return [AiDecisionRecord.from_json_row(e) for e in self.read_all()]

    # ── 写入（物理追加，不改已有行）────────────────────────────────

    def append(self, record: AiDecisionRecord) -> str:
        """Append one AI decision record; returns the new chain_hash."""
        self._ensure_dir()
        row_json = record.to_json_row()
        prev = self._last_chain_hash()
        ch = self._compute_chain_hash(prev, row_json)

        row_data = json.loads(row_json)
        row_data[self.CHAIN_HASH_KEY] = ch
        full = json.dumps(row_data, sort_keys=True, ensure_ascii=False)

        with open(self._ledger_path, "a", encoding="utf-8") as f:
            f.write(full + "\n")
            f.flush()
            os.fsync(f.fileno())
        return ch

    # ── 验证与查询 ───────────────────────────────────────────────────

    def verify_chain(self) -> tuple[bool, str]:
        """Verify the whole chain. Returns (valid, reason). Empty chain = True."""
        entries = self.read_all()
        if not entries:
            return True, "empty ledger"

        prev = self._root_hash()
        for i, entry in enumerate(entries, 1):
            stored = entry.pop(self.CHAIN_HASH_KEY, None)
            if stored is None:
                return False, f"line {i}: missing chain_hash"
            row_json = json.dumps(entry, sort_keys=True, ensure_ascii=False)
            computed = self._compute_chain_hash(prev, row_json)
            if computed != stored:
                return False, (
                    f"line {i}: mismatch — "
                    f"computed {computed[:16]}..., stored {stored[:16]}..."
                )
            prev = stored
        return True, f"chain verified ({len(entries)} entries)"

    def find_by_task(self, task_id: str) -> list[AiDecisionRecord]:
        return [r for r in self.read_records() if r.task_id == task_id]
