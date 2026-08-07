# -*- coding: utf-8 -*-
"""
test_t0146_event_vocabulary.py — T-0146 guard-events 词表 BLOCK/REJECTED 测试。

覆盖：RESULT_BLOCK/RESULT_REJECTED 常量存在；事件可写入 guard-events
（check_type 侧信道）；metrics 聚合（build_gate_defense）将 BLOCK/REJECTED
计为 rejected_requests；既有 PASS/FAIL/REPORT 语义不变。
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loop_core.governance_metrics import build_gate_defense  # noqa: E402
from loop_core.observability import (  # noqa: E402
    RESULT_BLOCK, RESULT_FAIL, RESULT_PASS, RESULT_REJECTED, RESULT_REPORT,
    GuardCheckEvent, GuardEventRecorder,
)


class EventVocabularyTest(unittest.TestCase):
    def test_block_rejected_constants_exist(self):
        """T-0146: 词表含 BLOCK / REJECTED。"""
        self.assertEqual(RESULT_BLOCK, "BLOCK")
        self.assertEqual(RESULT_REJECTED, "REJECTED")

    def test_existing_vocabulary_unchanged(self):
        """既有 PASS/FAIL/REPORT 语义不变（兼容）。"""
        self.assertEqual(RESULT_PASS, "PASS")
        self.assertEqual(RESULT_FAIL, "FAIL")
        self.assertEqual(RESULT_REPORT, "REPORT")

    def _recorder_with_dir(self, root: Path) -> GuardEventRecorder:
        """创建 recorder，事件路径指向临时目录（第一参是 path 非 root）。"""
        events = root / ".ai" / "evidence" / "observability" / "guard-events.jsonl"
        events.parent.mkdir(parents=True)
        return GuardEventRecorder(events)

    def test_block_event_recorded(self):
        """BLOCK 事件可写入 guard-events（check_type 侧信道）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rec = self._recorder_with_dir(root)
            ok = rec.record(GuardCheckEvent(
                guard_id="gate_guard", check_type="gate", result=RESULT_BLOCK,
                duration_ms=1.0, timestamp="2026-08-07T00:00:00Z", source="s",
                failure_reason="blocked unauthorized write"))
            self.assertTrue(ok, "BLOCK 事件必须写入成功")
            lines = (root / ".ai" / "evidence" / "observability" / "guard-events.jsonl") \
                .read_text(encoding="utf-8").splitlines()
            ev = json.loads(lines[0])
            self.assertEqual(ev["result"], "BLOCK")
            self.assertEqual(ev["check_type"], "gate")
            self.assertEqual(ev["failure_reason"], "blocked unauthorized write")

    def test_rejected_event_recorded(self):
        """REJECTED 事件可写入 guard-events。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rec = self._recorder_with_dir(root)
            ok = rec.record(GuardCheckEvent(
                guard_id="role_isolation", check_type="gate", result=RESULT_REJECTED,
                duration_ms=1.0, timestamp="2026-08-07T00:00:00Z", source="s"))
            self.assertTrue(ok)
            lines = (root / ".ai" / "evidence" / "observability" / "guard-events.jsonl") \
                .read_text(encoding="utf-8").splitlines()
            self.assertEqual(json.loads(lines[0])["result"], "REJECTED")

    def test_block_rejected_counted_as_rejected_requests(self):
        """T-0146+T-0145 联动：BLOCK/REJECTED 计入 rejected_requests。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rec = self._recorder_with_dir(root)
            for result in (RESULT_BLOCK, RESULT_REJECTED, RESULT_PASS, RESULT_FAIL, RESULT_REPORT):
                rec.record(GuardCheckEvent(
                    guard_id="g", check_type="gate", result=result,
                    duration_ms=1.0, timestamp="2026-08-07T00:00:00Z", source="s"))
            d = build_gate_defense(root)
            self.assertEqual(d["rejected_requests"], 2, "BLOCK+REJECTED 计 2；PASS/FAIL/REPORT 不计")


if __name__ == "__main__":
    unittest.main()
