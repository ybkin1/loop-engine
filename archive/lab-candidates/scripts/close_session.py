from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from continuity_producer import render_handoff
from governor_lib import GovernanceError, ai_dir, dump_yaml, project_root_arg, transactional_write_texts


def main() -> int:
    parser = project_root_arg()
    parser.add_argument("--note", default="")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    try:
        handoff, state = render_handoff(root, args.note)
        base = ai_dir(root)
        transactional_write_texts(
            base,
            {base / "state.yaml": dump_yaml(state) + "\n", base / "HANDOFF.md": handoff},
        )
        from governor_lib import parse_json_block

        checkpoint = parse_json_block(handoff, "CHECKPOINT")
    except GovernanceError as exc:
        print(f"[error] {exc.code}: {exc}")
        return 2
    except RuntimeError as exc:
        print(f"[error] TRANSACTION_ERROR: {exc}")
        return 2
    status = checkpoint["checkpoint_status"]
    print(f"[ok] HANDOFF_GENERATED_FROM_STRUCTURED_STATE: {base / 'HANDOFF.md'}")
    print(f"[checkpoint-status] {status}")
    return 0 if status in {"PENDING_SUCCESSOR_ACK", "STABLE_FIXTURE_ONLY", "STABLE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
