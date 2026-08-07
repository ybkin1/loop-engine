# -*- coding: utf-8 -*-
"""
test_t0140_performance_templates.py — T-0140 性能诊断模板落地测试。
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class PerformanceTemplatesTest(unittest.TestCase):
    def test_performance_diagnosis_template(self):
        p = ROOT / "skills" / "loop-governance" / "templates" / "performance" / "performance-diagnosis.md"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        for marker in ("分位指标选择", "长尾", "慢 SQL", "EXPLAIN", "索引", "GC",
                       "11 亿行", "p99"):
            self.assertIn(marker, text, f"missing: {marker}")

    def test_quality_performance_checklist(self):
        p = ROOT / "agents" / "quality-engineer" / "references" / "performance-checklist.md"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        self.assertIn("p99", text)
        self.assertIn("explain", text)

    def test_release_checklist_has_performance_checks(self):
        text = (ROOT / "skills" / "loop-governance" / "templates" / "deployment" / "release-checklist.md").read_text(encoding="utf-8")
        for marker in ("分位指标", "慢 SQL 清单 + explain", "索引确认证据", "T-0136 D-04"):
            self.assertIn(marker, text, f"missing: {marker}")


if __name__ == "__main__":
    unittest.main()
