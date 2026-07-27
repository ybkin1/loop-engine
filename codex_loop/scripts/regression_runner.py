"""
regression_runner.py — Local automated regression test runner.

Runs the full test suite and quality gates, compares results against
a stored baseline, and blocks on regressions.

Usage:
    python regression_runner.py --project-root <path>
    python regression_runner.py --project-root <path> --baseline <file>
    python regression_runner.py --project-root <path> --save-baseline
"""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run_tests(project_root: Path) -> dict:
    """Run the full test suite and return results."""
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=line"],
            capture_output=True, text=True,
            timeout=300, cwd=str(project_root),
        )
        passed = 0
        failed = 0
        for line in r.stdout.splitlines():
            if "passed" in line:
                # Parse: "193 passed, 1 skipped"
                parts = line.split()
                for p in parts:
                    if p.isdigit():
                        passed += int(p)
            elif "failed" in line:
                parts = line.split()
                for p in parts:
                    if p.isdigit():
                        failed += int(p)

        return {
            "exit_code": r.returncode,
            "passed": passed,
            "failed": failed,
            "output_hash": hashlib.sha256(r.stdout.encode()).hexdigest()[:16],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "passed": 0, "failed": 0, "error": "TIMEOUT"}
    except Exception as e:
        return {"exit_code": -1, "passed": 0, "failed": 0, "error": str(e)}


def run_lint(project_root: Path) -> dict:
    """Run lint check."""
    try:
        r = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "hooks/", "tools/", "scripts/", "src/", "loop_core/", "loop_engine/"],
            capture_output=True, text=True,
            timeout=60, cwd=str(project_root),
        )
        return {
            "exit_code": r.returncode,
            "errors": len([l for l in r.stdout.splitlines() if l.strip()]),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception:
        return {"exit_code": -1, "errors": -1}


def load_baseline(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_baseline(path: Path, results: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")


def compare_results(current: dict, baseline: dict) -> dict:
    """Compare current results against baseline."""
    regressions = []
    improvements = []

    if baseline:
        current_passed = current.get("tests", {}).get("passed", 0)
        baseline_passed = baseline.get("tests", {}).get("passed", 0)
        if current_passed < baseline_passed:
            regressions.append(f"Tests: {baseline_passed}→{current_passed} passed (regression)")
        elif current_passed > baseline_passed:
            improvements.append(f"Tests: {baseline_passed}→{current_passed} passed (improvement)")

        current_lint = current.get("lint", {}).get("errors", 0)
        baseline_lint = baseline.get("lint", {}).get("errors", 0)
        if current_lint > baseline_lint:
            regressions.append(f"Lint: {baseline_lint}→{current_lint} errors (regression)")

    return {
        "has_regressions": len(regressions) > 0,
        "regressions": regressions,
        "improvements": improvements,
        "verdict": "BLOCKED" if regressions else "PASS",
    }


def main():
    parser = argparse.ArgumentParser(description="Automated Regression Runner")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--baseline", default=".ai/evidence/regression_baseline.json")
    parser.add_argument("--save-baseline", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    baseline_path = root / args.baseline

    print("[regression] Running tests...")
    test_results = run_tests(root)
    print(f"[regression] Tests: {test_results.get('passed', 0)} passed, {test_results.get('failed', 0)} failed")

    print("[regression] Running lint...")
    lint_results = run_lint(root)
    print(f"[regression] Lint: {lint_results.get('errors', -1)} errors")

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tests": test_results,
        "lint": lint_results,
    }

    if args.save_baseline:
        save_baseline(baseline_path, results)
        print(f"[regression] Baseline saved to {args.baseline}")
        sys.exit(0)

    baseline = load_baseline(baseline_path)
    comparison = compare_results(results, baseline)

    if comparison["has_regressions"]:
        for r in comparison["regressions"]:
            print(f"[regression] REGRESSION: {r}")
        print("[regression] BLOCKED — regressions detected")
        sys.exit(2)
    else:
        for i in comparison["improvements"]:
            print(f"[regression] IMPROVEMENT: {i}")
        print("[regression] PASS — no regressions")
        sys.exit(0)


if __name__ == "__main__":
    main()
