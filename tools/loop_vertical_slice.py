#!/usr/bin/env python3
"""loop_vertical_slice.py — validate S1→S6 vertical slice evidence chain (T-0083 AC-08).

Checks that a task has the full phase evidence chain required for a governed
vertical slice: S1 gate approved by user → implementation artifacts →
S5 quality/security/test evidence → S6 acceptance report. Does NOT execute
phases (phases require human gates).

Usage: python tools/loop_vertical_slice.py --task T-0083
"""
import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    args = parser.parse_args()
    task_id = args.task

    checks: dict[str, dict] = {}
    ai = PROJECT_ROOT / ".ai"

    # S1: requirements gate approved by user
    gates = ai / "gates.yaml"
    import yaml
    data = yaml.safe_load(gates.read_text(encoding="utf-8")) if gates.exists() else {}
    task_gates = [g for g in data.get("gates", [])
                  if isinstance(g, dict) and g.get("task_id") == task_id]
    req_gates = [g for g in task_gates if g.get("status") == "approved"
                 and g.get("approval_actor") == "user"]
    checks["S1_requirements_gate"] = {
        "ok": len(req_gates) > 0,
        "detail": f"{len(req_gates)} user-approved gates",
    }

    # S2: task file + task_graph registration
    checks["S2_task_registered"] = {
        "ok": (ai / "tasks" / f"{task_id}.md").exists(),
        "detail": "task file exists",
    }

    # S4: implementation artifacts (evidence dir exists, phase dirs populated)
    ev = ai / "evidence" / task_id
    phase_dirs = [d for d in ev.iterdir() if d.is_dir()] if ev.exists() else []
    checks["S4_implementation_evidence"] = {
        "ok": len(phase_dirs) >= 1,
        "detail": f"{len(phase_dirs)} phase dirs: {[d.name for d in phase_dirs]}",
    }

    # S5: quality/security/test evidence
    s5_files = []
    for d in phase_dirs:
        if d.name in ("phase-3", "phase-5"):
            s5_files += [f.name for f in d.iterdir()]
    checks["S5_quality_evidence"] = {
        "ok": len(s5_files) >= 3,
        "detail": f"{len(s5_files)} files in phase-3/phase-5 dirs",
    }

    # S6: acceptance report
    acc = ev / "phase-6" / "acceptance-report.md"
    checks["S6_acceptance"] = {
        "ok": acc.exists(),
        "detail": "acceptance-report.md exists" if acc.exists() else "MISSING",
    }

    # Overall
    failed = [k for k, v in checks.items() if not v["ok"]]
    report = {
        "tool": "loop_vertical_slice",
        "task_id": task_id,
        "timestamp": json.dumps(None),  # placeholder replaced below
        "checks": checks,
        "failed": failed,
        "overall": "PASS" if not failed else "FAIL",
    }
    from datetime import datetime, timezone
    report["timestamp"] = datetime.now(timezone.utc).isoformat()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["overall"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
