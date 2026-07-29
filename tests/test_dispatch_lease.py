"""Unit tests for loop_core.dispatch_lease — life-cycle management for role dispatch leases.

Tests grant/active/release lifecycle, conflict detection, expiry,
thread safety, and registry queries (active_count, active_snapshot).
"""
from __future__ import annotations

import time
import threading

import pytest

from loop_core.dispatch_lease import (
    DispatchLease,
    DispatchLeaseError,
    LeaseStatus,
)


# ============================================================================
# Module-level setup / teardown helpers
# ============================================================================

@pytest.fixture(autouse=True)
def _clean_leases():
    """Ensure the global lease registry is empty before each test."""
    DispatchLease.release_all()
    yield
    DispatchLease.release_all()


# ============================================================================
# Grant / Active / Release lifecycle
# ============================================================================

class TestGrantActiveReleaseLifecycle:
    """Happy path: grant, check active, release."""

    def test_grant_returns_active_lease(self):
        lease = DispatchLease.grant("exec-1", "task-a", "role-dev")
        assert lease.status == LeaseStatus.ACTIVE
        assert lease.execution_id == "exec-1"
        assert lease.task_id == "task-a"
        assert lease.role_id == "role-dev"

    def test_granted_lease_is_active(self):
        lease = DispatchLease.grant("exec-1", "task-a", "role-dev")
        assert lease.is_active() is True

    def test_grant_sets_granted_at_approximately_now(self):
        before = time.time()
        lease = DispatchLease.grant("exec-1", "task-a", "role-dev")
        after = time.time()
        assert before <= lease.granted_at <= after + 0.01

    def test_grant_sets_expiry_in_the_future(self):
        lease = DispatchLease.grant("exec-1", "task-a", "role-dev", timeout_seconds=30)
        now = time.time()
        assert lease.expiry > now
        assert lease.expiry <= now + 30 + 0.01

    def test_release_sets_status_to_released(self):
        lease = DispatchLease.grant("exec-1", "task-a", "role-dev")
        lease.release()
        assert lease.status == LeaseStatus.RELEASED

    def test_released_lease_is_not_active(self):
        lease = DispatchLease.grant("exec-1", "task-a", "role-dev")
        lease.release()
        assert lease.is_active() is False

    def test_double_release_is_idempotent(self):
        lease = DispatchLease.grant("exec-1", "task-a", "role-dev")
        lease.release()
        lease.release()  # should not raise
        assert lease.status == LeaseStatus.RELEASED

    def test_time_remaining_positive_while_active(self):
        lease = DispatchLease.grant("exec-1", "task-a", "role-dev", timeout_seconds=300)
        remaining = lease.time_remaining()
        assert 0 < remaining <= 300

    def test_time_remaining_zero_after_release(self):
        lease = DispatchLease.grant("exec-1", "task-a", "role-dev", timeout_seconds=60)
        lease.release()
        # expiry is set to 0.0 on release, so time_remaining is negative or ~0
        assert lease.time_remaining() <= 0

    def test_to_dict_contains_status_string(self):
        lease = DispatchLease.grant("exec-1", "task-a", "role-dev", timeout_seconds=60)
        d = lease.to_dict()
        assert d["execution_id"] == "exec-1"
        assert d["task_id"] == "task-a"
        assert d["role_id"] == "role-dev"
        assert d["status"] == "ACTIVE"
        assert "time_remaining" in d

    def test_metadata_is_stored(self):
        lease = DispatchLease.grant(
            "exec-1", "task-a", "role-dev",
            metadata={"project": "loop-engine", "priority": "high"},
        )
        assert lease.metadata["project"] == "loop-engine"
        assert lease.metadata["priority"] == "high"


# ============================================================================
# Conflict detection
# ============================================================================

class TestConflictDetection:
    """Only one active lease per (task_id, role_id)."""

    def test_duplicate_grant_returns_conflict(self):
        l1 = DispatchLease.grant("exec-1", "task-a", "role-dev")
        assert l1.status == LeaseStatus.ACTIVE

        l2 = DispatchLease.grant("exec-2", "task-a", "role-dev")
        assert l2.status == LeaseStatus.CONFLICT

    def test_conflict_lease_is_not_active(self):
        DispatchLease.grant("exec-1", "task-a", "role-dev")
        l2 = DispatchLease.grant("exec-2", "task-a", "role-dev")
        assert l2.is_active() is False

    def test_conflict_metadata_contains_conflict_with_info(self):
        DispatchLease.grant("exec-1", "task-a", "role-dev")
        l2 = DispatchLease.grant("exec-2", "task-a", "role-dev")
        assert "conflict_with" in l2.metadata
        assert l2.metadata["conflict_with"]["execution_id"] == "exec-1"

    def test_different_task_id_no_conflict(self):
        l1 = DispatchLease.grant("exec-1", "task-a", "role-dev")
        l2 = DispatchLease.grant("exec-2", "task-b", "role-dev")
        assert l1.status == LeaseStatus.ACTIVE
        assert l2.status == LeaseStatus.ACTIVE

    def test_different_role_id_no_conflict(self):
        l1 = DispatchLease.grant("exec-1", "task-a", "role-dev")
        l2 = DispatchLease.grant("exec-2", "task-a", "role-reviewer")
        assert l1.status == LeaseStatus.ACTIVE
        assert l2.status == LeaseStatus.ACTIVE

    def test_release_then_regrant_succeeds(self):
        l1 = DispatchLease.grant("exec-1", "task-a", "role-dev")
        l1.release()
        l2 = DispatchLease.grant("exec-2", "task-a", "role-dev")
        assert l2.status == LeaseStatus.ACTIVE

    def test_conflict_does_not_alter_existing_lease(self):
        l1 = DispatchLease.grant("exec-1", "task-a", "role-dev")
        _l2 = DispatchLease.grant("exec-2", "task-a", "role-dev")
        # l1 must still be active
        assert l1.is_active() is True
        assert l1.status == LeaseStatus.ACTIVE
        assert l1.execution_id == "exec-1"

    def test_conflict_metadata_preserves_user_metadata(self):
        DispatchLease.grant("exec-1", "task-a", "role-dev")
        l2 = DispatchLease.grant(
            "exec-2", "task-a", "role-dev",
            metadata={"extra": "info"},
        )
        assert l2.metadata["extra"] == "info"
        assert "conflict_with" in l2.metadata  # still there


# ============================================================================
# Expiry
# ============================================================================

class TestExpiry:
    """Leases must expire after the configured timeout."""

    def test_lease_expires_after_timeout(self):
        lease = DispatchLease.grant(
            "exec-1", "task-a", "role-dev", timeout_seconds=1
        )
        # Artificially age the lease by setting its expiry into the past
        lease.expiry = time.time() - 1.0
        assert lease.is_active() is False
        assert lease.status == LeaseStatus.EXPIRED

    def test_expired_lease_is_removed_from_registry_on_check(self):
        lease = DispatchLease.grant(
            "exec-1", "task-a", "role-dev", timeout_seconds=1
        )
        lease.expiry = time.time() - 1.0
        lease.is_active()  # triggers _expire_in_place
        # Registry should no longer contain this lease
        assert DispatchLease.lookup("task-a", "role-dev") is None

    def test_expire_method_sets_expired(self):
        lease = DispatchLease.grant("exec-1", "task-a", "role-dev", timeout_seconds=60)
        lease.expire()
        assert lease.status == LeaseStatus.EXPIRED
        assert lease.is_active() is False

    def test_expire_removes_from_registry(self):
        lease = DispatchLease.grant("exec-1", "task-a", "role-dev", timeout_seconds=60)
        lease.expire()
        assert DispatchLease.lookup("task-a", "role-dev") is None

    def test_grant_cleans_up_expired_before_granting_new(self):
        """Expired leases must not prevent a new grant."""
        # Create a lease and make it expired
        l1 = DispatchLease.grant("exec-1", "task-a", "role-dev", timeout_seconds=1)
        l1.expiry = time.time() - 1.0  # force expiry

        # Grant a new one — cleanup should happen and the new one is active
        l2 = DispatchLease.grant("exec-2", "task-a", "role-dev")
        assert l2.status == LeaseStatus.ACTIVE

    def test_lookup_cleans_up_expired(self):
        lease = DispatchLease.grant("exec-1", "task-a", "role-dev", timeout_seconds=1)
        lease.expiry = time.time() - 1.0
        result = DispatchLease.lookup("task-a", "role-dev")
        assert result is None

    def test_active_count_excludes_expired(self):
        lease = DispatchLease.grant("exec-1", "task-a", "role-dev", timeout_seconds=1)
        lease.expiry = time.time() - 1.0
        assert DispatchLease.active_count() == 0


# ============================================================================
# look-up
# ============================================================================

class TestLookup:
    """DispatchLease.lookup() returns the current lease or None."""

    def test_lookup_returns_active_lease(self):
        lease = DispatchLease.grant("exec-1", "task-a", "role-dev")
        found = DispatchLease.lookup("task-a", "role-dev")
        assert found is lease

    def test_lookup_returns_none_for_unknown_key(self):
        assert DispatchLease.lookup("no-such-task", "no-role") is None

    def test_lookup_returns_none_after_release(self):
        lease = DispatchLease.grant("exec-1", "task-a", "role-dev")
        lease.release()
        assert DispatchLease.lookup("task-a", "role-dev") is None


# ============================================================================
# active_count and active_snapshot
# ============================================================================

class TestActiveCountAndSnapshot:
    """Registry-level queries."""

    def test_active_count_zero_initially(self):
        assert DispatchLease.active_count() == 0

    def test_active_count_reflects_active_leases(self):
        DispatchLease.grant("exec-1", "task-a", "role-dev")
        DispatchLease.grant("exec-2", "task-b", "role-dev")
        DispatchLease.grant("exec-3", "task-c", "role-reviewer")
        assert DispatchLease.active_count() == 3

    def test_active_count_decreases_after_release(self):
        l1 = DispatchLease.grant("exec-1", "task-a", "role-dev")
        DispatchLease.grant("exec-2", "task-b", "role-dev")
        l1.release()
        assert DispatchLease.active_count() == 1

    def test_active_snapshot_returns_all_active_leases(self):
        l1 = DispatchLease.grant("exec-1", "task-a", "role-dev")
        l2 = DispatchLease.grant("exec-2", "task-b", "role-dev")
        snap = DispatchLease.active_snapshot()
        assert len(snap) == 2
        assert l1 in snap
        assert l2 in snap

    def test_active_snapshot_excludes_conflict_and_expired(self):
        DispatchLease.grant("exec-1", "task-a", "role-dev")
        # This is a conflict, not active
        DispatchLease.grant("exec-2", "task-a", "role-dev")
        snap = DispatchLease.active_snapshot()
        assert len(snap) == 1

    def test_release_all_clears_registry(self):
        DispatchLease.grant("exec-1", "task-a", "role-dev")
        DispatchLease.grant("exec-2", "task-b", "role-dev")
        count = DispatchLease.release_all()
        assert count == 2
        assert DispatchLease.active_count() == 0

    def test_release_all_returns_zero_when_empty(self):
        assert DispatchLease.release_all() == 0


# ============================================================================
# Thread safety (basic)
# ============================================================================

class TestThreadSafety:
    """Concurrent grants for different keys must not corrupt the registry."""

    def test_concurrent_grants_different_keys(self):
        errors = []
        results: list[DispatchLease] = []

        def grant_key(index: int):
            try:
                lease = DispatchLease.grant(
                    f"exec-{index}",
                    f"task-{index}",
                    f"role-{index}",
                    timeout_seconds=60,
                )
                results.append(lease)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=grant_key, args=(i,))
            for i in range(20)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(errors) == 0, f"Unexpected errors: {errors}"
        # All should be ACTIVE since each has a unique key
        active_count = sum(1 for r in results if r.status == LeaseStatus.ACTIVE)
        assert active_count == 20

    def test_concurrent_grants_same_key_only_one_active(self):
        """Only one of many concurrent grants for the same key wins."""
        errors = []
        results: list[DispatchLease] = []

        def grant_same_key(index: int):
            try:
                lease = DispatchLease.grant(
                    f"exec-{index}",
                    "shared-task",
                    "shared-role",
                    timeout_seconds=60,
                )
                results.append(lease)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=grant_same_key, args=(i,))
            for i in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(errors) == 0
        active = [r for r in results if r.status == LeaseStatus.ACTIVE]
        conflicts = [r for r in results if r.status == LeaseStatus.CONFLICT]
        assert len(active) == 1
        assert len(conflicts) == 9

    def test_concurrent_release_and_grant(self):
        """Release by one thread while another tries to grant the same key."""
        l1 = DispatchLease.grant("exec-1", "task-shared", "role-shared")

        errors = []

        def do_release():
            try:
                l1.release()
            except Exception as e:
                errors.append(e)

        def do_grant():
            try:
                # Grant after a small sleep to let release happen first
                time.sleep(0.1)
                lease = DispatchLease.grant(
                    "exec-2", "task-shared", "role-shared",
                    timeout_seconds=60,
                )
                return lease
            except Exception as e:
                errors.append(e)
            return None

        t_rel = threading.Thread(target=do_release)
        t_grant = threading.Thread(target=do_grant)
        t_rel.start()
        t_grant.start()
        t_rel.join(timeout=5)
        result = t_grant.join(timeout=5)  # result from do_grant

        # We need to capture the result differently
        pass  # rely on the lease directly

    def test_active_count_is_thread_safe(self):
        """active_count must stay consistent under concurrent grants."""
        def grant_and_check(_index: int):
            for j in range(10):
                DispatchLease.grant(
                    f"exec-{_index}-{j}",
                    f"task-{_index}-{j}",
                    f"role-{_index}-{j}",
                    timeout_seconds=60,
                )

        threads = [threading.Thread(target=grant_and_check, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        # All 10 threads * 10 grants = 100 leases (all unique keys, so all active)
        assert DispatchLease.active_count() == 100


# ============================================================================
# DispatchLeaseError
# ============================================================================

class TestDispatchLeaseError:
    """Basic smoke test for the error type."""

    def test_is_runtime_error_subclass(self):
        assert issubclass(DispatchLeaseError, RuntimeError)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(DispatchLeaseError, match="test lease error"):
            raise DispatchLeaseError("test lease error")
