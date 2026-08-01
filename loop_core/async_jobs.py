"""Async Job Queue — background execution with lease-based duplicate protection.

T-0090 D7 交付（AC-03）。StaffDeck 对标（backend/app/async_jobs.py：
ThreadPoolExecutor + 内存状态 queued→running→succeeded/failed + 历史裁剪），
租约语义参照 loop_core/dispatch_lease.py 的防重复派发思想。

Design
------
- **Background execution** — a configurable ``ThreadPoolExecutor`` runs each
  submitted callable on a worker thread; the queue itself never blocks the
  caller for the task duration.
- **State tracking** — every job carries a ``JobStatus``::

      [submit] ──► queued ──► running ──► succeeded
                                │  │   └──► failed      (task raised)
                                │  └──────► cancelled   (cooperative cancel)
                                └────► cancelled        (cancelled while queued)

- **Lease-based dedup** — ``submit`` for a ``job_id`` that already has an
  active (queued/running) record returns ``SubmitOutcome(accepted=False,
  reason="duplicate")`` instead of executing again.  The same dedup applies
  to auto-generated job ids (deterministic hash of callable identity +
  args), so concurrent identical submissions collapse to one execution.
  Terminal jobs may be re-submitted (slot released, like a released lease);
  the in-memory record is replaced while the append-only log keeps the
  full trace.
- **Cooperative cancel** — ``cancel(job_id)`` on a queued job marks it
  ``cancelled`` immediately (it never executes); on a running job it sets a
  ``cancel_requested`` flag that the task polls via
  ``cancel_requested(job_id)``.  When the task returns, a cancelled-flagged
  job is finalized as ``cancelled`` and its result is discarded.
- **Never breaks the queue** — a task exception is captured, the job is
  finalized as ``failed`` with the error recorded, and the worker (and the
  queue) keep serving.  The same discipline applies to the optional
  append-only JSONL persistence: a write failure is counted and logged,
  never raised into the caller.
- **History trimming** — completed records beyond ``max_history`` are pruned
  (oldest terminal first; active jobs are never trimmed).  Default 500.

Usage::

    queue = AsyncJobQueue(max_workers=4)
    out = queue.submit(slow_audit, job_id="audit-2026-08-01")
    if out.accepted:
        ...                                   # poll status/result later
    if queue.status("audit-2026-08-01") == JobStatus.RUNNING:
        queue.cancel("audit-2026-08-01")      # cooperative request

    record = queue.result("audit-2026-08-01") # full JobRecord once terminal
    queue.shutdown(wait=True)                 # graceful stop
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Defaults ────────────────────────────────────────────────────────────────
DEFAULT_MAX_WORKERS = 4       # worker thread count when not configured
DEFAULT_MAX_HISTORY = 500     # in-memory record cap (oldest terminal trimmed)
DEFAULT_JOB_LOG_PATH = ".ai/evidence/observability/jobs.jsonl"


# ============================================================================
# JobStatus
# ============================================================================

class JobStatus(str, Enum):
    """Lifecycle status of a queued job."""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


ACTIVE_STATES = frozenset({JobStatus.QUEUED, JobStatus.RUNNING})
TERMINAL_STATES = frozenset({JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED})


# ============================================================================
# Error type
# ============================================================================

class AsyncJobQueueError(RuntimeError):
    """Raised by queue operations that cannot proceed (e.g. after shutdown)."""


# ============================================================================
# Value objects
# ============================================================================

@dataclass(frozen=True)
class SubmitOutcome:
    """Result of a ``submit`` call — carries the lease decision.

    - ``accepted=True``   — this submission created the job (or re-created a
      terminal job's slot); the callable will be executed.
    - ``accepted=False``  — lease conflict: an active (queued/running) job
      with the same ``job_id`` already exists; the callable was NOT executed.
    """
    job_id: str
    accepted: bool
    reason: str  # "submitted" | "duplicate"
    status: JobStatus  # status of the existing/created record at submit time


@dataclass
class JobRecord:
    """In-memory state + result of one job.

    Instances are mutated in-place by the queue while holding the queue
    lock; callers should treat them as read-only snapshots.
    """
    job_id: str
    status: JobStatus
    submitted_at: float
    started_at: float | None = None
    finished_at: float | None = None
    result: Any = None
    error: str | None = None
    error_type: str | None = None
    cancel_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def duration(self) -> float | None:
        """Wall-clock seconds of execution, or *None* if never started."""
        if self.started_at is None or self.finished_at is None:
            return None
        return self.finished_at - self.started_at

    def to_dict(self) -> dict[str, Any]:
        """Deterministic serialization (results kept raw; sanitize at write)."""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "submitted_at": round(self.submitted_at, 3),
            "started_at": round(self.started_at, 3) if self.started_at is not None else None,
            "finished_at": round(self.finished_at, 3) if self.finished_at is not None else None,
            "result": self.result,
            "error": self.error,
            "error_type": self.error_type,
            "cancel_requested": self.cancel_requested,
        }


# Sentinel distinguishing "no result set" from "result is None".
_MISSING = object()


# ============================================================================
# AsyncJobQueue
# ============================================================================

class AsyncJobQueue:
    """Thread-pool backed async job queue with lease-based dedup.

    Thread safety: a single ``threading.Lock`` guards ``_jobs``/``_events``
    and the optional JSONL persistence; worker wrappers acquire it for state
    transitions only (task callables run unlocked, as required).
    """

    def __init__(
        self,
        max_workers: int = DEFAULT_MAX_WORKERS,
        max_history: int = DEFAULT_MAX_HISTORY,
        persist_path: str | Path | None = None,
        thread_name_prefix: str = "async-job",
    ) -> None:
        self.max_workers = max(1, int(max_workers))
        self.max_history = None if max_history is None else max(0, int(max_history))
        self._executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix=thread_name_prefix,
        )
        self._jobs: dict[str, JobRecord] = {}          # insertion-ordered (oldest first)
        self._events: dict[str, threading.Event] = {}  # per-job terminal event
        self._lock = threading.Lock()
        self._shutdown = False
        self._persist_path: Path | None = None
        if persist_path is not None:
            self._persist_path = Path(persist_path)
        # Persistence failure counters — observation must never break business.
        self.persist_failures = 0
        self.persist_last_error: str | None = None

    # ==================================================================
    # Submission
    # ==================================================================

    def submit(
        self,
        fn: Callable[..., Any],
        *args: Any,
        job_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> SubmitOutcome:
        """Submit ``fn(*args, **kwargs)`` for background execution.

        Lease semantics: when ``job_id`` already has an **active**
        (queued/running) record, the callable is NOT executed and
        ``SubmitOutcome(accepted=False, reason="duplicate")`` is returned —
        duplicate dispatch prevented.  Terminal records may be re-submitted
        (their slot is released, mirroring a released dispatch lease).

        When ``job_id`` is omitted it is derived deterministically from the
        callable identity plus the arguments, so concurrent submissions of
        identical work also dedupe.

        Returns:
            A ``SubmitOutcome``; check ``.accepted`` before assuming the
            callable will run.
        """
        if job_id is None:
            job_id = self._auto_job_id(fn, args, kwargs)
        with self._lock:
            if self._shutdown:
                raise AsyncJobQueueError(f"queue is shut down; cannot submit {job_id!r}")
            existing = self._jobs.get(job_id)
            if existing is not None and existing.status in ACTIVE_STATES:
                return SubmitOutcome(
                    job_id=job_id,
                    accepted=False,
                    reason="duplicate",
                    status=existing.status,
                )
            record = JobRecord(
                job_id=job_id,
                status=JobStatus.QUEUED,
                submitted_at=time.time(),
                metadata=dict(metadata) if metadata is not None else {},
            )
            # Re-insertion moves the record to the end (fresh history slot).
            self._jobs.pop(job_id, None)
            self._jobs[job_id] = record
            self._events[job_id] = threading.Event()
            self._persist(record, phase="submit")
            self._executor.submit(self._run, job_id, fn, args, kwargs)
        return SubmitOutcome(
            job_id=job_id,
            accepted=True,
            reason="submitted",
            status=JobStatus.QUEUED,
        )

    # ==================================================================
    # Queries
    # ==================================================================

    def status(self, job_id: str) -> JobStatus | None:
        """Current ``JobStatus`` of a job, or *None* if unknown/trimmed."""
        with self._lock:
            record = self._jobs.get(job_id)
            return record.status if record is not None else None

    def result(self, job_id: str) -> JobRecord | None:
        """Full ``JobRecord`` of a job (status/result/error), or *None*."""
        with self._lock:
            record = self._jobs.get(job_id)
            # Return a shallow copy so callers cannot corrupt queue state.
            return record if record is None else JobRecord(**vars(record))

    def cancel_requested(self, job_id: str) -> bool:
        """Cooperative-cancel probe for tasks running inside the queue."""
        with self._lock:
            record = self._jobs.get(job_id)
            return bool(record is not None and record.cancel_requested)

    def wait(self, job_id: str, timeout: float | None = None) -> bool:
        """Block until the job reaches a terminal state.

        Returns *True* when the job is terminal (or unknown) within
        ``timeout`` seconds, *False* on timeout.  ``timeout=None`` waits
        indefinitely.
        """
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return True  # unknown/trimmed — nothing left to wait for
            if record.status in TERMINAL_STATES:
                return True
            event = self._events.get(job_id)
        if event is None:
            return True
        event.wait(timeout)
        with self._lock:
            record = self._jobs.get(job_id)
            return record is not None and record.status in TERMINAL_STATES

    def cancel(self, job_id: str) -> bool:
        """Request cancellation of a job (cooperative).

        - Queued job  — finalized as ``cancelled`` immediately; it never runs.
        - Running job — ``cancel_requested`` flag is set; the task polls it
          via ``cancel_requested(job_id)`` and returns; the job is then
          finalized as ``cancelled`` (result discarded).
        - Terminal/unknown job — no-op.

        Returns *True* when a cancel request was registered.
        """
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return False
            if record.status in TERMINAL_STATES:
                return False
            record.cancel_requested = True
            if record.status == JobStatus.QUEUED:
                self._finalize(record, JobStatus.CANCELLED)
            return True

    def queued_count(self) -> int:
        with self._lock:
            return sum(1 for r in self._jobs.values() if r.status == JobStatus.QUEUED)

    def running_count(self) -> int:
        with self._lock:
            return sum(1 for r in self._jobs.values() if r.status == JobStatus.RUNNING)

    def active_count(self) -> int:
        """Jobs still queued or running (lease-held job ids)."""
        with self._lock:
            return sum(1 for r in self._jobs.values() if r.status in ACTIVE_STATES)

    def history_size(self) -> int:
        """Number of in-memory records (before trimming)."""
        with self._lock:
            return len(self._jobs)

    def jobs(self) -> list[JobRecord]:
        """Snapshot of all in-memory records, oldest submission first."""
        with self._lock:
            return [JobRecord(**vars(r)) for r in self._jobs.values()]

    def snapshot(self) -> list[dict[str, Any]]:
        """Serializable snapshot of all in-memory records."""
        return [r.to_dict() for r in self.jobs()]

    # ==================================================================
    # Shutdown
    # ==================================================================

    def shutdown(self, wait: bool = True, timeout: float | None = None) -> bool:
        """Graceful shutdown.

        - Stops accepting new submissions (subsequent ``submit`` raises
          ``AsyncJobQueueError``).
        - With ``wait=True``, blocks until every queued/running job reaches
          a terminal state (bounded by ``timeout`` seconds) and returns
          *True*; returns *False* if the deadline expired first.
        - With ``wait=False``, returns immediately; already-submitted jobs
          keep running to completion in the background.

        Idempotent — subsequent calls return immediately.
        """
        with self._lock:
            if self._shutdown:
                return True
            self._shutdown = True
            active_ids = [jid for jid, r in self._jobs.items() if r.status in ACTIVE_STATES]
        self._executor.shutdown(wait=False)
        if not wait:
            return True
        deadline = None if timeout is None else time.monotonic() + timeout
        for job_id in active_ids:
            remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
            if not self.wait(job_id, timeout=remaining):
                return False
        return True

    def __enter__(self) -> AsyncJobQueue:
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.shutdown(wait=True)

    # ==================================================================
    # Worker wrapper — the queue never dies with a task
    # ==================================================================

    def _run(self, job_id: str, fn: Callable[..., Any], args: tuple, kwargs: dict) -> None:
        """Execute one job; every failure is captured into the record."""
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return
            if record.status == JobStatus.CANCELLED or record.cancel_requested:
                # Cancelled while queued (or between submit and start).
                self._finalize(record, JobStatus.CANCELLED)
                return
            record.status = JobStatus.RUNNING
            record.started_at = time.time()
            self._persist(record, phase="start")
        try:
            result = fn(*args, **kwargs)
        except BaseException as e:  # noqa: BLE001 — background worker must survive
            error = f"{type(e).__name__}: {e}"
            with self._lock:
                record = self._jobs.get(job_id)
                if record is None or record.status != JobStatus.RUNNING:
                    return
                if record.cancel_requested:
                    self._finalize(record, JobStatus.CANCELLED)
                else:
                    record.error = error
                    record.error_type = type(e).__name__
                    self._finalize(record, JobStatus.FAILED)
            logger.warning("async job %s failed (queue continues): %s", job_id, error)
            return
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None or record.status != JobStatus.RUNNING:
                return
            if record.cancel_requested:
                self._finalize(record, JobStatus.CANCELLED)
            else:
                record.result = result
                self._finalize(record, JobStatus.SUCCEEDED)

    def _finalize(
        self,
        record: JobRecord,
        status: JobStatus,
        result: Any = _MISSING,
    ) -> None:
        """Transition to a terminal state.  Caller must hold ``self._lock``."""
        record.status = status
        record.finished_at = time.time()
        if status == JobStatus.SUCCEEDED and result is not _MISSING:
            record.result = result
        event = self._events.get(record.job_id)
        if event is not None:
            event.set()
        self._persist(record, phase="terminal")
        self._trim_history()

    def _trim_history(self) -> None:
        """Prune oldest terminal records beyond ``max_history``.

        Active (queued/running) jobs are never trimmed.  Caller must hold
        ``self._lock``.
        """
        if self.max_history is None:
            return
        while len(self._jobs) > self.max_history:
            trimmed = next(
                (jid for jid, r in self._jobs.items() if r.status in TERMINAL_STATES),
                None,
            )
            if trimmed is None:
                break  # everything left is active — never trim active jobs
            self._jobs.pop(trimmed, None)
            self._events.pop(trimmed, None)

    # ==================================================================
    # Deterministic job ids
    # ==================================================================

    @staticmethod
    def _auto_job_id(fn: Callable[..., Any], args: tuple, kwargs: dict) -> str:
        """Stable job id from callable identity + arguments.

        Same callable with the same arguments always maps to the same id, so
        concurrent duplicate submissions collapse onto one job (lease dedup).
        """
        payload = {
            "module": getattr(fn, "__module__", None),
            "qualname": getattr(fn, "__qualname__", None),
            "args": list(args),
            "kwargs": kwargs,
        }
        raw = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return f"job-{digest}"

    # ==================================================================
    # Optional append-only persistence (never raises)
    # ==================================================================

    def _persist(self, record: JobRecord, phase: str) -> None:
        """Append one JSONL line for a job transition.

        Observation discipline (mirrors loop_core.observability): a failing
        write is counted in ``persist_failures`` / ``persist_last_error``
        and logged — the queue and its jobs never see the failure.
        """
        if self._persist_path is None:
            return
        try:
            line = json.dumps(
                {
                    "event": phase,
                    "record": self._sanitize_record(record),
                    "timestamp": time.time(),
                },
                ensure_ascii=False,
            ) + "\n"
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persist_path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:  # noqa: BLE001 — persistence never breaks the queue
            self.persist_failures += 1
            self.persist_last_error = f"{type(e).__name__}: {e}"
            logger.warning(
                "async job persistence write failed (queue continues): %s",
                self.persist_last_error,
            )

    @staticmethod
    def _sanitize_record(record: JobRecord) -> dict[str, Any]:
        """Make a record JSON-serializable (non-serializable results degrade
        to a typed marker instead of failing the append)."""
        data = record.to_dict()
        try:
            json.dumps(data)
        except (TypeError, ValueError):
            value = data["result"]
            data["result"] = {
                "__non_serializable__": type(value).__name__,
                "repr": repr(value)[:500],
            }
        return data

    # ==================================================================
    # Log replay (audit / failure-retry traceability)
    # ==================================================================

    def read_log(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Read back the persisted append-only log (JSONL).

        Returns the full history (or the last ``limit`` lines when given);
        corrupt trailing lines are skipped so a readable prefix survives.
        """
        if self._persist_path is None or not self._persist_path.exists():
            return []
        lines: list[dict[str, Any]] = []
        try:
            raw = self._persist_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        for line in raw:
            if not line.strip():
                continue
            try:
                lines.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # corrupt line — keep the readable prefix
        return lines if limit is None else lines[-limit:]
