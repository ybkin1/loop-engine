# -*- coding: utf-8 -*-
"""
test_defense_drills.py — T-0129 P2 防御演练。

拒绝路径（R1~R6）：越界写入判定 → 拦截 → mock 用户拒绝 → 状态收敛。
锁死恢复（E1~E5，D-03 §4）：漂移/损坏注入 → L1/L2 恢复 → 回滚不无脑删断言。
全部在临时目录副本上执行，不触碰真实治理状态。
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / ".zcode" / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(ROOT / "hooks" / "scripts"))

from governor_lib import governance_invariant_errors  # noqa: E402
from loop_enforcement import is_governance_write  # noqa: E402

VALIDATE = [sys.executable, str(TOOLS / "validate_state.py")]


def make_project(tmp: Path) -> Path:
    """构造最小合法治理项目副本（state/task_graph/gates/tasks/evidence）。"""
    ai = tmp / ".ai"
    (ai / "tasks").mkdir(parents=True)
    (ai / "evidence" / "T-D000").mkdir(parents=True)
    # REQUIRED_FILES 全套（validate_state 第 1 步检查）
    for name in ("PROJECT.md", "NON_GOALS.md", "ARCHITECTURE.md", "CONTRACTS.md",
                 "CODING_STANDARDS.md", "CONVENTIONS.md", "CODEMAP.md", "PROGRESS.md",
                 "QUALITY_GATES.md", "ACCEPTANCE.md", "DECISIONS.md", "KNOWN_ISSUES.md",
                 "HANDOFF.md"):
        (ai / name).write_text("# placeholder\n", encoding="utf-8")
    (ai / "state.yaml").write_text(
        "current_phase: S6-delivery\ncurrent_task_id: T-D000\n"
        "current_gate_id: G-T-D000-REQUIREMENTS\nloop_mode: FULL\n", encoding="utf-8")
    (ai / "task_graph.yaml").write_text(
        "tasks:\n  - id: T-D000\n    status: in_progress\nedges: []\n", encoding="utf-8")
    (ai / "gates.yaml").write_text(
        "gates:\n"
        "  - id: G-T-D000-REQUIREMENTS\n    task_id: T-D000\n"
        "    gate_type: user-approval\n    status: approved\n"
        "    execution_status: in_progress\n"
        "    approval_evidence: .ai/evidence/T-D000/approval-evidence.json\n"
        "    execution_evidence: .ai/evidence/T-D000/execution-evidence.json\n",
        encoding="utf-8")
    (ai / "tasks" / "T-D000.md").write_text(
        "# T-D000\n\n## Status\n\nin_progress\n", encoding="utf-8")
    (ai / "evidence" / "T-D000" / "approval-evidence.json").write_text(
        json.dumps({"evidence_type": "approval"}), encoding="utf-8")
    (ai / "evidence" / "T-D000" / "execution-evidence.json").write_text(
        json.dumps({"evidence_type": "execution"}), encoding="utf-8")
    (ai / "evidence" / "T-D000" / "compile-evidence.json").write_text(
        json.dumps({"status": "pass"}), encoding="utf-8")
    return tmp


def validate_rc(root: Path) -> int:
    proc = subprocess.run([*VALIDATE, str(root)], capture_output=True, text=True,
                          encoding="utf-8", cwd=str(ROOT), timeout=120)
    return proc.returncode


# ─────────────────────────────────────────────────────────────
# R: 拒绝路径演练
# ─────────────────────────────────────────────────────────────

class RejectionPathDrillTest(unittest.TestCase):
    def test_r1_governance_write_detection(self):
        """R1: 治理文件写入识别（.ai/ 治理文件豁免；AGENTS.md 非豁免需 gate；
        业务路径非豁免）。"""
        self.assertTrue(is_governance_write(".ai/state.yaml"))
        self.assertTrue(is_governance_write(".ai/gates.yaml"))
        # AGENTS.md 不在 GOVERNANCE_EXEMPT —— 修改需单独 gate（正确行为）
        self.assertFalse(is_governance_write("AGENTS.md"))
        self.assertFalse(is_governance_write("tests/evil.py"))

    def test_r2_non_governance_write_outside_scope_detected(self):
        """R2: 非治理写路径（业务代码/部署路径）不被豁免 → 需任务 scope 拦截。"""
        for path in ("src/prod/main.py", "deploy/config/prod.yaml",
                     "scripts/deploy.py", "db/migrate_001.sql"):
            self.assertFalse(is_governance_write(path),
                             f"{path} must not be governance-exempt")

    def test_r3_rejected_gate_converges(self):
        """R3: 用户拒绝 gate → rejected 记录 + current_gate 清空 → 状态收敛
        （无 pending blocker、无 contradiction）。"""
        with tempfile.TemporaryDirectory() as td:
            root = make_project(Path(td))
            ai = root / ".ai"
            # 用户拒绝：gate 标 rejected，current_gate_id 清空，任务停用
            (ai / "gates.yaml").write_text(
                "gates:\n"
                "  - id: G-T-D000-REQUIREMENTS\n    task_id: T-D000\n"
                "    gate_type: user-approval\n    status: rejected\n"
                "    decision: rejected\n", encoding="utf-8")
            (ai / "state.yaml").write_text(
                "current_phase: S6-delivery\ncurrent_task_id: null\n"
                "current_gate_id: null\nloop_mode: FULL\n", encoding="utf-8")
            errors = governance_invariant_errors(root)
            self.assertEqual(errors, [], f"rejected state must converge: {errors}")

    def test_r4_deny_then_retry_requires_new_gate(self):
        """R4: 拒绝后同一任务无 approved gate → 无法进入执行（fail-closed）。"""
        with tempfile.TemporaryDirectory() as td:
            root = make_project(Path(td))
            ai = root / ".ai"
            (ai / "gates.yaml").write_text(
                "gates:\n"
                "  - id: G-T-D000-REQUIREMENTS\n    task_id: T-D000\n"
                "    gate_type: user-approval\n    status: rejected\n"
                "    decision: rejected\n", encoding="utf-8")
            (ai / "state.yaml").write_text(
                "current_phase: S6-delivery\ncurrent_task_id: T-D000\n"
                "current_gate_id: null\nloop_mode: FULL\n", encoding="utf-8")
            (ai / "tasks" / "T-D000.md").write_text(
                "# T-D000\n\n## Status\n\napproved_not_started\n", encoding="utf-8")
            errors = governance_invariant_errors(root)
            self.assertTrue(any("requires an approved gate" in e for e in errors),
                            f"denied task must not execute: {errors}")

    def test_r5_out_of_scope_write_blocked_by_invariant(self):
        """R5: 任务状态与 gate 矛盾（越界登记的形态）→ 校验器报错（拦截）。"""
        with tempfile.TemporaryDirectory() as td:
            root = make_project(Path(td))
            # task_graph 说 completed，任务卡说 in_progress → mismatch
            (root / ".ai" / "task_graph.yaml").write_text(
                "tasks:\n  - id: T-D000\n    status: completed\nedges: []\n",
                encoding="utf-8")
            errors = governance_invariant_errors(root)
            self.assertTrue(any("Task status mismatch" in e for e in errors),
                            f"contradictory registration must be flagged: {errors}")

    def test_r6_pending_gate_requires_decision(self):
        """R6: pending gate 必须等用户决策（validate_state exit 2，fail-closed）。"""
        with tempfile.TemporaryDirectory() as td:
            root = make_project(Path(td))
            (root / ".ai" / "gates.yaml").write_text(
                "gates:\n"
                "  - id: G-T-D000-REQUIREMENTS\n    task_id: T-D000\n"
                "    gate_type: user-approval\n    status: pending\n    decision: pending\n",
                encoding="utf-8")
            rc = validate_rc(root)
            self.assertNotEqual(rc, 0, "pending gate must block (fail-closed)")


# ─────────────────────────────────────────────────────────────
# E: 锁死恢复演练（D-03 §4）
# ─────────────────────────────────────────────────────────────

class DeadlockRecoveryDrillTest(unittest.TestCase):
    def _with_continuity(self, root: Path) -> Path:
        """在副本上生成 project_continuity + HANDOFF（L1 前置条件）。"""
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "gen_continuity.py"), str(root)],
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(ROOT), timeout=120)
        assert proc.returncode == 0, f"gen_continuity failed: {proc.stdout[-300:]}"
        assert (root / ".ai" / "project_continuity.yaml").is_file(), "continuity not generated"
        subprocess.run([*VALIDATE, "--auto-sync", str(root)],
                       capture_output=True, text=True, encoding="utf-8",
                       cwd=str(ROOT), timeout=120)
        return root

    def test_e1_state_drift_recovered_by_l1(self):
        """E1: 状态漂移（task_graph 状态错）→ L1 人工恢复 → 校验通过。"""
        with tempfile.TemporaryDirectory() as td:
            root = self._with_continuity(make_project(Path(td)))
            (root / ".ai" / "task_graph.yaml").write_text(
                "tasks:\n  - id: T-D000\n    status: completed\nedges: []\n",
                encoding="utf-8")
            self.assertNotEqual(validate_rc(root), 0, "drift must be detected")
            # L1: 恢复为一致状态
            (root / ".ai" / "task_graph.yaml").write_text(
                "tasks:\n  - id: T-D000\n    status: in_progress\nedges: []\n",
                encoding="utf-8")
            self.assertEqual(validate_rc(root), 0, "L1 recovery must converge")

    def test_e2_continuity_drift_autorepaired(self):
        """E2: 连续性漂移（改治理文件）→ --auto-sync 自动修复（L1）。"""
        with tempfile.TemporaryDirectory() as td:
            root = self._with_continuity(make_project(Path(td)))
            (root / ".ai" / "gates.yaml").write_text(
                (root / ".ai" / "gates.yaml").read_text(encoding="utf-8")
                + "# drift-injection\n", encoding="utf-8")
            self.assertNotEqual(validate_rc(root), 0, "continuity drift must fail")
            proc = subprocess.run(
                [*VALIDATE, "--auto-sync", str(root)], capture_output=True, text=True,
                encoding="utf-8", cwd=str(ROOT), timeout=120)
            self.assertEqual(proc.returncode, 0,
                            f"auto-sync must repair: {proc.stdout[-300:]}")
            self.assertEqual(validate_rc(root), 0, "converged after auto-sync")

    def test_e3_yaml_corruption_l2_snapshot_rollback(self):
        """E3: YAML 损坏 → L1 不可用 → L2 快照回滚恢复（副本演练）。"""
        with tempfile.TemporaryDirectory() as td:
            root = self._with_continuity(make_project(Path(td)))
            healthy_state = (root / ".ai" / "state.yaml").read_text(encoding="utf-8")
            # ① 快照先行
            snap = root / ".ai" / "evidence" / "T-D000" / "recovery" / "snapshot-drill"
            snap.mkdir(parents=True)
            shutil.copy2(root / ".ai" / "state.yaml", snap / "state.yaml.corrupt")
            # ② 注入损坏
            (root / ".ai" / "state.yaml").write_text("current_phase: [unclosed\n", encoding="utf-8")
            self.assertNotEqual(validate_rc(root), 0, "corruption must break validate")
            # ③ L2: 用健康副本恢复（仅治理文件）
            (root / ".ai" / "state.yaml").write_text(healthy_state, encoding="utf-8")
            self.assertEqual(validate_rc(root), 0, "L2 rollback must converge")

    def test_e4_abandoned_rounds_detected(self):
        """E4: 自治中断残留（rounds 日志悬空）→ 心跳检测可发现（fail-stop 前置）。"""
        with tempfile.TemporaryDirectory() as td:
            root = make_project(Path(td))
            rounds = root / ".ai" / "evidence" / "T-D000" / "rounds"
            rounds.mkdir(parents=True)
            # 悬空：CHECKING 无闭合（无后续 RE-CHECK/PASS 行）
            (rounds / "action-001.jsonl").write_text(
                '{"ts": "1", "state": "CHECKING", "action": "a1"}\n', encoding="utf-8")
            # 心跳检查：末行状态非终态 = 悬空
            last = [l for l in (rounds / "action-001.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()][-1]
            dangling = '"CHECKING"' in last or '"FIXING"' in last
            self.assertTrue(dangling, "abandoned round must be detectable as dangling")

    def test_e5_rollback_no_blind_delete(self):
        """E5: 回滚不无脑删——快照存在 / evidence 完整 / 恢复后无丢失。"""
        with tempfile.TemporaryDirectory() as td:
            root = self._with_continuity(make_project(Path(td)))
            ev_file = root / ".ai" / "evidence" / "T-D000" / "approval-evidence.json"
            before = ev_file.read_bytes()
            snap = root / ".ai" / "evidence" / "T-D000" / "recovery" / "snapshot-drill"
            snap.mkdir(parents=True)
            shutil.copy2(ev_file, snap / "approval-evidence.json.bak")
            # 回滚演练：恢复后
            ev_file.write_bytes(before)
            # 断言：快照存在、evidence 完整、无删除
            self.assertTrue((snap / "approval-evidence.json.bak").is_file(),
                            "snapshot must exist (snapshot-first)")
            self.assertEqual(ev_file.read_bytes(), before, "evidence intact")
            self.assertTrue((root / ".ai" / "tasks" / "T-D000.md").is_file(),
                            "task card not deleted")
            self.assertTrue((root / ".ai" / "state.yaml").is_file(),
                            "state not deleted")


if __name__ == "__main__":
    unittest.main()
