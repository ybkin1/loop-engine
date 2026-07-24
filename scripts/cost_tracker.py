#!/usr/bin/env python3
"""
cost_tracker.py — Token cost tracking and reporting tool.

Reads cost log entries from .ai/evidence/costs/cost_log.jsonl and
generates a report aggregated by role and phase.

Usage:
    python cost_tracker.py --project-root <path> --report --json
"""
import argparse
import json
from pathlib import Path


def read_cost_log(project_root: Path) -> list[dict]:
    """Read all cost log entries from the JSONL file."""
    log_path = project_root / ".ai" / "evidence" / "costs" / "cost_log.jsonl"
    if not log_path.exists():
        return []
    entries = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def generate_report(entries: list[dict]) -> dict:
    """Aggregate cost entries by role and phase."""
    total = 0
    by_role: dict[str, int] = {}
    by_phase: dict[str, int] = {}
    rework = 0
    task_phase_seen: dict[str, int] = {}

    for entry in entries:
        tokens = entry.get("tokens", 0)
        role = entry.get("role", "unknown")
        phase = entry.get("phase", "unknown")
        task_id = entry.get("task_id", "")

        total += tokens
        by_role[role] = by_role.get(role, 0) + tokens
        by_phase[phase] = by_phase.get(phase, 0) + tokens

        # Rework detection: track task-phase combinations
        # If the same task appears in the same phase more than once, it is rework
        key = f"{task_id}:{phase}"
        if key in task_phase_seen:
            rework += 1
        task_phase_seen[key] = task_phase_seen.get(key, 0) + 1

    return {
        "summary": {"total_tokens": total},
        "by_role": by_role,
        "by_phase": by_phase,
        "rework_estimate": rework,
        "entry_count": len(entries),
    }


def main():
    parser = argparse.ArgumentParser(description="Loop Engine Token Cost Tracker")
    parser.add_argument("--project-root", required=True, help="Project root directory")
    parser.add_argument("--report", action="store_true", help="Generate cost report")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    entries = read_cost_log(root)

    if args.report:
        report = generate_report(entries)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"Total tokens: {report['summary']['total_tokens']}")
            print(f"Entries: {report['entry_count']}")
            print("\nBy role:")
            for role, tokens in sorted(report["by_role"].items()):
                print(f"  {role}: {tokens}")
            print("\nBy phase:")
            for phase, tokens in sorted(report["by_phase"].items()):
                print(f"  {phase}: {tokens}")
    else:
        print(json.dumps({"summary": {"total_tokens": 0}}))


if __name__ == "__main__":
    main()
