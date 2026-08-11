"""
test_degradation_wiring.py — T-0177 H1 退化框架接线回归测试。

背景：degradation.py（DEGRADATION_TABLE / get_adapter_info）与
enforcement_degradation.py 均为零调用者死代码；zcode 能力声明与
zcode_adapter.py（STRONG）互斥（MEDIUM）——"诚实性债务"。

修复：
1. degradation.py 的 zcode caps 统一为 STRONG（T-0174 插件 hooks 已登记，
   PreToolUse 拦截真实生效）。
2. loop_enforcement.py hook 运行时启动诊断接线（stderr 输出宿主级别，
   不改变拦截行为）。
3. enforcement_degradation.py 删除（与 degradation.py 功能重叠，0 引用）。
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tests")))

from loop_engine.degradation import DEGRADATION_TABLE, get_action_for_level, get_adapter_info
from loop_core.enforcement import EnforcementLevel


class TestDegradationTable(unittest.TestCase):
    """DEGRADATION_TABLE 语义保持（表驱动行为不变）。"""

    def test_table_covers_known_constraints(self):
        for cid in (
            "NO_IMPL_WITHOUT_REQUIREMENTS",
            "NO_DEV_WITHOUT_ARCHITECTURE",
            "NO_WRITE_WITHOUT_TASK",
            "NO_DELIVERY_WITHOUT_VERIFICATION",
            "NO_PASS_WITHOUT_REVIEW",
            "NO_NEXT_PHASE_WITH_BLOCKERS",
            "EVIDENCE_STALE_ON_CHANGE",
            "NO_AUTO_GATE_PASS",
        ):
            self.assertIn(cid, DEGRADATION_TABLE)

    def test_unknown_constraint_defaults_warn(self):
        from loop_engine.degradation import DegradationAction
        action = get_action_for_level("UNKNOWN-X", EnforcementLevel.STRONG)
        self.assertEqual(action, DegradationAction.WARN)


class TestHostCapabilityDeclaration(unittest.TestCase):
    """H1: zcode 能力声明统一为 STRONG（与 zcode_adapter.py 一致）。"""

    def test_zcode_is_strong(self):
        info = get_adapter_info("zcode")
        self.assertEqual(info["enforcement_level"], "STRONG")
        self.assertTrue(info["can_block_writes"])
        self.assertTrue(info["can_block_commands"])

    def test_zcode_all_constraints_enforceable(self):
        info = get_adapter_info("zcode")
        enforceable = [c for c in info["constraints"].values() if c["can_enforce"]]
        self.assertEqual(len(enforceable), len(info["constraints"]),
                         "STRONG 级别下全部约束应可强制")

    def test_qoder_is_medium(self):
        info = get_adapter_info("qoder")
        self.assertEqual(info["enforcement_level"], "MEDIUM")

    def test_unknown_host_falls_back_standalone(self):
        info = get_adapter_info("some-unknown-host")
        self.assertEqual(info["enforcement_level"], "ADVISORY")


class TestHookRuntimeWiring(unittest.TestCase):
    """H1: hook 运行时启动诊断接线（stderr 留痕，行为不变）。"""

    def test_hook_stderr_contains_degradation_diagnostic(self):
        """loop_enforcement 运行时输出 [enforcement-degradation] 诊断行。"""
        from test_enforcement import _make_project, _run_hook, STATE_FULL
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL)
            r = _run_hook("loop_enforcement.py", root, {
                "tool_name": "Bash",
                "tool_input": {"command": "git status"},
            })
            self.assertIn("[enforcement-degradation]", r.stderr)
            self.assertIn("level=STRONG", r.stderr)
            self.assertIn("constraints=8/8", r.stderr)

    def test_diagnostic_does_not_change_exit_code(self):
        """诊断不得改变拦截语义（fail-safe：行为不变）。"""
        from test_enforcement import _make_project, _run_hook, STATE_FULL_NO_TASK
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL_NO_TASK)
            r = _run_hook("loop_enforcement.py", root, {
                "tool_name": "Write",
                "tool_input": {"file_path": str(root / "src" / "main.py")},
            })
            self.assertEqual(r.returncode, 2, "无任务 FULL 下业务写入应仍被拦截")


if __name__ == "__main__":
    unittest.main()
