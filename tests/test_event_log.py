# -*- coding: utf-8 -*-
"""
test_event_log.py — T-0155 事件溯源影子层测试。

覆盖：append/read_events 回放；事件类型覆盖（task/gate/evidence/handoff）；
replay_check 一致性（投影=事件回放）；写入失败吞掉（观测不阻断业务）。
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".zcode" / "tools"))

from event_log import (  # noqa: E402
    EVENT_TYPES, append, events_file, read_events, replay_check,
)


class EventLogTest(unittest.TestCase):
    def _root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        # 最小投影骨架（state_sha256 锚点需要）
        (root / ".ai").mkdir(parents=True)
        (root / ".ai" / "state.yaml").write_text(
            "schema_version: 1\ncurrent_phase: S6-delivery\ncurrent_task_id: null\n",
            encoding="utf-8")
        (root / ".ai" / "gates.yaml").write_text("schema_version: 1\ngates: []\n", encoding="utf-8")
        (root / ".ai" / "task_graph.yaml").write_text("schema_version: 1\ntasks: []\n", encoding="utf-8")
        return root, td

    def test_append_and_read(self):
        root, td = self._root()
        try:
            ok = append(root, "task_registered", task_id="T-X", actor="ai",
                        detail={"depends_on": "T-0"})
            self.assertTrue(ok)
            ok2 = append(root, "gate_approved", gate_id="G-T-X-REQUIREMENTS",
                         task_id="T-X", actor="user")
            self.assertTrue(ok2)
            events = read_events(root)
            self.assertEqual(len(events), 2)
            self.assertEqual(events[0]["event_type"], "task_registered")
            self.assertEqual(events[0]["task_id"], "T-X")
            self.assertEqual(events[1]["gate_id"], "G-T-X-REQUIREMENTS")
            self.assertEqual(events[1]["actor"], "user")
            # tail 截断
            tail = read_events(root, tail=1)
            self.assertEqual(len(tail), 1)
            self.assertEqual(tail[0]["event_type"], "gate_approved")
        finally:
            td.cleanup()

    def test_event_types_coverage(self):
        """7 类事件类型覆盖（task/gate/evidence/handoff 生命周期）。"""
        for t in ("task_registered", "task_status_changed", "gate_created",
                  "gate_approved", "gate_completed", "evidence_attached",
                  "handoff_generated"):
            self.assertIn(t, EVENT_TYPES, f"missing event type: {t}")

    def test_invalid_type_dropped(self):
        root, td = self._root()
        try:
            ok = append(root, "bogus_type")
            self.assertFalse(ok, "未知类型应被丢弃")
            self.assertEqual(read_events(root), [], "未知类型不得写入")
        finally:
            td.cleanup()

    def test_replay_check_consistent(self):
        root, td = self._root()
        try:
            append(root, "task_registered", task_id="T-X")
            ok, msg = replay_check(root)
            self.assertTrue(ok, msg)
            self.assertIn("consistent", msg)
        finally:
            td.cleanup()

    def test_replay_check_detects_drift(self):
        root, td = self._root()
        try:
            append(root, "task_registered", task_id="T-X")
            # 事件记录后修改 state.yaml（模拟外部改状态）
            (root / ".ai" / "state.yaml").write_text(
                "schema_version: 1\ncurrent_phase: S6-delivery\ncurrent_task_id: T-999\n",
                encoding="utf-8")
            ok, msg = replay_check(root)
            self.assertFalse(ok, "投影漂移必须被事件链检测")
            self.assertIn("drifted", msg)
        finally:
            td.cleanup()

    def test_append_failure_swallowed(self):
        """写入失败吞掉（观测绝不阻断业务）。"""
        root, td = self._root()
        try:
            # 把事件路径指向不可写位置：events_file 是常量路径，改为用
            # 目录占用模拟失败 —— 用文件替代目录
            ev = events_file(root)
            ev.parent.mkdir(parents=True, exist_ok=True)
            # 用目录占位：删除已建文件并创建同名目录 → 打开失败
            ev.write_text("", encoding="utf-8")
            ev.unlink()
            ev.mkdir()  # 目录占用同名路径 → append 打开失败
            ok = append(root, "handoff_generated")
            self.assertFalse(ok, "写入失败应返回 False（不抛异常）")
        finally:
            td.cleanup()

    def test_read_events_skips_corrupt_lines(self):
        root, td = self._root()
        try:
            append(root, "task_registered", task_id="T-1")
            path = events_file(root)
            with path.open("a", encoding="utf-8") as f:
                f.write("{broken json\n")
            append(root, "gate_created", gate_id="G-1")
            events = read_events(root)
            self.assertEqual(len(events), 2, "损坏行跳过，其余事件保留")
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
