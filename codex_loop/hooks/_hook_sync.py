"""
_hook_sync.py — Plugin cache synchronization extracted from hook_common.py.

Implements auto_sync_to_plugin_cache: ensures local hook scripts are
synced to the ZCode plugin cache. This prevents deadlocks caused by
modifying local hooks without updating the cached copy that ZCode
actually executes.
"""

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def auto_sync_to_plugin_cache(project_root_path: Path) -> bool:
    """Sync local hook scripts to the ZCode plugin cache.

    When hooks are updated locally, the plugin cache may contain stale
    copies. ZCode loads hooks from the cache, not the project directory,
    so modifications to local hook scripts must be synced.

    The sync is one-directional: local project -> plugin cache.
    Returns True if sync succeeded, False on any error (non-fatal).

    This function is called at the start of loop_enforcement.main() to
    ensure the running hooks are always up-to-date with the local scripts.
    """
    try:
        # Locate plugin cache directory
        zcode_plugins = _find_plugin_cache_dir()
        if zcode_plugins is None:
            return False

        loop_gov_cache = zcode_plugins / "loop-governance"
        if not loop_gov_cache.exists():
            return False

        # Source: local hook scripts directory
        local_hooks = project_root_path / "hooks" / "scripts"
        if not local_hooks.is_dir():
            return False

        # Target: plugin cache hooks directory
        cache_hooks = loop_gov_cache / "hooks" / "scripts"
        cache_hooks.mkdir(parents=True, exist_ok=True)

        synced = 0
        for py_file in local_hooks.glob("*.py"):
            target = cache_hooks / py_file.name
            try:
                # Only sync if local is newer or target missing
                if not target.exists() or py_file.stat().st_mtime > target.stat().st_mtime:
                    shutil.copy2(str(py_file), str(target))
                    synced += 1
            except OSError:
                pass  # Non-fatal: individual file sync failure

        if synced > 0:
            logger.debug("Synced %d hook script(s) to plugin cache.", synced)
        return True
    except Exception:
        return False


def _find_plugin_cache_dir() -> Path | None:
    """Locate the ZCode plugin cache directory.

    Searches standard locations:
    1. ~/.zcode/cli/plugins/cache/
    2. ~/.zcode/plugins/
    """
    home = Path.home()
    candidates = [
        home / ".zcode" / "cli" / "plugins" / "cache",
        home / ".zcode" / "plugins",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None
