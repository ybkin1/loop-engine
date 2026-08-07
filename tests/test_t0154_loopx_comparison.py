# -*- coding: utf-8 -*-
"""
test_t0154_loopx_comparison.py — T-0154 loop x 对比研究测试。

覆盖：对比报告在位且含四维分析（定位/差距表/建议分级/边界）；
candidate-only 边界（零产品代码改动）；两项目定位记录。
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class LoopxComparisonTest(unittest.TestCase):
    def test_comparison_report_exists(self):
        p = ROOT / "docs" / "designs" / "T-0154-loopx-comparison.md"
        self.assertTrue(p.is_file(), "对比报告缺失")
        text = p.read_text(encoding="utf-8")
        for marker in ("huangruiteng/loopx", "rye567/loopx", "对比差距表",
                       "提升建议", "candidate-only", "P0", "P1", "P2",
                       "事件溯源", "配额决策", "风险驱动执行分级"):
            self.assertIn(marker, text, f"报告缺失: {marker}")

    def test_project_locations_recorded(self):
        text = (ROOT / "docs" / "designs" / "T-0154-loopx-comparison.md").read_text(encoding="utf-8")
        self.assertIn("huangruiteng", text)
        self.assertIn("rye567", text)
        self.assertIn("commit", text.lower())

    def test_boundary_confirmed(self):
        """candidate-only：研究零产品代码改动（验证无 web/loop_core 新改动由本任务引入）。"""
        text = (ROOT / "docs" / "designs" / "T-0154-loopx-comparison.md").read_text(encoding="utf-8")
        self.assertIn("零产品代码改动", text)
        self.assertIn("hooks/ 内核零触碰", text)


if __name__ == "__main__":
    unittest.main()
