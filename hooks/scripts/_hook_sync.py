#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_hook_sync.py — Plugin cache synchronization extracted from hook_common.py.

Implements auto_sync_to_plugin_cache: ensures local hook scripts are
synced to the ZCode plugin cache. This prevents deadlocks caused by
modifying local hooks without updating the cached copy that ZCode
actually executes.

v3.11.2 repair (T-0055E / F-0055-004):
  - Replaced mtime-only comparison with SHA-256 content hashing.
  - Added post-write hash verification.
  - Fixed plugin cache version directory selection.
"""

import hashlib
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def _sha256(path: Path) -> str:
    """Return SHA-256 hex digest of file contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy_verified(source: Path, target: Path) -> None:
    """Copy and verify — raises OSError if target hash does not match source."""
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(source), str(target))
    if _sha256(source) != _sha256(target):
        raise OSError(f"post-sync hash mismatch: {source} -> {target}")


def auto_sync_to_plugin_cache(project_root_path: Path) -> bool:
    """Sync local hook scripts to the ZCode plugin cache using content hashes.

    The sync is one-directional: local project -> plugin cache.
    Returns True if sync succeeded, False on any error (non-fatal).
    """
    try:
        zcode_plugins = _find_plugin_cache_dir()
        if zcode_plugins is None:
            return False

        loop_gov_cache = _find_loop_governance_version_dir(zcode_plugins)
        if loop_gov_cache is None:
            return False

        local_hooks = project_root_path / "hooks" / "scripts"
        if not local_hooks.is_dir():
            return False

        cache_hooks = loop_gov_cache / "hooks" / "scripts"
        cache_hooks.mkdir(parents=True, exist_ok=True)

        synced = 0
        for py_file in local_hooks.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            target = cache_hooks / py_file.name
            try:
                if not target.exists() or _sha256(py_file) != _sha256(target):
                    _copy_verified(py_file, target)
                    synced += 1
            except (OSError, PermissionError):
                pass  # Non-fatal: individual file sync failure

        if synced > 0:
            logger.debug("Synced %d hook script(s) to plugin cache (SHA-256 verified).", synced)
        return True
    except Exception:
        return False


def _find_plugin_cache_dir() -> Path | None:
    """Locate the ZCode plugin cache directory."""
    home = Path.home()
    cache_root = home / ".zcode" / "cli" / "plugins" / "cache" / "zcode-plugins-official"
    if cache_root.is_dir():
        return cache_root
    # Fallback
    for candidate in [
        home / ".zcode" / "cli" / "plugins" / "cache",
        home / ".zcode" / "plugins",
    ]:
        if candidate.is_dir():
            return candidate
    return None


def _find_loop_governance_version_dir(cache_root: Path) -> Path | None:
    """Select the latest loop-governance version directory with .zcode-plugin marker."""
    candidates = []
    for package_dir in cache_root.iterdir():
        if not package_dir.is_dir() or "loop-governance" not in package_dir.name.lower():
            continue
        versions = [
            child for child in package_dir.iterdir()
            if child.is_dir() and (child / ".zcode-plugin").exists()
        ]
        candidates.extend(versions or [package_dir])
    return max(candidates, key=lambda p: p.stat().st_mtime_ns) if candidates else None
