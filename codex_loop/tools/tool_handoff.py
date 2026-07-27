"""loop_handoff — Create a handoff between roles."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def run(from_role: str, to_role: str, context_summary: str, project_root: str = ".",
        artifacts: list = None) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    root = Path(project_root)
    handoff_dir = root / ".ai" / "handoffs"
    handoff_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    handoff_id = f"handoff-{from_role}-to-{to_role}-{now[:10]}"

    record = {
        "handoff_id": handoff_id,
        "from_role": from_role,
        "to_role": to_role,
        "created_at": now,
        "artifacts": artifacts or [],
        "artifacts_count": len(artifacts or []),
        "context_summary": context_summary,
        "context_hash": hashlib.sha256(context_summary.encode()).hexdigest()[:16],
    }

    filepath = handoff_dir / f"{handoff_id}.json"
    filepath.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")

    return record
