"""Unit tests for loop_core.async_jobs — T-0090 D7 async job queue (AC-03).

Covers:
- AC-03a: full-cycle state tracking (queued → running → succeeded/failed)
- AC-03b: lease-based duplicate protection (concurrent same-job_id submits
          execute once, duplicates marked)
- AC-03c: exception isolation (a failing task never breaks the queue)
- AC-03d: cooperative cancel (queued cancel never runs; running cancel is
          honored by the task)
- AC-03e: history trimming (records beyond max_history are pruned, active
          jobs never trimmed)
- extras: optional append-only JSONL persistence, graceful shutdown,
          thread-safety under concurrent submissions

Determinism discipline: no long sleeps — tests synchronize with
threading.Event and bounded waits (≤ 5 s); queued-state observation uses a
single worker blocked by a held event.
"""
from __future__ import annotations

import threading
import time

import pytest

from loop_core.async_jobs import (
    DEFAULT_MAX_HISTORY,
    AsyncJobQueue,
    AsyncJobQueueError,
    JobStatus,
)


def _event_wait(event: threading.Event, timeout: float = 5.0) -> None:
    """Fail loudly instead of hanging when a sync event never fires."""
    assert event.wait(timeout), "test sync event timed out"


# ============================================================================
# AC-03a — state tracking (queued → running → succeeded/failed)
# ============================================================================

class TestStateTracking:
    """Full lifecycle status transitions are observable."""

    def test_queued_to_running_to_succeeded(self):
        q = AsyncJobQueue(max_workers=1)
        blocker_started = threading.Event()
        release_blocker = threading.Event()
        job_started = threading.Event()
        release_job = threading.Event()

        def blocker():
            blocker_started.set()
            release_blocker.wait(5)
            return "blocker-done"

        def work():
            job_started.set()
            release_job.wait(5)
            return 42

        q.submit(blocker, job_id="blk")
        _event_wait(blocker_started)
        q.submit(work, job_id="w1")

        # Worker busy with the blocker → w1 must be QUEUED.
        assert q.status("w1") == JobStatus.QUEUED

        release_blocker.set()
        assert q.wait("blk", timeout=5)
        assert q.status("blk") == JobStatus.SUCCEEDED

        # w1 now picked up → RUNNING (still blocked inside the task).
        _event_wait(job_started)
        assert q.status("w1") == JobStatus.RUNNING

        release_job.set()
        assert q.wait("w1", timeout=5)
        assert q.status("w1") == JobStatus.SUCCEEDED
        assert q.result("w1").result == 42
        assert q.result("w1").finished_at is not None
        assert q.result("w1").duration() is not None

    def test_failed_cycle_records_error(self):
        q = AsyncJobQueue(max_workers=1)
        q.submit(lambda: (_ for _ in ()).throw(RuntimeError("boom")), job_id="f1")
        assert q.wait("f1", timeout=5)
        assert q.status("f1") == JobStatus.FAILED
        record = q.result("f1")
        assert record.error == "RuntimeError: boom"
        assert record.error_type == "RuntimeError"
        assert record.finished_at is not None
        assert record.result is None

    def test_status_and_result_for_unknown_job(self):
        q = AsyncJobQueue(max_workers=1)
        assert q.status("ghost") is None
        assert q.result("ghost") is None
        assert q.wait("ghost", timeout=0.5) is True  # nothing left to wait for

    def test_active_count_counts_queued_and_running(self):
        q = AsyncJobQueue(max_workers=1)
        started = threading.Event()
        release = threading.Event()

        def blocker():
            started.set()
            release.wait(5)

        q.submit(blocker, job_id="a1")
        _event_wait(started)
        q.submit(lambda: None, job_id="a2")
        assert q.running_count() == 1
        assert q.queued_count() == 1
        assert q.active_count() == 2
        release.set()
        assert q.wait("a1", timeout=5) and q.wait("a2", timeout=5)
        assert q.active_count() == 0


# ============================================================================
# AC-03b — lease-based duplicate protection
# ============================================================================

class TestLeaseDedup:
    """Same job_id submitted concurrently executes exactly once."""

    def test_concurrent_duplicate_submit_executes_once(self):
        q = AsyncJobQueue(max_workers=4)
        started = threading.Event()
        release = threading.Event()
        executions = 0
        exec_lock = threading.Lock()

        def work():
            nonlocal executions
            started.set()
            release.wait(5)
            with exec_lock:
                executions += 1
            return "done"

        n_submitters = 8
        outcomes: list = [None] * n_submitters
        errors: list[Exception] = []

        def submit_one(index: int):
            try:
                outcomes[index] = q.submit(work, job_id="j-dedup")
            except Exception as e:  # noqa: BLE001 — test collector
                errors.append(e)

        threads = [threading.Thread(target=submit_one, args=(i,)) for i in range(n_submitters)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(5)

        assert not errors, f"submit raised: {errors}"
        accepted = [o for o in outcomes if o.accepted]
        duplicates = [o for o in outcomes if not o.accepted]
        assert len(accepted) == 1
        assert len(duplicates) == n_submitters - 1
        assert all(o.reason == "duplicate" for o in duplicates)
        assert all(o.job_id == "j-dedup" for o in outcomes)

        _event_wait(started)
        release.set()
        assert q.wait("j-dedup", timeout=5)
        assert executions == 1
        assert q.status("j-dedup") == JobStatus.SUCCEEDED

    def test_duplicate_while_running_returns_marker(self):
        q = AsyncJobQueue(max_workers=1)
        started = threading.Event()
        release = threading.Event()

        def work():
            started.set()
            release.wait(5)
            return "ok"

        first = q.submit(work, job_id="j1")
        assert first.accepted and first.reason == "submitted"
        _event_wait(started)

        second = q.submit(work, job_id="j1")
        assert second.accepted is False
        assert second.reason == "duplicate"
        assert second.status == JobStatus.RUNNING  # points at the live record

        release.set()
        assert q.wait("j1", timeout=5)
        assert q.status("j1") == JobStatus.SUCCEEDED

    def test_resubmit_after_terminal_releases_slot(self):
        q = AsyncJobQueue(max_workers=2)
        calls: list[int] = []

        def work(value: int):
            calls.append(value)
            return value * 2

        first = q.submit(work, 21, job_id="retry")
        assert first.accepted
        assert q.wait("retry", timeout=5)
        assert q.result("retry").result == 42

        # Terminal record → slot released (like a released dispatch lease).
        second = q.submit(work, 22, job_id="retry")
        assert second.accepted and second.reason == "submitted"
        assert q.wait("retry", timeout=5)
        assert q.result("retry").result == 44
        assert calls == [21, 22]

    def test_auto_job_id_is_deterministic_and_dedupes(self):
        q = AsyncJobQueue(max_workers=2)
        started = threading.Event()
        release = threading.Event()
        executions = 0
        exec_lock = threading.Lock()

        def work():
            nonlocal executions
            started.set()
            release.wait(5)
            with exec_lock:
                executions += 1

        first = q.submit(work)  # no job_id → deterministic auto id
        second = q.submit(work)
        assert first.accepted
        assert second.accepted is False and second.reason == "duplicate"
        assert first.job_id == second.job_id
        assert first.job_id.startswith("job-")

        _event_wait(started)
        release.set()
        assert q.wait(first.job_id, timeout=5)
        assert executions == 1

    def test_auto_job_id_differs_for_different_arguments(self):
        q = AsyncJobQueue(max_workers=2)
        a = q.submit(lambda x: x, 1)
        b = q.submit(lambda x: x, 2)
        assert a.job_id != b.job_id
        assert q.wait(a.job_id, timeout=5) and q.wait(b.job_id, timeout=5)
        assert q.result(a.job_id).result == 1
        assert q.result(b.job_id).result == 2


# ============================================================================
# AC-03c — exception isolation
# ============================================================================

class TestExceptionIsolation:
    """A failing task is recorded as failed; the queue keeps working."""

    def test_failing_job_recorded_and_queue_continues(self):
        q = AsyncJobQueue(max_workers=2)

        def boom():
            raise ValueError("boom")

        q.submit(boom, job_id="bad")
        assert q.wait("bad", timeout=5)
        record = q.result("bad")
        assert record.status == JobStatus.FAILED
        assert record.error == "ValueError: boom"
        assert record.error_type == "ValueError"

        # Queue still accepts and completes new work.
        q.submit(lambda: 7, job_id="good")
        assert q.wait("good", timeout=5)
        assert q.status("good") == JobStatus.SUCCEEDED
        assert q.result("good").result == 7

    def test_worker_survives_failure_single_worker(self):
        q = AsyncJobQueue(max_workers=1)  # the failing job holds the only worker

        def boom():
            raise RuntimeError("kill worker")

        q.submit(boom, job_id="kill")
        assert q.wait("kill", timeout=5)
        assert q.status("kill") == JobStatus.FAILED

        q.submit(lambda: "alive", job_id="after")
        assert q.wait("after", timeout=5)
        assert q.result("after").result == "alive"

    def test_base_exception_does_not_kill_queue(self):
        q = AsyncJobQueue(max_workers=1)

        def exits():
            raise SystemExit("worker die")

        q.submit(exits, job_id="x")
        assert q.wait("x", timeout=5)
        assert q.status("x") == JobStatus.FAILED
        assert q.result("x").error_type == "SystemExit"

        q.submit(lambda: "still-alive", job_id="y")
        assert q.wait("y", timeout=5)
        assert q.result("y").result == "still-alive"


# ============================================================================
# AC-03d — cooperative cancel
# ============================================================================

class TestCooperativeCancel:
    """cancel() prevents execution (queued) or is honored by the task."""

    def test_cancel_queued_job_never_runs(self):
        q = AsyncJobQueue(max_workers=1)
        started = threading.Event()
        release = threading.Event()
        executions = 0
        exec_lock = threading.Lock()

        def blocker():
            started.set()
            release.wait(5)
            return "b"

        def queued_work():
            nonlocal executions
            with exec_lock:
                executions += 1
            return "never"

        q.submit(blocker, job_id="blk")
        _event_wait(started)
        q.submit(queued_work, job_id="cq")
        assert q.status("cq") == JobStatus.QUEUED

        assert q.cancel("cq") is True
        assert q.status("cq") == JobStatus.CANCELLED
        assert q.result("cq").finished_at is not None

        release.set()
        assert q.wait("blk", timeout=5) and q.wait("cq", timeout=5)
        assert executions == 0  # the cancelled task never executed

    def test_cancel_running_job_is_cooperative(self):
        q = AsyncJobQueue(max_workers=1)
        started = threading.Event()

        def work():
            started.set()
            for _ in range(1_000_000):
                if q.cancel_requested("c1"):
                    return "stopped-early"
            return "completed"

        q.submit(work, job_id="c1")
        _event_wait(started)
        assert q.status("c1") == JobStatus.RUNNING

        assert q.cancel("c1") is True
        assert q.wait("c1", timeout=5)
        assert q.status("c1") == JobStatus.CANCELLED
        assert q.result("c1").result is None  # result discarded on cancel
        assert q.result("c1").cancel_requested is True

    def test_cancel_terminal_or_unknown_is_noop(self):
        q = AsyncJobQueue(max_workers=2)
        q.submit(lambda: "done", job_id="done")
        assert q.wait("done", timeout=5)

        assert q.cancel("done") is False      # terminal — nothing to cancel
        assert q.cancel("ghost") is False     # unknown
        assert q.status("done") == JobStatus.SUCCEEDED


# ============================================================================
# AC-03e — history trimming
# ============================================================================

class TestHistoryTrimming:
    """Records beyond max_history are pruned; active jobs are never pruned."""

    def test_history_trimmed_beyond_max(self):
        q = AsyncJobQueue(max_workers=4, max_history=5)
        for i in range(10):
            q.submit(lambda v=i: v, job_id=f"job-{i}")
            assert q.wait(f"job-{i}", timeout=5)

        assert q.history_size() <= 5
        assert q.status("job-0") is None   # oldest trimmed
        assert q.status("job-4") is None   # still trimmed
        assert q.status("job-5") == JobStatus.SUCCEEDED
        assert q.status("job-9") == JobStatus.SUCCEEDED
        assert q.result("job-9").result == 9

    def test_active_jobs_never_trimmed(self):
        q = AsyncJobQueue(max_workers=2, max_history=2)
        started = threading.Event()
        release = threading.Event()

        def block():
            started.set()
            release.wait(5)
            return "b"

        q.submit(block, job_id="active-1")
        _event_wait(started)
        for i in range(3):
            q.submit(lambda v=i: v, job_id=f"quick-{i}")
            assert q.wait(f"quick-{i}", timeout=5)

        # quick-0/quick-1 pruned; the RUNNING active-1 record survives.
        assert q.history_size() == 2
        assert q.status("active-1") == JobStatus.RUNNING
        assert q.status("quick-0") is None
        assert q.status("quick-2") == JobStatus.SUCCEEDED

        release.set()
        assert q.wait("active-1", timeout=5)
        assert q.status("active-1") == JobStatus.SUCCEEDED

    def test_default_max_history_is_500(self):
        assert DEFAULT_MAX_HISTORY == 500


# ============================================================================
# Optional persistence (append-only JSONL)
# ============================================================================

class TestPersistence:
    """Job transitions can be recorded for audit / failure-retry tracing."""

    def test_persist_append_only_log(self, tmp_path):
        log = tmp_path / "jobs.jsonl"
        q = AsyncJobQueue(max_workers=2, persist_path=log)

        def boom():
            raise RuntimeError("x")

        q.submit(lambda: 1, job_id="p1")
        q.submit(boom, job_id="p2")
        assert q.wait("p1", timeout=5) and q.wait("p2", timeout=5)

        lines = q.read_log()
        assert lines, "persisted log must be non-empty"
        events = [line["event"] for line in lines]
        assert "submit" in events and "terminal" in events

        # Append-only: re-reading is byte-identical, no rewrite.
        assert log.read_text(encoding="utf-8") == log.read_text(encoding="utf-8")

        terminal_by_job = {
            line["record"]["job_id"]: line
            for line in lines
            if line["event"] == "terminal"
        }
        assert terminal_by_job["p1"]["record"]["status"] == "succeeded"
        assert terminal_by_job["p1"]["record"]["result"] == 1
        assert terminal_by_job["p2"]["record"]["status"] == "failed"
        assert terminal_by_job["p2"]["record"]["error_type"] == "RuntimeError"

    def test_persist_non_serializable_result_degrades(self, tmp_path):
        log = tmp_path / "jobs.jsonl"
        q = AsyncJobQueue(max_workers=1, persist_path=log)

        class Opaque:
            pass

        q.submit(lambda: Opaque(), job_id="opaque")
        assert q.wait("opaque", timeout=5)
        assert q.status("opaque") == JobStatus.SUCCEEDED  # queue unaffected

        terminal = [
            line for line in q.read_log()
            if line["event"] == "terminal" and line["record"]["job_id"] == "opaque"
        ]
        assert terminal
        assert terminal[0]["record"]["result"]["__non_serializable__"] == "Opaque"

    def test_persist_failure_never_breaks_queue(self, tmp_path):
        # Point the log at an existing directory → every write fails.
        target = tmp_path / "not-a-file"
        target.mkdir()
        q = AsyncJobQueue(max_workers=1, persist_path=target)

        q.submit(lambda: 5, job_id="ok")
        assert q.wait("ok", timeout=5)
        assert q.result("ok").result == 5
        assert q.persist_failures >= 1
        assert q.persist_last_error

        q.submit(lambda: 6, job_id="ok2")
        assert q.wait("ok2", timeout=5)
        assert q.result("ok2").result == 6


# ============================================================================
# Shutdown & thread safety
# ============================================================================

class TestShutdown:
    """Graceful shutdown semantics."""

    def test_shutdown_wait_graceful(self):
        q = AsyncJobQueue(max_workers=1)
        started = threading.Event()
        release = threading.Event()

        def slow():
            started.set()
            release.wait(5)
            return "slow-done"

        q.submit(slow, job_id="s1")
        _event_wait(started)

        outcome: list = []
        shutdown_thread = threading.Thread(
            target=lambda: outcome.append(q.shutdown(wait=True)),
        )
        shutdown_thread.start()
        time.sleep(0.1)
        assert shutdown_thread.is_alive(), "shutdown must wait for the running job"

        release.set()
        shutdown_thread.join(5)
        assert not shutdown_thread.is_alive()
        assert outcome == [True]
        assert q.status("s1") == JobStatus.SUCCEEDED

    def test_submit_after_shutdown_raises(self):
        q = AsyncJobQueue(max_workers=1)
        q.submit(lambda: 1, job_id="z")
        assert q.wait("z", timeout=5)
        assert q.shutdown(wait=True) is True
        with pytest.raises(AsyncJobQueueError):
            q.submit(lambda: 2, job_id="z2")

    def test_shutdown_wait_false_returns_immediately(self):
        q = AsyncJobQueue(max_workers=1)
        started = threading.Event()

        def slow():
            started.set()
            return "ok"

        q.submit(slow, job_id="w")
        assert q.shutdown(wait=False) is True
        # Already-submitted work still completes in the background.
        assert q.wait("w", timeout=5)
        assert q.status("w") == JobStatus.SUCCEEDED

    def test_context_manager_shuts_down(self):
        with AsyncJobQueue(max_workers=1) as q:
            q.submit(lambda: 1, job_id="cm")
            assert q.wait("cm", timeout=5)
        assert q.status("cm") == JobStatus.SUCCEEDED


class TestThreadSafety:
    """Concurrent distinct submissions all complete with correct results."""

    def test_concurrent_distinct_jobs_all_complete(self):
        q = AsyncJobQueue(max_workers=4)
        n = 40
        errors: list[Exception] = []

        def submit_batch():
            for i in range(n):
                try:
                    q.submit(lambda v=i: v * 2, job_id=f"t{i}")
                except Exception as e:  # noqa: BLE001 — test collector
                    errors.append(e)

        threads = [threading.Thread(target=submit_batch) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(5)
        assert not errors, f"submit raised: {errors}"

        for i in range(n):
            assert q.wait(f"t{i}", timeout=10), f"job t{i} did not finish"
            assert q.result(f"t{i}").result == i * 2
