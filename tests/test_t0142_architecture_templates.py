# -*- coding: utf-8 -*-
"""
test_t0142_architecture_templates.py — T-0142 架构与方法模板落地测试。
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class ArchitectureTemplatesTest(unittest.TestCase):
    def test_ddd_split_guide(self):
        p = ROOT / "skills" / "loop-governance" / "templates" / "architecture" / "ddd-split-guide.md"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        for marker in ("限界上下文", "聚合", "防腐层", "拆分决策表", "2 pizza",
                       "何时用 DDD"):
            self.assertIn(marker, text, f"missing: {marker}")

    def test_release_strategy_guide(self):
        p = ROOT / "skills" / "loop-governance" / "templates" / "deployment" / "release-strategy-guide.md"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        for marker in ("灰度发布", "蓝绿发布", "金丝雀", "决策输入", "决策流程"):
            self.assertIn(marker, text, f"missing: {marker}")

    def test_ddd_checklist(self):
        p = ROOT / "agents" / "system-architect" / "references" / "ddd-checklist.md"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        self.assertIn("四问", text)

    def test_tradeoff_checklist(self):
        p = ROOT / "agents" / "delivery-manager" / "references" / "tradeoff-checklist.md"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        for marker in ("MVP", "升级协议", "技术债"):
            self.assertIn(marker, text, f"missing: {marker}")

    def test_ai_boundary_doc(self):
        p = ROOT / "docs" / "designs" / "T-0136-D06-ai-boundary.md"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        for marker in ("可复算可验证", "价值/风险裁决", "USER_AUTHORITY",
                       "EVIDENCE_ONLY_BOUNDARY"):
            self.assertIn(marker, text, f"missing: {marker}")

    def test_release_checklist_has_arch_checks(self):
        text = (ROOT / "skills" / "loop-governance" / "templates" / "deployment" / "release-checklist.md").read_text(encoding="utf-8")
        for marker in ("拆分决策表已填", "发布策略选择依据", "排期冲突走升级协议",
                       "T-0136 D-06"):
            self.assertIn(marker, text, f"missing: {marker}")


if __name__ == "__main__":
    unittest.main()
