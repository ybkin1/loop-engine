"""Tests for loop_core.execution_ledger — 链式 hash 追加写账本。"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from loop_core.execution_ledger import (
    ChainBrokenError,
    ExecutionLedger,
    ExecutionRecord,
    ExecutionStatus,
)


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture
def tmp_root():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def ledger(tmp_root):
    return ExecutionLedger(tmp_root)


@pytest.fixture
def launch_record():
    return ExecutionRecord(
        execution_id="exec-001",
        session_id="zcode-sess-abc",
        actor_id="zcode-actor-dev-xyz",
        role_id="developer",
        task_id="T-0034",
        prompt_fingerprint="a" * 64,
        input_files_hash="b" * 64,
        status=ExecutionStatus.LAUNCHED,
        launched_at="2026-07-23T10:00:00Z",
        tool_constraints=["Read", "Write", "Edit"],
    )


# ═══════════════════════════════════════════════════════════════════════
# ExecutionRecord
# ═══════════════════════════════════════════════════════════════════════

class TestExecutionRecord:
    def test_to_json_row_roundtrip(self):
        rec = ExecutionRecord(
            execution_id="exec-001",
            session_id="sess-1",
            actor_id="actor-1",
            role_id="developer",
            task_id="T-1",
            prompt_fingerprint="f" * 64,
            input_files_hash="e" * 64,
            status=ExecutionStatus.LAUNCHED,
            launched_at="2026-07-23T10:00:00Z",
        )
        row = rec.to_json_row()
        data = json.loads(row)
        restored = ExecutionRecord.from_json_row(data)
        assert restored.execution_id == rec.execution_id
        assert restored.role_id == rec.role_id
        assert restored.status == rec.status

    def test_completed_record_fields(self):
        rec = ExecutionRecord(
            execution_id="exec-002",
            session_id="sess-2",
            actor_id="actor-2",
            role_id="reviewer",
            task_id="T-2",
            prompt_fingerprint="c" * 64,
            input_files_hash="d" * 64,
            status=ExecutionStatus.COMPLETED,
            launched_at="2026-07-23T10:00:00Z",
            completed_at="2026-07-23T10:05:00Z",
            exit_code=0,
            output_hash="e" * 64,
            tool_violations=["deploy"],
        )
        assert rec.exit_code == 0
        assert "deploy" in rec.tool_violations


# ═══════════════════════════════════════════════════════════════════════
# ExecutionLedger — 基本读写
# ═══════════════════════════════════════════════════════════════════════

class TestExecutionLedgerBasic:
    def test_empty_ledger_reads_empty(self, ledger):
        assert ledger.read_all() == []
        assert ledger.read_records() == []

    def test_verify_empty_ledger(self, ledger):
        valid, reason = ledger.verify_chain()
        assert valid is True
        assert "empty" in reason

    def test_append_entry_creates_file(self, ledger, launch_record):
        ledger.append_entry(launch_record)
        assert ledger.exists

    def test_append_entry_returns_chain_hash(self, ledger, launch_record):
        ch = ledger.append_entry(launch_record)
        assert len(ch) == 64
        assert all(c in "0123456789abcdef" for c in ch)

    def test_read_all_after_append(self, ledger, launch_record):
        ledger.append_entry(launch_record)
        entries = ledger.read_all()
        assert len(entries) == 1
        assert entries[0]["execution_id"] == "exec-001"
        assert "chain_hash" in entries[0]

    def test_multiple_entries_preserved(self, ledger, launch_record):
        ledger.append_entry(launch_record)
        r2 = ExecutionRecord(
            execution_id="exec-002",
            session_id="sess-2", actor_id="actor-2",
            role_id="reviewer", task_id="T-0034",
            prompt_fingerprint="b" * 64,
            input_files_hash="c" * 64,
            status=ExecutionStatus.LAUNCHED,
            launched_at="2026-07-23T11:00:00Z",
        )
        ledger.append_entry(r2)
        assert len(ledger.read_all()) == 2

    def test_record_launch_validates_status(self, ledger):
        rec = ExecutionRecord(
            execution_id="exec-001", session_id="s", actor_id="a",
            role_id="dev", task_id="T-1",
            prompt_fingerprint="f" * 64, input_files_hash="g" * 64,
            status=ExecutionStatus.COMPLETED,  # 错！
            launched_at="2026-07-23T10:00:00Z",
        )
        with pytest.raises(ValueError, match="LAUNCHED"):
            ledger.record_launch(rec)


# ═══════════════════════════════════════════════════════════════════════
# Chain Hash 验证
# ═══════════════════════════════════════════════════════════════════════

class TestChainHash:
    def test_verify_single_entry(self, ledger, launch_record):
        ledger.append_entry(launch_record)
        valid, reason = ledger.verify_chain()
        assert valid is True

    def test_verify_multiple_entries(self, ledger, launch_record):
        ledger.append_entry(launch_record)
        r2 = ExecutionRecord(
            execution_id="exec-002", session_id="s2", actor_id="a2",
            role_id="reviewer", task_id="T-0034",
            prompt_fingerprint="c" * 64, input_files_hash="d" * 64,
            status=ExecutionStatus.LAUNCHED,
            launched_at="2026-07-23T11:00:00Z",
        )
        ledger.append_entry(r2)
        valid, reason = ledger.verify_chain()
        assert valid is True

    def test_tampered_ledger_detected(self, ledger, launch_record):
        """篡改账本 → chain 断裂 → 可检测"""
        ledger.append_entry(launch_record)

        # 直接修改文件内容（模拟篡改）
        path = ledger._ledger_path
        original = path.read_text()
        tampered = original.replace("exec-001", "exec-HACKED")
        path.write_text(tampered)

        valid, reason = ledger.verify_chain()
        assert valid is False
        assert "mismatch" in reason.lower() or "broken" in reason.lower()

    def test_inserted_line_detected(self, ledger, launch_record):
        """插入伪造行 → chain 断裂"""
        ledger.append_entry(launch_record)
        path = ledger._ledger_path
        # 在中间插入一行
        fake = json.dumps({"execution_id": "exec-FAKE", "chain_hash": "0" * 64})
        path.write_text(path.read_text() + "\n" + fake + "\n")

        valid, _ = ledger.verify_chain()
        assert valid is False

    def test_different_ledgers_independent_chains(self, tmp_root):
        """两个不同项目的账本有独立链。"""
        l1 = ExecutionLedger(tmp_root / "proj1")
        l2 = ExecutionLedger(tmp_root / "proj2")

        r1 = ExecutionRecord(
            execution_id="e1", session_id="s1", actor_id="a1",
            role_id="dev", task_id="T-1",
            prompt_fingerprint="a" * 64, input_files_hash="b" * 64,
            status=ExecutionStatus.LAUNCHED,
            launched_at="2026-07-23T10:00:00Z",
        )
        # 相同内容的 record 附加到不同账本 → 相同 chain_hash
        # 因为 chain_hash = SHA256(root || row_json)
        l1.append_entry(r1)
        ch1 = l1.read_all()[0]["chain_hash"]

        r1_same = ExecutionRecord(
            execution_id="e1", session_id="s1", actor_id="a1",
            role_id="dev", task_id="T-1",
            prompt_fingerprint="a" * 64, input_files_hash="b" * 64,
            status=ExecutionStatus.LAUNCHED,
            launched_at="2026-07-23T10:00:00Z",
        )
        l2.append_entry(r1_same)
        ch2 = l2.read_all()[0]["chain_hash"]

        assert ch1 == ch2  # 相同内容 + 相同 root → 相同 chain_hash

        # 但第二条分叉后，链就不同了
        r3 = ExecutionRecord(
            execution_id="e3", session_id="s3", actor_id="a3",
            role_id="qa", task_id="T-3",
            prompt_fingerprint="c" * 64, input_files_hash="d" * 64,
            status=ExecutionStatus.LAUNCHED,
            launched_at="2026-07-23T11:00:00Z",
        )
        r4 = ExecutionRecord(
            execution_id="e4", session_id="s4", actor_id="a4",
            role_id="ops", task_id="T-4",
            prompt_fingerprint="e" * 64, input_files_hash="f" * 64,
            status=ExecutionStatus.LAUNCHED,
            launched_at="2026-07-23T12:00:00Z",
        )
        l1.append_entry(r3)
        l2.append_entry(r4)
        assert l1.read_all()[1]["chain_hash"] != l2.read_all()[1]["chain_hash"]


# ═══════════════════════════════════════════════════════════════════════
# record_completion — LAUNCHED → COMPLETED 工作流
# ═══════════════════════════════════════════════════════════════════════

class TestRecordCompletion:
    def test_completion_appends_new_entry(self, ledger, launch_record):
        ledger.record_launch(launch_record)
        ch = ledger.record_completion(
            "exec-001", ExecutionStatus.COMPLETED, exit_code=0,
            output_hash="o" * 64,
        )
        entries = ledger.read_all()
        assert len(entries) == 2
        assert entries[1]["status"] == "COMPLETED"
        assert entries[1]["execution_id"] == "exec-001"

    def test_completion_preserves_launch_fields(self, ledger, launch_record):
        ledger.record_launch(launch_record)
        ledger.record_completion("exec-001", ExecutionStatus.COMPLETED)
        records = ledger.read_records()
        comp = records[-1]
        assert comp.actor_id == launch_record.actor_id
        assert comp.session_id == launch_record.session_id
        assert comp.prompt_fingerprint == launch_record.prompt_fingerprint

    def test_completion_unknown_id_raises(self, ledger):
        with pytest.raises(ValueError, match="exec-UNKNOWN"):
            ledger.record_completion("exec-UNKNOWN", ExecutionStatus.COMPLETED)

    def test_violated_status(self, ledger, launch_record):
        ledger.record_launch(launch_record)
        ledger.record_completion(
            "exec-001", ExecutionStatus.VIOLATED,
            tool_violations=["deploy"],
        )
        records = ledger.read_records()
        assert records[-1].status == ExecutionStatus.VIOLATED
        assert "deploy" in records[-1].tool_violations


# ═══════════════════════════════════════════════════════════════════════
# 查询
# ═══════════════════════════════════════════════════════════════════════

class TestQueries:
    def test_find_by_execution_id(self, ledger, launch_record):
        ledger.append_entry(launch_record)
        found = ledger.find_by_execution_id("exec-001")
        assert found is not None
        assert found.role_id == "developer"

    def test_find_missing_returns_none(self, ledger):
        assert ledger.find_by_execution_id("nonexistent") is None

    def test_find_by_task(self, ledger, launch_record):
        ledger.append_entry(launch_record)
        r2 = ExecutionRecord(
            execution_id="exec-002", session_id="s2", actor_id="a2",
            role_id="reviewer", task_id="T-0034",
            prompt_fingerprint="x" * 64, input_files_hash="y" * 64,
            status=ExecutionStatus.LAUNCHED,
            launched_at="2026-07-23T11:00:00Z",
        )
        ledger.append_entry(r2)
        results = ledger.find_by_task("T-0034")
        assert len(results) == 2

    def test_find_by_role(self, ledger, launch_record):
        ledger.append_entry(launch_record)
        devs = ledger.find_by_role("T-0034", "developer")
        revs = ledger.find_by_role("T-0034", "independent-reviewer")
        assert len(devs) == 1
        assert len(revs) == 0


# ═══════════════════════════════════════════════════════════════════════
# Cross-Validation
# ═══════════════════════════════════════════════════════════════════════

class TestCrossValidate:
    def test_valid_cross_validation(self, ledger):
        dev = ExecutionRecord(
            execution_id="e-dev", session_id="s1", actor_id="actor-dev",
            role_id="developer", task_id="T-0034",
            prompt_fingerprint="a" * 64, input_files_hash="b" * 64,
            status=ExecutionStatus.LAUNCHED,
            launched_at="2026-07-23T10:00:00Z",
        )
        rev = ExecutionRecord(
            execution_id="e-rev", session_id="s2", actor_id="actor-rev",
            role_id="independent-reviewer", task_id="T-0034",
            prompt_fingerprint="c" * 64, input_files_hash="d" * 64,
            status=ExecutionStatus.LAUNCHED,
            launched_at="2026-07-23T10:05:00Z",
        )
        ledger.append_entry(dev)
        ledger.append_entry(rev)

        result = ledger.cross_validate("T-0034")
        assert result["valid"] is True
        assert result["actors_differ"] is True
        assert result["fingerprints_differ"] is True

    def test_same_actor_detected(self, ledger):
        dev = ExecutionRecord(
            execution_id="e-dev", session_id="s1", actor_id="same-actor",
            role_id="developer", task_id="T-0034",
            prompt_fingerprint="a" * 64, input_files_hash="b" * 64,
            status=ExecutionStatus.LAUNCHED,
            launched_at="2026-07-23T10:00:00Z",
        )
        rev = ExecutionRecord(
            execution_id="e-rev", session_id="s2", actor_id="same-actor",
            role_id="independent-reviewer", task_id="T-0034",
            prompt_fingerprint="c" * 64, input_files_hash="d" * 64,
            status=ExecutionStatus.LAUNCHED,
            launched_at="2026-07-23T10:05:00Z",
        )
        ledger.append_entry(dev)
        ledger.append_entry(rev)

        result = ledger.cross_validate("T-0034")
        assert result["valid"] is False
        assert "same actor_id" in str(result["violations"]).lower()

    def test_identical_fingerprints_detected(self, ledger):
        same_fp = "f" * 64
        dev = ExecutionRecord(
            execution_id="e-dev", session_id="s1", actor_id="a1",
            role_id="developer", task_id="T-0034",
            prompt_fingerprint=same_fp, input_files_hash="b" * 64,
            status=ExecutionStatus.LAUNCHED,
            launched_at="2026-07-23T10:00:00Z",
        )
        rev = ExecutionRecord(
            execution_id="e-rev", session_id="s2", actor_id="a2",
            role_id="independent-reviewer", task_id="T-0034",
            prompt_fingerprint=same_fp, input_files_hash="d" * 64,
            status=ExecutionStatus.LAUNCHED,
            launched_at="2026-07-23T10:05:00Z",
        )
        ledger.append_entry(dev)
        ledger.append_entry(rev)

        result = ledger.cross_validate("T-0034")
        assert result["fingerprints_differ"] is False
        assert any("fingerprint" in v.lower() for v in result["violations"])

    def test_missing_role_reported(self, ledger):
        dev = ExecutionRecord(
            execution_id="e-dev", session_id="s1", actor_id="a1",
            role_id="developer", task_id="T-0034",
            prompt_fingerprint="a" * 64, input_files_hash="b" * 64,
            status=ExecutionStatus.LAUNCHED,
            launched_at="2026-07-23T10:00:00Z",
        )
        ledger.append_entry(dev)
        result = ledger.cross_validate("T-0034")
        assert result["valid"] is False
        assert any("reviewer" in v.lower() for v in result["violations"])


# ═══════════════════════════════════════════════════════════════════════
# 边界测试
# ═══════════════════════════════════════════════════════════════════════

class TestBoundaryCases:
    """Boundary and edge-case tests for ExecutionLedger and ExecutionRecord."""

    # ── 1. Corrupted JSON line in middle of ledger → read_all() behavior ──

    def test_corrupted_json_line_raises(self, ledger, launch_record):
        """A corrupted JSON line in the middle should raise json.JSONDecodeError."""
        ledger.append_entry(launch_record)

        # Append a second valid entry
        r2 = ExecutionRecord(
            execution_id="exec-002", session_id="s2", actor_id="a2",
            role_id="reviewer", task_id="T-0034",
            prompt_fingerprint="c" * 64, input_files_hash="d" * 64,
            status=ExecutionStatus.LAUNCHED,
            launched_at="2026-07-23T11:00:00Z",
        )
        ledger.append_entry(r2)

        # Now corrupt the middle by inserting a bad line
        path = ledger._ledger_path
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        # Insert a corrupted line between line 0 and line 1
        lines.insert(1, "this is not valid json {{{[[[\n")
        path.write_text("".join(lines), encoding="utf-8")

        with __import__("pytest").raises(json.JSONDecodeError):
            ledger.read_all()

    # ── 2. Auto-checkpoint at 200 entries → archive created, chain resets ──

    def test_auto_checkpoint_archives_and_resets(self, tmp_root, monkeypatch):
        """After _MAX_ENTRIES entries, old file is archived and chain resets."""
        # Lower the threshold for fast testing
        monkeypatch.setattr(ExecutionLedger, "_MAX_ENTRIES", 5)

        ledger = ExecutionLedger(tmp_root)

        # Append 5 entries (will trigger checkpoint on the 5th)
        for i in range(5):
            rec = ExecutionRecord(
                execution_id=f"exec-{i:03d}",
                session_id=f"sess-{i}", actor_id=f"actor-{i}",
                role_id="developer", task_id="T-0001",
                prompt_fingerprint="f" * 64, input_files_hash="e" * 64,
                status=ExecutionStatus.LAUNCHED,
                launched_at="2026-07-23T10:00:00Z",
            )
            ledger.append_entry(rec)

        # After checkpoint, the original file should be archived
        ledger_dir = tmp_root / ".ai" / "ledger"
        jsonl_files = sorted(ledger_dir.glob("*.jsonl"))
        # Should have: executions.jsonl (new, empty or reset) + one archive file
        archive_files = [f for f in jsonl_files if f.name != "executions.jsonl"]
        assert len(archive_files) >= 1, f"expected at least 1 archive file, got: {[f.name for f in jsonl_files]}"

        # The current ledger should be empty (chain reset)
        assert not ledger.exists or ledger.read_all() == []

        # New entries after checkpoint should start fresh chain
        ch = ledger.append_entry(ExecutionRecord(
            execution_id="exec-post-checkpoint",
            session_id="sess-new", actor_id="actor-new",
            role_id="developer", task_id="T-0001",
            prompt_fingerprint="a" * 64, input_files_hash="b" * 64,
            status=ExecutionStatus.LAUNCHED,
            launched_at="2026-07-23T11:00:00Z",
        ))
        assert len(ch) == 64
        valid, reason = ledger.verify_chain()
        assert valid is True, reason

    # ── 3. from_json_row with missing required field → KeyError ──

    def test_from_json_row_missing_required_field(self):
        """Passing a dict missing required fields raises KeyError."""
        with __import__("pytest").raises(KeyError):
            ExecutionRecord.from_json_row({})

        with __import__("pytest").raises(KeyError):
            ExecutionRecord.from_json_row({"execution_id": "e1"})

    # ── 4. Unicode edge case in execution_id ──

    def test_unicode_execution_id_roundtrip(self):
        """Unicode characters in execution_id should survive roundtrip."""
        unicode_id = "exec-\u4e2d\u6587-\U0001f600-test"  # 中文 + 😀 emoji
        rec = ExecutionRecord(
            execution_id=unicode_id,
            session_id="sess-1",
            actor_id="actor-1",
            role_id="developer",
            task_id="T-0001",
            prompt_fingerprint="a" * 64,
            input_files_hash="b" * 64,
            status=ExecutionStatus.LAUNCHED,
            launched_at="2026-07-23T10:00:00Z",
        )
        row = rec.to_json_row()
        data = json.loads(row)
        restored = ExecutionRecord.from_json_row(data)
        assert restored.execution_id == unicode_id
        assert "\u4e2d" in restored.execution_id
