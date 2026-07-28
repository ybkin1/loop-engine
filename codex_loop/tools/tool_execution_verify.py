"""loop_execution_verify -- Verify execution ledger chain integrity."""
import sys
from pathlib import Path


def run(project_root: str = ".") -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from codex_loop.evidence.execution_ledger import ExecutionLedger

    root = Path(project_root)
    ledger = ExecutionLedger(root)
    valid, reason = ledger.verify_chain()

    return {
        "valid": valid,
        "reason": reason,
        "ledger_exists": ledger.exists,
    }
