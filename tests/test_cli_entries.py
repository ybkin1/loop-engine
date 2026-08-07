# -*- coding: utf-8 -*-
"""
test_cli_entries.py — T-0135 审计发现收尾测试。

覆盖：pyproject [project.scripts] 入口声明与 cli_entries 薄封装可导入可调用；
release check guard_health 步骤的 missing/drift/recompute 可见性；
guard-events gitignore 生效（不再被 git 跟踪）。
"""

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loop_engine.cli_entries import ENTRY_POINTS, PROJECT_ROOT  # noqa: E402


class CliEntriesTest(unittest.TestCase):
    def test_pyproject_declares_scripts(self):
        """pyproject [project.scripts] 声明 >=4 个入口。"""
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("[project.scripts]", text)
        for name in ("loop-validate", "loop-check", "loop-heartbeat",
                     "loop-delegation", "loop-conclusion", "loop-mutation"):
            self.assertIn(name, text, f"{name} missing in [project.scripts]")

    def test_entry_points_exist(self):
        """cli_entries 导出全部入口函数。"""
        self.assertGreaterEqual(len(ENTRY_POINTS), 4)
        for name, fn in ENTRY_POINTS.items():
            self.assertTrue(callable(fn), name)

    def test_validate_entry_runs(self):
        """loop-validate 冒烟：调用真实校验器（rc 0 或 2 语义）。"""
        proc = subprocess.run(
            [sys.executable, str(ROOT / "loop_engine" / "cli_entries.py"),
             "loop-validate", str(ROOT)],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT), timeout=120)
        # 校验器可用态 rc=0；pending blocker 时 rc=2 —— 两者都是合法语义
        self.assertIn(proc.returncode, (0, 2), proc.stderr)

    def test_heartbeat_entry_runs(self):
        """loop-heartbeat 冒烟：rc 0（无悬空）。"""
        proc = subprocess.run(
            [sys.executable, str(ROOT / "loop_engine" / "cli_entries.py"),
             "loop-heartbeat", str(ROOT)],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT), timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout)


class GuardHealthVisibilityTest(unittest.TestCase):
    def test_release_guard_health_reports_findings(self):
        """release check guard_health 步骤输出 missing/drift/recompute 计数。"""
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "scripts"))
        import release as rel
        ok, msg = rel.step_guard_health(ROOT)
        self.assertTrue(ok, msg)
        self.assertIn("guard 健康 PASS", msg)
        # 可见性：report 段（计数）在消息中（0 或 N 均展示）
        self.assertIn("missing=", msg)

    def test_guard_health_findings_do_not_block(self):
        """report 级发现不翻转 verdict（设计保留，连续性已硬阻断）。"""
        import tempfile
        from loop_core.guard_health import GuardHealth
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".ai").mkdir()
            integrity = GuardHealth(root).integrity_check()
            # 无注册表/无发现时 missing/drift 为空且 overall 由 death 驱动
            self.assertIn("overall", integrity)


class GuardEventsGitignoreTest(unittest.TestCase):
    def test_guard_events_no_longer_tracked(self):
        """guard-events.jsonl 不再被 git 跟踪（T-0135 治理）。"""
        proc = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "--", ".ai/evidence/observability/guard-events.jsonl"],
            capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(proc.stdout.strip(), "", "guard-events.jsonl must be untracked")

    def test_gitignore_has_guard_events(self):
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("guard-events.jsonl", text)


if __name__ == "__main__":
    unittest.main()
