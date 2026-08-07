# -*- coding: utf-8 -*-
"""
test_t0151_backlog_landing.py — T-0151 backlog 落地测试。

覆盖：test-strategy 金字塔 70/20/10 约束在位；KNOWN_ISSUES Debt Register
结构化账本存在（P0~P3 分级 + 来源/处理列）；backlog 评估文档在位。
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class BacklogLandingTest(unittest.TestCase):
    def test_test_strategy_pyramid(self):
        p = ROOT / "skills" / "loop-governance" / "templates" / "testing" / "test-strategy.md"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        for marker in ("测试金字塔约束", "70%", "20%", "10%", "| 单元测试 | ≥60% |",
                       "| E2E 测试 | ≤15% |", "T-0151"):
            self.assertIn(marker, text, f"test-strategy missing: {marker}")

    def test_debt_register_exists(self):
        p = ROOT / ".ai" / "KNOWN_ISSUES.md"
        text = p.read_text(encoding="utf-8")
        for marker in ("## Debt Register", "DR-001", "P0 安全/数据风险",
                       "隔离+监控+封装"):
            self.assertIn(marker, text, f"KNOWN_ISSUES missing: {marker}")

    def test_backlog_assessment_doc(self):
        p = ROOT / "docs" / "designs" / "T-0151-backlog-assessment.md"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        for marker in ("Tech-writer", "SRE", "Threat-modeling", "Backlog 状态表"):
            self.assertIn(marker, text, f"assessment missing: {marker}")


if __name__ == "__main__":
    unittest.main()


class T0152ReleaseChecklistPyramidTest(unittest.TestCase):
    """T-0152: release-checklist 金字塔检查点与 test-strategy §4.5 对应。"""

    def test_release_checklist_has_pyramid_check(self):
        text = (ROOT / "skills" / "loop-governance" / "templates" / "deployment" / "release-checklist.md").read_text(encoding="utf-8")
        self.assertIn("测试金字塔", text)
        self.assertIn("单元 ≥60%", text)
        self.assertIn("test-strategy §4.5", text)

    def test_test_strategy_pyramid_section_consistent(self):
        text = (ROOT / "skills" / "loop-governance" / "templates" / "testing" / "test-strategy.md").read_text(encoding="utf-8")
        self.assertIn("单元测试 | ≥60%", text)
        self.assertIn("15~25%", text)
        self.assertIn("≤15%", text)
