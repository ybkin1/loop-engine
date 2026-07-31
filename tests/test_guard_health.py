"""T-0083 AC-05: guard death tests for the Guard Health Check subsystem.

Proves the battery genuinely detects guard death:
- a broken regex (the T-0082 corruption class: stripped backslashes) makes a
  negative-control fixture that MUST block suddenly pass — the fixture catches it;
- negative controls (secret write, redirect write) are blocked by the live hooks;
- positive control (clean content) passes — guards do not over-block;
- summary semantics: any BROKEN or DORMANT guard => overall FAIL.
"""
import io
import json
import re
import subprocess
import sys
from pathlib import Path

from loop_core.guard_health import GuardHealth, GuardHealthResult

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / "hooks" / "scripts"

# Fixtures mirror loop_core.guard_health.GuardHealth.battery()
FIXTURE_REDIRECT_WRITE = {
    "tool_name": "Bash",
    "tool_input": {"command": 'echo "evil" > tests/tmp_evil.txt'},
    "cwd": str(ROOT),
}
FIXTURE_SECRET_WRITE = {
    "tool_name": "Write",
    "tool_input": {
        "file_path": "tests/tmp_secret_test.py",
        "content": 'password = "hunter2secret123"',
    },
    "cwd": str(ROOT),
}
FIXTURE_CLEAN_WRITE = {
    "tool_name": "Write",
    "tool_input": {"file_path": "tests/tmp_clean_test.py", "content": "x = 1\n"},
    "cwd": str(ROOT),
}


def run_hook(guard_name: str, payload: dict) -> int:
    """Run a guard hook script as the battery does: JSON on stdin, rc returned."""
    p = subprocess.run(
        [sys.executable, str(HOOKS / f"{guard_name}.py")],
        input=json.dumps(payload), capture_output=True, text=True, timeout=30,
    )
    return p.returncode


def run_guard_in_process(module, payload: dict) -> int:
    """Run a guard's main() in-process with stdin/stdout redirected."""
    out = io.StringIO()
    old_stdin, old_stdout = sys.stdin, sys.stdout
    sys.stdin = io.StringIO(json.dumps(payload))
    sys.stdout = out
    try:
        return module.main()
    finally:
        sys.stdin, sys.stdout = old_stdin, old_stdout


# ── 1. Battery smoke test ──
def test_battery_runs_and_reports_every_guard():
    gh = GuardHealth(ROOT)
    guards = sorted({c.guard for c in gh.battery()})
    results = gh.run()

    assert {r.guard for r in results} == set(guards)
    assert len(results) == len(guards)
    for r in results:
        assert r.status in ("ALIVE", "DORMANT", "BROKEN", "NOT_VERIFIED")
        assert (HOOKS / f"{r.guard}.py").exists(), f"hook script missing for {r.guard}"
        assert r.negative_total >= 1
        assert r.checked_at
        assert r.blocked >= 0 and r.allowed >= 0


# ── 2. Mutation test: a dead regex must be caught by the fixture ──
def test_gate_guard_fixture_isolation_pending_blocks_approved_passes():
    """GC-001/GC-008 fixture isolation: gate_guard's pending-block logic is
    exercised against an isolated temp project (the real repo has no pending
    gate). A pending gate must block the write (GC-001), and an approved
    in-scope gate must allow it (GC-008) — both via the battery runner, so the
    fixture materialization path is covered end-to-end.
    """
    gh = GuardHealth(ROOT)
    results = {r.guard: r for r in gh.run()}
    gg = results["gate_guard"]
    assert gg.blocked == 1, "GC-001 must block a pending-gate write in fixture"
    assert gg.allowed == 1, "GC-008 must allow an approved-gate write in fixture"
    assert gg.status == "ALIVE"


def test_mutation_removing_backslash_makes_fixture_pass():
    """Kill bash_content_guard's first DANGEROUS_PATTERNS regex (remove a
    backslash from \\s+ — the exact corruption class that made the guard 100%
    dead in T-0082) and prove the negative-control fixture that MUST block now
    PASSES. A guard with the dead regex goes unnoticed by the battery's
    machinery only if the fixture itself is weak; this test proves it is not.
    """
    sys.path.insert(0, str(HOOKS))
    import bash_content_guard as bg

    original = bg.DANGEROUS_PATTERNS
    pat_src = original[0][0].pattern
    assert r"\s+" in pat_src, "fixture expects a \\s+ in the redirect pattern"
    broken_regex = re.compile(pat_src.replace(r"\s+", "s+", 1))
    mutated = [(broken_regex, original[0][1])] + list(original[1:])

    try:
        bg.DANGEROUS_PATTERNS = mutated
        rc_dead = run_guard_in_process(bg, FIXTURE_REDIRECT_WRITE)
    finally:
        bg.DANGEROUS_PATTERNS = original

    # The mutated (dead) guard fails to block the redirect write...
    assert rc_dead == 0, (
        "mutation did not reproduce guard death: a broken regex must let the "
        f"redirect write through, got rc={rc_dead}"
    )
    # ...while the live guard does block it — the fixture discriminates.
    assert run_guard_in_process(bg, FIXTURE_REDIRECT_WRITE) == 2


# ── 3. Negative control: content_guard blocks a secret write ──
def test_content_guard_blocks_secret_write():
    rc = run_hook("content_guard", FIXTURE_SECRET_WRITE)
    assert rc == 2, f"secret content must be blocked, got rc={rc}"


# ── 4. Negative control: bash_content_guard blocks a redirect write ──
def test_bash_content_guard_blocks_redirect_write():
    rc = run_hook("bash_content_guard", FIXTURE_REDIRECT_WRITE)
    assert rc == 2, f"redirect write must be blocked, got rc={rc}"


# ── 5. Positive control: clean content passes (no over-blocking) ──
def test_content_guard_allows_clean_content():
    rc = run_hook("content_guard", FIXTURE_CLEAN_WRITE)
    assert rc == 0, f"clean content must pass, got rc={rc}"


# ── 6. Summary semantics: BROKEN or DORMANT => overall FAIL ──
def _result(status: str) -> GuardHealthResult:
    return GuardHealthResult(
        guard="fake_guard", status=status,
        blocked=0, negative_total=1, allowed=0, positive_total=0, errors=[],
    )


def test_summary_overall_fails_on_broken(monkeypatch):
    gh = GuardHealth(ROOT)
    monkeypatch.setattr(GuardHealth, "run", lambda self: [_result("BROKEN")])
    assert gh.summary()["overall"] == "FAIL"
    assert gh.summary()["broken"] == 1


def test_summary_overall_fails_on_dormant(monkeypatch):
    gh = GuardHealth(ROOT)
    monkeypatch.setattr(GuardHealth, "run", lambda self: [_result("DORMANT")])
    assert gh.summary()["overall"] == "FAIL"
    assert gh.summary()["dormant"] == 1


def test_summary_overall_passes_when_all_alive(monkeypatch):
    gh = GuardHealth(ROOT)
    alive = GuardHealthResult(
        guard="fake_guard", status="ALIVE",
        blocked=1, negative_total=1, allowed=1, positive_total=1, errors=[],
    )
    monkeypatch.setattr(GuardHealth, "run", lambda self: [alive])
    assert gh.summary()["overall"] == "PASS"
