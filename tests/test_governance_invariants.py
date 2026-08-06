# -*- coding: utf-8 -*-
"""
test_governance_invariants.py — T-0127 P0: 三文件一致性检测（governance_invariant_errors）
正/反例测试。

夹具：临时目录构造 .ai/ 最小治理结构（state/task_graph/gates/tasks/evidence），
调用 governor_lib.governance_invariant_errors 断言期望的漂移错误。
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".zcode" / "tools"))

from governor_lib import governance_invariant_errors  # noqa: E402

TASK = "T-0001"
GATE = "G-T-0001-REQUIREMENTS"


class GovFixture:
    """构造最小治理夹具。"""

    def __init__(self, state_overrides=None, task_graph_status="in_progress",
                 task_file_status="in_progress", gate_status="approved",
                 gate_exec="in_progress", gate_task_id=TASK, include_approval_evidence=True,
                 include_execution_evidence=True, include_compile_evidence=True,
                 include_task_in_graph=True, duplicate_task=False,
                 current_gate_id=GATE):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        ai = root / ".ai"
        (ai / "tasks").mkdir(parents=True)
        (ai / "evidence" / TASK).mkdir(parents=True)

        state = {
            "schema_version": 1,
            "current_phase": "S6-delivery",
            "current_task_id": TASK,
            "current_gate_id": current_gate_id,
            "loop_mode": "FULL",
        }
        state.update(state_overrides or {})
        (ai / "state.yaml").write_text(self._dump(state), encoding="utf-8")

        tasks = []
        if include_task_in_graph:
            tasks.append({"id": TASK, "status": task_graph_status})
        if duplicate_task:
            tasks.append({"id": TASK, "status": task_graph_status})
        (ai / "task_graph.yaml").write_text(
            self._dump({"tasks": tasks, "edges": []}), encoding="utf-8")

        gates = [{
            "id": GATE,
            "task_id": gate_task_id,
            "gate_type": "user-approval",
            "status": gate_status,
            "execution_status": gate_exec,
        }]
        if include_approval_evidence:
            gates[0]["approval_evidence"] = f".ai/evidence/{TASK}/approval-evidence.json"
            (ai / "evidence" / TASK / "approval-evidence.json").write_text(
                json.dumps({"evidence_type": "approval"}), encoding="utf-8")
        if include_execution_evidence:
            gates[0]["execution_evidence"] = f".ai/evidence/{TASK}/execution-evidence.json"
            (ai / "evidence" / TASK / "execution-evidence.json").write_text(
                json.dumps({"evidence_type": "execution"}), encoding="utf-8")
        (ai / "gates.yaml").write_text(self._dump({"gates": gates}), encoding="utf-8")

        (ai / "tasks" / f"{TASK}.md").write_text(
            f"# {TASK}\n\n## Status\n\n{task_file_status}\n", encoding="utf-8")

        if include_compile_evidence:
            (ai / "evidence" / TASK / "compile-evidence.json").write_text(
                json.dumps({"status": "pass"}), encoding="utf-8")

        self.root = root

    @staticmethod
    def _dump(obj) -> str:
        import yaml
        return yaml.safe_dump(obj, allow_unicode=True, sort_keys=False)

    def close(self):
        self.tmp.cleanup()


class GovernanceInvariantsTest(unittest.TestCase):
    def _errors(self, fx) -> list[str]:
        try:
            return governance_invariant_errors(fx.root)
        finally:
            fx.close()

    def test_consistent_state_no_invariant_errors(self):
        """正例：state/task_graph/gates/task 文件完全一致 → 无 invariant 错误。"""
        errors = self._errors(GovFixture())
        self.assertEqual(errors, [])

    def test_task_graph_status_mismatch(self):
        """反例：task_graph 状态与任务卡 Status 不一致。"""
        errors = self._errors(GovFixture(task_graph_status="completed"))
        self.assertTrue(any("Task status mismatch" in e and TASK in e for e in errors),
                        f"expected mismatch error, got: {errors}")

    def test_missing_status_section(self):
        """反例：任务卡缺 ## Status 节。"""
        fx = GovFixture()
        (fx.root / ".ai" / "tasks" / f"{TASK}.md").write_text(
            f"# {TASK}\n\nno status here\n", encoding="utf-8")
        errors = self._errors(fx)
        self.assertTrue(any("Current task status missing or invalid" in e for e in errors),
                        f"expected missing-status error, got: {errors}")

    def test_gate_task_mismatch(self):
        """反例：current_gate_id 属于其他任务。"""
        errors = self._errors(GovFixture(gate_task_id="T-9999"))
        self.assertTrue(any("GATE_TASK_MISMATCH" in e for e in errors),
                        f"expected GATE_TASK_MISMATCH, got: {errors}")

    def test_current_task_missing_in_graph(self):
        """反例：task_graph 无当前任务节点。"""
        errors = self._errors(GovFixture(include_task_in_graph=False))
        self.assertTrue(any("must appear exactly once" in e and "0" in e for e in errors),
                        f"expected exactly-once(0) error, got: {errors}")

    def test_duplicate_task_in_graph(self):
        """反例：task_graph 重复当前任务节点。"""
        errors = self._errors(GovFixture(duplicate_task=True))
        self.assertTrue(any("must appear exactly once" in e and "2" in e for e in errors),
                        f"expected exactly-once(2) error, got: {errors}")

    def test_in_progress_requires_approval_evidence(self):
        """反例：in_progress 但 gate 缺 approval_evidence（文件不存在）。"""
        errors = self._errors(GovFixture(include_approval_evidence=False))
        self.assertTrue(any("requires approval evidence" in e for e in errors),
                        f"expected approval-evidence error, got: {errors}")

    def test_in_progress_requires_execution_evidence(self):
        """反例：in_progress 但缺 execution_evidence。"""
        errors = self._errors(GovFixture(include_execution_evidence=False))
        self.assertTrue(any("requires execution evidence" in e for e in errors),
                        f"expected execution-evidence error, got: {errors}")

    def test_pending_gate_not_current(self):
        """反例：任务有 pending gate 但 current_gate_id 为空。"""
        errors = self._errors(GovFixture(
            current_gate_id=None,
            gate_status="pending",
            gate_exec=None,
        ))
        self.assertTrue(any("Pending gate for current task is not current_gate_id" in e for e in errors),
                        f"expected pending-gate-pointer error, got: {errors}")


if __name__ == "__main__":
    unittest.main()
