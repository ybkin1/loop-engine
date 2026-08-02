"""
Unit tests for loop_core.approval_ledger — ApprovalRecord + ApprovalLedger.

Covers:
- ApprovalRecord.create() auto-generation (approval_id, hashes, expiration)
- is_expired() logic (expired vs not-yet-expired)
- is_valid() logic (approved+unexpired=True, others=False)
- scope_hash changes with scope content
- ApprovalLedger.record_approval() writes correctly to gates.yaml
- ApprovalLedger.get_approval() round-trips correctly
- ApprovalLedger.validate_scope() detects scope creep
- ApprovalLedger.find_expired() returns only expired gate IDs
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure the parent directory is on sys.path so we can import loop_core
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tempfile
import textwrap
import pytest

from loop_core.approval_ledger import (
    ApprovalRecord,
    ApprovalLedger,
    Decision,
    Source,
    _sha256,
    _short_uuid,
    _parse_datetime,
)


# ── Helpers ────────────────────────────────────────────────────────────────


def _make_temp_gates_yaml(
    gates: list[dict] | None = None,
) -> Path:
    """Create a temporary gates.yaml with the given gate list and return its Path."""
    import yaml

    doc = {"schema_version": 1, "gates": gates or []}
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    )
    yaml.dump(doc, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp.close()
    return Path(tmp.name)


def _sample_record(**overrides) -> ApprovalRecord:
    """Create a sample ApprovalRecord with sensible defaults, allowing overrides."""
    defaults = dict(
        gate_id="G-T-0001-TEST",
        decision=Decision.APPROVED,
        source=Source.EXPLICIT_MESSAGE,
        packet_content="decision packet body",
        scope_content="path1\npath2\naction1\naction2",
        user_input="user said approve",
        approval_text="I approve this gate.",
        task_id="T-0001",
        ttl_days=30,
    )
    defaults.update(overrides)
    return ApprovalRecord.create(**defaults)


# ── Helpers (pure function) ───────────────────────────────────────────────


class TestHelpers:
    """Tests for the internal helper utilities."""

    def test_short_uuid_length(self):
        result = _short_uuid()
        assert len(result) == 12
        # Should be hex characters only
        assert all(c in "0123456789abcdef" for c in result)

    def test_short_uuid_uniqueness(self):
        results = {_short_uuid() for _ in range(100)}
        assert len(results) == 100  # Very unlikely to collide

    def test_sha256_deterministic(self):
        assert _sha256("hello") == _sha256("hello")

    def test_sha256_different_content(self):
        assert _sha256("hello") != _sha256("world")

    def test_parse_datetime_utc(self):
        dt = _parse_datetime("2026-07-23T12:00:00+00:00")
        assert dt.tzinfo is not None

    def test_parse_datetime_offset(self):
        dt = _parse_datetime("2026-07-23T20:00:00+08:00")
        # Offset is preserved; hour remains 20 with +08:00 tz
        assert dt.hour == 20
        assert dt.tzinfo is not None
        assert dt.utcoffset() == timedelta(hours=8)

    def test_parse_datetime_naive_assumes_utc(self):
        dt = _parse_datetime("2026-07-23T12:00:00")
        assert dt.tzinfo is not None
        assert dt.utcoffset() == timedelta(0)


# ── ApprovalRecord.create() ────────────────────────────────────────────────


class TestApprovalRecordCreate:
    """Tests for ApprovalRecord.create() factory method."""

    def test_approval_id_format(self):
        rec = _sample_record()
        assert rec.approval_id.startswith("AR-")
        assert len(rec.approval_id) == 15  # "AR-" + 12 hex chars

    def test_human_actor_is_user(self):
        rec = _sample_record()
        assert rec.human_actor == "user"

    def test_decision_stored(self):
        rec = _sample_record(decision=Decision.REJECTED)
        assert rec.decision == Decision.REJECTED

    def test_source_stored(self):
        rec = _sample_record(source=Source.INTERACTIVE_DIALOG)
        assert rec.source == Source.INTERACTIVE_DIALOG

    def test_packet_hash_computed(self):
        rec = _sample_record(packet_content="hello")
        assert rec.packet_hash == _sha256("hello")

    def test_scope_hash_computed(self):
        rec = _sample_record(scope_content="path1\npath2")
        assert rec.scope_hash == _sha256("path1\npath2")

    def test_input_fingerprint_computed(self):
        rec = _sample_record(user_input="approve please")
        assert rec.input_fingerprint == _sha256("approve please")

    def test_recorded_at_is_iso8601(self):
        rec = _sample_record()
        dt = datetime.fromisoformat(rec.recorded_at)
        assert isinstance(dt, datetime)

    def test_expiration_is_iso8601_and_future(self):
        rec = _sample_record(ttl_days=30)
        exp = datetime.fromisoformat(rec.expiration)
        now = datetime.now(timezone.utc)
        # Expiration should be roughly 30 days in the future
        delta = exp - now
        assert timedelta(days=29) < delta < timedelta(days=31)

    def test_ttl_days_respected(self):
        rec5 = _sample_record(ttl_days=5)
        exp5 = datetime.fromisoformat(rec5.expiration)
        now = datetime.now(timezone.utc)
        delta = exp5 - now
        assert timedelta(days=4) < delta < timedelta(days=6)

    def test_optional_fields_stored(self):
        rec = _sample_record(
            approval_text="ok", task_id="T-0042", ttl_days=30
        )
        assert rec.approval_text == "ok"
        assert rec.task_id == "T-0042"

    def test_previous_approval_id_defaults_to_none(self):
        rec = _sample_record()
        assert rec.previous_approval_id is None

    def test_create_with_none_optionals(self):
        rec = _sample_record(approval_text=None, task_id=None)
        assert rec.approval_text is None
        assert rec.task_id is None


# ── is_expired() ───────────────────────────────────────────────────────────


class TestIsExpired:
    """Tests for ApprovalRecord.is_expired()."""

    def test_not_expired_when_far_future(self):
        rec = _sample_record(ttl_days=365)
        assert rec.is_expired() is False

    def test_expired_when_in_past(self):
        # Build a record whose expiration is 1 second ago
        now = datetime.now(timezone.utc)
        past_exp = (now - timedelta(seconds=1)).isoformat()
        rec = _sample_record()
        # Directly set expiration to the past (bypass create)
        rec.expiration = past_exp
        assert rec.is_expired() is True

    def test_not_expired_when_exactly_at_expiration(self):
        # Boundary: exactly at expiration should be considered expired
        now = datetime.now(timezone.utc)
        rec = _sample_record()
        rec.expiration = now.isoformat()
        # We consider "now >= exp" as expired, so exact match is expired
        assert rec.is_expired() is True

    def test_not_expired_one_second_before(self):
        now = datetime.now(timezone.utc)
        future = (now + timedelta(seconds=1)).isoformat()
        rec = _sample_record()
        rec.expiration = future
        assert rec.is_expired() is False

    def test_expired_record_with_timezone_offset(self):
        # Expiration string with +08:00 timezone
        past = datetime.now(timezone.utc) - timedelta(days=1)
        rec = _sample_record()
        rec.expiration = past.isoformat()
        assert rec.is_expired() is True


# ── is_valid() ─────────────────────────────────────────────────────────────


class TestIsValid:
    """Tests for ApprovalRecord.is_valid()."""

    def test_valid_when_approved_and_not_expired(self):
        rec = _sample_record(decision=Decision.APPROVED, ttl_days=30)
        assert rec.is_valid() is True

    def test_invalid_when_rejected(self):
        rec = _sample_record(decision=Decision.REJECTED, ttl_days=30)
        assert rec.is_valid() is False

    def test_invalid_when_repair_requested(self):
        rec = _sample_record(decision=Decision.REPAIR_REQUESTED, ttl_days=30)
        assert rec.is_valid() is False

    def test_invalid_when_expired_even_if_approved(self):
        now = datetime.now(timezone.utc)
        past = (now - timedelta(days=1)).isoformat()
        rec = _sample_record(decision=Decision.APPROVED, ttl_days=30)
        rec.expiration = past
        assert rec.is_valid() is False


# ── scope_hash ─────────────────────────────────────────────────────────────


class TestScopeHash:
    """Tests verifying scope_hash changes with scope content."""

    def test_different_scope_different_hash(self):
        rec_a = _sample_record(scope_content="path1\naction1")
        rec_b = _sample_record(scope_content="path2\naction2")
        assert rec_a.scope_hash != rec_b.scope_hash

    def test_same_scope_same_hash(self):
        content = "path1\npath2\nactionX"
        rec_a = _sample_record(scope_content=content)
        rec_b = _sample_record(scope_content=content)
        assert rec_a.scope_hash == rec_b.scope_hash

    def test_scope_hash_uses_sorted_content(self):
        # The scope_content parameter should be pre-sorted by the caller;
        # the hash just reflects whatever string is passed.
        unsorted = "pathB\npathA"
        sorted_ = "pathA\npathB"
        assert _sha256(unsorted) != _sha256(sorted_)


# ── ApprovalLedger.record_approval() ─────────────────────────────────────


class TestRecordApproval:
    """Tests for ApprovalLedger.record_approval()."""

    def test_writes_approval_block_to_gate(self):
        gates = [{"id": "G-T-0001-TEST", "status": "pending"}]
        gates_path = _make_temp_gates_yaml(gates)
        try:
            rec = _sample_record(gate_id="G-T-0001-TEST")
            ledger = ApprovalLedger()
            ledger.record_approval(rec, gates_path)

            # Read back the YAML and check the approval block
            import yaml
            with open(gates_path, "r", encoding="utf-8") as fh:
                doc = yaml.safe_load(fh)
            gate = doc["gates"][0]
            assert gate["approval"]["approval_id"] == rec.approval_id
            assert gate["approval"]["decision"] == "approved"
            assert gate["approval"]["packet_hash"] == rec.packet_hash
            assert gate["approval"]["scope_hash"] == rec.scope_hash
            assert gate["approval"]["expiration"] == rec.expiration
        finally:
            gates_path.unlink(missing_ok=True)

    def test_approval_overwrites_previous(self):
        gates = [{"id": "G-T-0001-TEST", "status": "pending"}]
        gates_path = _make_temp_gates_yaml(gates)
        try:
            ledger = ApprovalLedger()
            rec1 = _sample_record(gate_id="G-T-0001-TEST")
            ledger.record_approval(rec1, gates_path)

            rec2 = _sample_record(
                gate_id="G-T-0001-TEST",
                approval_text="updated approval",
            )
            ledger.record_approval(rec2, gates_path)

            # Should have the second record's data
            loaded = ledger.get_approval("G-T-0001-TEST", gates_path)
            assert loaded is not None
            assert loaded.approval_id == rec2.approval_id
            assert loaded.approval_text == "updated approval"
        finally:
            gates_path.unlink(missing_ok=True)

    def test_raises_when_gate_not_found(self):
        gates = [{"id": "G-T-OTHER", "status": "pending"}]
        gates_path = _make_temp_gates_yaml(gates)
        try:
            rec = _sample_record(gate_id="G-T-MISSING")
            ledger = ApprovalLedger()
            with pytest.raises(ValueError, match="G-T-MISSING"):
                ledger.record_approval(rec, gates_path)
        finally:
            gates_path.unlink(missing_ok=True)

    def test_raises_when_file_not_found(self):
        ledger = ApprovalLedger()
        rec = _sample_record()
        with pytest.raises(FileNotFoundError):
            ledger.record_approval(rec, Path("/nonexistent/gates.yaml"))

    def test_preserves_other_gates_on_write(self):
        gates = [
            {"id": "G-001", "status": "pending"},
            {"id": "G-002", "status": "approved"},
        ]
        gates_path = _make_temp_gates_yaml(gates)
        try:
            rec = _sample_record(gate_id="G-001")
            ledger = ApprovalLedger()
            ledger.record_approval(rec, gates_path)

            # G-002 should still be intact and have no approval block
            loaded = ledger.get_approval("G-002", gates_path)
            assert loaded is None

            # G-001 should have the approval
            loaded = ledger.get_approval("G-001", gates_path)
            assert loaded is not None
            assert loaded.gate_id == "G-001"
        finally:
            gates_path.unlink(missing_ok=True)

    def test_optional_fields_stored(self):
        gates = [{"id": "G-T-0001-TEST", "status": "pending"}]
        gates_path = _make_temp_gates_yaml(gates)
        try:
            rec = _sample_record(
                gate_id="G-T-0001-TEST",
                approval_text="go ahead",
                task_id="T-0042",
            )
            # Manually set previous_approval_id since create doesn't accept it
            rec.previous_approval_id = "AR-prev123"

            ledger = ApprovalLedger()
            ledger.record_approval(rec, gates_path)

            import yaml
            with open(gates_path, "r", encoding="utf-8") as fh:
                doc = yaml.safe_load(fh)
            approval = doc["gates"][0]["approval"]
            assert approval.get("approval_text") == "go ahead"
            assert approval.get("task_id") == "T-0042"
            assert approval.get("previous_approval_id") == "AR-prev123"
        finally:
            gates_path.unlink(missing_ok=True)


# ── ApprovalLedger.get_approval() ───────────────────────────────────────


class TestGetApproval:
    """Tests for ApprovalLedger.get_approval()."""

    def test_round_trip(self):
        gates = [{"id": "G-T-0001-TEST", "status": "pending"}]
        gates_path = _make_temp_gates_yaml(gates)
        try:
            rec = _sample_record(gate_id="G-T-0001-TEST")
            ledger = ApprovalLedger()
            ledger.record_approval(rec, gates_path)

            loaded = ledger.get_approval("G-T-0001-TEST", gates_path)
            assert loaded is not None
            assert loaded.approval_id == rec.approval_id
            assert loaded.gate_id == rec.gate_id
            assert loaded.decision == rec.decision
            assert loaded.source == rec.source
            assert loaded.packet_hash == rec.packet_hash
            assert loaded.scope_hash == rec.scope_hash
            assert loaded.input_fingerprint == rec.input_fingerprint
            assert loaded.recorded_at == rec.recorded_at
            assert loaded.expiration == rec.expiration
            assert loaded.approval_text == rec.approval_text
            assert loaded.task_id == rec.task_id
        finally:
            gates_path.unlink(missing_ok=True)

    def test_returns_none_for_missing_gate(self):
        gates = [{"id": "G-001", "status": "pending"}]
        gates_path = _make_temp_gates_yaml(gates)
        try:
            ledger = ApprovalLedger()
            assert ledger.get_approval("G-MISSING", gates_path) is None
        finally:
            gates_path.unlink(missing_ok=True)

    def test_returns_none_when_no_approval_block(self):
        gates = [{"id": "G-001", "status": "pending"}]
        gates_path = _make_temp_gates_yaml(gates)
        try:
            ledger = ApprovalLedger()
            assert ledger.get_approval("G-001", gates_path) is None
        finally:
            gates_path.unlink(missing_ok=True)

    def test_returns_none_for_nonexistent_file(self):
        ledger = ApprovalLedger()
        assert ledger.get_approval("G-001", Path("/nonexistent/gates.yaml")) is None

    def test_round_trip_rejected_decision(self):
        gates = [{"id": "G-REJ", "status": "pending"}]
        gates_path = _make_temp_gates_yaml(gates)
        try:
            rec = _sample_record(
                gate_id="G-REJ", decision=Decision.REJECTED
            )
            ledger = ApprovalLedger()
            ledger.record_approval(rec, gates_path)

            loaded = ledger.get_approval("G-REJ", gates_path)
            assert loaded is not None
            assert loaded.decision == Decision.REJECTED
        finally:
            gates_path.unlink(missing_ok=True)


# ── ApprovalLedger.validate_scope() ─────────────────────────────────────


class TestValidateScope:
    """Tests for ApprovalLedger.validate_scope()."""

    def test_scope_match_returns_true(self):
        scope = "path1\npath2\naction1\naction2"
        rec = _sample_record(scope_content=scope)
        ledger = ApprovalLedger()
        assert ledger.validate_scope(rec, scope) is True

    def test_scope_mismatch_returns_false(self):
        rec = _sample_record(scope_content="path1\naction1")
        ledger = ApprovalLedger()
        assert ledger.validate_scope(rec, "path2\naction2") is False

    def test_scope_creep_detected_when_path_added(self):
        original = "path1\npath2\naction1"
        rec = _sample_record(scope_content=original)
        ledger = ApprovalLedger()
        # Adding a new path changes the scope hash
        modified = "path1\npath2\npath3\naction1"
        assert ledger.validate_scope(rec, modified) is False

    def test_scope_creep_detected_when_action_added(self):
        original = "path1\naction1"
        rec = _sample_record(scope_content=original)
        ledger = ApprovalLedger()
        modified = "path1\naction1\naction2"
        assert ledger.validate_scope(rec, modified) is False

    def test_empty_scope(self):
        rec = _sample_record(scope_content="")
        ledger = ApprovalLedger()
        assert ledger.validate_scope(rec, "") is True
        assert ledger.validate_scope(rec, "something") is False


# ── ApprovalLedger.find_expired() ───────────────────────────────────────


class TestFindExpired:
    """Tests for ApprovalLedger.find_expired()."""

    def _write_approval_to_temp_gate(
        self, gates_path: Path, gate_id: str, expiration: str
    ) -> None:
        """Helper: write an approval block directly into a temp gates.yaml."""
        import yaml

        with open(gates_path, "r", encoding="utf-8") as fh:
            doc = yaml.safe_load(fh) or {}

        for gate in doc.get("gates", []):
            if gate.get("id") == gate_id:
                gate["approval"] = {
                    "approval_id": f"AR-test-{gate_id}",
                    "human_actor": "user",
                    "decision": "approved",
                    "source": "explicit_user_message",
                    "packet_hash": "abc123",
                    "scope_hash": "def456",
                    "input_fingerprint": "ghi789",
                    "recorded_at": "2026-01-01T00:00:00+00:00",
                    "expiration": expiration,
                }
                break

        with open(gates_path, "w", encoding="utf-8") as fh:
            yaml.dump(
                doc, fh, default_flow_style=False, allow_unicode=True,
                sort_keys=False,
            )

    def test_returns_expired_gate_ids(self):
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        gates = [
            {"id": "G-EXPIRED", "status": "approved"},
            {"id": "G-VALID", "status": "approved"},
        ]
        gates_path = _make_temp_gates_yaml(gates)
        try:
            self._write_approval_to_temp_gate(gates_path, "G-EXPIRED", past)
            self._write_approval_to_temp_gate(
                gates_path, "G-VALID",
                (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            )

            ledger = ApprovalLedger()
            expired = ledger.find_expired(gates_path)
            assert expired == ["G-EXPIRED"]
        finally:
            gates_path.unlink(missing_ok=True)

    def test_returns_empty_when_none_expired(self):
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        gates = [{"id": "G-FRESH", "status": "approved"}]
        gates_path = _make_temp_gates_yaml(gates)
        try:
            self._write_approval_to_temp_gate(gates_path, "G-FRESH", future)
            ledger = ApprovalLedger()
            expired = ledger.find_expired(gates_path)
            assert expired == []
        finally:
            gates_path.unlink(missing_ok=True)

    def test_skips_gates_without_approval(self):
        gates = [
            {"id": "G-NO-APPROVAL", "status": "pending"},
        ]
        gates_path = _make_temp_gates_yaml(gates)
        try:
            ledger = ApprovalLedger()
            expired = ledger.find_expired(gates_path)
            assert expired == []
        finally:
            gates_path.unlink(missing_ok=True)

    def test_returns_empty_for_nonexistent_file(self):
        ledger = ApprovalLedger()
        expired = ledger.find_expired(Path("/nonexistent/gates.yaml"))
        assert expired == []

    def test_multiple_expired(self):
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        gates = [
            {"id": "G-EXP1", "status": "approved"},
            {"id": "G-EXP2", "status": "approved"},
            {"id": "G-OK", "status": "approved"},
        ]
        gates_path = _make_temp_gates_yaml(gates)
        try:
            self._write_approval_to_temp_gate(gates_path, "G-EXP1", past)
            self._write_approval_to_temp_gate(gates_path, "G-EXP2", past)
            self._write_approval_to_temp_gate(gates_path, "G-OK", future)

            ledger = ApprovalLedger()
            expired = ledger.find_expired(gates_path)
            assert sorted(expired) == ["G-EXP1", "G-EXP2"]
        finally:
            gates_path.unlink(missing_ok=True)

    def test_handles_unparseable_expiration(self):
        gates = [{"id": "G-BAD", "status": "approved"}]
        gates_path = _make_temp_gates_yaml(gates)
        try:
            # Write an approval block with an unparseable expiration string
            import yaml
            with open(gates_path, "r", encoding="utf-8") as fh:
                doc = yaml.safe_load(fh)
            doc["gates"][0]["approval"] = {
                "approval_id": "AR-bad",
                "human_actor": "user",
                "decision": "approved",
                "source": "explicit_user_message",
                "packet_hash": "abc",
                "scope_hash": "def",
                "input_fingerprint": "ghi",
                "recorded_at": "2026-01-01T00:00:00+00:00",
                "expiration": "not-a-datetime",
            }
            with open(gates_path, "w", encoding="utf-8") as fh:
                yaml.dump(
                    doc, fh, default_flow_style=False,
                    allow_unicode=True, sort_keys=False,
                )

            ledger = ApprovalLedger()
            expired = ledger.find_expired(gates_path)
            # Unparseable should be skipped, not crash
            assert expired == []
        finally:
            gates_path.unlink(missing_ok=True)


# ── user_comprehension_confirmed (T-0104 设计-4 §4.3.2) ────────────────────


class TestUserComprehensionConfirmed:
    """ApprovalRecord 可选字段：有值/无值（None）两种读取路径。"""

    def test_round_trip_true(self):
        gates = [{"id": "G-COMP-TRUE", "status": "pending"}]
        gates_path = _make_temp_gates_yaml(gates)
        try:
            rec = _sample_record(
                gate_id="G-COMP-TRUE",
                user_comprehension_confirmed=True,
            )
            ledger = ApprovalLedger()
            ledger.record_approval(rec, gates_path)

            loaded = ledger.get_approval("G-COMP-TRUE", gates_path)
            assert loaded is not None
            assert loaded.user_comprehension_confirmed is True
        finally:
            gates_path.unlink(missing_ok=True)

    def test_round_trip_false(self):
        gates = [{"id": "G-COMP-FALSE", "status": "pending"}]
        gates_path = _make_temp_gates_yaml(gates)
        try:
            rec = _sample_record(
                gate_id="G-COMP-FALSE",
                user_comprehension_confirmed=False,
            )
            ledger = ApprovalLedger()
            ledger.record_approval(rec, gates_path)
            loaded = ledger.get_approval("G-COMP-FALSE", gates_path)
            assert loaded is not None
            assert loaded.user_comprehension_confirmed is False
        finally:
            gates_path.unlink(missing_ok=True)

    def test_legacy_record_without_key_reads_none(self):
        """存量记录无 user_comprehension_confirmed 键 → None（未采集）。"""
        gates = [{"id": "G-LEGACY", "status": "approved"}]
        gates_path = _make_temp_gates_yaml(gates)
        try:
            import yaml
            with open(gates_path, "r", encoding="utf-8") as fh:
                doc = yaml.safe_load(fh) or {}
            doc["gates"][0]["approval"] = {
                "approval_id": "AR-legacy",
                "human_actor": "user",
                "decision": "approved",
                "source": "explicit_user_message",
                "packet_hash": "abc",
                "scope_hash": "def",
                "input_fingerprint": "ghi",
                "recorded_at": "2026-01-01T00:00:00+00:00",
                "expiration": "2026-02-01T00:00:00+00:00",
                # 无 user_comprehension_confirmed 键 = 设计-4 落地前的存量记录
            }
            with open(gates_path, "w", encoding="utf-8") as fh:
                yaml.dump(
                    doc, fh, default_flow_style=False,
                    allow_unicode=True, sort_keys=False,
                )

            ledger = ApprovalLedger()
            loaded = ledger.get_approval("G-LEGACY", gates_path)
            assert loaded is not None
            assert loaded.user_comprehension_confirmed is None
        finally:
            gates_path.unlink(missing_ok=True)

    def test_record_approval_omits_key_when_none(self):
        """record 值为 None 时不写入该键（存量写入逻辑零变化）。"""
        gates = [{"id": "G-COMP-NONE", "status": "pending"}]
        gates_path = _make_temp_gates_yaml(gates)
        try:
            rec = _sample_record(
                gate_id="G-COMP-NONE",
                user_comprehension_confirmed=None,
            )
            ledger = ApprovalLedger()
            ledger.record_approval(rec, gates_path)

            import yaml
            with open(gates_path, "r", encoding="utf-8") as fh:
                doc = yaml.safe_load(fh)
            approval = doc["gates"][0]["approval"]
            assert "user_comprehension_confirmed" not in approval

            loaded = ledger.get_approval("G-COMP-NONE", gates_path)
            assert loaded.user_comprehension_confirmed is None
        finally:
            gates_path.unlink(missing_ok=True)
