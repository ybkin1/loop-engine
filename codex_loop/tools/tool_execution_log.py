"""loop_execution_log — Query execution ledger entries."""
import sys
from pathlib import Path


def run(project_root: str = ".", task_id: str = None, role_id: str = None, recent: int = 10) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    ledger_path = Path(project_root) / ".ai" / "ledger" / "executions.jsonl"
    if not ledger_path.exists():
        return {"entries": [], "total": 0, "message": "No execution ledger found"}

    entries = []
    try:
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                import json
                entry = json.loads(line)
                if task_id and entry.get("task_id") != task_id:
                    continue
                if role_id and entry.get("role_id") != role_id:
                    continue
                entries.append(entry)
    except Exception as e:
        return {"error": str(e)}

    entries = entries[-recent:] if recent > 0 else entries
    return {"entries": entries, "total": len(entries)}
