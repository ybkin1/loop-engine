from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from codex_loop.governance.authority_records import production_capability, require_production_authority
from codex_loop.governance.governor_lib import GovernanceError


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Isolated Project Governor action boundary")
    result.add_argument("project_root")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("capability")
    commands.add_parser("create-pending-gate")
    commands.add_parser("decide-pending-gate")
    commands.add_parser("start-approved-execution")
    commands.add_parser("run-final-validation")
    return result


def main() -> int:
    args = parser().parse_args()
    root = Path(args.project_root).resolve()
    try:
        if args.command == "capability":
            for key, value in production_capability().items():
                print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
            return 0
        if args.command in {"create-pending-gate", "decide-pending-gate", "start-approved-execution"}:
            require_production_authority()
        if args.command == "run-final-validation":
            from validation_runner import run_gate_bound_validation

            run_gate_bound_validation(root)
            return 0
    except GovernanceError as exc:
        print(f"[error] {exc.code}: {exc}")
        return 2
    print(f"[error] VALIDATION_ERROR: unsupported command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
