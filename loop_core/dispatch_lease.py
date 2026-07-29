"""Dispatch Lease — lifecycle management for role dispatch leases.

Prevents duplicate dispatch for the same (task_id, role_id) combination by
issuing time-bound leases.  Leases auto-expire after a configurable timeout,
and can be explicitly released when a sub-agent session completes.

Design
------
- **Grant**    — acquire a lease for an (execution_id, task_id, role_id) triple
- **Active**   — check whether a lease is still valid (not expired / released)
- **Release**  — explicitly return a lease so the slot can be re-used
- **Expire**   — leases time out automatically; ``is_active()`` returns False
                 once the expiry wall-clock passes
- **Conflict** — attempting to grant a lease for a (task_id, role_id) that
                 already has an active lease returns a lease with
                 ``LeaseStatus.CONFLICT``

Usage::

    lease = DispatchLease.grant(execution_id="exec-1", task_id="task-a", role_id="dev")
    if lease.status == LeaseStatus.CONFLICT:
        ...  # duplicate dispatch prevented

    if lease.is_active():
        ...  # proceed with dispatch

    lease.release()
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar


# ============================================================================
# LeaseStatus
# ============================================================================

class LeaseStatus(str, Enum):
    """Lifecycle status of a dispatch lease."""
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    RELEASED = "RELEASED"
    CONFLICT = "CONFLICT"


# ============================================================================
# Error type
# ============================================================================

class DispatchLeaseError(RuntimeError):
    """Raised by lease operations that cannot proceed (fail-closed)."""


# ============================================================================
# DispatchLease
# ============================================================================

@dataclass
class DispatchLease:
    """A time-bound lease that prevents duplicate dispatch.

    Each lease is keyed by ``(task_id, role_id)``.  Only one **active** lease
    may exist per key at any moment.  The class-level ``_active_leases``
    registry is the shared source of truth (in-process only; cross-process
    coordination requires a persistent store).

    **Lifecycle state machine**::

        [grant] ──► ACTIVE ──► [timeout] ──► EXPIRED
                       │
                       └────── [release] ──► RELEASED

        [grant while active] ──► CONFLICT  (no mutate)

    Instances should be treated as mutable value objects — their ``status``
    field is updated in-place by ``is_active()`` and ``release()``.
    """

    execution_id: str
    task_id: str
    role_id: str
    expiry: float
    status: LeaseStatus = LeaseStatus.ACTIVE
    granted_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    # ── Class-level lease registry ─────────────────────────────────────
    _active_leases: ClassVar[dict[str, "DispatchLease"]] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()

    # ==================================================================
    # Class methods — lease lifecycle
    # ==================================================================

    @classmethod
    def grant(
        cls,
        execution_id: str,
        task_id: str,
        role_id: str,
        *,
        timeout_seconds: int = 300,
        metadata: dict[str, Any] | None = None,
    ) -> "DispatchLease":
        """Grant a new dispatch lease.

        If an active lease already exists for this ``(task_id, role_id)``
        combination the returned lease carries ``LeaseStatus.CONFLICT``
        instead of ``ACTIVE``, preventing duplicate dispatch.

        Args:
            execution_id:
                The execution that owns this lease.
            task_id:
                The task being dispatched.
            role_id:
                The role (e.g. ``"developer"``, ``"reviewer"``).
            timeout_seconds:
                How long the lease remains valid before auto-expiry.
            metadata:
                Optional opaque metadata stored on the lease.

        Returns:
            A ``DispatchLease``.  Always check ``.status`` before proceeding:
            - ``ACTIVE``   — lease granted, dispatch may proceed
            - ``CONFLICT`` — duplicate dispatch prevented
        """
        cls._cleanup_expired()
        key = cls._lease_key(task_id, role_id)

        with cls._lock:
            existing = cls._active_leases.get(key)
            if existing is not None and existing.is_active():
                return cls(
                    execution_id=execution_id,
                    task_id=task_id,
                    role_id=role_id,
                    expiry=existing.expiry,
                    status=LeaseStatus.CONFLICT,
                    metadata={
                        "reason": "Duplicate dispatch prevented — existing active lease",
                        "conflict_with": {
                            "execution_id": existing.execution_id,
                            "granted_at": existing.granted_at,
                            "expiry": existing.expiry,
                        },
                        **(metadata or {}),
                    },
                )

            lease = cls(
                execution_id=execution_id,
                task_id=task_id,
                role_id=role_id,
                expiry=time.time() + timeout_seconds,
                status=LeaseStatus.ACTIVE,
                metadata=metadata or {},
            )
            cls._active_leases[key] = lease
            return lease

    @classmethod
    def lookup(cls, task_id: str, role_id: str) -> "DispatchLease | None":
        """Return the current lease for a task/role pair, or *None*."""
        cls._cleanup_expired()
        with cls._lock:
            return cls._active_leases.get(cls._lease_key(task_id, role_id))

    @classmethod
    def active_count(cls) -> int:
        """Number of currently active leases in the registry."""
        cls._cleanup_expired()
        with cls._lock:
            return len(cls._active_leases)

    @classmethod
    def release_all(cls) -> int:
        """Release every active lease.  Returns the count released."""
        with cls._lock:
            count = len(cls._active_leases)
            cls._active_leases.clear()
            return count

    @classmethod
    def active_snapshot(cls) -> list["DispatchLease"]:
        """Return a snapshot of all currently active leases."""
        cls._cleanup_expired()
        with cls._lock:
            return list(cls._active_leases.values())

    # ==================================================================
    # Instance methods
    # ==================================================================

    def is_active(self) -> bool:
        """Check whether this lease is still valid.

        Returns *False* when the lease has expired, been released, or
        represents a conflict.  Calling this method on an expired-but-
        not-yet-cleaned lease triggers an in-place expiry.
        """
        if self.status in (LeaseStatus.EXPIRED, LeaseStatus.RELEASED, LeaseStatus.CONFLICT):
            return False
        if time.time() >= self.expiry:
            self._expire_in_place()
            return False
        return True

    def release(self) -> None:
        """Explicitly release this lease.

        Removes it from the class-level registry so the (task_id, role_id)
        slot can be claimed by a new dispatch.
        """
        if self.status == LeaseStatus.RELEASED:
            return
        self.status = LeaseStatus.RELEASED
        self.expiry = 0.0
        key = self._lease_key(self.task_id, self.role_id)
        with self._lock:
            if self._active_leases.get(key) is self:
                del self._active_leases[key]

    def expire(self) -> None:
        """Force this lease to expire immediately."""
        self._expire_in_place()

    def time_remaining(self) -> float:
        """Seconds until expiry (negative if already expired)."""
        return self.expiry - time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "role_id": self.role_id,
            "expiry": self.expiry,
            "granted_at": self.granted_at,
            "status": self.status.value,
            "time_remaining": self.time_remaining(),
        }

    # ==================================================================
    # Internal
    # ==================================================================

    def _expire_in_place(self) -> None:
        """Mark expired and remove from registry."""
        self.status = LeaseStatus.EXPIRED
        key = self._lease_key(self.task_id, self.role_id)
        with self._lock:
            if self._active_leases.get(key) is self:
                del self._active_leases[key]

    @staticmethod
    def _lease_key(task_id: str, role_id: str) -> str:
        """Stable sortable key for a (task_id, role_id) pair."""
        return f"{task_id}::{role_id}"

    @classmethod
    def _cleanup_expired(cls) -> None:
        """Purge all expired or released leases from the registry."""
        now = time.time()
        with cls._lock:
            expired_keys = [
                key
                for key, lease in cls._active_leases.items()
                if lease.status in (LeaseStatus.EXPIRED, LeaseStatus.RELEASED)
                or now >= lease.expiry
            ]
            for key in expired_keys:
                lease = cls._active_leases.pop(key, None)
                if lease is not None and lease.status not in (LeaseStatus.RELEASED, LeaseStatus.EXPIRED):
                    lease.status = LeaseStatus.EXPIRED
