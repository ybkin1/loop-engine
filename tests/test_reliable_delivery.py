"""T-0089 U7: reliable evidence delivery — AC-02 acceptance tests.

Covers the four AC-02 acceptance criteria for the ``transactional_write_texts``
reliability enhancements (idempotency, backoff retry, stale recovery, backward
compatibility):

- AC-02a: idempotent writes — resubmitting identical content produces no
  duplicate write / duplicate record; different content writes normally.
- AC-02b: backoff retry — transient failures are retried with exponential
  backoff and succeed; exhausting the attempt limit raises a clear error
  instead of silently dropping the write.
- AC-02c: stale recovery — an expired journal marker is reset safely, while a
  fresh marker or an actively-written (concurrent writer) marker is refused.
- AC-02d: backward compatibility — with default parameters the behavior is
  byte-identical to the legacy implementation.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = PROJECT_ROOT / ".zcode" / "tools"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import governor_lib  # noqa: E402
from governor_lib import (  # noqa: E402
    RetryPolicy,
    TransactionResult,
    transactional_write_texts,
)

MARKER_NAME = ".project-governor-transaction.json"
IDEMPOTENCY_TABLE = ".project-governor-idempotency.json"


def _stale_marker(base: Path, *, created_at: str, entries: list[dict] | None = None) -> Path:
    """Write an unresolved journal marker that looks old enough to reset."""
    marker = base / MARKER_NAME
    marker.write_text(
        json.dumps(
            {
                "transaction_id": "stale-tx-001",
                "entries": entries or [],
                "committed": [],
                "created_at": created_at,
            }
        ),
        encoding="utf-8",
    )
    return marker


class ReliableDeliveryBase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name) / ".ai"
        self.base.mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def marker(self) -> Path:
        return self.base / MARKER_NAME

    def table(self) -> Path:
        return self.base / IDEMPOTENCY_TABLE

    def assert_no_leftovers(self) -> None:
        leftovers = [
            path.name for path in self.base.iterdir()
            if path.name.endswith(".tmp") or path.name.endswith(".bak")
        ]
        self.assertEqual(leftovers, [], f"staged/backup leftovers: {leftovers}")


# ── AC-02a: idempotent writes ────────────────────────────────────────────────


class IdempotentWriteTests(ReliableDeliveryBase):
    def test_duplicate_submission_skips_write_and_records_once(self) -> None:
        target = self.base / "state.yaml"
        first = transactional_write_texts(self.base, {target: "content-a"}, idempotent=True)
        self.assertEqual(first.written, [str(target)])
        self.assertEqual(first.skipped, [])

        second = transactional_write_texts(self.base, {target: "content-a"}, idempotent=True)
        self.assertEqual(second.written, [])
        self.assertEqual(second.skipped, [str(target)])

        # No duplicate write: content unchanged and exactly one table record.
        self.assertEqual(target.read_text(encoding="utf-8"), "content-a")
        table = json.loads(self.table().read_text(encoding="utf-8"))
        self.assertEqual(len(table), 1)
        self.assertEqual(table[str(target)]["fingerprint"], governor_lib.hashlib.sha256(b"content-a").hexdigest())

    def test_different_content_writes_and_updates_fingerprint(self) -> None:
        target = self.base / "note.txt"
        transactional_write_texts(self.base, {target: "v1"}, idempotent=True)
        second = transactional_write_texts(self.base, {target: "v2"}, idempotent=True)
        self.assertEqual(second.written, [str(target)])
        self.assertEqual(second.skipped, [])
        self.assertEqual(target.read_text(encoding="utf-8"), "v2")
        table = json.loads(self.table().read_text(encoding="utf-8"))
        self.assertEqual(table[str(target)]["fingerprint"], governor_lib.hashlib.sha256(b"v2").hexdigest())
        # The new fingerprint now deduplicates.
        third = transactional_write_texts(self.base, {target: "v2"}, idempotent=True)
        self.assertEqual(third.skipped, [str(target)])

    def test_partial_duplicate_multi_path_transaction(self) -> None:
        first_path = self.base / "a.yaml"
        second_path = self.base / "b.yaml"
        transactional_write_texts(self.base, {first_path: "same", second_path: "same"}, idempotent=True)
        retry = transactional_write_texts(self.base, {first_path: "same", second_path: "changed"}, idempotent=True)
        self.assertEqual(sorted(retry.skipped), [str(first_path)])
        self.assertEqual(sorted(retry.written), [str(second_path)])
        self.assertEqual(second_path.read_text(encoding="utf-8"), "changed")
        table = json.loads(self.table().read_text(encoding="utf-8"))
        self.assertEqual(set(table), {str(first_path), str(second_path)})

    def test_skipped_write_leaves_no_staged_files_or_marker(self) -> None:
        target = self.base / "evidence.md"
        transactional_write_texts(self.base, {target: "content"}, idempotent=True)
        skipped = transactional_write_texts(self.base, {target: "content"}, idempotent=True)
        self.assertEqual(skipped.skipped, [str(target)])
        self.assertFalse(self.marker().exists())
        self.assert_no_leftovers()


# ── AC-02b: backoff retry ────────────────────────────────────────────────────


class BackoffRetryTests(ReliableDeliveryBase):
    def _fail_first_commits(self, failures: int):
        """Patch os.replace to fail the first N staged->target commits."""
        real_replace = governor_lib.os.replace
        counter = {"left": failures}

        def flaky(source, destination):
            if str(source).endswith(".tmp") and counter["left"] > 0:
                counter["left"] -= 1
                raise OSError("injected commit failure")
            return real_replace(source, destination)

        return mock.patch.object(governor_lib.os, "replace", side_effect=flaky)

    def test_retry_succeeds_after_failures_with_exponential_backoff(self) -> None:
        target = self.base / "state.yaml"
        sleeps = []

        with self._fail_first_commits(2), mock.patch.object(
            governor_lib, "_sleep", side_effect=lambda seconds: sleeps.append(seconds)
        ):
            result = transactional_write_texts(
                self.base, {target: "after"},
                retry={"max_attempts": 4, "backoff_base_seconds": 0.01, "backoff_multiplier": 2.0},
            )
        self.assertIsInstance(result, TransactionResult)
        self.assertEqual(result.attempts, 3)
        self.assertEqual(result.written, [str(target)])
        self.assertEqual(target.read_text(encoding="utf-8"), "after")
        # Exponential backoff: base * multiplier^(attempt-1).
        self.assertEqual(sleeps, [0.01, 0.02])
        self.assertFalse(self.marker().exists())
        self.assert_no_leftovers()

    def test_retry_exhaustion_raises_clear_error_not_silent_drop(self) -> None:
        target = self.base / "state.yaml"
        sleeps = []

        with self._fail_first_commits(99), mock.patch.object(
            governor_lib, "_sleep", side_effect=lambda seconds: sleeps.append(seconds)
        ):
            with self.assertRaisesRegex(OSError, "injected commit failure"):
                transactional_write_texts(
                    self.base, {target: "never"},
                    retry=RetryPolicy(max_attempts=3, backoff_base_seconds=0.01),
                )
        self.assertEqual(sleeps, [0.01, 0.02])
        # Nothing was silently written; the journal is clean for the next attempt.
        self.assertFalse(target.exists())
        self.assertFalse(self.marker().exists())
        self.assert_no_leftovers()

    def test_retry_recovers_from_concurrent_modification_conflict(self) -> None:
        target = self.base / "state.yaml"
        target.write_text("before", encoding="utf-8")
        real_fingerprint = governor_lib.file_fingerprint
        tampered = {"done": False}

        def fingerprint_once(path):
            fingerprint = real_fingerprint(path)
            # Simulate the target changing on disk after staging: the first
            # commit-phase fingerprint check sees a different fingerprint and
            # raises the concurrent-modification conflict.
            if not tampered["done"]:
                tampered["done"] = True
                return "0" * 64 if fingerprint is not None else None
            return fingerprint

        with mock.patch.object(governor_lib, "file_fingerprint", side_effect=fingerprint_once), mock.patch.object(
            governor_lib, "_sleep"
        ):
            result = transactional_write_texts(
                self.base, {target: "after"},
                retry={"max_attempts": 3, "backoff_base_seconds": 0.0},
            )
        # Attempt 1 hit "Concurrent modification detected" and rolled back;
        # attempt 2 staged and committed cleanly.
        self.assertEqual(result.attempts, 2)
        self.assertEqual(target.read_text(encoding="utf-8"), "after")
        self.assertFalse(self.marker().exists())

    def test_first_attempt_success_reports_one_attempt(self) -> None:
        target = self.base / "ok.txt"
        sleeps = []
        with mock.patch.object(governor_lib, "_sleep", side_effect=lambda seconds: sleeps.append(seconds)):
            result = transactional_write_texts(
                self.base, {target: "ok"}, retry={"max_attempts": 5, "backoff_base_seconds": 0.01}
            )
        self.assertEqual(result.attempts, 1)
        self.assertEqual(sleeps, [])
        self.assertEqual(target.read_text(encoding="utf-8"), "ok")

    def test_invalid_retry_policy_rejected(self) -> None:
        target = self.base / "x.txt"
        with self.assertRaisesRegex(Exception, "max_attempts"):
            transactional_write_texts(self.base, {target: "x"}, retry={"max_attempts": 0})
        with self.assertRaisesRegex(Exception, "Unknown retry policy keys"):
            transactional_write_texts(self.base, {target: "x"}, retry={"max_attempts": 2, "bogus": 1})
        self.assertFalse(target.exists())


# ── AC-02c: stale recovery / stuck-transaction reset ─────────────────────────


class StaleRecoveryTests(ReliableDeliveryBase):
    def _leftover_entry(self, name: str) -> dict:
        staged = self.base / f".{name}.STALE.tmp"
        backup = self.base / f".{name}.STALE.bak"
        staged.write_text("staged", encoding="utf-8")
        backup.write_text("backup", encoding="utf-8")
        return {"path": str(self.base / name), "staged": str(staged), "backup": str(backup),
                "existed": False, "fingerprint": None}

    def test_stale_marker_reset_allows_rewrite_and_cleans_leftovers(self) -> None:
        target = self.base / "state.yaml"
        entry = self._leftover_entry("state.yaml")
        _stale_marker(self.base, created_at=(datetime.now().astimezone() - timedelta(hours=2)).isoformat(), entries=[entry])

        transactional_write_texts(self.base, {target: "fresh"}, stale_timeout_seconds=60)

        self.assertEqual(target.read_text(encoding="utf-8"), "fresh")
        self.assertFalse(self.marker().exists())
        # Leftover staged/backup files from the stale transaction were cleaned.
        self.assertFalse(Path(entry["staged"]).exists())
        self.assertFalse(Path(entry["backup"]).exists())
        self.assert_no_leftovers()

    def test_fresh_marker_refused_as_concurrent_writer(self) -> None:
        target = self.base / "state.yaml"
        entry = self._leftover_entry("state.yaml")
        _stale_marker(self.base, created_at=datetime.now().astimezone().isoformat(), entries=[entry])

        with self.assertRaisesRegex(RuntimeError, "Active Project Governor transaction in progress"):
            transactional_write_texts(self.base, {target: "fresh"}, stale_timeout_seconds=60)

        # Refusal is non-destructive: marker and leftovers stay for the owner.
        self.assertTrue(self.marker().exists())
        self.assertTrue(Path(entry["staged"]).exists())
        self.assertFalse(target.exists())

    def test_stale_marker_with_active_writer_refused(self) -> None:
        target = self.base / "state.yaml"
        _stale_marker(self.base, created_at=(datetime.now().astimezone() - timedelta(hours=2)).isoformat())
        mutated = {"done": False}

        def active_writer(seconds):
            # During the no-concurrent-writer settle interval a foreign writer
            # keeps committing to the journal — the reset must refuse.
            if not mutated["done"]:
                mutated["done"] = True
                marker = self.marker()
                marker.write_text(
                    marker.read_text(encoding="utf-8").replace('"committed": []', '"committed": ["state.yaml"]'),
                    encoding="utf-8",
                )

        with mock.patch.object(governor_lib, "_sleep", side_effect=active_writer):
            with self.assertRaisesRegex(RuntimeError, "Concurrent writer detected while resetting stale transaction"):
                transactional_write_texts(self.base, {target: "fresh"}, stale_timeout_seconds=60)
        self.assertTrue(self.marker().exists())
        self.assertFalse(target.exists())

    def test_legacy_journal_without_created_at_uses_mtime(self) -> None:
        target = self.base / "state.yaml"
        marker = self.marker()
        marker.write_text(
            json.dumps({"transaction_id": "legacy", "entries": [], "committed": []}),
            encoding="utf-8",
        )
        old = time.time() - 3600
        os.utime(marker, (old, old))

        transactional_write_texts(self.base, {target: "fresh"}, stale_timeout_seconds=60)

        self.assertEqual(target.read_text(encoding="utf-8"), "fresh")
        self.assertFalse(marker.exists())

    def test_corrupt_journal_refused_not_deleted(self) -> None:
        target = self.base / "state.yaml"
        marker = self.marker()
        marker.write_text("{not-json", encoding="utf-8")
        old = time.time() - 3600
        os.utime(marker, (old, old))

        with self.assertRaisesRegex(RuntimeError, "Corrupt transaction journal"):
            transactional_write_texts(self.base, {target: "fresh"}, stale_timeout_seconds=60)
        self.assertTrue(marker.exists(), "corrupt marker must not be destroyed")
        self.assertFalse(target.exists())


# ── AC-02d: backward compatibility (defaults unchanged) ─────────────────────


class BackwardCompatibilityTests(ReliableDeliveryBase):
    def test_default_success_matches_legacy_semantics(self) -> None:
        target = self.base / "state.yaml"
        result = transactional_write_texts(self.base, {target: "value"})
        self.assertIsNone(result)
        self.assertEqual(target.read_text(encoding="utf-8"), "value")
        self.assertFalse(self.marker().exists())
        self.assertFalse(self.table().exists(), "default mode must not create the idempotency table")
        self.assert_no_leftovers()

    def test_default_repeated_submission_rewrites_every_time(self) -> None:
        target = self.base / "state.yaml"
        transactional_write_texts(self.base, {target: "v1"})
        transactional_write_texts(self.base, {target: "v2"})
        # No dedup records are kept in default mode.
        self.assertFalse(self.table().exists())
        self.assertEqual(target.read_text(encoding="utf-8"), "v2")

    def test_default_unresolved_marker_raises_legacy_error(self) -> None:
        marker = self.marker()
        marker.write_text("{}", encoding="utf-8")
        target = self.base / "state.yaml"
        with self.assertRaisesRegex(RuntimeError, "Unresolved Project Governor transaction"):
            transactional_write_texts(self.base, {target: "value"})
        # Refusal is non-destructive and the marker is left untouched.
        self.assertTrue(marker.exists())
        self.assertEqual(marker.read_text(encoding="utf-8"), "{}")
        self.assertFalse(target.exists())

    def test_default_rolls_back_after_partial_commit(self) -> None:
        first = self.base / "first.txt"
        second = self.base / "second.txt"
        first.write_text("before-first", encoding="utf-8")
        second.write_text("before-second", encoding="utf-8")
        real_replace = governor_lib.os.replace
        calls = {"n": 0}

        def fail_second_commit(source, destination):
            if str(source).endswith(".tmp"):
                calls["n"] += 1
                if calls["n"] == 2:
                    raise OSError("injected partial commit failure")
            return real_replace(source, destination)

        with mock.patch.object(governor_lib.os, "replace", side_effect=fail_second_commit):
            with self.assertRaises(OSError):
                transactional_write_texts(self.base, {first: "after-first", second: "after-second"})
        self.assertEqual(first.read_text(encoding="utf-8"), "before-first")
        self.assertEqual(second.read_text(encoding="utf-8"), "before-second")
        self.assertFalse(self.marker().exists())
        self.assert_no_leftovers()


if __name__ == "__main__":
    unittest.main()
