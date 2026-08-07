# -*- coding: utf-8 -*-
"""
test_t0141_consistency_templates.py — T-0141 一致性设计模板落地测试。
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class ConsistencyTemplatesTest(unittest.TestCase):
    def test_consistency_design_template(self):
        p = ROOT / "skills" / "loop-governance" / "templates" / "consistency" / "consistency-design.md"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        for marker in ("先删缓存", "先更新库", "强一致", "最终一致", "异步化",
                       "三层不丢", "幂等", "对账", "范围声明"):
            self.assertIn(marker, text, f"missing: {marker}")

    def test_architect_consistency_checklist(self):
        p = ROOT / "agents" / "system-architect" / "references" / "consistency-checklist.md"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        self.assertIn("幂等", text)
        self.assertIn("对账", text)

    def test_release_checklist_has_consistency_checks(self):
        text = (ROOT / "skills" / "loop-governance" / "templates" / "deployment" / "release-checklist.md").read_text(encoding="utf-8")
        for marker in ("数据流一致性标注", "缓存失效方案", "消息不丢设计", "幂等设计",
                       "T-0136 D-05"):
            self.assertIn(marker, text, f"missing: {marker}")


if __name__ == "__main__":
    unittest.main()
