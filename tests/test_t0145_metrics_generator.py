# -*- coding: utf-8 -*-
"""
test_t0145_metrics_generator.py — T-0145 metrics-report 生成器测试。

覆盖：mutation_metrics/gate_defense 由生成器实时聚合（读侧计数）；
rejected_requests 从 guard-events 真实计数；缺失报告 → NOT_AVAILABLE。
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loop_core.governance_metrics import (  # noqa: E402
    build_gate_defense, build_mutation_metrics, build_report,
)


class MutationMetricsGeneratorTest(unittest.TestCase):
    def test_reads_mutation_reports(self):
        """生成器从 mutation-report-m1/m2.json 实时聚合（读侧计数）。"""
        m = build_mutation_metrics(ROOT)
        self.assertEqual(m["m1_deterministic"]["verdict"], "PASS")
        self.assertEqual(m["m2_real_role"]["verdict"], "PASS")
        self.assertEqual(m["m1_deterministic"]["detected"], 6)
        self.assertIn("source_refs", m)

    def test_missing_report_is_not_available(self):
        """报告缺失 → NOT_AVAILABLE（不伪造）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m = build_mutation_metrics(root)
            self.assertEqual(m["m1_deterministic"]["verdict"], "NOT_AVAILABLE")
            self.assertIn("missing", m["m1_deterministic"]["reason"])

    def test_threshold_matches_release_gate(self):
        """P2-1 修复：阈值与 release mutation_gate 一致（M1>=5/6, M2>=4/6）。"""
        import json as _json
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            obs = root / ".ai" / "evidence" / "observability"
            obs.mkdir(parents=True)
            # M1 5/6（release 门禁放行下限）、M2 4/6（下限）→ 必须 PASS
            (obs / "mutation-report-m1.json").write_text(
                _json.dumps({"detected": 5, "seeded": 6}), encoding="utf-8")
            (obs / "mutation-report-m2.json").write_text(
                _json.dumps({"detected": 4, "seeded": 6}), encoding="utf-8")
            m = build_mutation_metrics(root)
            self.assertEqual(m["m1_deterministic"]["verdict"], "PASS",
                             "M1 5/6 达 release 门禁下限必须 PASS")
            self.assertEqual(m["m2_real_role"]["verdict"], "PASS",
                             "M2 4/6 达 release 门禁下限必须 PASS")
            # 低于下限 → FAIL
            (obs / "mutation-report-m1.json").write_text(
                _json.dumps({"detected": 4, "seeded": 6}), encoding="utf-8")
            m2 = build_mutation_metrics(root)
            self.assertEqual(m2["m1_deterministic"]["verdict"], "FAIL")


class GateDefenseGeneratorTest(unittest.TestCase):
    def _write_guard_events(self, root: Path, events: list[dict]) -> Path:
        p = root / ".ai" / "evidence" / "observability" / "guard-events.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")
        return p

    def test_rejected_requests_real_count(self):
        """rejected_requests 从 guard-events 真实计数（BLOCK/REJECTED）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_guard_events(root, [
                {"check_type": "gate", "result": "BLOCK", "guard_id": "g1"},
                {"check_type": "gate", "result": "REJECTED", "guard_id": "g2"},
                {"check_type": "gate", "result": "PASS", "guard_id": "g3"},
                {"check_type": "recompute", "result": "FAIL", "guard_id": "g4"},
            ])
            d = build_gate_defense(root)
            self.assertEqual(d["rejected_requests"], 2, "BLOCK+REJECTED 各 1 计 2")

    def test_no_events_zero(self):
        """无 guard-events → rejected_requests = 0（非恒 0 口径值，是真实计数）。"""
        with tempfile.TemporaryDirectory() as td:
            d = build_gate_defense(Path(td))
            self.assertEqual(d["rejected_requests"], 0)

    def test_report_contains_generated_fields(self):
        """build_report 输出含 mutation_metrics/gate_defense（生成器接入）。"""
        r = build_report(str(ROOT))
        d = r.to_dict()
        self.assertIn("mutation_metrics", d)
        self.assertIn("gate_defense", d)
        self.assertIn("rejected_requests", d["gate_defense"])
        self.assertIn("source_refs", d["mutation_metrics"])


if __name__ == "__main__":
    unittest.main()


class T0149P3CloseoutTest(unittest.TestCase):
    """T-0149: P3 观察收尾包测试。"""

    def test_render_markdown_contains_new_sections(self):
        """render_markdown 渲染 mutation/gate_defense 区块。"""
        from loop_core.governance_metrics import render_markdown
        r = build_report(str(ROOT))
        md = render_markdown(r)
        self.assertIn("## Mutation / Gate Defense", md)
        self.assertIn("m1_deterministic", md)
        self.assertIn("rejected_requests", md)

    def test_defense_drill_rate_from_file(self):
        """defense_drill_pass_rate 从 test_defense_drills.py 动态统计。"""
        d = build_gate_defense(ROOT)
        rate = d["defense_drill_pass_rate"]
        self.assertRegex(rate, r"^\d+/\d+$")
        self.assertNotEqual(rate, "0/0", "演练用例应存在")
        # 口径 = 用例数/用例数（release 驱动全过）
        num = int(rate.split("/")[0])
        self.assertGreaterEqual(num, 11, "至少 11 个演练用例")

    def test_defense_drill_missing_file_zero(self):
        """测试文件缺失 → 0/0（如实标注不伪造）。"""
        with tempfile.TemporaryDirectory() as td:
            d = build_gate_defense(Path(td))
            self.assertEqual(d["defense_drill_pass_rate"], "0/0")


class T0149ReproNormEdgeTest(unittest.TestCase):
    """T-0149: repro_norm 边界加固（10 位数字误伤 / UNC / 裸盘符）。"""

    def _norm(self, text, rules=("strip-timestamps", "strip-absolute-paths")):
        import sys as _sys
        _sys.path.insert(0, str(ROOT))
        from loop_core.guard_health import GuardHealth
        import tempfile as _tf
        with _tf.TemporaryDirectory() as td:
            return GuardHealth(Path(td))._normalize_output(text, list(rules))

    def test_ten_digit_id_not_mangled(self):
        """普通 10 位 ID/计数不被误替换（仅时间戳上下文）。"""
        out = self._norm("user_id=1234567890 count=1000000000 ok")
        self.assertIn("1234567890", out, "10 位 ID 不应被替换为 <TS>")
        self.assertIn("1000000000", out)

    def test_epoch_with_unit_stripped(self):
        """带单位/小数的 epoch 秒被替换。"""
        out = self._norm("took 1723000000.512ms done")
        self.assertNotIn("1723000000", out)
        self.assertIn("<TS>", out)

    def test_unc_path_stripped(self):
        """UNC 路径（双反斜杠 server share）被替换。"""
        out = self._norm("copied " + chr(92)*2 + "srv01" + chr(92) + "share" + chr(92) + "data" + chr(92) + "file.txt done")
        self.assertNotIn("srv01", out)
        self.assertIn("<ABS>", out)

    def test_bare_drive_stripped(self):
        """裸盘符路径（C 冒号反斜杠 tmp）被替换。"""
        out = self._norm("path C:" + chr(92) + "tmp" + chr(92) + "x.txt written")
        self.assertNotIn("tmp", out)
        self.assertIn("<ABS>", out)
