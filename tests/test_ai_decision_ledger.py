"""
Tests for loop_core.approval_ledger.AiDecisionRecord / AiDecisionLedger
(T-0104 设计-3 §3.3.4) — AI 决策记录账本。

Covers:
- AiDecisionRecord.create() auto-generation (AD-{uuid12}, recorded_at)
- to_json_row / from_json_row round-trip
- AiDecisionLedger.append() writes .ai/ledger/ai-decisions.jsonl (append-only)
- chain_hash 链校验（仿 test_execution_ledger：篡改/插入 → 断裂可检测）
- ledger_guard 只读兼容验证：hooks/scripts/ledger_guard.py 对新文件
  append+chain 校验通过（零 hook 改动成立的实证）
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.approval_ledger import (  # noqa: E402
    AiDecisionLedger,
    AiDecisionRecord,
)

SCRIPTS = Path(__file__).resolve().parent.parent / "hooks" / "scripts"
LEDGER_GUARD = str(SCRIPTS / "ledger_guard.py")


@pytest.fixture
def tmp_root():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def _sample_decision(decision_id: str = "AD-deadbeef1234") -> AiDecisionRecord:
    return AiDecisionRecord(
        decision_id=decision_id,
        task_id="T-0104",
        phase="S4-implementation",
        role_id="developer",
        decision="[AI判断] 选择了分批实现而不是一次性全量实现",
        why_not_ask="低风险且可在既有批准范围内兜底",
        impact_if_wrong="错误则影响交付节奏而非正确性，可在 S5 质量门发现",
        reason_ref="DEV-S4-001",
        recorded_at="2026-08-02T10:00:00+00:00",
    )


def _run_ledger_guard(project_root: str, tool_input: dict) -> subprocess.CompletedProcess:
    """以 ZCode hook 调用方式子进程运行 ledger_guard.py（只读验证，不改 hook）。"""
    hook_input = json.dumps({
        "cwd": project_root,
        "tool_name": tool_input.get("tool_name", "Write"),
        "tool_input": tool_input,
    })
    env = {**os.environ, "ZCODE_PROJECT_DIR": project_root}
    return subprocess.run(
        [sys.executable, LEDGER_GUARD],
        input=hook_input, capture_output=True, text=True, timeout=15, env=env,
    )


class TestAiDecisionRecord:
    def test_create_generates_id_and_timestamp(self):
        rec = AiDecisionRecord.create(
            task_id="T-0104",
            phase="S4-implementation",
            role_id="developer",
            decision="d",
            why_not_ask="w",
            impact_if_wrong="i",
            reason_ref="DEV-S4-001",
        )
        assert rec.decision_id.startswith("AD-")
        assert len(rec.decision_id) == 15  # "AD-" + 12 hex
        assert all(c in "0123456789abcdef" for c in rec.decision_id[3:])
        assert rec.recorded_at  # ISO-8601 UTC
        assert rec.reason_ref == "DEV-S4-001"

    def test_create_defaults_reason_ref_none(self):
        rec = AiDecisionRecord.create(
            task_id="T-0104", phase="S4-implementation",
            role_id="main-thread", decision="d", why_not_ask="w",
            impact_if_wrong="i",
        )
        assert rec.reason_ref is None

    def test_json_round_trip(self):
        rec = _sample_decision()
        restored = AiDecisionRecord.from_json_row(json.loads(rec.to_json_row()))
        assert restored == rec

    def test_no_human_actor_field(self):
        """AI 决策记录不混入 ApprovalRecord 的 human_actor 语义。"""
        rec = _sample_decision()
        assert "human_actor" not in json.loads(rec.to_json_row())


class TestAiDecisionLedger:
    def test_append_creates_ledger_file(self, tmp_root):
        ledger = AiDecisionLedger(tmp_root)
        ledger.append(_sample_decision())
        assert ledger.exists
        assert ledger.path == tmp_root / ".ai" / "ledger" / "ai-decisions.jsonl"

    def test_read_records_round_trip(self, tmp_root):
        ledger = AiDecisionLedger(tmp_root)
        rec = _sample_decision()
        ledger.append(rec)
        records = ledger.read_records()
        assert len(records) == 1
        assert records[0].decision_id == rec.decision_id
        assert records[0].role_id == "developer"
        assert records[0].why_not_ask == rec.why_not_ask

    def test_append_returns_chain_hash(self, tmp_root):
        ledger = AiDecisionLedger(tmp_root)
        ch = ledger.append(_sample_decision())
        assert len(ch) == 64
        assert all(c in "0123456789abcdef" for c in ch)

    def test_chain_verified_multiple_entries(self, tmp_root):
        ledger = AiDecisionLedger(tmp_root)
        ledger.append(_sample_decision("AD-aaa000000001"))
        ledger.append(_sample_decision("AD-aaa000000002"))
        valid, reason = ledger.verify_chain()
        assert valid is True
        assert "2 entries" in reason

    def test_empty_ledger_chain_valid(self, tmp_root):
        ledger = AiDecisionLedger(tmp_root)
        valid, reason = ledger.verify_chain()
        assert valid is True
        assert "empty" in reason

    def test_tampered_entry_detected(self, tmp_root):
        ledger = AiDecisionLedger(tmp_root)
        ledger.append(_sample_decision())
        path = ledger.path
        tampered = path.read_text(encoding="utf-8").replace(
            "developer", "HACKED-role"
        )
        path.write_text(tampered, encoding="utf-8")
        valid, reason = ledger.verify_chain()
        assert valid is False
        assert "mismatch" in reason.lower() or "broken" in reason.lower()

    def test_inserted_fake_line_detected(self, tmp_root):
        ledger = AiDecisionLedger(tmp_root)
        ledger.append(_sample_decision())
        path = ledger.path
        fake = json.dumps({"decision_id": "AD-fake", "chain_hash": "0" * 64})
        path.write_text(path.read_text(encoding="utf-8") + "\n" + fake + "\n",
                        encoding="utf-8")
        valid, _ = ledger.verify_chain()
        assert valid is False

    def test_find_by_task(self, tmp_root):
        ledger = AiDecisionLedger(tmp_root)
        ledger.append(_sample_decision("AD-aaa000000001"))
        other = _sample_decision("AD-aaa000000002")
        other.task_id = "T-9999"
        ledger.append(other)
        found = ledger.find_by_task("T-0104")
        assert len(found) == 1
        assert found[0].task_id == "T-0104"

    # ── ledger_guard 兼容验证（只读，零 hook 改动） ─────────────────────

    def test_ledger_guard_accepts_new_file_append(self, tmp_root):
        """ledger_guard 对 ai-decisions.jsonl 的追加 + 链校验通过（exit 0）。

        D-03 §3.3.4 前置验证：verify_ledger_chain 对"空文件起步的新链"
        行为与 executions.jsonl 一致 → 零 hook 改动成立。
        """
        ledger = AiDecisionLedger(tmp_root)
        ledger.append(_sample_decision())
        ledger.append(_sample_decision("AD-aaa000000002"))

        content = ledger.path.read_text(encoding="utf-8")
        r = _run_ledger_guard(str(tmp_root), {
            "tool_name": "Write",
            "path": str(ledger.path),
            "content": content,
        })
        assert r.returncode == 0, f"ledger_guard blocked: {r.stdout} {r.stderr}"

    def test_ledger_guard_blocks_tampered_new_file(self, tmp_root):
        """篡改后的 ai-decisions.jsonl 被 ledger_guard 阻断（exit 2）。"""
        ledger = AiDecisionLedger(tmp_root)
        ledger.append(_sample_decision())
        tampered = ledger.path.read_text(encoding="utf-8").replace(
            "S4-implementation", "S4-HACKED"
        )
        r = _run_ledger_guard(str(tmp_root), {
            "tool_name": "Write",
            "path": str(ledger.path),
            "content": tampered,
        })
        assert r.returncode == 2
