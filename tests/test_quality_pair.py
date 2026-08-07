# -*- coding: utf-8 -*-
"""
test_quality_pair.py — T-0133 P3 三层质量线程落地测试。

覆盖：SubagentSpec.quality_pair 强制规则 / EvalCaseResult.evidence_ref /
agent 判定断言化桥接 / CHECK_RECOMPUTE（report 级 + 连续失败 fail-closed）/
角色契约 T-0133 规范在位。
"""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loop_core.subagent_manifest import QualityPair, SubagentSpec  # noqa: E402
from loop_core.evals import EvalCaseResult, EvalVerdict, finding_to_eval_case  # noqa: E402
from loop_core.guard_health import GuardHealth  # noqa: E402


class QualityPairSchemaTest(unittest.TestCase):
    def test_weighted_spec_requires_quality_pair(self):
        """重量动作无 quality_pair → ValueError（编排无效，机器可判）。"""
        with self.assertRaises(ValueError) as ctx:
            SubagentSpec(subagent_id="dev-1", role_hint="developer",
                         prompt="implement X", is_weighted=True)
        self.assertIn("quality_pair", str(ctx.exception))

    def test_weighted_spec_with_quality_pair_ok(self):
        """重量动作携带 quality_pair → 正常构造。"""
        spec = SubagentSpec(
            subagent_id="dev-1", role_hint="developer", prompt="implement X",
            is_weighted=True,
            quality_pair=QualityPair(
                quality_role="quality-engineer",
                check_scope=["src/loop_core/executor.py"],
                eval_cases=[{"case_id": "QP-001", "title": "t",
                             "input": {"command": "true"}, "rule": {"type": "exit_code",
                             "params": {"expected": 0}}, "severity": "medium"}],
                round_limit=3,
            ))
        self.assertEqual(spec.quality_pair.quality_role, "quality-engineer")
        self.assertEqual(spec.quality_pair.round_limit, 3)

    def test_light_spec_without_quality_pair_ok(self):
        """轻量动作无 quality_pair → 正常（分层伴飞：hook 检查足够）。"""
        spec = SubagentSpec(subagent_id="doc-1", role_hint="general-purpose",
                            prompt="update docs")
        self.assertIsNone(spec.quality_pair)


class EvidenceRefTest(unittest.TestCase):
    def test_evidence_ref_serialized(self):
        """EvalCaseResult.evidence_ref 序列化输出（D-02 M5）。"""
        r = EvalCaseResult(case_id="c1", title="t", severity="high",
                           verdict=EvalVerdict.FAIL, duration_ms=1.0,
                           rule_type="exit_code", version="1",
                           reason="bad", evidence_ref="src/x.py:12")
        d = r.to_dict()
        self.assertEqual(d["evidence_ref"], "src/x.py:12")
        self.assertEqual(d["result"], "FAIL")

    def test_evidence_ref_default_none(self):
        """无 evidence_ref 默认 None（向后兼容既有用例）。"""
        r = EvalCaseResult(case_id="c2", title="t", severity="low",
                           verdict=EvalVerdict.PASS, duration_ms=0.5,
                           rule_type="text_contains", version="1")
        self.assertIsNone(r.evidence_ref)


class AssertionBridgeTest(unittest.TestCase):
    def test_finding_to_eval_case_pass(self):
        """桥接：finding 行号在产物范围内 → 断言 PASS。"""
        with tempfile.TemporaryDirectory() as td:
            art = Path(td) / "artifact.py"
            art.write_text("\n".join(f"line{i}" for i in range(10)), encoding="utf-8")
            case = finding_to_eval_case(
                {"id": "SEC-001", "title": "sql injection", "line": 5, "severity": "critical"},
                str(art))
            self.assertEqual(case.case_id, "QP-SEC-001")
            self.assertEqual(case.severity, "critical")
            self.assertIn("assertion-bridge", case.tags)

    def test_finding_to_eval_case_fail_on_missing_line(self):
        """桥接：finding 行号超出产物 → 断言 FAIL（证据引用无效）。"""
        with tempfile.TemporaryDirectory() as td:
            art = Path(td) / "artifact.py"
            art.write_text("x = 1\n", encoding="utf-8")
            case = finding_to_eval_case(
                {"id": "QE-1", "title": "x", "line": 99, "severity": "low"}, str(art))
            from loop_core.evals import EvalRunner
            runner = EvalRunner([case])
            report = runner.run()
            self.assertEqual(report.overall.value, "FAIL")


class RecomputeDetectionTest(unittest.TestCase):
    def _write_recompute_events(self, root: Path, events: list[dict]) -> None:
        p = root / ".ai" / "evidence" / "observability" / "recompute-events.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        with p.open("w", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps({"ts": now, **ev}) + "\n")

    def test_single_fail_is_report_only(self):
        """单次复算失败 → report 级（不翻转 verdict）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".ai").mkdir()
            self._write_recompute_events(root, [
                {"task_id": "T-1", "report_ref": "r1", "result": "FAIL"},
            ])
            health = GuardHealth(root)
            findings = health.recompute_detection()
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["finding"], "RECOMPUTE_REPORT")
            self.assertNotEqual(findings[0]["severity"], "fail-closed")

    def test_three_consecutive_fails_escalate_fail_closed(self):
        """连续 3 次失败 → fail-closed（overall FAIL）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".ai").mkdir()
            self._write_recompute_events(root, [
                {"task_id": "T-1", "report_ref": "r1", "result": "FAIL"},
                {"task_id": "T-1", "report_ref": "r2", "result": "FAIL"},
                {"task_id": "T-1", "report_ref": "r3", "result": "FAIL"},
            ])
            health = GuardHealth(root)
            findings = health.recompute_detection()
            self.assertEqual(findings[0]["finding"], "RECOMPUTE_BROKEN")
            self.assertEqual(findings[0]["severity"], "fail-closed")
            integrity = health.integrity_check()
            self.assertEqual(integrity["overall"], "FAIL")

    def test_pass_breaks_trailing_fail_chain(self):
        """PASS 中断连续失败链 → 不升级。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".ai").mkdir()
            self._write_recompute_events(root, [
                {"task_id": "T-1", "report_ref": "r1", "result": "FAIL"},
                {"task_id": "T-1", "report_ref": "r2", "result": "FAIL"},
                {"task_id": "T-1", "report_ref": "r3", "result": "PASS"},
            ])
            health = GuardHealth(root)
            findings = health.recompute_detection()
            self.assertFalse(any(f["finding"] == "RECOMPUTE_BROKEN" for f in findings))


class RoleContractTest(unittest.TestCase):
    def test_quality_roles_have_t0133_when_to_use(self):
        """质量线程角色契约包含 T-0133 动作级触发与只读规范。"""
        for path in ("agents/quality-engineer/SKILL.md",
                     "agents/test-engineer/SKILL.md",
                     "agents/security-engineer/SKILL.md",
                     "agents/independent-reviewer/SKILL.md"):
            text = (ROOT / path).read_text(encoding="utf-8")
            self.assertIn("T-0133", text, f"{path} missing T-0133 marker")
            self.assertIn("只读校验规范", text, f"{path} missing read-only spec")

    def test_main_thread_has_quality_pair_rule(self):
        """main-thread 编排协议含质量配对规则。"""
        text = (ROOT / "agents/main-thread/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("质量配对", text)


if __name__ == "__main__":
    unittest.main()
