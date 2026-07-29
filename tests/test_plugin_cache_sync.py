from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SYNC_PATH = PROJECT_ROOT / ".zcode" / "tools" / "sync_plugin_cache.py"


def _load_sync_module():
    spec = importlib.util.spec_from_file_location("sync_plugin_cache", SYNC_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── Runtime file sync tests ──────────────────────────────────────────────

def test_runtime_files_sync_by_hash_even_when_cache_mtime_is_newer(tmp_path):
    """Stale-mtime: cache mtime is newer but hash differs — must still sync."""
    sync = _load_sync_module()
    cache = tmp_path / "cache"
    for relative in (Path("tools/server.py"), Path("loop_core/role_capability.py")):
        source = PROJECT_ROOT / relative
        target = cache / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("stale cache copy", encoding="utf-8")
        target.touch()

    assert sync.sync_runtime_files(PROJECT_ROOT, cache) == 2
    for relative in (Path("tools/server.py"), Path("loop_core/role_capability.py")):
        assert _sha256(PROJECT_ROOT / relative) == _sha256(cache / relative)
    assert sync.sync_runtime_files(PROJECT_ROOT, cache) == 0


def test_runtime_sync_post_write_hash_verification_detects_mismatch(tmp_path, monkeypatch):
    """Hash mismatch after copy must raise OSError."""
    sync = _load_sync_module()
    source = PROJECT_ROOT / "tools" / "server.py"
    target = tmp_path / "tools" / "server.py"

    def corrupt_copy(src, dst):
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        Path(dst).write_text("corrupted", encoding="utf-8")

    monkeypatch.setattr(sync.shutil, "copy2", corrupt_copy)
    try:
        sync._copy_verified(source, target)
    except OSError as exc:
        assert "post-sync hash mismatch" in str(exc)
    else:
        raise AssertionError("expected post-sync hash verification failure")


def test_runtime_sync_idempotent_no_redundant_writes(tmp_path):
    """Second sync after successful sync must return 0."""
    sync = _load_sync_module()
    cache = tmp_path / "cache"

    count1 = sync.sync_runtime_files(PROJECT_ROOT, cache)
    assert count1 >= 1

    count2 = sync.sync_runtime_files(PROJECT_ROOT, cache)
    assert count2 == 0, f"expected idempotent sync (0), got {count2}"


# ── Hook scripts sync tests ───────────────────────────────────────────────

def test_hook_scripts_sync_by_hash_skips_identical_cache(tmp_path):
    """Hook scripts with identical hash must not re-sync even when cache newer."""
    import shutil

    sync = _load_sync_module()
    project = tmp_path / "project"
    cache = tmp_path / "cache"
    scripts_dir = project / "hooks" / "scripts"
    scripts_dir.mkdir(parents=True)

    script = scripts_dir / "demo_hook.py"
    script.write_text("print('hello')\n", encoding="utf-8")

    cache_script = cache / "hooks" / "scripts" / "demo_hook.py"
    cache_script.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(script), str(cache_script))
    cache_script.touch()

    assert sync.sync_hook_scripts(project, cache) == 0


def test_hook_scripts_sync_by_hash_detects_content_change(tmp_path):
    """Hook scripts with different hash must sync regardless of mtime."""
    sync = _load_sync_module()
    project = tmp_path / "project"
    cache = tmp_path / "cache"
    scripts_dir = project / "hooks" / "scripts"
    scripts_dir.mkdir(parents=True)

    script = scripts_dir / "demo_hook.py"
    script.write_text("print('new')\n", encoding="utf-8")

    cache_script = cache / "hooks" / "scripts" / "demo_hook.py"
    cache_script.parent.mkdir(parents=True, exist_ok=True)
    cache_script.write_text("print('old')\n", encoding="utf-8")

    assert sync.sync_hook_scripts(project, cache) == 1
    assert _sha256(script) == _sha256(cache_script)


# ── Plugin cache discovery tests ──────────────────────────────────────────

def test_find_plugin_cache_returns_none_when_no_cache(tmp_path, monkeypatch):
    """When no plugin cache exists, find_plugin_cache must return None."""
    sync = _load_sync_module()

    def fake_home():
        return tmp_path / "no-such-home"

    monkeypatch.setattr(sync.Path, "home", fake_home)
    assert sync.find_plugin_cache() is None


def test_find_plugin_cache_selects_version_with_dot_zcode_plugin_marker(tmp_path, monkeypatch):
    """Version directory with .zcode-plugin marker should be preferred."""
    import time
    sync = _load_sync_module()

    home = tmp_path / "home"
    cache_root = home / ".zcode" / "cli" / "plugins" / "cache" / "zcode-plugins-official"
    pkg = cache_root / "loop-governance"
    v1 = pkg / "1.0.0"
    v2 = pkg / "2.0.0"
    v1.mkdir(parents=True)
    (v1 / ".zcode-plugin").write_text("{}")
    time.sleep(0.1)  # ensure v2 has a visibly newer st_mtime_ns
    v2.mkdir(parents=True)
    (v2 / ".zcode-plugin").write_text("{}")

    def fake_home():
        return home

    monkeypatch.setattr(sync.Path, "home", fake_home)
    result = sync.find_plugin_cache()
    assert result is not None
    assert result.name == "2.0.0"


# ── Source-of-truth integrity tests ───────────────────────────────────────

def test_copy_verified_preserves_file_content(tmp_path):
    """Normal copy must produce hash-identical target."""
    sync = _load_sync_module()
    source = tmp_path / "source.txt"
    target = tmp_path / "dest" / "target.txt"
    source.write_text("hello world\n", encoding="utf-8")

    sync._copy_verified(source, target)
    assert _sha256(source) == _sha256(target)


def test_sync_skips_missing_source_file(tmp_path):
    """Missing source files must be skipped without error."""
    sync = _load_sync_module()
    cache = tmp_path / "cache"
    project = tmp_path / "empty_project"
    project.mkdir()

    result = sync.sync_runtime_files(project, cache)
    assert result == 0
