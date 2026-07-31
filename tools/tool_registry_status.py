#!/usr/bin/env python3
"""tool_registry_status.py — Capability Registry status CLI (T-0087 U1).

列出注册表确定性快照（snapshot_id + 每个 checker/guard 的绑定）+ 三类完整性
检测（death 已有电池 / missing 遗漏 / drift 漂移）。

Usage:
  python tools/tool_registry_status.py            # text summary
  python tools/tool_registry_status.py --json     # full JSON
  python tools/tool_registry_status.py --report   # write evidence JSON to
                                                  #   .ai/evidence/T-0087/capability-registry/status.json

Exit codes:
  0 = all healthy (no missing/drift, guards alive)
  1 = report-level findings only (MISSING/DRIFT) — never blocks the loop
  2 = a guard is BROKEN or DORMANT (death fail-closed, unchanged semantics)
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from loop_core.capability_registry import build_default_registry  # noqa: E402
from loop_core.guard_health import GuardHealth  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Capability Registry status")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--report", action="store_true",
                        help="write evidence report to .ai/evidence/T-0087/capability-registry/status.json")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    registry = build_default_registry(root)
    snapshot = registry.snapshot()
    integrity = GuardHealth(root, registry=registry).integrity_check()
    missing, drift = integrity["missing"], integrity["drift"]

    report = {
        "snapshot_id": snapshot.snapshot_id,
        "canonical_json": snapshot.canonical_json,
        "bindings": [b.to_dict() for b in snapshot.entries.values()],
        "integrity": {
            "death": integrity["death"],
            "missing": missing,
            "drift": drift,
            "overall": integrity["overall"],
        },
        "checked_at": integrity["checked_at"],
    }

    if args.report:
        out = root / ".ai" / "evidence" / "T-0087" / "capability-registry" / "status.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"report written: {out}")

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        death = integrity["death"]
        print(f"Capability registry snapshot: {snapshot.snapshot_id[:16]}…")
        print(f"  bindings: {len(snapshot.entries)} "
              f"(checkers: {sum(1 for b in snapshot.entries.values() if b.provider_id == 'checker')}, "
              f"guards: {sum(1 for b in snapshot.entries.values() if b.provider_id == 'guard')})")
        for b in snapshot.entries.values():
            flag = "  [DRIFT]" if any(d["capability_id"] == b.capability_id for d in drift) else ""
            print(f"  {b.capability_id:<28} {b.provider_id:<7} v{b.version[:12]} "
                  f"{b.implementation_path}{flag}")
        print(f"Guard death: {death['alive']} ALIVE / {death['dormant']} DORMANT / "
              f"{death['broken']} BROKEN -> {death['overall']}")
        print(f"MISSING: {len(missing)}   DRIFT: {len(drift)}   "
              f"(report-level, never blocks)")
        for d in missing:
            print(f"  [MISSING] {d['implementation_path']}")
        for d in drift:
            print(f"  [DRIFT]   {d['capability_id']} ({d['implementation_path']})")
        print(f"Overall: {integrity['overall']}")

    if death["overall"] != "PASS":
        return 2   # death fail-closed — unchanged semantics
    if missing or drift:
        return 1   # report-level findings only
    return 0


if __name__ == "__main__":
    sys.exit(main())
