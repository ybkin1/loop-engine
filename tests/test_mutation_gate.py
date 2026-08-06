# -*- coding: utf-8 -*-
"""
test_mutation_gate.py — T-0128 step_mutation_gate 门禁测试（AC-05 fail-closed）。

四场景：报告缺失 → FAIL；M1 低于阈值 → FAIL；M2 低于阈值 → FAIL；达标 → PASS。
"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import release as rel  # noqa: E402


def _write_report(root: Path, name: str, detected: int, seeded: int) -> None:
    obs = root / ".ai" / "evidence" / "observability"
    obs.mkdir(parents=True, exist_ok=True)
    (obs / name).write_text(json.dumps({
        "detected": detected, "seeded": seeded, "verdict": "PASS" if detected >= seeded else "FAIL",
    }), encoding="utf-8")


class MutationGateTest(unittest.TestCase):
    def test_missing_report_fails_closed(self, ):
        """报告缺失 → FAIL（没跑过就当不合格，fail-closed）。"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ok, msg = rel.step_mutation_gate(root)
            self.assertFalse(ok)
            self.assertIn("缺失", msg)

    def test_m1_below_threshold_fails(self):
        """M1=4/6（需 >=5/6）→ FAIL。"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_report(root, "mutation-report-m1.json", 4, 6)
            _write_report(root, "mutation-report-m2.json", 6, 6)
            ok, msg = rel.step_mutation_gate(root)
            self.assertFalse(ok)
            self.assertIn("FAIL", msg)
            self.assertIn("M1 4/6", msg)

    def test_m2_below_threshold_fails(self):
        """M2=3/6（需 >=4/6）→ FAIL。"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_report(root, "mutation-report-m1.json", 6, 6)
            _write_report(root, "mutation-report-m2.json", 3, 6)
            ok, msg = rel.step_mutation_gate(root)
            self.assertFalse(ok)
            self.assertIn("FAIL", msg)
            self.assertIn("M2 3/6", msg)

    def test_meets_threshold_passes(self):
        """M1=6/6 且 M2=6/6 → PASS。"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_report(root, "mutation-report-m1.json", 6, 6)
            _write_report(root, "mutation-report-m2.json", 6, 6)
            ok, msg = rel.step_mutation_gate(root)
            self.assertTrue(ok)
            self.assertIn("PASS", msg)


if __name__ == "__main__":
    unittest.main()
