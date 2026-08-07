# -*- coding: utf-8 -*-
"""
test_risk_grading.py — T-0157 风险驱动执行分级测试。

覆盖：三态分级；critical_triggers 强制 FULL；打分阈值矩阵；
ACCEPTED_RISK 记录；SKIPPED 白名单（仅审核/审计门）；advisory-only
（gate 语义不变）；CLI 只建议。
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from loop_engine.risk_grading import (  # noqa: E402
    CRITICAL_TRIGGERS, MODE_SKIPPABLE_STAGES, accepted_risk, grade_risk,
    is_skippable,
)


class RiskGradingTest(unittest.TestCase):
    def test_critical_triggers_force_full(self):
        for trigger in ("auth", "permission", "db_schema", "external_side_effect",
                        "core_state_transition", "secret", "payment", "production_data"):
            r = grade_risk("change", {trigger: True})
            self.assertEqual(r["level"], "FULL", f"{trigger} 必须强制 FULL")
            self.assertIn(trigger, r["triggers_hit"])

    def test_high_score_full(self):
        r = grade_risk("x", {"api_contract": True, "sql": True, "mq": True})
        self.assertEqual(r["level"], "FULL")
        self.assertEqual(r["score"], 9)

    def test_medium_score_standard(self):
        r = grade_risk("x", {"api_contract": True})
        self.assertEqual(r["level"], "STANDARD")
        self.assertEqual(r["score"], 3)

    def test_low_score_light(self):
        r = grade_risk("x", {"test_only": True})
        self.assertEqual(r["level"], "LIGHT")
        self.assertEqual(r["score"], -1)

    def test_desc_keyword_inference(self):
        r = grade_risk("修改 API 接口契约并加 SQL 查询")
        self.assertEqual(r["level"], "FULL", "api_contract(3)+sql(3)=6 ≥ 4")
        r2 = grade_risk("仅更新文档")
        self.assertEqual(r2["level"], "LIGHT")

    def test_desc_critical_inference(self):
        """desc 文本命中 critical 关键字 → FULL（防漏判）。"""
        r = grade_risk("修改支付接口并动数据库表结构")
        self.assertEqual(r["level"], "FULL")
        self.assertIn("payment", r["triggers_hit"])
        self.assertIn("db_schema", r["triggers_hit"])
        r2 = grade_risk("给用户加登录认证")
        self.assertEqual(r2["level"], "FULL")
        self.assertIn("auth", r2["triggers_hit"])

    def test_accepted_risk_recorded(self):
        """ACCEPTED_RISK 记录到事件日志（user actor）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".ai").mkdir(parents=True)
            (root / ".ai" / "state.yaml").write_text(
                "schema_version: 1\ncurrent_phase: S6-delivery\ncurrent_task_id: null\n",
                encoding="utf-8")
            (root / ".ai" / "gates.yaml").write_text("schema_version: 1\ngates: []\n", encoding="utf-8")
            (root / ".ai" / "task_graph.yaml").write_text("schema_version: 1\ntasks: []\n", encoding="utf-8")
            ok = accepted_risk(root, "T-X", "LIGHT", "docs-only change")
            self.assertTrue(ok)
            from event_log import read_events
            events = read_events(root)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["actor"], "user")
            self.assertTrue(events[0]["detail"].get("accepted_risk"))

    def test_skippable_whitelist(self):
        """SKIPPED 白名单：仅审核/审计门，FULL 不可跳过。"""
        self.assertTrue(is_skippable("design_review", "LIGHT"))
        self.assertTrue(is_skippable("audit_review", "STANDARD"))
        self.assertFalse(is_skippable("design_review", "FULL"))
        self.assertFalse(is_skippable("development", "LIGHT"), "开发门不可跳过")
        self.assertFalse(is_skippable("health_check", "LIGHT"), "健康门不可跳过")
        self.assertEqual(MODE_SKIPPABLE_STAGES, {"design_review", "audit_review"})

    def test_cli_advisory_only(self):
        """/loop-risk CLI 可调用且只建议。"""
        proc = subprocess.run(
            [sys.executable, str(ROOT / "src" / "loop_engine" / "cli_entries.py"),
             "loop-risk", "修改支付接口并动数据库"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT), timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("level:", proc.stdout)
        self.assertIn("advisory only", proc.stdout)

    def test_all_critical_triggers_listed(self):
        """8 个 critical triggers 全在常量中。"""
        self.assertEqual(len(CRITICAL_TRIGGERS), 8)


if __name__ == "__main__":
    unittest.main()
