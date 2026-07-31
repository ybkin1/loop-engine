#!/usr/bin/env python3
"""loop_guard_health.py — Guard Health Check CLI (T-0083).

Usage:
  python tools/loop_guard_health.py            # run battery, print summary
  python tools/loop_guard_health.py --json     # JSON output
  python tools/loop_guard_health.py --report   # write .ai/evidence/T-0083/guard-health/report.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from loop_core.guard_health import GuardHealth  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Guard Health Check")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--report", action="store_true", help="write evidence report")
    args = parser.parse_args()

    gh = GuardHealth(Path(__file__).resolve().parent.parent)
    summary = gh.summary()
    if args.report:
        out = gh.write_report(".ai/evidence/T-0083/guard-health/report.json")
        print(f"report written: {out}")
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"Guards checked: {summary['guards_checked']}")
        print(f"  ALIVE:  {summary['alive']}")
        print(f"  DORMANT: {summary['dormant']}")
        print(f"  BROKEN: {summary['broken']}")
        for r in summary['results']:
            if r['status'] != 'ALIVE':
                print(f"  [!] {r['guard']}: {r['status']} errors={r['errors'][:3]}")
        print(f"Overall: {summary['overall']}")
    return 0 if summary["overall"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
