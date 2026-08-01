"""
test_version_consistency.py — Verify version consistency across project files (T-0046).

Checks that pyproject.toml is the single source of truth and all other files
declare consistent versions.
"""
import os
import re
import json
import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")


def _read(rel_path):
    full = os.path.join(PROJECT_ROOT, rel_path)
    if not os.path.exists(full):
        return None
    with open(full, "r", encoding="utf-8") as f:
        return f.read()


def _get_pyproject_version():
    content = _read("pyproject.toml")
    assert content is not None, "pyproject.toml not found"
    m = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    assert m, "version not found in pyproject.toml"
    return m.group(1)


class TestVersionConsistency:
    def test_pyproject_version_exists(self):
        version = _get_pyproject_version()
        assert version, "pyproject.toml version is empty"

    def test_readme_version_matches(self):
        expected = _get_pyproject_version()
        content = _read("README.md")
        assert content is not None, "README.md not found"
        # Look for version pattern like **v3.0.0**
        m = re.search(r'\*\*v?(\d+\.\d+\.\d+)\*\*', content)
        assert m, "version not found in README.md"
        assert m.group(1) == expected, (
            f"README.md version {m.group(1)} != pyproject.toml {expected}"
        )

    def test_loop_engine_init_version(self):
        expected = _get_pyproject_version()
        content = _read("src/loop_engine/__init__.py")
        assert content is not None, "src/loop_engine/__init__.py not found"
        m = re.search(r'__version__\s*=\s*"([^"]+)"', content)
        assert m, "__version__ not found in src/loop_engine/__init__.py"
        assert m.group(1) == expected, (
            f"src/loop_engine/__init__.py version {m.group(1)} != pyproject.toml {expected}"
        )

    def test_plugin_json_version(self):
        expected = _get_pyproject_version()
        content = _read(".zcode-plugin/plugin.json")
        assert content is not None, ".zcode-plugin/plugin.json not found"
        data = json.loads(content)
        actual = data.get("version", "")
        assert actual == expected, (
            f"plugin.json version {actual} != pyproject.toml {expected}"
        )

    def test_version_manifest_exists(self):
        content = _read(".ai/version-manifest.yaml")
        assert content is not None, ".ai/version-manifest.yaml not found"
        assert "project_release_version" in content

    def test_changelog_latest_matches_pyproject(self):
        """T-0098 (D8): CHANGELOG 最新条目必须与 pyproject 版本一致。"""
        expected = _get_pyproject_version()
        content = _read("CHANGELOG.md")
        assert content is not None, "CHANGELOG.md not found"
        m = re.search(r'^##\s+v?(\d+\.\d+\.\d+)', content, re.MULTILINE)
        assert m, "version entry not found in CHANGELOG.md"
        assert m.group(1) == expected, (
            f"CHANGELOG.md latest {m.group(1)} != pyproject.toml {expected}"
        )

    def test_delivery_doc_version_header(self):
        expected = _get_pyproject_version()
        content = _read("docs/06-delivery.md")
        assert content is not None, "docs/06-delivery.md not found"
        # Check the version table row
        m = re.search(r'\|\s*版本号\s*\|\s*v?(\d+\.\d+\.\d+)\s*\|', content)
        assert m, "version table not found in docs/06-delivery.md"
        assert m.group(1) == expected, (
            f"docs/06-delivery.md version {m.group(1)} != pyproject.toml {expected}"
        )
