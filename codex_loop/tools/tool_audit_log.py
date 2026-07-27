"""loop_audit_log — Append and verify chain-hashed audit ledger entries."""
import sys
from pathlib import Path


def run(event: str, actor: str, project_root: str = ".", details: dict = None, verify: bool = False) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from codex_loop.core.audit_ledger import AuditLedger

    ledger_path = Path(project_root) / ".ai" / "audit_ledger.jsonl"

    if verify:
        ledger = AuditLedger(str(ledger_path))
        integrity = ledger.verify_integrity()
        return {
            "verified": integrity.valid,
            "total_entries": integrity.total_entries,
            "message": integrity.message,
            "first_invalid_seq": integrity.first_invalid_seq,
        }

    ledger = AuditLedger(str(ledger_path))
    entry = ledger.append(event=event, actor=actor, details=details or {})
    return {
        "appended": True,
        "seq": entry.seq,
        "timestamp": entry.timestamp,
        "event": entry.event,
        "actor": entry.actor,
        "chain_hash": entry.chain_hash[:16] + "...",
    }
