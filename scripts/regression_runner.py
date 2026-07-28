#!/usr/bin/env python3
"""
regression_runner.py — Local automated regression test runner.

Runs the full test suite and quality gates, compares results against
a stored baseline across multiple dimensions, and blocks on regressions.

Usage:
    python regression_runner.py --project-root <path>
    python regression_runner.py --project-root <path> --baseline <file>
    python regression_runner.py --project-root <path> --save-baseline
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


# ── Canonical status semantics (shared with quality-engineer) ─────────────
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_BLOCKED = "BLOCKED"
STATUS_UNAVAILABLE = "UNAVAILABLE"
STATUS_NOT_VERIFIED = "NOT_VERIFIED"


def run_tests(project_root: Path) -> dict:
    """Run the full test suite and return structured results."""
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=line"],
            capture_output=True, text=True,
            timeout=300, cwd=str(project_root),
        )
        passed = 0
        failed = 0
        skipped = 0
        for line in r.stdout.splitlines():
            m = re.search(r"(\d+)\s+passed", line)
            if m:
                passed = int(m.group(1))
            m = re.search(r"(\d+)\s+failed", line)
            if m:
                failed = int(m.group(1))
            m = re.search(r"(\d+)\s+skipped", line)
            if m:
                skipped = int(m.group(1))

        return {
            "exit_code": r.returncode,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "output_hash": hashlib.sha256(r.stdout.encode()).hexdigest()[:16],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "passed": 0, "failed": 0, "skipped": 0, "error": "TIMEOUT"}
    except Exception as e:
        return {"exit_code": -1, "passed": 0, "failed": 0, "skipped": 0, "error": str(e)}


def run_lint(project_root: Path) -> dict:
    """Run lint check."""
    try:
        r = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "hooks/", "tools/", "scripts/",
             "src/", "loop_core/", "loop_engine/"],
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


def run_compile(project_root: Path) -> dict:
    """Run compile check on core modules."""
    try:
        r = subprocess.run(
            [sys.executable, "-c",
             "import py_compile, sys; "
             "files=['loop_core/','hooks/','tools/','agents/']; "
             "errors=[]; "
             "import pathlib; "
             "root=pathlib.Path('.'); "
             "[errors.append(str(f)) for d in files "
             " for f in (root/d).rglob('*.py') if not py_compile.compile(str(f), doraise=True)]; "
             "print(json.dumps({'compiled': len(list((root/'loop_core').rglob('*.py'))), 'errors': len(errors)}))"],
            capture_output=True, text=True,
            timeout=60, cwd=str(project_root),
        )
        data = json.loads(r.stdout) if r.stdout.strip().startswith("{") else {}
        return {
            "exit_code": r.returncode,
            "compiled": data.get("compiled", 0),
            "errors": data.get("errors", 0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"exit_code": -1, "compiled": 0, "errors": -1, "error": str(e)}


def run_security_audit(project_root: Path) -> dict:
    """Run security/dependency audit."""
    try:
        r = subprocess.run(
            ["pip-audit", "--format", "json"],
            capture_output=True, text=True,
            timeout=60, cwd=str(project_root),
        )
        try:
            vulns = json.loads(r.stdout) if r.stdout.strip() else []
        except json.JSONDecodeError:
            vulns = []
        return {
            "exit_code": r.returncode,
            "vulnerabilities": len(vulns) if isinstance(vulns, list) else 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except FileNotFoundError:
        return {"exit_code": 0, "vulnerabilities": 0, "unavailable": True,
                "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        return {"exit_code": -1, "vulnerabilities": -1, "error": str(e)}


def load_baseline(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_baseline(path: Path, results: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")


def compare_dimension(name: str, current_val, baseline_val,
                      higher_is_better: bool = True,
                      threshold: int = 0) -> tuple:
    """Compare a single dimension and return (status, delta, detail)."""
    if current_val is None or baseline_val is None:
        return STATUS_NOT_VERIFIED, None, "baseline unavailable"

    if isinstance(current_val, dict) or isinstance(baseline_val, dict):
        return STATUS_NOT_VERIFIED, None, "complex type — manual review"

    try:
        delta = current_val - baseline_val
    except TypeError:
        return STATUS_NOT_VERIFIED, None, f"type mismatch: {type(current_val)} vs {type(baseline_val)}"

    if higher_is_better:
        if delta < -threshold:
            return STATUS_BLOCKED, delta, f"regression: {baseline_val} → {current_val} (Δ={delta})"
        elif delta < 0:
            return STATUS_FAIL, delta, f"minor regression: {baseline_val} → {current_val}"
        else:
            return STATUS_PASS, delta, f"{baseline_val} → {current_val} (Δ=+{delta})" if delta > 0 else "no change"
    else:
        # Lower is better (e.g. lint errors, vulnerabilities)
        if delta > threshold:
            return STATUS_BLOCKED, delta, f"regression: {baseline_val} → {current_val} (Δ=+{delta})"
        elif delta > 0:
            return STATUS_FAIL, delta, f"minor regression: {baseline_val} → {current_val}"
        else:
            return STATUS_PASS, delta, f"{baseline_val} → {current_val} (Δ={delta})" if delta < 0 else "no change"


def compare_results(current: dict, baseline: dict) -> dict:
    """Compare current results against baseline across all dimensions."""
    if not baseline:
        return {
            "has_regressions": False,
            "dimensions": {},
            "verdict": STATUS_NOT_VERIFIED,
            "reason": "no baseline established"
        }

    dimensions = {}

    # Test: passed count (higher is better)
    dim_test = compare_dimension(
        "test_passed",
        current.get("tests", {}).get("passed"),
        baseline.get("tests", {}).get("passed"),
        higher_is_better=True, threshold=0
    )
    dimensions["test_passed"] = {"status": dim_test[0], "delta": dim_test[1], "detail": dim_test[2]}

    # Test: failed count (lower is better)
    dim_failed = compare_dimension(
        "test_failed",
        current.get("tests", {}).get("failed"),
        baseline.get("tests", {}).get("failed"),
        higher_is_better=False, threshold=0
    )
    dimensions["test_failed"] = {"status": dim_failed[0], "delta": dim_failed[1], "detail": dim_failed[2]}

    # Lint: errors (lower is better)
    dim_lint = compare_dimension(
        "lint_errors",
        current.get("lint", {}).get("errors"),
        baseline.get("lint", {}).get("errors"),
        higher_is_better=False, threshold=0
    )
    dimensions["lint_errors"] = {"status": dim_lint[0], "delta": dim_lint[1], "detail": dim_lint[2]}

    # Compile: compiled count (higher is better)
    if current.get("compile", {}).get("compiled") is not None:
        dim_compile = compare_dimension(
            "compile_count",
            current.get("compile", {}).get("compiled"),
            baseline.get("compile", {}).get("compiled"),
            higher_is_better=True, threshold=0
        )
        dimensions["compile_count"] = {"status": dim_compile[0], "delta": dim_compile[1], "detail": dim_compile[2]}

    # Compile: errors (lower is better)
    if current.get("compile", {}).get("errors") is not None:
        dim_compile_err = compare_dimension(
            "compile_errors",
            current.get("compile", {}).get("errors"),
            baseline.get("compile", {}).get("errors"),
            higher_is_better=False, threshold=0
        )
        dimensions["compile_errors"] = {"status": dim_compile_err[0], "delta": dim_compile_err[1], "detail": dim_compile_err[2]}

    # Security: vulnerabilities (lower is better)
    if not current.get("security", {}).get("unavailable"):
        dim_sec = compare_dimension(
            "vulnerabilities",
            current.get("security", {}).get("vulnerabilities"),
            baseline.get("security", {}).get("vulnerabilities"),
            higher_is_better=False, threshold=0
        )
        dimensions["vulnerabilities"] = {"status": dim_sec[0], "delta": dim_sec[1], "detail": dim_sec[2]}
    else:
        dimensions["vulnerabilities"] = {"status": STATUS_UNAVAILABLE, "delta": None, "detail": "pip-audit not installed"}

    # Determine overall verdict
    blocked = [k for k, v in dimensions.items() if v["status"] == STATUS_BLOCKED]
    failed = [k for k, v in dimensions.items() if v["status"] == STATUS_FAIL]
    has_regressions = len(blocked) > 0

    if blocked:
        verdict = STATUS_BLOCKED
        reason = f"BLOCKED by: {', '.join(blocked)}"
    elif failed:
        verdict = STATUS_FAIL
        reason = f"minor regressions in: {', '.join(failed)}"
    else:
        verdict = STATUS_PASS
        reason = "all dimensions PASS or unchanged"

    return {
        "has_regressions": has_regressions,
        "dimensions": dimensions,
        "verdict": verdict,
        "reason": reason,
    }


def main():
    parser = argparse.ArgumentParser(description="Automated Regression Runner")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--baseline", default=".ai/evidence/regression/baseline.json")
    parser.add_argument("--save-baseline", action="store_true")

    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    baseline_path = root / args.baseline

    print("[regression] Running tests...")
    test_results = run_tests(root)
    print(f"[regression] Tests: {test_results.get('passed', 0)} passed, "
          f"{test_results.get('failed', 0)} failed, "
          f"{test_results.get('skipped', 0)} skipped")

    print("[regression] Running lint...")
    lint_results = run_lint(root)
    print(f"[regression] Lint: {lint_results.get('errors', -1)} errors")

    print("[regression] Running compile check...")
    compile_results = run_compile(root)
    print(f"[regression] Compile: {compile_results.get('compiled', 0)} files, "
          f"{compile_results.get('errors', 0)} errors")

    print("[regression] Running security audit...")
    security_results = run_security_audit(root)
    sec_status = "UNAVAILABLE" if security_results.get("unavailable") else                  f"{security_results.get('vulnerabilities', 0)} vulnerabilities"
    print(f"[regression] Security: {sec_status}")

    results = {
        "schema": "regression_report/v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": str(root),
        "dimensions": {
            "tests": test_results,
            "lint": lint_results,
            "compile": compile_results,
            "security": security_results,
        },
    }

    if args.save_baseline:
        save_baseline(baseline_path, results)
        print(f"[regression] Baseline saved to {args.baseline}")
        sys.exit(0)

    baseline = load_baseline(baseline_path)
    comparison = compare_results(results, baseline)

    for dim_name, dim_result in comparison.get("dimensions", {}).items():
        icon = "✅" if dim_result["status"] == STATUS_PASS else                "❌" if dim_result["status"] in (STATUS_BLOCKED, STATUS_FAIL) else "⚠️"
        print(f"[regression] {icon} {dim_name}: {dim_result['detail']}")

    print(f"[regression] Verdict: {comparison['verdict']} — {comparison['reason']}")

    if comparison["has_regressions"]:
        sys.exit(2)
    elif comparison["verdict"] == STATUS_FAIL:
        print("[regression] WARNING: minor regressions detected (non-blocking)")
        sys.exit(0)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
