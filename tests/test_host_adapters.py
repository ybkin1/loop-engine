"""
test_host_adapters.py — T-0177 M1 多宿主适配器回归测试。

背景：ClaudeCodeAdapter 原为 38 行纯继承 ZCodeAdapter——宿主身份虚假
（Claude Code 没有 .zcode/ 目录），多宿主只是名义。

修复：共享实现提取到 _host_base.HostAdapterBase（config_dir_name 参数化），
ZCodeAdapter（.zcode/）与 ClaudeCodeAdapter（.claude/）各自独立声明宿主。
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from loop_engine.adapters import ClaudeCodeAdapter, ZCodeAdapter
from loop_core.enforcement import EnforcementLevel


class TestZCodeAdapter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".ai").mkdir(parents=True)
        (self.root / ".ai" / "state.yaml").write_text("current_task_id: T-0001\n", encoding="utf-8")
        self.adapter = ZCodeAdapter(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_host_identity(self):
        self.assertEqual(self.adapter.host_name, "ZCode")
        self.assertEqual(self.adapter.enforcement_level, EnforcementLevel.STRONG)

    def test_config_dir_is_zcode(self):
        self.assertEqual(self.adapter._config_dir, self.root / ".zcode")

    def test_agent_id_launch_records_evidence(self):
        """launch_agent 记录证据文件（与 test_dispatcher 依赖一致）。

        注：agent_id 为秒级时间戳生成（原有行为，同秒多次调用不保证唯一），
        此处只验证格式与证据落盘，不改变行为。
        """
        agent_id = self.adapter.launch_agent("reviewer", "p", [], "out.json")
        self.assertTrue(agent_id.startswith("agent_reviewer_"))
        log = self.root / ".ai" / "evidence" / "agent_logs" / f"{agent_id}.json"
        self.assertTrue(log.exists())
        record = json.loads(log.read_text(encoding="utf-8"))
        self.assertEqual(record["role_id"], "reviewer")

    def test_state_roundtrip(self):
        self.adapter.save_state({"current_task_id": "T-0001", "loop_mode": "FULL"})
        state = self.adapter.load_state()
        self.assertEqual(state["loop_mode"], "FULL")

    def test_evidence_freeze_and_check(self):
        f = self.root / "note.txt"
        f.write_text("hello", encoding="utf-8")
        sha = self.adapter.freeze_evidence("ev-1", {"note": "note.txt"})
        self.assertTrue(self.adapter.check_evidence_freshness("ev-1"))
        self.assertEqual(len(sha), 64)


class TestClaudeCodeAdapter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".ai").mkdir(parents=True)
        (self.root / ".ai" / "state.yaml").write_text("current_task_id: T-0001\n", encoding="utf-8")
        self.adapter = ClaudeCodeAdapter(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_host_identity(self):
        self.assertEqual(self.adapter.host_name, "Claude Code")
        self.assertEqual(self.adapter.enforcement_level, EnforcementLevel.STRONG)

    def test_config_dir_is_claude(self):
        """M1 核心：Claude Code 宿主使用 .claude/ 而非 .zcode/。"""
        self.assertEqual(self.adapter._config_dir, self.root / ".claude")
        self.assertNotEqual(self.adapter._config_dir, self.root / ".zcode")

    def test_validate_startup_warns_missing_settings(self):
        result = self.adapter.validate_startup()
        warnings = " ".join(result["warnings"])
        self.assertIn("settings.json", warnings)

    def test_validate_startup_no_warning_with_settings(self):
        claude_dir = self.root / ".claude"
        claude_dir.mkdir(parents=True)
        (claude_dir / "settings.json").write_text("{}", encoding="utf-8")
        # 补全 .ai 治理文件，使基座校验无 errors
        (self.root / ".ai" / "gates.yaml").write_text("gates: []\n", encoding="utf-8")
        (self.root / ".ai" / "task_graph.yaml").write_text("tasks: []\n", encoding="utf-8")
        result = self.adapter.validate_startup()
        self.assertEqual(result["errors"], [])
        self.assertTrue(result["state_usable"])

    def test_state_roundtrip_independent(self):
        """Claude adapter 独立于 ZCode adapter 的状态行为。"""
        self.adapter.save_state({"current_task_id": "T-0001"})
        zcode = ZCodeAdapter(self.root)
        self.assertEqual(zcode.load_state()["current_task_id"], "T-0001")


if __name__ == "__main__":
    unittest.main()
