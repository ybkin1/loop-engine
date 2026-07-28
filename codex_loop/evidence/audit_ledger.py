"""
Audit Ledger — Chain-hashed append-only JSONL audit log (v3.4).

Every entry:
- Is appended to .ai/audit_ledger.jsonl
- Contains the SHA256 hash of the previous entry (chain integrity)
- Records event type, actor, timestamp, and structured details

Verification detects tampering by walking the chain and comparing hashes.
Pattern adapted from Qoder's AuditLedger + ZCode's execution_ledger.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class AuditEntry:
    """A single audit log entry with chain hash."""
    seq: int
    timestamp: str
    event: str           # e.g., "gate_advance", "role_activate", "veto", "handoff"
    actor: str           # role_id or "system"
    details: dict[str, Any] = field(default_factory=dict)
    chain_hash: str = ""  # SHA256 of previous entry's JSON


@dataclass
class AuditIntegrity:
    """Result of verifying the audit ledger chain."""
    valid: bool
    total_entries: int
    first_invalid_seq: int | None = None
    message: str = ""


class AuditLedger:
    """Chain-hashed append-only JSONL audit log."""

    def __init__(self, filepath: str | Path):
        self._path = Path(filepath)
        self._entries: list[AuditEntry] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            for line in self._path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    data = json.loads(line)
                    self._entries.append(AuditEntry(**data))
        except (json.JSONDecodeError, OSError):
            pass

    @property
    def length(self) -> int:
        return len(self._entries)

    def append(self, event: str, actor: str, details: dict[str, Any] | None = None) -> AuditEntry:
        """Append a new entry with chain hash."""
        prev_hash = ""
        if self._entries:
            prev_json = json.dumps(self._entries[-1].__dict__, sort_keys=True, ensure_ascii=False)
            prev_hash = hashlib.sha256(prev_json.encode()).hexdigest()

        entry = AuditEntry(
            seq=len(self._entries),
            timestamp=datetime.now(timezone.utc).isoformat(),
            event=event,
            actor=actor,
            details=details or {},
            chain_hash=prev_hash,
        )

        self._entries.append(entry)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry.__dict__, ensure_ascii=False) + "\n"
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(line)

        return entry

    def verify_integrity(self) -> AuditIntegrity:
        """Verify chain integrity by recomputing all hashes."""
        if not self._entries:
            return AuditIntegrity(valid=True, total_entries=0, message="Empty ledger")

        prev_hash = ""
        for i, entry in enumerate(self._entries):
            expected_hash = entry.chain_hash
            if expected_hash != prev_hash:
                return AuditIntegrity(
                    valid=False,
                    total_entries=len(self._entries),
                    first_invalid_seq=i,
                    message=f"Chain broken at seq {i}: expected {prev_hash[:12]}..., got {expected_hash[:12]}...",
                )
            entry_json = json.dumps(entry.__dict__, sort_keys=True, ensure_ascii=False)
            prev_hash = hashlib.sha256(entry_json.encode()).hexdigest()

        return AuditIntegrity(
            valid=True,
            total_entries=len(self._entries),
            message=f"All {len(self._entries)} entries verified",
        )

    def recent(self, n: int = 10) -> list[AuditEntry]:
        return self._entries[-n:] if self._entries else []

    def find_by_event(self, event: str) -> list[AuditEntry]:
        """Find all entries matching a given event type."""
        return [e for e in self._entries if e.event == event]

    def find_by_actor(self, actor: str) -> list[AuditEntry]:
        """Find all entries created by a given actor."""
        return [e for e in self._entries if e.actor == actor]
