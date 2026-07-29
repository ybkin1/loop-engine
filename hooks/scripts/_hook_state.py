#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_hook_state.py — Governance state reading utilities extracted from hook_common.py.

Functions for reading .ai/state.yaml, .ai/gates.yaml, .ai/task_graph.yaml
and related governance state files.

v3.11.2 repair (T-0055E / F-0055-002):
  - Unified error semantics: load_state / load_gates / load_tasks now return
    (data, error) tuples so callers can distinguish "missing file",
    "parse error", and "empty but valid".
  - Empty collections no longer silently degrade to the same value as error.
  - All readers use the same fail-open / fail-closed contract.
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
TASKS_REL = Path(".ai") / "task_graph.yaml"

# ── Error sentinels ────────────────────────────────────────────────────────
ERR_MISSING = "MISSING_FILE"
ERR_PARSE = "PARSE_ERROR"
ERR_NO_YAML = "NO_YAML_LIBRARY"


def load_state(root: Path) -> tuple[dict, str | None]:
    """Load .ai/state.yaml. Returns (data, error_sentinel).

    data: dict (empty on error, {} on missing file — callers must check error_sentinel).
    error_sentinel: None on success, ERR_MISSING / ERR_PARSE / ERR_NO_YAML otherwise.
    """
    sp = root / STATE_REL
    if not sp.exists():
        return {}, ERR_MISSING
    if yaml is None:
        return _fallback_parse(sp), ERR_NO_YAML
    try:
        with open(sp, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            return {}, ERR_PARSE
        return data, None
    except Exception:
        try:
            return _fallback_parse(sp), ERR_PARSE
        except Exception:
            return {}, ERR_PARSE


def load_gates(root: Path) -> tuple[list[dict], str | None]:
    """Load gates from .ai/gates.yaml. Returns (gates_list, error_sentinel)."""
    gp = root / GATES_REL
    if not gp.exists():
        return [], ERR_MISSING
    if yaml is None:
        return [], ERR_NO_YAML
    try:
        with open(gp, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        gates = data.get("gates", [])
        if not isinstance(gates, list):
            return [], ERR_PARSE
        return gates, None
    except Exception:
        return [], ERR_PARSE


def load_tasks(root: Path) -> tuple[list[dict], str | None]:
    """Load tasks from .ai/task_graph.yaml. Returns (tasks_list, error_sentinel)."""
    tp = root / TASKS_REL
    if not tp.exists():
        return [], ERR_MISSING
    if yaml is None:
        return [], ERR_NO_YAML
    try:
        with open(tp, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        tasks = data.get("tasks", [])
        if not isinstance(tasks, list):
            return [], ERR_PARSE
        return tasks, None
    except Exception:
        return [], ERR_PARSE


def pending_gates(root: Path) -> list[str]:
    """Return list of gate IDs with status == "pending" in gates.yaml.

    Returns empty list on file missing / parse error / no pending gates.
    Callers should use load_gates() directly if they need to distinguish
    "no pending gates" from "could not read gates".
    """
    gates, err = load_gates(root)
    if err is not None:
        return []
    return [g["id"] for g in gates if isinstance(g, dict) and g.get("status") == "pending"]


def current_task_id(root: Path) -> str | None:
    """Extract current_task_id from state.yaml. Returns None on any error."""
    state, err = load_state(root)
    if err is not None:
        return None
    tid = state.get("current_task_id")
    return tid if tid and tid != "null" else None


# ── Internal helpers ──────────────────────────────────────────────────────

def _fallback_parse(sp: Path) -> dict:
    """Line-by-line key-value parsing for top-level scalar keys only."""
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
    except Exception as _e:
        import logging; logging.getLogger("hook_state").debug("State read degraded: %s", _e)
    return state
