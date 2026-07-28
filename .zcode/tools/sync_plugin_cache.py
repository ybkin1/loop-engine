#!/usr/bin/env python3
"""
sync_plugin_cache.py — Sync project hook scripts and config to ZCode plugin cache.

Usage: python .zcode/tools/sync_plugin_cache.py <project_root>
"""
import hashlib
import shutil
import sys
from pathlib import Path


# The project checkout is the source of truth.  These runtime files are loaded
# from the plugin cache by some ZCode sessions, so mtime-only hook syncing is
# insufficient for them.
RUNTIME_FILES = (
    (Path("tools") / "server.py", Path("tools") / "server.py"),
    (Path("loop_core") / "role_capability.py", Path("loop_core") / "role_capability.py"),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy_verified(source: Path, target: Path) -> None:
    """Copy a source-of-truth file and fail if the cache is not identical."""
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(source), str(target))
    if _sha256(source) != _sha256(target):
        raise OSError(f"post-sync hash mismatch: {source} -> {target}")

def find_plugin_cache() -> Path | None:
    home = Path.home()
    cache_root = home / ".zcode" / "cli" / "plugins" / "cache" / "zcode-plugins-official"
    if not cache_root.exists():
        return None
    candidates = []
    for package_dir in cache_root.iterdir():
        if not package_dir.is_dir() or "loop-governance" not in package_dir.name.lower():
            continue
        versions = [
            child for child in package_dir.iterdir()
            if child.is_dir() and (child / ".zcode-plugin").exists()
        ]
        candidates.extend(versions or [package_dir])
    return max(candidates, key=lambda path: path.stat().st_mtime_ns) if candidates else None

def sync_hook_scripts(project_root: Path, cache_dir: Path) -> int:
    local = project_root / "hooks" / "scripts"
    if not local.is_dir(): return 0
    cache = cache_dir / "hooks" / "scripts"
    cache.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in local.glob("*.py"):
        if f.name.startswith("__"): continue
        t = cache / f.name
        if not t.exists() or _sha256(f) != _sha256(t):
            _copy_verified(f, t); n += 1
    if n: print(f"[sync] {n} hook scripts synced.")
    return n


def sync_runtime_files(project_root: Path, cache_dir: Path) -> int:
    """Synchronize cache copies of runtime files using content hashes."""
    n = 0
    for source_rel, target_rel in RUNTIME_FILES:
        source = project_root / source_rel
        target = cache_dir / target_rel
        if not source.is_file():
            continue
        if not target.exists() or _sha256(source) != _sha256(target):
            _copy_verified(source, target)
            n += 1
    if n:
        print(f"[sync] {n} runtime files synced and verified.")
    return n

def sync_config(project_root: Path, cache_dir: Path) -> int:
    local = project_root / ".zcode" / "skills" / "loop-governance"
    if not local.is_dir(): return 0
    cache = cache_dir / "skills" / "loop-governance"
    cache.mkdir(parents=True, exist_ok=True)
    n = 0
    for src, dst in [
        (local / "config.yaml", cache / "config.yaml"),
    ]:
        if src.exists() and (not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime):
            shutil.copy2(str(src), str(dst)); n += 1
    tmpl_src = local / "templates"
    tmpl_dst = cache / "templates"
    if tmpl_src.is_dir():
        tmpl_dst.mkdir(parents=True, exist_ok=True)
        for f in tmpl_src.glob("*.md"):
            t = tmpl_dst / f.name
            if not t.exists() or f.stat().st_mtime > t.stat().st_mtime:
                shutil.copy2(str(f), str(t)); n += 1
    if n: print(f"[sync] {n} config/template files synced.")
    return n

def main():
    if len(sys.argv) < 2:
        print("Usage: python sync_plugin_cache.py <project_root>"); sys.exit(1)
    root = Path(sys.argv[1]).resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory"); sys.exit(1)
    cache = find_plugin_cache()
    if cache is None:
        print("[sync] Plugin cache not found. Install: zcode plugin install loop-governance")
        sys.exit(1)
    print(f"[sync] From: {root}")
    print(f"[sync] To:   {cache}")
    e = sync_hook_scripts(root, cache) + sync_runtime_files(root, cache) + sync_config(root, cache)
    sys.exit(0 if e == 0 else 2)

if __name__ == "__main__":
    main()
