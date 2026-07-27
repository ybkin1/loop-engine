from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from continuity_producer import render_handoff
from governor_lib import GovernanceError, ai_dir, dump_yaml, load_yaml, project_root_arg, transactional_write_texts


def main() -> int:
    parser = project_root_arg()
    parser.add_argument("--note", default="")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()

    # v3.5: Validate --note for ambiguous phrasing
    if args.note:
        ambiguous = [
            ("not started", "avoid 'not started' — may conflict with implementation_started state"),
            ("未开始", "避免'未开始'——可能与 implementation_started 状态冲突"),
            ("has not started", "avoid 'has not started' — prefer 'this session: no code changes'"),
        ]
        state = load_yaml(root / ".ai" / "state.yaml")
        impl_started = state.get("implementation_started", False)
        for phrase, warning in ambiguous:
            if phrase.lower() in args.note.lower() and impl_started:
                print(f"[warn] NOTE_AMBIGUITY: {warning}. Note was: '{args.note}'")
                print("[warn] Consider: 'this session: no product code changes' instead.")
                break

    try:
        # v3.5: Auto-repair continuity before render to prevent drift deadlock
        try:
            from repair_continuity import repair_continuity
            repair_continuity(root)
        except Exception:
            pass  # Non-critical: repair is best-effort

        handoff, state = render_handoff(root, args.note)
        base = ai_dir(root)
        transactional_write_texts(
            base,
            {base / "state.yaml": dump_yaml(state) + "\n", base / "HANDOFF.md": handoff},
        )

        # v3.5: Auto-fix stale anchor files when state contradicts them
        _fix_stale_anchors(root, state, base)

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


def _fix_stale_anchors(root: Path, state: dict, base: Path) -> None:
    """Auto-fix anchor files when they contradict state.yaml (v3.5).

    This eliminates the root cause of HANDOFF drift: stale source files
    that claim "implementation has not started" when state says otherwise.
    """
    import os

    impl_started = state.get("implementation_started")
    if not impl_started:
        return  # Nothing to fix — state also says not started

    # Fix PROJECT.md
    project_md = base / "PROJECT.md"
    if project_md.exists():
        text = project_md.read_text(encoding="utf-8")
        updated = text
        stale_claims = [
            "Product implementation has not started.",
            "implementation has not started",
            "Product implementation has not started",
        ]
        for claim in stale_claims:
            if claim in updated:
                updated = updated.replace(
                    claim,
                    "Product implementation is authorized and in progress under the current work package."
                )
        if updated != text:
            tmp = project_md.with_suffix(".md.tmp")
            tmp.write_text(updated, encoding="utf-8")
            os.replace(str(tmp), str(project_md))
            print("[close_session] Fixed stale PROJECT.md anchor: 'implementation not started' -> 'in progress'")

    # Fix architecture-authority.yaml
    arch_auth = base / "architecture-authority.yaml"
    if arch_auth.exists():
        text = arch_auth.read_text(encoding="utf-8")
        updated = text.replace(
            "implementation_started: false",
            "implementation_started: true  # authorized under current work package"
        )
        if updated != text:
            tmp = arch_auth.with_suffix(".yaml.tmp")
            tmp.write_text(updated, encoding="utf-8")
            os.replace(str(tmp), str(arch_auth))
            print("[close_session] Fixed stale architecture-authority.yaml: implementation_started=false -> true")


if __name__ == "__main__":
    raise SystemExit(main())
