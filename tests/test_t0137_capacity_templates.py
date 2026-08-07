# -*- coding: utf-8 -*-
"""
test_t0137_capacity_templates.py — T-0137 容量压测模板落地测试。

覆盖：capacity-estimate / load-test-plan 模板在位且结构完整（五步法/
三形态/四指标/防污染）；角色 references 在位；release-checklist 容量
检查点存在。
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class CapacityTemplatesTest(unittest.TestCase):
    def test_capacity_estimate_template_exists(self):
        p = ROOT / "skills" / "loop-governance" / "templates" / "capacity" / "capacity-estimate.md"
        self.assertTrue(p.is_file(), "capacity-estimate.md missing")
        text = p.read_text(encoding="utf-8")
        # 五步法 + 示例场景（含 2000→20 万 QPS）+ 假设清单
        self.assertIn("QPS 估算（五步法）", text)
        self.assertIn("2000", text)
        self.assertIn("20 万", text)
        self.assertIn("假设清单", text)
        self.assertIn("资源粗算", text)

    def test_load_test_plan_template_exists(self):
        p = ROOT / "skills" / "loop-governance" / "templates" / "capacity" / "load-test-plan.md"
        self.assertTrue(p.is_file(), "load-test-plan.md missing")
        text = p.read_text(encoding="utf-8")
        # 压测类型 / 流量三形态 / 防污染 / 四指标合格线 / 容量拐点
        self.assertIn("压测类型选择", text)
        self.assertIn("流量模型（三形态）", text)
        self.assertIn("防污染生产", text)
        self.assertIn("合格标准（四指标）", text)
        self.assertIn("容量上限", text)
        self.assertIn("p99", text)

    def test_architect_capacity_checklist(self):
        p = ROOT / "agents" / "system-architect" / "references" / "capacity-checklist.md"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        self.assertIn("capacity-estimate", text)
        self.assertIn("流量翻一倍/十倍", text)

    def test_release_load_test_checklist(self):
        p = ROOT / "agents" / "release-engineer" / "references" / "load-test-checklist.md"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        self.assertIn("NOGO", text)
        self.assertIn("防污染", text)
        self.assertIn("峰值", text)

    def test_release_checklist_has_capacity_checks(self):
        p = ROOT / "skills" / "loop-governance" / "templates" / "deployment" / "release-checklist.md"
        text = p.read_text(encoding="utf-8")
        for marker in ("压测报告存在且覆盖目标 QPS",
                       "容量拐点已测",
                       "压测防污染证据",
                       "容量预估表单",
                       "T-0136 D-01"):
            self.assertIn(marker, text, f"release-checklist missing: {marker}")


if __name__ == "__main__":
    unittest.main()
