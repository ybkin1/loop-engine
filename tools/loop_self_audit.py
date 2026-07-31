#!/usr/bin/env python3
"""loop_self_audit.py — Loop self-audit (dogfooding) runner (T-0083 AC-04).

Runs the full baseline audit battery that T-0082 Phase 0 performed MANUALLY,
now scripted: validate_state + guard health + compile + pytest + security
scan + static analysis. Output: .ai/evidence/T-0083/guard-health/self-audit.json

Usage:
  python tools/loop_self_audit.py            # full audit
  python tools/loop_self_audit.py --quick    # validate_state + guard health only
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], timeout: int = 300) -> dict:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           cwd=str(PROJECT_ROOT))
        return {"rc": p.returncode, "stdout": p.stdout[-4000:], "stderr": p.stderr[-2000:]}
    except subprocess.TimeoutExpired:
        return {"rc": -1, "stdout": "", "stderr": f"TIMEOUT>{timeout}s"}
    except FileNotFoundError:
        return {"rc": -2, "stdout": "", "stderr": "command not found"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Loop self-audit")
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()

    results: dict[str, dict] = {}

    # 1. validate_state
    results["validate_state"] = run([
        sys.executable, str(PROJECT_ROOT / ".zcode" / "tools" / "validate_state.py"),
        str(PROJECT_ROOT),
    ])

    # 2. Guard health
    results["guard_health"] = run([
        sys.executable, str(PROJECT_ROOT / "tools" / "loop_guard_health.py"), "--json",
    ])

    if not args.quick:
        # 3. compile
        results["compile"] = run([sys.executable, "-m", "compileall", "-q", "loop_core/"])
        # 4. pytest (core only to bound runtime)
        results["pytest_core"] = run([
            sys.executable, "-m", "pytest", "tests/test_loop_core.py",
            "tests/test_verdicts.py", "tests/test_guard_health.py", "-q", "--tb=line",
        ])
        # 5. security scan
        results["security_scan"] = run([
            sys.executable, "-c",
            "import sys; sys.path.insert(0,'.'); "
            "from loop_core.security_scanner import scan_security; "
            "r = scan_security('loop_core', task_id='T-0083', phase='S5-quality', git_commit='self-audit'); "
            "print(f'critical={r.critical} high={r.high} verdict={r.verdict.value}')",
        ])
        # 6. static analysis
        results["static_analysis"] = run([
            sys.executable, "-c",
            "import sys; sys.path.insert(0,'.'); "
            "from loop_core.static_analyzer import analyze_project; "
            "r = analyze_project('loop_core', task_id='T-0083', phase='S5-quality', git_commit='self-audit'); "
            "print(f'errors={r.errors} warnings={r.warnings} verdict={r.verdict.value}')",
        ])

    # Verdict computation
    checks = {}
    if args.quick:
        checks = {"validate_state", "guard_health"}
    else:
        checks = set(results.keys())
    failed = [k for k, r in results.items()
              if k in checks and r.get("rc", -1) != 0 and k not in ("validate_state",)]
    # validate_state returns 2 when NO_ACTIVE_TASK (expected idle) — treat rc 0/2 as OK
    if results.get("validate_state", {}).get("rc") not in (0, 2):
        failed.append("validate_state")
    # guard health: rc 0 = PASS, rc 2 = guard broken
    gh = results.get("guard_health", {})
    if gh.get("rc") == 2:
        failed.append("guard_health")

    report = {
        "tool": "loop_self_audit",
        "version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
            cwd=str(PROJECT_ROOT)).stdout.strip(),
        "results": results,
        "failed": failed,
        "overall": "PASS" if not failed else "FAIL",
    }
    out = PROJECT_ROOT / ".ai" / "evidence" / "T-0083" / "guard-health" / "self-audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"overall": report["overall"], "failed": failed}, indent=2))
    return 0 if report["overall"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
