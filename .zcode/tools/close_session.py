from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from continuity_producer import render_handoff
from governor_lib import GovernanceError, ai_dir, dump_yaml, load_yaml, project_root_arg, transactional_write_texts


# T-0111: 修复器触发点 guard-events 事件写入（观测侧旁路，绝不阻断业务）。
# 与 loop_core.observability 的 GuardCheckEvent 同 schema（check_type=
# "repair"，guard_id="repair_continuity"）；loop_core 不可导入时降级为
# 等价的最小 JSONL 追加。写入失败一律吞掉——观测不得改变 close_session
# 的任何判定与 exit code 语义。
def _record_repair_event(root: Path, result: str, failure_reason: str) -> None:
    import json as _json
    import uuid as _uuid
    from datetime import datetime as _dt, timezone as _tz
    try:
        import sys as _sys
        if str(root) not in _sys.path:
            _sys.path.insert(0, str(root))
        from loop_core.observability import (
            CHECK_REPAIR, GuardCheckEvent, GuardEventRecorder,
        )
        rec = GuardEventRecorder(
            root / ".ai" / "evidence" / "observability" / "guard-events.jsonl"
        )
        rec.record(GuardCheckEvent(
            guard_id="repair_continuity",
            check_type=CHECK_REPAIR,
            result=result,
            duration_ms=0.0,
            failure_reason=failure_reason,
            timestamp=_dt.now(_tz.utc).isoformat(),
            source=f"tool:{Path(__file__).name}",
        ))
    except Exception:  # noqa: BLE001 — 观测失败绝不阻断业务
        try:
            p = root / ".ai" / "evidence" / "observability" / "guard-events.jsonl"
            p.parent.mkdir(parents=True, exist_ok=True)
            line = {
                "event_id": _uuid.uuid4().hex[:16],
                "guard_id": "repair_continuity",
                "capability_id": None,
                "check_type": "repair",
                "result": result,
                "duration_ms": 0.0,
                "failure_reason": failure_reason,
                "timestamp": _dt.now(_tz.utc).isoformat(),
                "source": f"tool:{Path(__file__).name}",
            }
            with open(p, "a", encoding="utf-8") as f:
                f.write(_json.dumps(line, ensure_ascii=False) + "\n")
        except Exception:  # noqa: BLE001
            pass


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
        # v3.5: Auto-repair only dynamic manifest drift; semantic/static drift remains blocking
        try:
            from repair_continuity import repair_continuity
            result = repair_continuity(root, dynamic_only=True)
            # T-0111: 收尾修复事件（PASS —— 动态修复执行完成，fixed=0 属
            # 正常无漂移；fixed>0 表明生成路径漏更新清单）
            _record_repair_event(
                root, "PASS",
                f"dynamic fixed={result.get('fixed', 0)}",
            )
        except TypeError:
            # Backward-compatible tool without dynamic_only: do not auto-repair
            _record_repair_event(
                root, "FAIL",
                "dynamic repair skipped: repair_continuity lacks dynamic_only "
                "(TypeError)",
            )
        except Exception:
            # 既有语义：修复失败不阻断收尾（继续走后续校验，语义漂移仍阻断）
            import traceback as _tb
            _record_repair_event(
                root, "FAIL",
                f"dynamic repair failed: {_tb.format_exc(limit=1)}",
            )

        # Validate continuity after the restricted repair attempt.
        # Any semantic hash mismatch or static source drift must stop close_session.
        from continuity_producer import load_project_continuity
        load_project_continuity(root)

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


# T-0058: Anchor fixes run best-effort; failures are logged but do not block closeout.
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
