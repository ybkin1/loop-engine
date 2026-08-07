# -*- coding: utf-8 -*-
"""
test_delegation.py — T-0134 P4 委托模式测试。

覆盖：LoopMode DELEGATED/MANUAL 枚举 + fail-closed 回退 / 委托链
register/check/revoke 全路径 / 结论包生成三要素 / 升级协议文档在位。
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".zcode" / "tools"))
sys.path.insert(0, str(ROOT))

from loop_core.router import LoopMode  # noqa: E402


class LoopModeEnumTest(unittest.TestCase):
    def test_delegated_and_manual_exist(self):
        """DELEGATED / MANUAL 枚举存在（T-0134 AC-01）。"""
        self.assertIn("delegated", LoopMode._value2member_map_)
        self.assertIn("manual", LoopMode._value2member_map_)

    def test_unknown_mode_falls_back_to_full(self):
        """未知 loop_mode → FULL（fail-closed，绝不 LIGHTWEIGHT）。"""
        from loop_core.intent_router_modes import ActiveTaskSnapshot
        snap = ActiveTaskSnapshot.from_task({"id": "T-X", "loop_mode": "bogus_mode"})
        self.assertEqual(snap.loop_mode, LoopMode.FULL)

    def test_missing_mode_falls_back_to_full(self):
        """缺失 loop_mode → FULL（fail-closed）。"""
        from loop_core.intent_router_modes import ActiveTaskSnapshot
        snap = ActiveTaskSnapshot.from_task({"id": "T-X"})
        self.assertEqual(snap.loop_mode, LoopMode.FULL)

    def test_known_modes_still_resolve(self):
        """既有模式正常解析（LIGHTWEIGHT/STANDARD/FULL/DELEGATED/MANUAL）。"""
        from loop_core.intent_router_modes import ActiveTaskSnapshot
        for name, value in (("FULL", "full"), ("DELEGATED", "delegated"),
                            ("MANUAL", "manual"), ("LIGHTWEIGHT", "lightweight")):
            snap = ActiveTaskSnapshot.from_task({"id": "T-X", "loop_mode": value})
            self.assertEqual(snap.loop_mode.value, value, name)


class DelegationChainTest(unittest.TestCase):
    def _chain(self, root: Path, tasks: str, chain: str = "C-TEST") -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / ".zcode" / "tools" / "gov_delegation.py"),
             str(root), "register", "--chain", chain, "--tasks", tasks],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def _gates_file(self, root: Path) -> Path:
        p = root / ".ai" / "gates.yaml"
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text("gates: []\n", encoding="utf-8")
        return p

    def test_register_check_revoke_flow(self):
        """委托链全路径：register → check 0 → revoke → check 2。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._gates_file(root)
            self._chain(root, "T-A,T-B", "C-1")
            chk = subprocess.run(
                [sys.executable, str(ROOT / ".zcode" / "tools" / "gov_delegation.py"),
                 str(root), "check", "--task", "T-A"],
                capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
            self.assertEqual(chk.returncode, 0, chk.stdout)
            rev = subprocess.run(
                [sys.executable, str(ROOT / ".zcode" / "tools" / "gov_delegation.py"),
                 str(root), "revoke", "--chain", "C-1"],
                capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
            self.assertEqual(rev.returncode, 0)
            chk2 = subprocess.run(
                [sys.executable, str(ROOT / ".zcode" / "tools" / "gov_delegation.py"),
                 str(root), "check", "--task", "T-A"],
                capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
            self.assertEqual(chk2.returncode, 2, "revoked chain must fail closed")

    def test_task_outside_chain_fails_closed(self):
        """链外任务 → check 2（fail-closed）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._gates_file(root)
            self._chain(root, "T-A")
            chk = subprocess.run(
                [sys.executable, str(ROOT / ".zcode" / "tools" / "gov_delegation.py"),
                 str(root), "check", "--task", "T-Z"],
                capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
            self.assertEqual(chk.returncode, 2)

    def test_revoke_keeps_record(self):
        """revoke 不删除记录（append-only，status 变更）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._gates_file(root)
            self._chain(root, "T-A", "C-2")
            subprocess.run(
                [sys.executable, str(ROOT / ".zcode" / "tools" / "gov_delegation.py"),
                 str(root), "revoke", "--chain", "C-2"],
                capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
            import yaml
            doc = yaml.safe_load((root / ".ai" / "gates.yaml").read_text(encoding="utf-8"))
            chains = [d for d in doc.get("delegations", []) if d["chain_id"] == "C-2"]
            self.assertEqual(len(chains), 1)
            self.assertEqual(chains[0]["status"], "revoked")


class ConclusionPacketTest(unittest.TestCase):
    def test_packet_three_elements(self):
        """结论包三要素：成果一句话 / 演示 / 证据路径。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            proc = subprocess.run(
                [sys.executable, str(ROOT / ".zcode" / "tools" / "conclusion_packet.py"),
                 str(root), "--task", "T-1", "--summary", "功能完成",
                 "--demo", "冒烟通过", "--evidence", ".ai/x.md,.ai/y.md"],
                capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            out = root / ".ai" / "evidence" / "T-1" / "conclusion-packet.md"
            text = out.read_text(encoding="utf-8")
            self.assertIn("功能完成", text)      # 成果一句话
            self.assertIn("冒烟通过", text)      # 演示
            self.assertIn(".ai/x.md", text)      # 证据路径
            self.assertIn("验收对象是成果", text)


class EscalationProtocolDocTest(unittest.TestCase):
    def test_escalation_doc_exists(self):
        """升级协议文档在位（4 类价值问题 + 选择题形态）。"""
        text = (ROOT / "docs" / "09-escalation-protocol.md").read_text(encoding="utf-8")
        self.assertIn("4 类", text)
        self.assertIn("产品取舍", text)
        self.assertIn("外部边界", text)
        self.assertIn("选择题", text)


if __name__ == "__main__":
    unittest.main()
