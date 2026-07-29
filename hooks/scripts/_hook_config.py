#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_hook_config.py — Configuration loading utilities extracted from hook_common.py.

Functions for loading loop-governance config.yaml and determining
runtime behavior (fail-closed vs fail-open, exemption paths, etc.).
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import yaml
except ImportError:
    yaml = None

SKILL_REL_DIR = Path(".zcode") / "skills" / "loop-governance"

DEFAULT_CONFIG = {
    "hooks": {
        "fail_closed_on_error": True,
    },
    "gate_guard": {
        "enabled": True,
        "fail_on_state_error": "closed",
        "decision_recording_exempt": [".ai/gates.yaml"],
    },
    "path_guard": {
        "enabled": True,
        "decision": "ask",
        "protected_paths": [
            "AGENTS.md",
            "stable/",
            "registry/",
        ],
    },
    "role_isolation": {
        "enabled": True,
        "warn_incomplete_roles": True,
    },
    "loop_enforcement": {
        "enabled": True,
    },
}


def _merge(defaults: dict, override: dict) -> dict:
    """Shallow merge: override keys take precedence."""
    result = dict(defaults)
    if isinstance(override, dict):
        result.update(override)
    return result


def load_config(root: Path) -> dict:
    """Load loop-governance config.yaml, merging with DEFAULT_CONFIG.

    Returns DEFAULT_CONFIG if config file is missing or unreadable.
    """
    cfg_path = root / SKILL_REL_DIR / "config.yaml"
    if not cfg_path.exists() or yaml is None:
        return dict(DEFAULT_CONFIG)
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return dict(DEFAULT_CONFIG)
    if not isinstance(data, dict):
        return dict(DEFAULT_CONFIG)
    # Merge each section
    result = dict(DEFAULT_CONFIG)
    for section in DEFAULT_CONFIG:
        if section in data and isinstance(data[section], dict):
            result[section] = _merge(DEFAULT_CONFIG[section], data[section])
    return result


def should_fail_closed(root: Path) -> bool:
    """Determine whether the hook should fail-closed on errors.

    Reads config.yaml to check fail_closed_on_error setting.
    Defaults to True (fail-closed) if config is unavailable.
    """
    try:
        cfg = load_config(root)
        hooks_cfg = cfg.get("hooks", {})
        return hooks_cfg.get("fail_closed_on_error", True)
    except Exception:
        return True  # Fail-closed is the safe default
