# -*- coding: utf-8 -*-
"""
test_t0139_migration_templates.py — T-0139 数据迁移模板落地测试。

覆盖：data-migration-plan 模板（四阶段/回滚/不丢三层/拆分专项）在位；
角色 references 在位；release-checklist 迁移检查点存在；外部边界提醒。
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class MigrationTemplatesTest(unittest.TestCase):
    def test_data_migration_plan_template_exists(self):
        p = ROOT / "skills" / "loop-governance" / "templates" / "migration" / "data-migration-plan.md"
        self.assertTrue(p.is_file(), "data-migration-plan.md missing")
        text = p.read_text(encoding="utf-8")
        for marker in ("四阶段法", "回滚方案", "数据不丢失", "双写", "灰度切流",
                       "断点续传", "单体→微服务", "外部边界"):
            self.assertIn(marker, text, f"data-migration-plan missing: {marker}")

    def test_architect_migration_checklist(self):
        p = ROOT / "agents" / "system-architect" / "references" / "migration-checklist.md"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        self.assertIn("双写", text)
        self.assertIn("回滚", text)
        self.assertIn("外部边界", text)

    def test_release_migration_checklist(self):
        p = ROOT / "agents" / "release-engineer" / "references" / "migration-release-checklist.md"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        self.assertIn("NOGO", text)
        self.assertIn("回滚演练", text)

    def test_release_checklist_has_migration_checks(self):
        p = ROOT / "skills" / "loop-governance" / "templates" / "deployment" / "release-checklist.md"
        text = p.read_text(encoding="utf-8")
        for marker in ("迁移方案三件套", "回滚触发条件", "灰度切流档位", "数据校验方案",
                       "T-0136 D-03"):
            self.assertIn(marker, text, f"release-checklist missing: {marker}")


if __name__ == "__main__":
    unittest.main()
