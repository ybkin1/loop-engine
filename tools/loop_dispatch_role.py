#!/usr/bin/env python3
"""loop_dispatch_role.py — main-thread CLI to prepare/complete role dispatches.

Usage:
  python tools/loop_dispatch_role.py prepare --role developer --task T-0082 --phase S4-implementation --gate G-T-0082-REQUIREMENTS --prompt "..."
  python tools/loop_dispatch_role.py complete --dispatch-id DP-xxx --status COMPLETED --summary "..."
  python tools/loop_dispatch_role.py verify --task T-0082
  python tools/loop_dispatch_role.py list
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from loop_core.role_dispatch import RoleDispatchManager, DispatchOrder  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Role dispatch CLI (main-thread orchestrator)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_prep = sub.add_parser("prepare")
    p_prep.add_argument("--role", required=True)
    p_prep.add_argument("--task", required=True)
    p_prep.add_argument("--phase", required=True)
    p_prep.add_argument("--gate", required=True)
    p_prep.add_argument("--prompt", required=True)
    p_prep.add_argument("--paths", default="", help="comma-separated allowed paths")

    p_comp = sub.add_parser("complete")
    p_comp.add_argument("--dispatch-id", required=True)
    p_comp.add_argument("--status", default="COMPLETED")
    p_comp.add_argument("--summary", default="")

    p_verify = sub.add_parser("verify")
    p_verify.add_argument("--task", required=True)

    sub.add_parser("list")

    args = parser.parse_args()
    mgr = RoleDispatchManager(Path(__file__).resolve().parent.parent)

    if args.command == "prepare":
        paths = [p.strip() for p in args.paths.split(",") if p.strip()]
        order = mgr.prepare_dispatch(
            role_id=args.role, task_id=args.task, phase=args.phase,
            gate_id=args.gate, prompt=args.prompt, allowed_paths=paths,
        )
        print(json.dumps(order.to_dict(), indent=2, ensure_ascii=False))
    elif args.command == "complete":
        # Reconstruct order from receipt file
        receipt_path = mgr.receipts_dir / f"{args.dispatch_id}.receipt.json"
        if not receipt_path.exists():
            print(f"ERROR: receipt not found for {args.dispatch_id}", file=sys.stderr)
            return 1
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        order = DispatchOrder(
            dispatch_id=receipt["dispatch_id"],
            role_id=receipt["role_id"],
            task_id=receipt["task_id"],
            phase=receipt["phase"],
            gate_id=receipt["gate_id"],
            actor_id=receipt["actor"],
            session_id=receipt["child_session"],
            child_session_id=receipt["child_session"],
            prompt="",
            allowed_paths=(),
        )
        out = mgr.complete_dispatch(order, status=args.status, output_summary=args.summary)
        print(json.dumps(out, indent=2, ensure_ascii=False))
    elif args.command == "verify":
        receipts = mgr.list_receipts()
        orders = []
        seen_ids: set[str] = set()
        for r in receipts:
            # launch AND completion receipts both carry the launch identity fields
            # (completion merges the launch receipt before appending its own fields)
            if r.get("receipt_type") in ("launch", "completion") and r.get("task_id") == args.task:
                did = r.get("dispatch_id")
                if not did or did in seen_ids:
                    continue
                seen_ids.add(did)
                try:
                    orders.append(DispatchOrder(
                        dispatch_id=did, role_id=r["role_id"],
                        task_id=r["task_id"], phase=r["phase"], gate_id=r["gate_id"],
                        actor_id=r["actor"], session_id=r["child_session"],
                        child_session_id=r["child_session"], prompt="",
                    ))
                except KeyError:
                    continue
        violations = mgr.verify_role_isolation(orders)
        if violations:
            print("ISOLATION_VIOLATIONS:")
            for v in violations:
                print(f"  - {v}")
            return 2
        print(f"ISOLATION_OK: {len(orders)} dispatches, all distinct actor/session")
    elif args.command == "list":
        for r in mgr.list_receipts():
            print(json.dumps(r, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
