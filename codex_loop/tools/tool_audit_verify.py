"""loop_audit_verify -- Verify chain-hashed audit ledger integrity."""
import sys
from pathlib import Path


def run(project_root: str = ".") -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from codex_loop.evidence.audit_ledger import AuditLedger

    root = Path(project_root)
    ledger_path = root / ".ai" / "audit_ledger.jsonl"
    ledger = AuditLedger(ledger_path)
    integrity = ledger.verify_integrity()

    return {
        "valid": integrity.valid,
        "total_entries": integrity.total_entries,
        "first_invalid_seq": integrity.first_invalid_seq,
        "message": integrity.message,
    }
