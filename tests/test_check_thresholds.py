# -*- coding: utf-8 -*-
"""
test_check_thresholds.py — 阈值对比工具的单元测试。
纯逻辑测试，不依赖外部工具。
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agents" / "quality-engineer" / "scripts"))
from check_thresholds import check, check_all, compare_audit, compare_coverage, compare_lint, compare_test


class CompareLintTest(unittest.TestCase):
    def test_zero_errors_passes(self):
        self.assertTrue(compare_lint(0, 0))
    def test_below_threshold_passes(self):
        self.assertFalse(compare_lint(3, 0))
    def test_at_threshold_passes(self):
        self.assertTrue(compare_lint(0, 0))


class CompareCoverageTest(unittest.TestCase):
    def test_above_threshold_passes(self):
        self.assertTrue(compare_coverage(91, 80))
    def test_below_threshold_fails(self):
        self.assertFalse(compare_coverage(62, 80))
    def test_at_threshold_passes(self):
        self.assertTrue(compare_coverage(80, 80))


class CompareTestTest(unittest.TestCase):
    def test_all_passed(self):
        ok, _ = compare_test("40/40", 0)
        self.assertTrue(ok)
    def test_two_failed(self):
        ok, detail = compare_test("38/40", 0)
        self.assertFalse(ok)
        self.assertIn("2", detail)
    def test_integer_failed_count(self):
        ok, _ = compare_test(3, 2)
        self.assertFalse(ok)
    def test_unparseable_value(self):
        ok, detail = compare_test("garbage", 0)
        self.assertFalse(ok)
        self.assertIn("无法解析", detail)


class CompareAuditTest(unittest.TestCase):
    def test_no_vulns_passes(self):
        ok, _ = compare_audit({"HIGH": 0, "CRITICAL": 0}, {"HIGH": 0, "CRITICAL": 0})
        self.assertTrue(ok)
    def test_high_vuln_blocks(self):
        ok, detail = compare_audit({"HIGH": 1}, {"HIGH": 0})
        self.assertFalse(ok)
        self.assertIn("HIGH", detail)
    def test_json_string_value_passes(self):
        ok, _ = compare_audit('{"HIGH":0,"CRITICAL":0}', '{"HIGH":0,"CRITICAL":0}')
        self.assertTrue(ok)
    def test_invalid_json_fails(self):
        ok, detail = compare_audit("not json", {"HIGH": 0})
        self.assertFalse(ok)
        self.assertIn("无法解析", detail)


class CheckSingleTest(unittest.TestCase):
    def test_lint_blocked(self):
        item = check("lint", 5, 0)
        self.assertEqual(item["status"], "BLOCKED")
        self.assertIn("5 > 0", item["reason"])
    def test_lint_pass(self):
        item = check("lint", 0, 0)
        self.assertEqual(item["status"], "PASS")
    def test_coverage_blocked(self):
        item = check("coverage", 62, 80)
        self.assertEqual(item["status"], "BLOCKED")
    def test_audit_blocked(self):
        item = check("audit", {"HIGH": 2}, {"HIGH": 0})
        self.assertEqual(item["status"], "BLOCKED")
        self.assertIn("HIGH: 2 > 0", item["reason"])
    def test_unknown_check_passes(self):
        item = check("unknown", 999, 0)
        self.assertEqual(item["status"], "PASS")


class CheckAllTest(unittest.TestCase):
    def test_all_pass(self):
        items, overall, blocked = check_all(
            {"lint": 0, "coverage": 80},
            {"lint": 0, "coverage": 91}
        )
        self.assertEqual(overall, "PASS")
        self.assertEqual(len(blocked), 0)
    def test_one_blocked(self):
        items, overall, blocked = check_all(
            {"lint": 0, "coverage": 80, "audit": {"HIGH": 0}},
            {"lint": 0, "coverage": 62, "audit": {"HIGH": 2}}
        )
        self.assertEqual(overall, "BLOCKED")
        self.assertGreater(len(blocked), 0)
    def test_all_blocked(self):
        items, overall, blocked = check_all(
            {"lint": 0, "coverage": 80},
            {"lint": 5, "coverage": 30}
        )
        self.assertEqual(overall, "BLOCKED")
        self.assertEqual(len(blocked), 2)


class CliTest(unittest.TestCase):
    def setUp(self):
        self.script = Path(__file__).resolve().parent.parent / "agents" / "quality-engineer" / "scripts" / "check_thresholds.py"

    def test_cli_pass(self):
        import subprocess
        r = subprocess.run(
            [sys.executable, str(self.script), "lint", "0", "0"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
    def test_cli_blocked(self):
        import subprocess
        r = subprocess.run(
            [sys.executable, str(self.script), "lint", "5", "0"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(r.returncode, 2, f"stderr: {r.stderr}")
        out = json.loads(r.stdout)
        self.assertEqual(out["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
