"""
sync_plugin_cache.py — Sync project hook scripts and config to ZCode plugin cache.

Usage: python .zcode/tools/sync_plugin_cache.py <project_root>
"""
import shutil
import sys
from pathlib import Path


def find_plugin_cache() -> Path | None:
    home = Path.home()
    cache_root = home / ".zcode" / "cli" / "plugins" / "cache" / "zcode-plugins-official"
    if cache_root.exists():
        for d in cache_root.iterdir():
            if d.is_dir() and "loop-governance" in d.name.lower():
                return d
    return None

def sync_hook_scripts(project_root: Path, cache_dir: Path) -> int:
    local = project_root / "hooks" / "scripts"
    if not local.is_dir():
        return 0
    cache = cache_dir / "hooks" / "scripts"
    cache.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in local.glob("*.py"):
        if f.name.startswith("__"):
            continue
        t = cache / f.name
        if not t.exists() or f.stat().st_mtime > t.stat().st_mtime:
            shutil.copy2(str(f), str(t))
            n += 1
    if n:
        print(f"[sync] {n} hook scripts synced.")
    return 0

def sync_config(project_root: Path, cache_dir: Path) -> int:
    local = project_root / ".zcode" / "skills" / "loop-governance"
    if not local.is_dir():
        return 0
    cache = cache_dir / "skills" / "loop-governance"
    cache.mkdir(parents=True, exist_ok=True)
    n = 0
    for src, dst in [
        (local / "config.yaml", cache / "config.yaml"),
    ]:
        if src.exists() and (not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime):
            shutil.copy2(str(src), str(dst))
            n += 1
    tmpl_src = local / "templates"
    tmpl_dst = cache / "templates"
    if tmpl_src.is_dir():
        tmpl_dst.mkdir(parents=True, exist_ok=True)
        for f in tmpl_src.glob("*.md"):
            t = tmpl_dst / f.name
            if not t.exists() or f.stat().st_mtime > t.stat().st_mtime:
                shutil.copy2(str(f), str(t))
            n += 1
    if n:
        print(f"[sync] {n} config/template files synced.")
    return 0

def main():
    if len(sys.argv) < 2:
        print("Usage: python sync_plugin_cache.py <project_root>")
        sys.exit(1)
    root = Path(sys.argv[1]).resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory")
        sys.exit(1)
    cache = find_plugin_cache()
    if cache is None:
        print("[sync] Plugin cache not found. Install: zcode plugin install loop-governance")
        sys.exit(1)
    print(f"[sync] From: {root}")
    print(f"[sync] To:   {cache}")
    e = sync_hook_scripts(root, cache) + sync_config(root, cache)
    sys.exit(0 if e == 0 else 2)

if __name__ == "__main__":
    main()
