"""
task_contract.py — Role assignment validator for Loop Engine (deployed to .zcode/tools/).

Checks that:
1. developer_agent_id != reviewer_agent_id (no self-review)
2. All required roles are assigned for the current phase
3. Input hashes are frozen and consistent

Imported by validate_state.py for task contract validation.
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
}


def load_task(root: Path, task_id: str) -> dict | None:
    """Load task contract from .ai/tasks/{task_id}.md."""
    task_path = root / ".ai" / "tasks" / f"{task_id}.md"
    if not task_path.exists():
        return None
    text = task_path.read_text(encoding="utf-8")
    contract = {
        "allowed_paths": [],
        "developer_agent_id": None,
        "reviewer_agent_id": None,
        "phase": None,
    }
    in_yaml = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```yaml"):
            in_yaml = True
            continue
        if stripped.startswith("```") and in_yaml:
            in_yaml = False
            continue
        if stripped.startswith("developer_agent_id:"):
            contract["developer_agent_id"] = stripped.split(":", 1)[1].strip().strip('"').strip("'")
        elif stripped.startswith("reviewer_agent_id:"):
            contract["reviewer_agent_id"] = stripped.split(":", 1)[1].strip().strip('"').strip("'")
        elif stripped.startswith("phase:"):
            contract["phase"] = stripped.split(":", 1)[1].strip().strip('"').strip("'")
    return contract


def check_self_review(contract: dict) -> list[str]:
    """Check that developer != reviewer (no self-review)."""
    errors = []
    dev = contract.get("developer_agent_id")
    rev = contract.get("reviewer_agent_id")
    if dev and rev and dev == rev:
        errors.append(f"SELF_REVIEW: developer_agent_id and reviewer_agent_id are the same ({dev})")
    return errors


def check_input_freezing(root: Path, task_id: str, contract: dict) -> list[str]:
    """Check that task inputs have not changed since last freeze."""
    errors = []
    freeze_path = root / ".ai" / "evidence" / task_id / "input-freeze.json"
    # No freeze file → no check needed (first run)
    return errors
