"""
_hook_state.py — Governance state reading utilities extracted from hook_common.py.

Functions for reading .ai/state.yaml, .ai/gates.yaml, .ai/task_graph.yaml
and related governance state files.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import yaml
except ImportError:
    yaml = None

STATE_REL = Path(".ai") / "state.yaml"
GATES_REL = Path(".ai") / "gates.yaml"


def load_state(root: Path) -> dict:
    """Load .ai/state.yaml as a dict. Returns empty dict on missing/unreadable file.

    When PyYAML is unavailable, falls back to simple line-by-line key-value parsing
    (top-level scalar keys only — nested data like phases/completed_roles is lost).
    """
    sp = root / STATE_REL
    if not sp.exists():
        return {}
    if yaml is not None:
        try:
            with open(sp, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            pass
    # Fallback: line-by-line key-value scan
    state: dict = {}
    try:
        for line in sp.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if ":" in stripped and not stripped.startswith("#"):
                key, _, val = stripped.partition(":")
                val = val.strip().strip('"').strip("'")
                if val in ("null", "~", ""):
                    val = None
                state[key.strip()] = val
    except Exception:
        pass
    return state



# Sentinel for corrupted governance state (T-0052 — aligned with enforcement_hub._CORRUPT_SENTINEL)
_CORRUPT_SENTINEL = object()


def load_state_fail_closed(root: Path) -> dict:
    """Load state.yaml — FAIL CLOSED on corruption.

    Unlike load_state() which silently returns {} on error, this function
    raises an exception when the state file exists but cannot be parsed.
    Hooks that enforce governance decisions should use this function.
    Session brief hooks may use load_state() for non-blocking operation.
    """
    sp = root / STATE_REL
    if not sp.exists():
        return {}
    try:
        import yaml
        with open(sp, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        raise RuntimeError(f"Corrupted state.yaml: {e}") from e
def _naive_pending_scan(text: str) -> set[str]:
    """Quick scan for 'status: pending' lines in gates.yaml text."""
    pending: set[str] = set()
    current_id: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- id:"):
            current_id = stripped.split(":", 1)[1].strip().strip('"').strip("'")
        elif stripped.startswith("status:") and "pending" in stripped.lower() and current_id:
            pending.add(current_id)
    return pending


def pending_gates(root: Path) -> list[dict]:
    """Return all gates in .ai/gates.yaml whose status is 'pending'."""
    gp = root / GATES_REL
    if not gp.exists():
        return []
    try:
        if yaml is not None:
            with open(gp, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            gates = data.get("gates", []) if isinstance(data, dict) else []
            return [g for g in gates if isinstance(g, dict) and g.get("status") == "pending"]
        text = gp.read_text(encoding="utf-8")
        pending_ids = _naive_pending_scan(text)
        return [{"id": pid, "status": "pending"} for pid in pending_ids]
    except Exception:
        return []


def load_tasks_for_context(root: Path) -> list[dict]:
    """Load task list from .ai/task_graph.yaml for enforcement context."""
    tp = root / ".ai" / "task_graph.yaml"
    if not tp.exists() or yaml is None:
        return []
    try:
        with open(tp, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("tasks", []) if isinstance(data, dict) else []
    except Exception:
        return []


def load_gates_for_context(root: Path) -> dict:
    """Load gate data as {gate_id: status} dict for enforcement context."""
    gp = root / GATES_REL
    if not gp.exists() or yaml is None:
        return {}
    try:
        with open(gp, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        gates = data.get("gates", []) if isinstance(data, dict) else []
        return {g["id"]: g["status"] for g in gates if isinstance(g, dict) and g.get("id") and g.get("status")}
    except Exception:
        return {}


def load_phase_gates_for_context(root: Path) -> dict:
    """Build {Phase: gate_status} mapping for phase-gate enforcement."""
    gp = root / GATES_REL
    if not gp.exists() or yaml is None:
        return {}
    gt_map = {
        "requirements": "S1-requirements", "architecture": "S2-architecture",
        "interface": "S3-interface", "implementation": "S4-implementation",
        "quality": "S5-quality", "delivery": "S6-delivery",
        "integration": "S7-integration", "functional_test": "S8-functional-test",
        "fix_optimize": "S9-fix-optimize", "performance": "S10-performance",
        "maintenance": "S11-maintenance",
    }
    try:
        with open(gp, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        gates = data.get("gates", []) if isinstance(data, dict) else []
        result = {}
        for g in gates:
            if not isinstance(g, dict):
                continue
            gt = str(g.get("gate_type", "")).lower()
            gs = str(g.get("status", ""))
            if gt in gt_map and gs:
                phase = gt_map[gt]
                existing = result.get(phase)
                if existing is None or gs == "blocked":
                    result[phase] = gs
        return result
    except Exception:
        return {}
