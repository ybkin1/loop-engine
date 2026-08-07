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
