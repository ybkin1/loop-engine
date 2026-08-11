# -*- coding: utf-8 -*-
"""
test_quota_decision.py — T-0156 配额决策路由测试。

覆盖：5 态决策矩阵（pending→ask / 悬空→repair / 超预算→quiet /
返工→wait / 正常→deliver / 异常→wait fail-safe）；/loop-quota CLI
只建议不执行。
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from loop_engine.quota_decision import (  # noqa: E402
    QuotaContext, decide_quota, decide_quota_safe,
)


class QuotaDecisionTest(unittest.TestCase):
    def test_pending_gate_asks(self):
        r = decide_quota(QuotaContext(pending_gates=["G-T-1-REQUIREMENTS"]))
        self.assertEqual(r["decision"], "ask")
        self.assertIn("G-T-1", r["reason"])

    def test_stale_rounds_repair(self):
        r = decide_quota(QuotaContext(stale_rounds=2))
        self.assertEqual(r["decision"], "repair")
        self.assertIn("stale", r["reason"])

    def test_over_budget_quiet(self):
        r = decide_quota(QuotaContext(cost_tokens=900, budget_tokens=1000))
        self.assertEqual(r["decision"], "quiet")
        self.assertEqual(r["factors"]["budget_ratio"], 0.9)

    def test_high_rework_wait(self):
        r = decide_quota(QuotaContext(rework_ratio=0.5))
        self.assertEqual(r["decision"], "wait")

    def test_normal_deliver(self):
        r = decide_quota(QuotaContext(cost_tokens=100, budget_tokens=1000, rework_ratio=0.1))
        self.assertEqual(r["decision"], "deliver")
        self.assertIn("no blockers", r["reason"])

    def test_priority_order(self):
        """优先级：pending gate 优先于悬空/预算。"""
        r = decide_quota(QuotaContext(pending_gates=["G-1"], stale_rounds=1,
                                      cost_tokens=900, budget_tokens=1000))
        self.assertEqual(r["decision"], "ask", "pending gate 优先")

    def test_fail_safe_input_error_wait(self):
        """输入异常（budget_tokens=0 且 cost 高）→ 不崩溃，正常决策。"""
        r = decide_quota(QuotaContext(cost_tokens=500, budget_tokens=0))
        # budget=0 → budget_ratio None → 跳过 quiet，看返工/正常
        self.assertIn(r["decision"], ("deliver", "wait"))

    def test_cli_advisory_only(self):
        """/loop-quota CLI 可调用且只建议（输出 advisory 标注）。"""
        proc = subprocess.run(
            [sys.executable, str(ROOT / "src" / "loop_engine" / "cli_entries.py"),
             "loop-quota", str(ROOT)],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT), timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("decision:", proc.stdout)
        self.assertIn("advisory only", proc.stdout)

    def test_safe_returns_dict(self):
        """decide_quota_safe 从真实项目读取，返回 5 态之一。"""
        r = decide_quota_safe(ROOT)
        self.assertIn("decision", r)
        self.assertIn(r["decision"], ("deliver", "ask", "wait", "repair", "quiet"))


class QuotaFailSafeTest(unittest.TestCase):
    """T-0156 审查 P2 修复：fail-safe 语义（真实驱动 decide_quota_safe fallback）。"""

    def _stub_cost_tracker(self, root: Path, summary: dict):
        """注入假 loop_engine.cost_tracker 模块（真实驱动 decide_quota_safe）。"""
        import types
        import loop_engine.quota_decision as qd
        fake = types.ModuleType("loop_engine.cost_tracker")
        class FakeTracker:
            def __init__(self, _root):
                pass
            def summary(self):
                return dict(summary)
        fake.CostTracker = FakeTracker
        # 从 sys.modules 注入（src 布局下 import 优先命中 sys.modules）
        import sys as _sys
        _sys.modules["loop_engine.cost_tracker"] = fake
        self.addCleanup(lambda: _sys.modules.pop("loop_engine.cost_tracker", None))

    def test_cost_unavailable_waits(self):
        """cost 数据不可得 → wait（不确定默认保守，不 deliver）。"""
        import loop_engine.quota_decision as qd
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".ai").mkdir(parents=True)
            (root / ".ai" / "gates.yaml").write_text("gates: []\n", encoding="utf-8")
            # 无 cost 数据（注入 summary 抛出）→ cost_available False
            def boom(_root):
                raise RuntimeError("no cost data")
            import types
            import sys as _sys
            fake = types.ModuleType("loop_engine.cost_tracker")
            fake.CostTracker = boom
            _sys.modules["loop_engine.cost_tracker"] = fake
            self.addCleanup(lambda: _sys.modules.pop("loop_engine.cost_tracker", None))
            r = qd.decide_quota_safe(root)
            self.assertEqual(r["decision"], "wait")
            self.assertFalse(r["factors"].get("cost_available", True))

    def test_budget_missing_waits(self):
        """方案 A：summary 无 budget_tokens 键 → budget 不确定 → wait。

        真实驱动 decide_quota_safe（注入假 cost_tracker），验证 fallback
        分支而非直接构造 QuotaContext。
        """
        import loop_engine.quota_decision as qd
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".ai").mkdir(parents=True)
            (root / ".ai" / "gates.yaml").write_text("gates: []\n", encoding="utf-8")
            self._stub_cost_tracker(root, {
                "total_tokens": 100, "rework_ratio": 0.1,  # 无 budget_tokens
            })
            r = qd.decide_quota_safe(root)
            self.assertEqual(r["decision"], "wait", "budget 缺失应视为不确定 → wait")
            self.assertTrue(r["factors"].get("cost_available"))
            self.assertFalse(r["factors"].get("budget_available"))

    def test_budget_present_delivers(self):
        """budget_tokens 存在且正常 → deliver（真实 fallback 路径）。"""
        import loop_engine.quota_decision as qd
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".ai").mkdir(parents=True)
            (root / ".ai" / "gates.yaml").write_text("gates: []\n", encoding="utf-8")
            self._stub_cost_tracker(root, {
                "total_tokens": 100, "budget_tokens": 1000, "rework_ratio": 0.1,
            })
            r = qd.decide_quota_safe(root)
            self.assertEqual(r["decision"], "deliver")
            self.assertEqual(r["factors"]["budget_ratio"], 0.1)

    def test_over_budget_quiet_via_safe(self):
        """真实路径：budget 存在且超阈值 → quiet。"""
        import loop_engine.quota_decision as qd
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".ai").mkdir(parents=True)
            (root / ".ai" / "gates.yaml").write_text("gates: []\n", encoding="utf-8")
            self._stub_cost_tracker(root, {
                "total_tokens": 900, "budget_tokens": 1000, "rework_ratio": 0.1,
            })
            r = qd.decide_quota_safe(root)
            self.assertEqual(r["decision"], "quiet")
            self.assertEqual(r["factors"]["budget_ratio"], 0.9)

    def test_same_name_module_in_root_not_imported(self):
        """T-0177 H4 回归：目标项目根存在同名 loop_engine 模块时不得被导入。

        原实现 sys.path.insert(0, root) 会让 root 下的 loop_engine.py 劫持
        cost_tracker 导入（H4 评审发现）。修复后使用包内相对导入，仅同包
        cost_tracker 可被使用。
        """
        import loop_engine.quota_decision as qd
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".ai").mkdir(parents=True)
            (root / ".ai" / "gates.yaml").write_text("gates: []\n", encoding="utf-8")
            # 在目标项目根放置同名模块（劫持向量）
            (root / "loop_engine.py").write_text(
                "class CostTracker:\n"
                "    def __init__(self, _root): raise ImportError('hijacked')\n",
                encoding="utf-8",
            )
            self._stub_cost_tracker(root, {
                "total_tokens": 100, "budget_tokens": 1000, "rework_ratio": 0.1,
            })
            r = qd.decide_quota_safe(root)
            # 不被 root 下同名文件劫持：正常走注入的 stub（deliver）
            self.assertEqual(r["decision"], "deliver")


if __name__ == "__main__":
    unittest.main()
