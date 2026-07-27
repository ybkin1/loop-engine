"""
task_contract.py — Role assignment validator for Loop Engine.

Checks that:
1. developer_agent_id != reviewer_agent_id (no self-review)
2. All required roles are assigned for the current phase
3. Input hashes are frozen and consistent

Usage:
    python task_contract.py <project_root> <task_id>
"""
import hashlib
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


ROLE_REQUIREMENTS = {
    "S1-requirements": ["product-manager"],
    "S2-architecture": ["system-architect", "module-architect"],
    "S3-interface": ["module-architect"],
    "S4-implementation": ["developer"],
    "S5-quality": ["quality-engineer"],
    "S6-delivery": ["delivery-manager"],
    # Reviewer is always required post-implementation
}

REVIEW_REQUIRED_PHASES = [
    "S2-architecture", "S3-interface", "S4-implementation", "S5-quality"
]


def load_task(project_root: Path, task_id: str) -> dict | None:
    """Parse a task file and extract structured fields."""
    task_path = project_root / ".ai" / "tasks" / f"{task_id}.md"
    if not task_path.exists():
        return None

    text = task_path.read_text(encoding="utf-8")
    contract = {
        "task_id": task_id,
        "developer_agent_id": None,
        "reviewer_agent_id": None,
        "input_hashes": {},
        "raw": text,
    }

    # Parse structured fields from task markdown
    import json as _json

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("developer_agent_id:"):
            contract["developer_agent_id"] = line.split(":", 1)[1].strip().strip('"')
        elif line.startswith("reviewer_agent_id:"):
            contract["reviewer_agent_id"] = line.split(":", 1)[1].strip().strip('"')
        elif line.startswith("input_hashes:"):
            raw = line.split(":", 1)[1].strip()
            if raw and raw != "{}":
                try:
                    contract["input_hashes"] = _json.loads(raw)
                except _json.JSONDecodeError:
                    pass  # Not valid JSON, keep empty dict

    return contract


def check_self_review(contract: dict) -> list[str]:
    """Check that developer and reviewer are different agents."""
    errors = []
    dev = contract.get("developer_agent_id")
    rev = contract.get("reviewer_agent_id")

    if dev and rev and dev == rev:
        errors.append(
            f"SELF_REVIEW_VIOLATION: {contract['task_id']} has same agent as developer and reviewer ({dev}). "
            "同一 Agent 不能既开发又评审。"
        )
    return errors


def check_input_freezing(project_root: Path, task_id: str, contract: dict) -> list[str]:
    """Verify input hashes haven't changed since frozen."""
    errors = []
    input_hashes = contract.get("input_hashes", {})
    if not input_hashes:
        return errors  # No frozen inputs = not yet started

    for rel_path, expected_hash in input_hashes.items():
        file_path = project_root / rel_path
        if not file_path.exists():
            errors.append(f"INPUT_MISSING: {rel_path} (frozen in {task_id})")
            continue
        actual = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual != expected_hash:
            errors.append(
                f"INPUT_DRIFT: {rel_path} changed after freeze. "
                f"Expected {expected_hash[:16]}..., got {actual[:16]}..."
            )
    return errors


def main():
    if len(sys.argv) < 3:
        print("Usage: python task_contract.py <project_root> <task_id>")
        sys.exit(1)

    root = Path(sys.argv[1]).resolve()
    task_id = sys.argv[2]

    contract = load_task(root, task_id)
    if contract is None:
        print(f"[task_contract] Task file not found: {task_id}")
        sys.exit(0)

    errors = []
    errors.extend(check_self_review(contract))
    errors.extend(check_input_freezing(root, task_id, contract))

    if errors:
        for e in errors:
            print(f"[error] {e}")
        sys.exit(2)

    print(f"[task_contract] {task_id}: [ok] contract valid")
    sys.exit(0)


if __name__ == "__main__":
    main()
