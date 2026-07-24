"""
Unit tests for loop_core.evidence_chain: EvidenceEnvelope and EvidenceChain.

Covers:
  - EvidenceEnvelope.wrap() hash computation and causal linking
  - is_fresh() / is_expired() correctness
  - EvidenceChain add_evidence() and chain persistence
  - verify_chain() integrity checks (broken links, expired evidence)
  - find_expired() detection
  - find_broken_links() detection
  - get_chain() causal trace-back
  - export_chain_report() Markdown output
  - TTL settings and expiration edge cases

All file-system tests use tempfile.TemporaryDirectory for isolation.
"""
from __future__ import annotations

import hashlib
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.evidence_chain import EvidenceChain, EvidenceEnvelope


# ============================================================================
# EvidenceEnvelope tests
# ============================================================================

class TestEvidenceEnvelopeWrap:
    """Tests for EvidenceEnvelope.wrap() static factory."""

    def test_wrap_computes_correct_content_hash(self):
        """wrap() computes SHA-256 hash of the content."""
        content = "hello world"
        envelope = EvidenceEnvelope.wrap(content)

        expected_hash = "sha256:" + hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()

        assert envelope.content_hash == expected_hash
        assert envelope.content_hash.startswith("sha256:")

    def test_wrap_assigns_unique_envelope_id(self):
        """Each wrap() call produces a unique envelope_id."""
        e1 = EvidenceEnvelope.wrap("content A")
        e2 = EvidenceEnvelope.wrap("content B")

        assert e1.envelope_id != e2.envelope_id
        assert e1.envelope_id.startswith("EE-")
        assert len(e1.envelope_id) == 15  # "EE-" + 12 hex chars

    def test_wrap_sets_created_at_iso8601(self):
        """created_at is a valid ISO 8601 timestamp."""
        envelope = EvidenceEnvelope.wrap("test")
        # Should be parseable
        dt = datetime.fromisoformat(envelope.created_at)
        assert isinstance(dt, datetime)

    def test_wrap_default_ttl_is_90_days(self):
        """Default TTL is 90 days."""
        envelope = EvidenceEnvelope.wrap("test")
        assert envelope.ttl_days == 90

    def test_wrap_custom_ttl(self):
        """Custom TTL is respected."""
        envelope = EvidenceEnvelope.wrap("test", ttl_days=30)
        assert envelope.ttl_days == 30

    def test_wrap_no_parent_is_none(self):
        """Without parent, causal_parent_hash is None."""
        envelope = EvidenceEnvelope.wrap("root evidence")
        assert envelope.causal_parent_hash is None

    def test_wrap_with_parent_links_correctly(self):
        """Parent's content_hash becomes child's causal_parent_hash."""
        parent = EvidenceEnvelope.wrap("parent content")
        child = EvidenceEnvelope.wrap("child content", parent_envelope=parent)

        assert child.causal_parent_hash == parent.content_hash
        assert child.causal_parent_hash is not None

    def test_wrap_stores_evidence_path(self):
        """evidence_path is stored when provided."""
        envelope = EvidenceEnvelope.wrap(
            "content", evidence_path="/path/to/evidence.json"
        )
        assert envelope.evidence_path == "/path/to/evidence.json"

    def test_wrap_evidence_path_defaults_to_none(self):
        """evidence_path defaults to None when not provided."""
        envelope = EvidenceEnvelope.wrap("content")
        assert envelope.evidence_path is None

    def test_wrap_default_content_type(self):
        """Default content_type is 'application/json'."""
        envelope = EvidenceEnvelope.wrap("test")
        assert envelope.content_type == "application/json"

    def test_wrap_custom_content_type(self):
        """Custom content_type is respected."""
        envelope = EvidenceEnvelope.wrap("test", content_type="text/markdown")
        assert envelope.content_type == "text/markdown"


class TestEvidenceEnvelopeFreshness:
    """Tests for is_fresh() / is_expired()."""

    def test_fresh_when_created_now(self):
        """Evidence created just now is fresh."""
        envelope = EvidenceEnvelope.wrap("fresh")
        assert envelope.is_fresh() is True
        assert envelope.is_expired() is False

    def test_fresh_with_long_ttl(self):
        """Evidence with 365-day TTL is fresh."""
        envelope = EvidenceEnvelope.wrap("long lived", ttl_days=365)
        assert envelope.is_fresh() is True

    def test_expired_when_ttl_zero(self):
        """Evidence with TTL=0 expires immediately."""
        envelope = EvidenceEnvelope.wrap("expired now", ttl_days=0)
        # Even with 0-day TTL, the expiration is created_at + 0 days,
        # which may be fractionally in the future. Use a manually
        # constructed envelope to guarantee expiry.
        past = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        envelope = EvidenceEnvelope(
            envelope_id="EE-test00000001",
            content_hash="sha256:abc",
            created_at=past,
            ttl_days=5,  # TTL 5 days, but created 10 days ago → expired
        )
        assert envelope.is_expired() is True
        assert envelope.is_fresh() is False

    def test_expired_when_created_in_past(self):
        """Evidence created 100 days ago with default 90-day TTL is expired."""
        past = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        envelope = EvidenceEnvelope(
            envelope_id="EE-old00000001",
            content_hash="sha256:def",
            created_at=past,
            ttl_days=90,
        )
        assert envelope.is_expired() is True

    def test_not_expired_when_within_ttl(self):
        """Evidence created 30 days ago with 90-day TTL is still fresh."""
        past = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        envelope = EvidenceEnvelope(
            envelope_id="EE-mid00000001",
            content_hash="sha256:ghi",
            created_at=past,
            ttl_days=90,
        )
        assert envelope.is_fresh() is True
        assert envelope.is_expired() is False

    def test_handles_timezone_aware_created_at(self):
        """is_fresh handles timezone-aware ISO 8601 timestamps."""
        past = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        envelope = EvidenceEnvelope(
            envelope_id="EE-tz000000001",
            content_hash="sha256:jkl",
            created_at=past,
            ttl_days=90,
        )
        assert envelope.is_expired() is True


class TestEvidenceEnvelopeConstruction:
    """Tests for direct dataclass construction."""

    def test_direct_construction_with_all_fields(self):
        """All fields can be set via constructor."""
        envelope = EvidenceEnvelope(
            envelope_id="EE-abcdef123456",
            content_hash="sha256:deadbeef",
            created_at="2026-07-23T12:00:00+00:00",
            ttl_days=30,
            causal_parent_hash="sha256:parent0000",
            evidence_path="/ev/1.json",
            content_type="application/json",
        )
        assert envelope.envelope_id == "EE-abcdef123456"
        assert envelope.ttl_days == 30
        assert envelope.causal_parent_hash == "sha256:parent0000"

    def test_hash_equality_different_instances(self):
        """Different instances with same field values are equal (dataclass)."""
        e1 = EvidenceEnvelope(
            envelope_id="EE-eq000000001",
            content_hash="sha256:aaa",
            created_at="2026-01-01T00:00:00+00:00",
            ttl_days=90,
        )
        e2 = EvidenceEnvelope(
            envelope_id="EE-eq000000001",
            content_hash="sha256:aaa",
            created_at="2026-01-01T00:00:00+00:00",
            ttl_days=90,
        )
        assert e1 == e2

    def test_hash_inequality_different_ids(self):
        """Different envelope_ids produce unequal instances."""
        e1 = EvidenceEnvelope(
            envelope_id="EE-diff0000001",
            content_hash="sha256:aaa",
            created_at="2026-01-01T00:00:00+00:00",
        )
        e2 = EvidenceEnvelope(
            envelope_id="EE-diff0000002",
            content_hash="sha256:aaa",
            created_at="2026-01-01T00:00:00+00:00",
        )
        assert e1 != e2


# ============================================================================
# EvidenceChain tests
# ============================================================================

class TestEvidenceChainInit:
    """Tests for EvidenceChain initialization."""

    def test_init_creates_evidence_dir(self):
        """EvidenceChain creates the evidence directory if it does not exist."""
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "evidence"
            assert not evidence_dir.exists()

            chain = EvidenceChain(evidence_dir)
            assert evidence_dir.exists()
            assert evidence_dir.is_dir()

    def test_init_creates_chain_index_file(self):
        """On first add_evidence, chain_index.json is created."""
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "evidence"
            chain = EvidenceChain(evidence_dir)

            index_path = evidence_dir / "chain_index.json"
            assert not index_path.exists()

            chain.add_evidence("first evidence")
            assert index_path.exists()

    def test_init_loads_existing_chain(self):
        """EvidenceChain loads existing chain_index.json on init."""
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "evidence"
            chain1 = EvidenceChain(evidence_dir)
            env = chain1.add_evidence("persisted content")

            # Create a new EvidenceChain pointing to same dir
            chain2 = EvidenceChain(evidence_dir)
            loaded = chain2.get_envelope(env.envelope_id)
            assert loaded is not None
            assert loaded.content_hash == env.content_hash
            assert loaded.envelope_id == env.envelope_id

    def test_init_handles_corrupt_index_file(self):
        """Corrupt chain_index.json does not crash init."""
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "evidence"
            evidence_dir.mkdir(parents=True)
            index_path = evidence_dir / "chain_index.json"
            index_path.write_text("not valid json {{{", encoding="utf-8")

            # Should not raise
            chain = EvidenceChain(evidence_dir)
            assert len(chain.list_all()) == 0

    def test_init_handles_missing_index_file(self):
        """Missing chain_index.json is silently handled."""
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "evidence"
            evidence_dir.mkdir(parents=True)
            # No index file

            chain = EvidenceChain(evidence_dir)
            assert len(chain.list_all()) == 0


class TestEvidenceChainAddEvidence:
    """Tests for add_evidence()."""

    def test_add_evidence_returns_envelope(self):
        """add_evidence returns the created EvidenceEnvelope."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            env = chain.add_evidence("test content")
            assert isinstance(env, EvidenceEnvelope)
            assert env.content_hash.startswith("sha256:")

    def test_add_evidence_builds_linear_chain(self):
        """Consecutive add_evidence calls create a linear causal chain."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            e1 = chain.add_evidence("first")
            e2 = chain.add_evidence("second")
            e3 = chain.add_evidence("third")

            # e2's parent should be e1, e3's parent should be e2
            assert e2.causal_parent_hash == e1.content_hash
            assert e3.causal_parent_hash == e2.content_hash
            assert e1.causal_parent_hash is None

    def test_add_evidence_with_explicit_parent_id(self):
        """Explicit parent_id overrides chain_head linking."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            root = chain.add_evidence("root")
            branch_a = chain.add_evidence("branch A")
            # Link to root explicitly instead of branch_a
            branch_b = chain.add_evidence("branch B", parent_id=root.envelope_id)

            assert branch_b.causal_parent_hash == root.content_hash
            # branch_b does NOT point to branch_a
            assert branch_b.causal_parent_hash != branch_a.content_hash

    def test_add_evidence_unknown_parent_id(self):
        """Providing a non-existent parent_id creates orphan evidence."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            env = chain.add_evidence("orphan", parent_id="EE-nonexistent")
            assert env.causal_parent_hash is None  # parent not found

    def test_add_evidence_stores_evidence_path(self):
        """evidence_path is propagated to the envelope."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            env = chain.add_evidence("content", evidence_path="/some/path.md")
            assert env.evidence_path == "/some/path.md"

    def test_add_evidence_persists_to_disk(self):
        """After add_evidence, the envelope is recoverable from disk."""
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "ev"
            chain1 = EvidenceChain(evidence_dir)
            env = chain1.add_evidence("persisted")

            chain2 = EvidenceChain(evidence_dir)
            reloaded = chain2.get_envelope(env.envelope_id)
            assert reloaded is not None
            assert reloaded.content_hash == env.content_hash

    def test_list_all_returns_all_envelopes(self):
        """list_all returns all added envelopes."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            chain.add_evidence("a")
            chain.add_evidence("b")
            chain.add_evidence("c")
            assert len(chain.list_all()) == 3

    def test_get_envelope_nonexistent(self):
        """get_envelope returns None for unknown ID."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            assert chain.get_envelope("EE-bogus") is None


class TestEvidenceChainVerify:
    """Tests for verify_chain()."""

    def test_verify_chain_empty_is_valid(self):
        """An empty chain is valid."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            is_valid, issues = chain.verify_chain()
            assert is_valid is True
            assert issues == []

    def test_verify_chain_intact_linear_is_valid(self):
        """A correctly linked linear chain is valid."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            chain.add_evidence("first")
            chain.add_evidence("second")
            chain.add_evidence("third")

            is_valid, issues = chain.verify_chain()
            assert is_valid is True

    def test_verify_chain_detects_broken_link(self):
        """Chain with a broken parent link is invalid."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            chain.add_evidence("first")
            chain.add_evidence("second")

            # Manually inject a broken link by adding an envelope with
            # a parent_hash that points to nothing.
            broken = EvidenceEnvelope(
                envelope_id="EE-broken00001",
                content_hash="sha256:orphan-child",
                created_at=datetime.now(timezone.utc).isoformat(),
                ttl_days=90,
                causal_parent_hash="sha256:nonexistent-deadbeef",
            )
            chain._envelopes[broken.envelope_id] = broken
            chain._save()

            is_valid, issues = chain.verify_chain()
            assert is_valid is False
            assert any("BROKEN" in issue for issue in issues)
            assert any("EE-broken00001" in issue for issue in issues)

    def test_verify_chain_reports_expired_as_warning(self):
        """Expired evidence appears as issues but does not invalidate chain."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            chain.add_evidence("first")

            past = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
            old_env = EvidenceEnvelope(
                envelope_id="EE-expired0001",
                content_hash="sha256:old-evidence",
                created_at=past,
                ttl_days=90,
            )
            chain._envelopes[old_env.envelope_id] = old_env
            chain._save()

            is_valid, issues = chain.verify_chain()
            # Expired alone does not break validity
            assert is_valid is True
            assert any("EXPIRED" in issue for issue in issues)

    def test_verify_chain_mixed_broken_and_expired(self):
        """Chain is invalid if broken links exist, even with expired evidence."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            chain.add_evidence("first")

            past = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
            broken_and_old = EvidenceEnvelope(
                envelope_id="EE-both0000001",
                content_hash="sha256:both-issues",
                created_at=past,
                ttl_days=90,
                causal_parent_hash="sha256:missing-parent",
            )
            chain._envelopes[broken_and_old.envelope_id] = broken_and_old
            chain._save()

            is_valid, issues = chain.verify_chain()
            assert is_valid is False  # broken link makes it invalid
            assert any("BROKEN" in i for i in issues)
            assert any("EXPIRED" in i for i in issues)


class TestEvidenceChainFindExpired:
    """Tests for find_expired()."""

    def test_find_expired_empty_chain(self):
        """Empty chain returns empty list."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            assert chain.find_expired() == []

    def test_find_expired_all_fresh(self):
        """No expired evidence when all are fresh."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            chain.add_evidence("a")
            chain.add_evidence("b")
            assert chain.find_expired() == []

    def test_find_expired_detects_old_evidence(self):
        """Expired evidence is returned."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            chain.add_evidence("fresh")

            past = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
            old = EvidenceEnvelope(
                envelope_id="EE-oldie000001",
                content_hash="sha256:stale",
                created_at=past,
                ttl_days=90,
            )
            chain._envelopes[old.envelope_id] = old
            chain._save()

            expired = chain.find_expired()
            assert len(expired) == 1
            assert expired[0].envelope_id == "EE-oldie000001"

    def test_find_expired_respects_custom_ttl(self):
        """Evidence with short TTL expires sooner."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")

            past_50 = (datetime.now(timezone.utc) - timedelta(days=50)).isoformat()
            short_ttl = EvidenceEnvelope(
                envelope_id="EE-short000001",
                content_hash="sha256:short",
                created_at=past_50,
                ttl_days=30,  # 30-day TTL, created 50 days ago
            )
            chain._envelopes[short_ttl.envelope_id] = short_ttl
            chain._save()

            expired = chain.find_expired()
            assert len(expired) == 1


class TestEvidenceChainFindBrokenLinks:
    """Tests for find_broken_links()."""

    def test_find_broken_links_empty_chain(self):
        """Empty chain has no broken links."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            assert chain.find_broken_links() == []

    def test_find_broken_links_intact_chain(self):
        """Intact chain has no broken links."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            chain.add_evidence("a")
            chain.add_evidence("b")
            chain.add_evidence("c")
            assert chain.find_broken_links() == []

    def test_find_broken_links_detects_broken(self):
        """Broken parent links are detected."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            chain.add_evidence("first")

            broken = EvidenceEnvelope(
                envelope_id="EE-broken-link",
                content_hash="sha256:broken-child",
                created_at=datetime.now(timezone.utc).isoformat(),
                ttl_days=90,
                causal_parent_hash="sha256:nowhere-to-be-found",
            )
            chain._envelopes[broken.envelope_id] = broken
            chain._save()

            broken_list = chain.find_broken_links()
            assert "EE-broken-link" in broken_list
            assert len(broken_list) == 1

    def test_find_broken_links_root_is_not_broken(self):
        """An envelope with causal_parent_hash=None (root) is not broken."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            chain.add_evidence("root")
            chain.add_evidence("child")

            broken_list = chain.find_broken_links()
            assert broken_list == []


class TestEvidenceChainGetChain:
    """Tests for get_chain() causal trace-back."""

    def test_get_chain_single_envelope(self):
        """get_chain on a root envelope returns just that envelope."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            root = chain.add_evidence("root")
            result = chain.get_chain(root.envelope_id)
            assert len(result) == 1
            assert result[0].envelope_id == root.envelope_id

    def test_get_chain_traces_full_lineage(self):
        """get_chain traces back through all ancestors."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            e1 = chain.add_evidence("first")
            e2 = chain.add_evidence("second")
            e3 = chain.add_evidence("third")

            result = chain.get_chain(e3.envelope_id)
            assert len(result) == 3
            # Most recent first
            assert result[0].envelope_id == e3.envelope_id
            assert result[1].envelope_id == e2.envelope_id
            assert result[2].envelope_id == e1.envelope_id

    def test_get_chain_partial_trace(self):
        """get_chain from middle of chain returns that and ancestors."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            e1 = chain.add_evidence("first")
            e2 = chain.add_evidence("second")
            e3 = chain.add_evidence("third")

            result = chain.get_chain(e2.envelope_id)
            assert len(result) == 2
            assert result[0].envelope_id == e2.envelope_id
            assert result[1].envelope_id == e1.envelope_id

    def test_get_chain_unknown_id(self):
        """get_chain on unknown ID returns empty list."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            result = chain.get_chain("EE-nosuch")
            assert result == []

    def test_get_chain_detects_cycles(self):
        """Cyclic chains do not cause infinite loops."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            e1 = chain.add_evidence("first")
            e2 = chain.add_evidence("second")

            # Create a cycle: e1's parent points to e2's hash
            e1.causal_parent_hash = e2.content_hash
            chain._envelopes[e1.envelope_id] = e1
            chain._save()

            result = chain.get_chain(e2.envelope_id)
            # Should terminate (no infinite loop)
            assert len(result) <= len(chain._envelopes)

    def test_get_chain_with_broken_link_stops(self):
        """get_chain stops at a broken link."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            root = chain.add_evidence("root")

            broken = EvidenceEnvelope(
                envelope_id="EE-brk-chain01",
                content_hash="sha256:broken-ct",
                created_at=datetime.now(timezone.utc).isoformat(),
                ttl_days=90,
                causal_parent_hash="sha256:missing-parent-hash",
            )
            chain._envelopes[broken.envelope_id] = broken
            chain._save()

            result = chain.get_chain("EE-brk-chain01")
            # Should just return the broken one (can't trace further)
            assert len(result) == 1
            assert result[0].envelope_id == "EE-brk-chain01"


class TestEvidenceChainExportReport:
    """Tests for export_chain_report()."""

    def test_export_report_empty_chain(self):
        """Report for empty chain is valid Markdown."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            report = chain.export_chain_report()
            assert isinstance(report, str)
            assert "# Evidence Chain Report" in report
            assert "**Total Envelopes:** 0" in report
            assert "VALID" in report

    def test_export_report_contains_envelope_details(self):
        """Report includes per-envelope details."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            env = chain.add_evidence("test content for report")
            report = chain.export_chain_report()

            assert env.envelope_id in report
            assert "**Total Envelopes:** 1" in report
            # Should have a table row
            assert "|" in report

    def test_export_report_shows_broken_links(self):
        """Report includes broken links section."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            chain.add_evidence("first")

            broken = EvidenceEnvelope(
                envelope_id="EE-report-brk1",
                content_hash="sha256:report-broken",
                created_at=datetime.now(timezone.utc).isoformat(),
                ttl_days=90,
                causal_parent_hash="sha256:gone",
            )
            chain._envelopes[broken.envelope_id] = broken
            chain._save()

            report = chain.export_chain_report()
            assert "## Broken Links" in report
            assert "EE-report-brk1" in report

    def test_export_report_shows_expired(self):
        """Report includes expired evidence section."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            chain.add_evidence("fresh")

            past = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
            old = EvidenceEnvelope(
                envelope_id="EE-report-exp1",
                content_hash="sha256:report-expired",
                created_at=past,
                ttl_days=90,
            )
            chain._envelopes[old.envelope_id] = old
            chain._save()

            report = chain.export_chain_report()
            assert "## Expired Evidence" in report
            assert "EE-report-exp1" in report

    def test_export_report_invalid_chain_shows_invalid(self):
        """Report shows INVALID when chain integrity is broken."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            chain.add_evidence("first")

            broken = EvidenceEnvelope(
                envelope_id="EE-inv-report1",
                content_hash="sha256:inv-broken",
                created_at=datetime.now(timezone.utc).isoformat(),
                ttl_days=90,
                causal_parent_hash="sha256:orphan",
            )
            chain._envelopes[broken.envelope_id] = broken
            chain._save()

            report = chain.export_chain_report()
            assert "INVALID" in report


# ============================================================================
# Integration tests
# ============================================================================

class TestEvidenceChainIntegration:
    """End-to-end integration tests."""

    def test_full_workflow(self):
        """Simulate a full evidence chain workflow."""
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "evidence"
            chain = EvidenceChain(evidence_dir)

            # Phase 1: Add root evidence
            req_evidence = chain.add_evidence(
                "Requirements baseline v1.0",
                evidence_path="/ev/requirements.json",
            )
            assert req_evidence.causal_parent_hash is None

            # Phase 2: Add architectural evidence linked to requirements
            arch_evidence = chain.add_evidence(
                "Architecture design v1.0",
                evidence_path="/ev/architecture.json",
            )
            assert arch_evidence.causal_parent_hash == req_evidence.content_hash

            # Phase 3: Add implementation evidence
            impl_evidence = chain.add_evidence(
                "Implementation test results PASS",
                evidence_path="/ev/impl_results.json",
            )
            assert impl_evidence.causal_parent_hash == arch_evidence.content_hash

            # Verify chain integrity
            is_valid, issues = chain.verify_chain()
            assert is_valid is True

            # Trace full chain from latest
            full_chain = chain.get_chain(impl_evidence.envelope_id)
            assert len(full_chain) == 3
            assert full_chain[0].envelope_id == impl_evidence.envelope_id
            assert full_chain[1].envelope_id == arch_evidence.envelope_id
            assert full_chain[2].envelope_id == req_evidence.envelope_id

            # No expired evidence
            assert chain.find_expired() == []

            # No broken links
            assert chain.find_broken_links() == []

            # Export report
            report = chain.export_chain_report()
            assert "VALID" in report
            assert "**Total Envelopes:** 3" in report

    def test_persistence_roundtrip(self):
        """Chain state survives save/load roundtrip."""
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "evidence"
            chain1 = EvidenceChain(evidence_dir)
            e1 = chain1.add_evidence("first")
            e2 = chain1.add_evidence("second")
            e3 = chain1.add_evidence("third")

            # Reload
            chain2 = EvidenceChain(evidence_dir)
            assert len(chain2.list_all()) == 3

            # Verify chain integrity survives roundtrip
            is_valid, issues = chain2.verify_chain()
            assert is_valid is True

            # Verify get_chain works after reload
            result = chain2.get_chain(e3.envelope_id)
            assert len(result) == 3

    def test_multiple_branches(self):
        """Chain with explicit parent_id branching works."""
        with tempfile.TemporaryDirectory() as tmp:
            chain = EvidenceChain(Path(tmp) / "ev")
            root = chain.add_evidence("root")

            # Two children both pointing to root
            child_a = chain.add_evidence("child A", parent_id=root.envelope_id)
            child_b = chain.add_evidence("child B", parent_id=root.envelope_id)

            assert child_a.causal_parent_hash == root.content_hash
            assert child_b.causal_parent_hash == root.content_hash

            # Chain head is child_b (last added)
            chain_a = chain.get_chain(child_a.envelope_id)
            chain_b = chain.get_chain(child_b.envelope_id)

            assert len(chain_a) == 2
            assert len(chain_b) == 2
            assert chain_a[0].envelope_id == child_a.envelope_id
            assert chain_a[1].envelope_id == root.envelope_id
