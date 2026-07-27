"""
User Service with SEEDED DEFECTS for Loop role validation.

WARNING: This file contains INTENTIONAL defects (SD-001 through SD-006)
designed to test whether Loop's AI roles can detect known issues.
Do NOT use this code in any production system.

Each defect is marked with a DEFECT-SD-XXX comment explaining the issue,
the expected detector role, and why it matters.
"""

from __future__ import annotations

from typing import Any


# ─────────────────────────────────────────────────────────────
# Simulated database interface — avoids external dependencies
# ─────────────────────────────────────────────────────────────
class FakeDB:
    """Fake database for demonstration purposes only."""

    def execute(self, query: str, params: list | None = None) -> list[dict]:
        """Simulate a database query."""
        return []

    def get_user(self, user_id: int) -> dict:
        """Simulate fetching a single user."""
        return {"id": user_id, "name": "test_user", "age": 30}


class OrderService:
    """Simulated order service — referenced by UserService to create
    a circular dependency (DEFECT-SD-006)."""

    def __init__(self, user_service: UserService | None = None):
        self.user_service = user_service

    def get_orders_for_user(self, user_id: int) -> list:
        return []


# ─────────────────────────────────────────────────────────────
# UserService — contains 6 seeded defects
# ─────────────────────────────────────────────────────────────
class UserService:
    """User service with deliberately inserted defects.

    Each defect is annotated with its ID, type, severity, and the
    expected detector role. See defect_registry.json for full details.
    """

    def __init__(self, db_connection: Any):
        self.db = db_connection

    # ── DEFECT-SD-001: SQL Injection (f-string query building) ──
    # Type: security    Severity: critical    Detector: security-engineer
    def search_users(self, keyword: str) -> list:
        """Search users by name keyword.

        DEFECT-SD-001: Uses f-string to build SQL query instead of
        parameterized queries. Attacker-supplied keyword can escape
        the LIKE clause and execute arbitrary SQL.

        Expected detection: security-engineer via SQL injection lint rule
        or code review pattern matching.
        """
        query = f"SELECT * FROM users WHERE name LIKE '%{keyword}%'"
        return self.db.execute(query)

    # ── DEFECT-SD-002: Missing input validation ──
    # Type: quality     Severity: high        Detector: quality-engineer
    def create_user(self, username: str, password: str, email: str):
        """Create a new user record.

        DEFECT-SD-002: No validation on any field:
        - username could be empty, contain SQL/HTML/script tags
        - email is not checked for format (no @, no domain)
        - password has no minimum length or complexity requirements
        - No trimming or normalization of inputs

        Expected detection: quality-engineer via input validation
        rules or static analysis of function signatures.
        """
        self.db.execute(
            "INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
            [username, password, email],
        )

    # ── DEFECT-SD-003: Password stored in plaintext ──
    # Type: security    Severity: critical    Detector: security-engineer
    def set_password(self, user_id: int, new_password: str):
        """Update a user's password.

        DEFECT-SD-003: Password is stored as-is without hashing.
        Any database compromise exposes all user passwords in plaintext.
        Should use bcrypt, argon2, or at minimum SHA-256 with salt.

        Expected detection: security-engineer via keyword scan for
        'password' combined with absence of hash/salt operations.
        """
        self.db.execute(
            "UPDATE users SET password = ? WHERE id = ?",
            [new_password, user_id],
        )

    # ── DEFECT-SD-004: Division by zero ──
    # Type: logic       Severity: medium      Detector: test-engineer
    def get_average_age(self, user_ids: list[int]) -> float:
        """Compute average age across given user ids.

        DEFECT-SD-004: If user_ids is empty, total/len triggers
        ZeroDivisionError. The function does not guard against
        empty input.

        Expected detection: test-engineer via boundary/edge case
        testing (empty list input) or static analysis.
        """
        total = 0
        for uid in user_ids:
            user = self.db.get_user(uid)
            total += user["age"]
        return total / len(user_ids)  # BUG: ZeroDivisionError on empty list

    # ── DEFECT-SD-005: N+1 query problem ──
    # Type: performance Severity: high        Detector: architect / reviewer
    def get_users_with_orders(self) -> list[dict]:
        """Get all users with their associated orders.

        DEFECT-SD-005: Executes a separate query for each user's orders
        (N+1 pattern). For N users, this makes N+1 database round-trips
        instead of a single JOIN query. At scale, this causes massive
        performance degradation.

        Expected detection: architect or independent-reviewer via
        code review identifying loop-contained queries.
        """
        users = self.db.execute("SELECT * FROM users")
        result: list[dict] = []
        for user in users:
            orders = self.db.execute(
                f"SELECT * FROM orders WHERE user_id = {user['id']}"
            )
            result.append({"user": user, "orders": orders})
        return result

    # ── DEFECT-SD-006: Circular dependency ──
    # Type: architecture Severity: medium     Detector: architect
    # NOTE: This is a module-level defect — the OrderService class
    # at the top of this file references UserService, and the
    # user_service module references order_service at import time.
    # The annotation below documents the architectural violation.
    def set_order_service(self, order_service: OrderService):
        """Inject order service reference.

        DEFECT-SD-006: UserService holds a direct reference to OrderService,
        while OrderService also references UserService — creating a
        circular module dependency. This tight coupling makes the two
        modules impossible to test or deploy independently, and can
        cause import-time deadlocks.

        Expected detection: architect via dependency graph analysis
        or import-linter tooling.
        """
        self._order_service = order_service
