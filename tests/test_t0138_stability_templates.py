# -*- coding: utf-8 -*-
"""
test_t0138_stability_templates.py — T-0138 稳定性模板落地测试。

覆盖：resilience-design 模板（RT 五阶梯/熔断/降级恢复三判定）在位；
角色 references 在位；release-checklist 稳定性检查点存在。
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class StabilityTemplatesTest(unittest.TestCase):
    def test_resilience_design_template_exists(self):
        p = ROOT / "skills" / "loop-governance" / "templates" / "stability" / "resilience-design.md"
        self.assertTrue(p.is_file(), "resilience-design.md missing")
        text = p.read_text(encoding="utf-8")
        for marker in ("RT 治理五阶梯", "熔断阈值", "半开恢复", "降级恢复判定",
                       "50ms", "5s", "p99"):
            self.assertIn(marker, text, f"resilience-design missing: {marker}")

    def test_architect_resilience_checklist(self):
        p = ROOT / "agents" / "system-architect" / "references" / "resilience-checklist.md"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        self.assertIn("熔断", text)
        self.assertIn("降级", text)

    def test_release_resilience_checklist(self):
        p = ROOT / "agents" / "release-engineer" / "references" / "resilience-release-checklist.md"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        self.assertIn("NOGO", text)
        self.assertIn("阈值推导", text)

    def test_release_checklist_has_stability_checks(self):
        p = ROOT / "skills" / "loop-governance" / "templates" / "deployment" / "release-checklist.md"
        text = p.read_text(encoding="utf-8")
        for marker in ("熔断配置存在", "阈值推导文档", "降级演练记录", "超时配置",
                       "T-0136 D-02"):
            self.assertIn(marker, text, f"release-checklist missing: {marker}")


if __name__ == "__main__":
    unittest.main()
