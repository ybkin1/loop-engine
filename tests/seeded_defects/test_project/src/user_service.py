"""
User Service — Implementation with SEEDED DEFECTS for Loop validation.

WARNING: This file contains INTENTIONAL defects for testing the Loop review system.
Do NOT use this code in any real project.
"""
import os
import sqlite3
import hashlib

# ── SEEDED DEFECT #1: Hardcoded API key (violates FR-SEC-03) ──
EXTERNAL_API_KEY = "sk-abc123def456ghi789jkl012mno345pqr678stu901vwx234"

# ── SEEDED DEFECT #2: SQL injection in login (violates FR-SEC-02) ──
def login(username: str, password: str) -> dict | None:
    """Authenticate a user. SEEDED DEFECT: SQL injection via string concatenation."""
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    # VULNERABLE: direct string formatting, no parameterization
    query = f"SELECT id, username, role FROM users WHERE username = '{username}' AND password_hash = '{password_hash}'"
    cursor.execute(query)
    row = cursor.fetchone()
    conn.close()

    if row:
        return {"id": row[0], "username": row[1], "role": row[2]}
    return None


# ── SEEDED DEFECT #3: Missing input validation (violates FR-SEC-01) ──
def get_user_by_id(user_id: str) -> dict | None:
    """Get a user by ID. No input validation on user_id."""
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # No validation that user_id is actually an integer
    cursor.execute("SELECT id, username, email FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "username": row[1], "email": row[2]}
    return None


def list_all_users(admin_token: str) -> list[dict]:
    """List all users. Admin only."""
    if admin_token != os.environ.get("ADMIN_TOKEN"):
        raise PermissionError("Unauthorized")
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, role FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "username": r[1], "email": r[2], "role": r[3]} for r in rows]
