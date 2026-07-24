# -*- coding: utf-8 -*-
"""
test_quality_gates.py — run_quality_gates.py 的解析与报告生成测试。

使用 mock subprocess 模拟各工具的输出，不依赖实际安装 lint/test 工具。
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# 将被测模块所在目录加入路径
_SRC_PROJECT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = _SRC_PROJECT / "agents" / "quality-engineer" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from run_quality_gates import (
    collect_results,
    generate_report,
    load_config,
    parse_audit_output,
    parse_lint_output,
    parse_test_output,
)


class ParseLintOutputTest(unittest.TestCase):
    def test_ruff_json(self):
        raw = json.dumps([
            {"code": "F401", "message": "`os` imported but unused", "location": {"row": 3}},
            {"code": "E501", "message": "Line too long", "location": {"row": 12}},
        ])
        count, _ = parse_lint_output(raw, 0, "ruff check --output-format json .")
        self.assertEqual(count, 2)

    def test_eslint_json(self):
        raw = json.dumps([
            {"filePath": "src/a.js", "messages": [{"ruleId": "no-unused-vars"}, {"ruleId": "semi"}]},
            {"filePath": "src/b.js", "messages": []},
        ])
        count, _ = parse_lint_output(raw, 0, "eslint src/ --format json")
        self.assertEqual(count, 2)

    def test_raw_lines(self):
        raw = "./src/app.py:3:1: F401 `os` imported but unused\nFound 1 error.\n"
        count, _ = parse_lint_output(raw, 1, "some-linter src/")
        self.assertEqual(count, 1)


class ParseTestOutputTest(unittest.TestCase):
    def test_pytest_all_passed(self):
        raw = "tests/test_a.py ..\ntests/test_b.py ...\n\n=========================== 5 passed in 0.12s ==========================="
        passed, total, cov, _ = parse_test_output(raw, 0, "pytest --cov=src")
        self.assertEqual(passed, 5)
        self.assertEqual(total, 5)

    def test_pytest_with_failures(self):
        raw = "tests/test_a.py .F.\ntests/test_b.py ..\n\n======================== 4 passed, 1 failed in 0.15s ========================="
        passed, total, cov, _ = parse_test_output(raw, 1, "pytest --cov=src")
        self.assertEqual(passed, 4)
        self.assertEqual(total, 5)

    def test_pytest_with_coverage_line(self):
        raw = (
            "tests/test_a.py ...\n\n"
            "---------- coverage: platform win32 ----------\n"
            "Name        Stmts   Miss  Cover\n"
            "src/a.py       10      2    80%\n"
            "src/b.py        5      0   100%\n"
            "----------------------------------------\n"
            "TOTAL          15      2    87%\n"
        )
        _, _, cov, _ = parse_test_output(raw, 0, "pytest --cov=src")
        self.assertEqual(cov, 87)


class ParseAuditOutputTest(unittest.TestCase):
    def test_npm_audit_json(self):
        data = {
            "vulnerabilities": {
                "lodash": {"severity": "high", "range": "<4.17.21"},
                "minimist": {"severity": "critical", "range": "<1.2.6"},
            }
        }
        raw = json.dumps(data)
        counts = parse_audit_output(raw, 1, "npm audit --json")
        self.assertEqual(counts["HIGH"], 1)
        self.assertEqual(counts["CRITICAL"], 1)

    def test_no_vulns(self):
        data = {"vulnerabilities": {}}
        raw = json.dumps(data)
        counts = parse_audit_output(raw, 0, "npm audit --json")
        self.assertEqual(counts["HIGH"], 0)
        self.assertEqual(counts["CRITICAL"], 0)


class MockRunCheckTest(unittest.TestCase):
    """用 mock 子进程模拟完整流程：配置 → 采集 → 报告生成。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        # 写一个最小 config.yaml 到临时目录
        config_dir = self.tmp / ".zcode" / "skills" / "loop-governance"
        config_dir.mkdir(parents=True)
        (config_dir / "config.yaml").write_text("""
quality_gates:
  lint_command: "mock-lint"
  lint_threshold: 0
  typecheck_command: "mock-tsc"
  typecheck_threshold: 0
  test_command: "mock-pytest"
  test_threshold: 0
  coverage_threshold: 80
  audit_command: "mock-audit"
  audit_threshold:
    HIGH: 0
    CRITICAL: 0
""", encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _mock_run(self, command, **kwargs):
        """模拟各工具的输出。"""
        cmd = command[0] if isinstance(command, list) else command
        if "mock-lint" in cmd:
            return MagicMock(returncode=0, stdout="[]", stderr="")
        if "mock-tsc" in cmd:
            return MagicMock(returncode=0, stdout="", stderr="")
        if "mock-pytest" in cmd:
            return MagicMock(returncode=0, stdout="5 passed in 0.1s\nTOTAL 20 0 100%", stderr="")
        if "mock-audit" in cmd:
            return MagicMock(returncode=0, stdout='{"vulnerabilities":{}}', stderr="")
        return MagicMock(returncode=0, stdout="", stderr="")

    @patch("subprocess.run")
    def test_collect_and_report_pass(self, mock_run):
        mock_run.side_effect = self._mock_run

        gates = load_config(self.tmp)
        results = collect_results(gates, self.tmp)

        self.assertGreater(len(results), 0)
        for r in results:
            if not r.get("skipped"):
                self.assertIn("value", r)
                self.assertIn("threshold", r)

        output_dir = self.tmp / ".ai" / "evidence" / "quality"
        overall, blocked = generate_report(results, self.tmp, output_dir)

        # 在 mock 数据下应全部 PASS
        self.assertEqual(overall, "PASS")
        self.assertEqual(len(blocked), 0)

        # 验证文件确实写入了
        self.assertTrue((output_dir / "quality_report.json").exists())
        self.assertTrue((output_dir / "quality_summary.md").exists())

        # 验证 JSON schema
        report = json.loads((output_dir / "quality_report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["schema"], "quality_report/v1")
        self.assertEqual(report["role"], "quality-engineer")
        self.assertEqual(report["overall"], "PASS")
        self.assertIn("checks", report)

    @patch("subprocess.run")
    def test_blocked_on_lint_and_coverage(self, mock_run):
        """模拟：lint 发现 5 个 error + 覆盖率仅 62% → BLOCKED"""

        def mock_values(command, **kwargs):
            cmd = command if isinstance(command, str) else str(command)
            if "mock-lint" in cmd:
                raw = json.dumps([{"code": "F401"}, {"code": "E501"}, {"code": "W293"}, {"code": "F841"}, {"code": "E302"}])
                return MagicMock(returncode=1, stdout=raw, stderr="")
            if "mock-tsc" in cmd:
                return MagicMock(returncode=0, stdout="", stderr="")
            if "mock-pytest" in cmd:
                return MagicMock(returncode=0,
                                 stdout="3 passed, 2 failed in 0.2s\nTOTAL 30 11 62%",
                                 stderr="")
            if "mock-audit" in cmd:
                return MagicMock(returncode=0, stdout='{"vulnerabilities":{}}', stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_values

        gates = load_config(self.tmp)
        results = collect_results(gates, self.tmp)
        output_dir = self.tmp / "quality_output"
        overall, blocked = generate_report(results, self.tmp, output_dir)

        self.assertEqual(overall, "BLOCKED")
        self.assertGreaterEqual(len(blocked), 2)

        report = json.loads((output_dir / "quality_report.json").read_text(encoding="utf-8"))
        lint_item = next(c for c in report["checks"] if c["name"] == "lint")
        self.assertEqual(lint_item["status"], "blocked")

        cov_item = next(c for c in report["checks"] if c["name"] == "coverage")
        self.assertEqual(cov_item["status"], "blocked")
        self.assertEqual(cov_item["value"], 62)

    @patch("subprocess.run")
    def test_audit_with_high_vuln_blocks(self, mock_run):
        """模拟：npm audit 发现 1 个 HIGH → BLOCKED"""
        def mock_run_fn(command, **kwargs):
            cmd = command if isinstance(command, str) else str(command)
            if "mock-lint" in cmd:
                return MagicMock(returncode=0, stdout="[]", stderr="")
            if "mock-tsc" in cmd:
                return MagicMock(returncode=0, stdout="", stderr="")
            if "mock-pytest" in cmd:
                return MagicMock(returncode=0, stdout="5 passed in 0.1s\nTOTAL 20 0 100%", stderr="")
            if "mock-audit" in cmd:
                data = {"vulnerabilities": {"lodash": {"severity": "high"}}}
                return MagicMock(returncode=1, stdout=json.dumps(data), stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_run_fn

        gates = load_config(self.tmp)
        results = collect_results(gates, self.tmp)
        output_dir = self.tmp / "quality_output2"
        overall, blocked = generate_report(results, self.tmp, output_dir)

        self.assertEqual(overall, "BLOCKED")
        self.assertIn("audit", blocked[0] if blocked else "")

        report = json.loads((output_dir / "quality_report.json").read_text(encoding="utf-8"))
        audit_item = next(c for c in report["checks"] if c["name"] == "audit")
        self.assertEqual(audit_item["status"], "blocked")


if __name__ == "__main__":
    unittest.main(verbosity=2)
