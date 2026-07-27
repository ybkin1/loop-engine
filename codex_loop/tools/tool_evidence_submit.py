"""loop_evidence_submit — Submit evidence with hash binding."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def run(evidence_id: str, evidence_type: str, content: str, project_root: str = ".",
        role_id: str = None, gate_id: str = None, ttl_seconds: int = None) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    root = Path(project_root)
    evidence_dir = root / ".ai" / "evidence" / "submitted"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    content_hash = hashlib.sha256(content.encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()

    record = {
        "evidence_id": evidence_id,
        "type": evidence_type,
        "content_hash": content_hash,
        "submitted_at": now,
        "role_id": role_id,
        "gate_id": gate_id,
        "ttl_seconds": ttl_seconds,
    }

    filepath = evidence_dir / f"{evidence_id}.json"
    filepath.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "submitted": True,
        "evidence_id": evidence_id,
        "content_hash": content_hash[:16] + "...",
        "stored_at": str(filepath),
    }
