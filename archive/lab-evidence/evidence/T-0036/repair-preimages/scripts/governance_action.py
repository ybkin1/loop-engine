from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from governor_lib import (
    GovernanceError,
    bind_final_validation,
    create_pending_gate_action,
    decide_pending_gate_action,
    load_inline_json_record,
    load_json_record,
    snapshot_final_validation,
    start_approved_execution_action,
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Candidate-only Project Governor action boundary")
    result.add_argument("project_root")
    commands = result.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create-pending-gate")
    add_action_source(create)
    create.add_argument("--gate-packet", required=True)

    decide = commands.add_parser("decide-pending-gate")
    add_action_source(decide)
    decide.add_argument("--decision", choices=["approved", "rejected"], required=True)

    start = commands.add_parser("start-approved-execution")
    add_action_source(start)

    snapshot = commands.add_parser("snapshot-final-validation")
    add_action_source(snapshot)
    snapshot.add_argument("--path", action="append", required=True)
    snapshot.add_argument("--protected-path", action="append", default=[])

    bind = commands.add_parser("bind-final-validation")
    add_action_source(bind)
    bind.add_argument("--snapshot-token", required=True)
    command_source = bind.add_mutually_exclusive_group(required=True)
    command_source.add_argument("--command-evidence")
    command_source.add_argument("--command-evidence-json")
    bind.add_argument("--command-evidence-ref")
    bind.add_argument("--manifest", required=True)
    return result


def add_action_source(command: argparse.ArgumentParser) -> None:
    source = command.add_mutually_exclusive_group(required=True)
    source.add_argument("--action-record")
    source.add_argument("--action-record-json")
    command.add_argument("--action-evidence")


def main() -> int:
    args = parser().parse_args()
    root = Path(args.project_root).resolve()
    try:
        if args.action_record:
            record, record_path = load_json_record(root, args.action_record)
        elif args.action_evidence:
            record, record_path = load_inline_json_record(root, args.action_record_json, args.action_evidence)
        else:
            raise GovernanceError("VALIDATION_ERROR", "Inline action JSON requires --action-evidence")
        if args.command == "create-pending-gate":
            packet, _ = load_json_record(root, args.gate_packet)
            create_pending_gate_action(root, record, record_path, packet)
        elif args.command == "decide-pending-gate":
            decide_pending_gate_action(root, record, record_path, args.decision)
        elif args.command == "start-approved-execution":
            start_approved_execution_action(root, record, record_path)
        elif args.command == "snapshot-final-validation":
            token = snapshot_final_validation(root, record, record_path, args.path, args.protected_path)
            print(f"[snapshot-token] {token}")
        elif args.command == "bind-final-validation":
            if args.command_evidence:
                command, command_path = load_json_record(root, args.command_evidence)
            elif args.command_evidence_ref:
                command, command_path = load_inline_json_record(
                    root, args.command_evidence_json, args.command_evidence_ref
                )
            else:
                raise GovernanceError(
                    "VALIDATION_ERROR", "Inline command evidence requires --command-evidence-ref"
                )
            bind_final_validation(
                root,
                record,
                record_path,
                args.snapshot_token,
                command,
                command_path,
                args.manifest,
            )
        else:
            raise GovernanceError("VALIDATION_ERROR", f"Unsupported command: {args.command}")
    except GovernanceError as exc:
        print(f"[error] {exc.code}: {exc}")
        return 2
    except RuntimeError as exc:
        print(f"[error] TRANSACTION_ERROR: {exc}")
        return 2
    print(f"[ok] {args.command} completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
