"""
test_release_bump.py — T-0100 (F-03) release.py bump 版本同步机制验收。

- AC-01a: bump 更新 pyproject.toml（事实来源）+ CHANGELOG 头部 + 全部版本载体
  （loop_core/__init__.py、src/loop_engine/__init__.py、README.md、
  docs/06-delivery.md、.zcode-plugin/plugin.json、.ai/version-manifest.yaml）。
- AC-01b: 原子写 —— 临时文件 + os.replace；写失败不留半成品、不残留 .tmp。
- AC-01c: 幂等（同版本 no-op）；非法版本号 → 用法错误（exit 2）；dry-run 不落盘。
- AC-01d: 缺失载体不阻断（迷你项目可缺 docs/ 等），报错时已更新载体不回滚但
  目标文件不被写坏。
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))

from scripts import release as rel  # noqa: E402

CARRIER_FILES = (
    "pyproject.toml",
    "CHANGELOG.md",
    "loop_core/__init__.py",
    "src/loop_engine/__init__.py",
    "README.md",
    "docs/06-delivery.md",
    ".zcode-plugin/plugin.json",
    ".ai/version-manifest.yaml",
)


@pytest.fixture
def mini_project(tmp_path: Path) -> Path:
    """迷你项目根：复制真实项目的全部版本载体（3.12.39 对齐后状态）。"""
    root = tmp_path / "project"
    for rel_path in CARRIER_FILES:
        src = PROJECT_ROOT / rel_path
        dst = root / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
    return root


def _version_of(root: Path, rel_path: str) -> str:
    content = (root / rel_path).read_text(encoding="utf-8")
    if rel_path == "pyproject.toml":
        m = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    elif rel_path == "CHANGELOG.md":
        m = re.search(r"^##\s+v?(\d+\.\d+\.\d+)", content, re.MULTILINE)
    elif rel_path.endswith("__init__.py"):
        m = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    elif rel_path == "README.md":
        m = re.search(r"\*\*v?(\d+\.\d+\.\d+)\*\*", content)
    elif rel_path == "docs/06-delivery.md":
        m = re.search(r"\|\s*版本号\s*\|\s*v?(\d+\.\d+\.\d+)\s*\|", content)
    elif rel_path == ".zcode-plugin/plugin.json":
        m = re.search(r'"version"\s*:\s*"([^"]+)"', content)
    elif rel_path == ".ai/version-manifest.yaml":
        m = re.search(r'^project_release_version:\s*"([^"]+)"', content, re.MULTILINE)
    else:
        raise AssertionError(f"unknown carrier: {rel_path}")
    assert m, f"载体缺少版本字段: {rel_path}"
    return m.group(1)


class TestBumpUpdatesCarriers:
    def test_bump_updates_all_carriers(self, mini_project: Path):
        assert rel.cmd_bump(mini_project, "9.8.7") == 0
        for rel_path in CARRIER_FILES:
            assert _version_of(mini_project, rel_path) == "9.8.7", rel_path
        # 版本一致性测试对同一套载体可直接通过（逐项等于 pyproject）
        assert rel.load_version(mini_project) == "9.8.7"

    def test_bump_changelog_inserts_at_head_keeps_old(self, mini_project: Path):
        old_content = (mini_project / "CHANGELOG.md").read_text(encoding="utf-8")
        assert rel.cmd_bump(mini_project, "9.8.7") == 0
        content = (mini_project / "CHANGELOG.md").read_text(encoding="utf-8")
        # 新条目在头部，旧条目保留且降序（新版本在旧版本之前）
        assert content.index("## v9.8.7") < content.index("## v3.12.39")
        assert "先 bump 再提交" in content
        assert "## v3.12.39" in content  # 原条目未丢失

    def test_bump_readme_and_docs(self, mini_project: Path):
        assert rel.cmd_bump(mini_project, "9.8.7") == 0
        readme = (mini_project / "README.md").read_text(encoding="utf-8")
        assert "**v9.8.7**" in readme
        doc = (mini_project / "docs" / "06-delivery.md").read_text(encoding="utf-8")
        assert "> Loop Engine v9.8.7" in doc
        assert "| 版本号 | v9.8.7 |" in doc

    def test_bump_version_manifest_keeps_history(self, mini_project: Path):
        assert rel.cmd_bump(mini_project, "9.8.7") == 0
        after = (mini_project / ".ai" / "version-manifest.yaml").read_text(encoding="utf-8")
        # 投影字段更新，历史快照（historical_snapshots）保持不动
        assert 'project_release_version: "9.8.7"' in after
        assert 'core_protocol_version: "9.8.7"' in after
        assert 'plugin_version: "9.8.7"' in after
        history = after.split("historical_snapshots:")[1].split("consistency_check:")[0]
        assert "9.8.7" not in history, "历史快照不得被 bump 改写"
        # consistency_check 投影值应更新
        assert 'pyproject_toml: "9.8.7"' in after

    def test_bump_idempotent_same_version(self, mini_project: Path):
        assert rel.cmd_bump(mini_project, rel.load_version(mini_project)) == 0
        for rel_path in CARRIER_FILES:
            assert _version_of(mini_project, rel_path) == rel.load_version(mini_project)

    def test_bump_dry_run_writes_nothing(self, mini_project: Path):
        before = {
            p: (mini_project / p).read_bytes() for p in CARRIER_FILES
        }
        assert rel.cmd_bump(mini_project, "9.8.7", dry_run=True) == 0
        for rel_path, blob in before.items():
            assert (mini_project / rel_path).read_bytes() == blob, rel_path

    def test_bump_invalid_version_is_usage_error(self, mini_project: Path):
        assert rel.cmd_bump(mini_project, "abc") == 2
        assert rel.cmd_bump(mini_project, "3.12") == 2
        assert rel.cmd_bump(mini_project, "3.12.39-beta") == 2
        assert rel.load_version(mini_project) == "3.12.39"  # 未改动

    def test_bump_missing_optional_carrier_skips(self, tmp_path: Path):
        root = tmp_path / "project"
        root.mkdir()
        shutil.copy(PROJECT_ROOT / "pyproject.toml", root / "pyproject.toml")
        assert rel.cmd_bump(root, "9.8.7") == 0
        assert rel.load_version(root) == "9.8.7"  # 事实来源仍更新


class TestBumpAtomicity:
    def test_atomic_write_no_leftover_tmp(self, mini_project: Path):
        assert rel.cmd_bump(mini_project, "9.8.7") == 0
        leftovers = list(mini_project.rglob("*.tmp"))
        assert leftovers == [], f"原子写残留临时文件: {leftovers}"

    def test_atomic_write_failure_keeps_original(self, mini_project: Path, monkeypatch):
        """os.replace 失败 → 目标文件保持原内容，临时文件被清理。"""
        target = mini_project / "pyproject.toml"
        original = target.read_bytes()

        def boom(src, dst):
            raise OSError("simulated replace failure")

        monkeypatch.setattr(rel.os, "replace", boom)
        with pytest.raises(OSError):
            rel._atomic_write(target, target.read_text(encoding="utf-8").replace(
                "3.12.39", "9.8.7"))
        assert target.read_bytes() == original, "写失败必须保持原内容"
        assert not list(mini_project.glob("*.tmp")), "写失败必须清理临时文件"

    def test_bump_carrier_failure_reports_error(self, mini_project: Path, monkeypatch):
        """某载体更新失败 → bump 报错（exit 1）；pyproject 未被写坏。"""
        def bad_updater(content, version):
            raise ValueError("simulated carrier error")

        carriers = [(p, bad_updater if p == "CHANGELOG.md" else u)
                    for p, u in rel.VERSION_CARRIERS]
        monkeypatch.setattr(rel, "VERSION_CARRIERS", carriers)
        assert rel.cmd_bump(mini_project, "9.8.7") == 1
        # pyproject（首个载体）已更新 —— 报错信息明确提示人工核对
        assert rel.load_version(mini_project) == "9.8.7"
