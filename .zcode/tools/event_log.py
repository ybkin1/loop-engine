#!/usr/bin/env python3
"""
event_log.py — T-0155 事件溯源影子层（loopx P0-1 采纳）。

对治理状态写入追加 JSONL 事件链（.ai/evidence/observability/state-events.jsonl），
state.yaml 仍为权威投影；事件链提供审计可追溯性（谁在何时改了什么状态）。

原则：
- **影子层只读审计流**：不参与任何判定，写入失败吞掉（观测绝不阻断业务，
  与 guard-events 同原则）。
- 事件文件为运行时产物（gitignore 不跟踪，同 guard-events 治理）。

用法：
    python event_log.py <root> append --type task_status_changed --task T-XXXX [--actor ai] [--detail '{"from":"pending"}']
    python event_log.py <root> read [--tail N]
    python event_log.py <root> replay-check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("event_log")

EVENTS_PATH = ".ai/evidence/observability/state-events.jsonl"

EVENT_TYPES = {
    "task_registered", "task_status_changed", "gate_created", "gate_approved",
    "gate_completed", "evidence_attached", "handoff_generated",
}

ACTORS = {"ai", "user", "system"}


def events_file(root: Path) -> Path:
    return root / EVENTS_PATH


def append(root: Path, event_type: str, *, task_id: str | None = None,
           gate_id: str | None = None, actor: str = "system",
           detail: dict | None = None, state_sha256: str | None = None) -> bool:
    """追加一条事件。失败吞掉（观测绝不阻断业务）。"""
    try:
        if event_type not in EVENT_TYPES:
            logger.warning("EVENT_LOG_INVALID_TYPE: %s (dropped)", event_type)
            return False
        if actor not in ACTORS:
            actor = "system"
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event_id": uuid.uuid4().hex[:16],
            "event_type": event_type,
            "actor": actor,
            "task_id": task_id,
            "gate_id": gate_id,
            "detail": detail or {},
            "state_sha256": state_sha256 or _state_fingerprint(root),
        }
        path = events_file(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        return True
    except Exception as exc:  # noqa: BLE001 — 观测失败绝不阻断业务
        logger.warning("EVENT_LOG_WRITE_FAILED (business continues): %s", exc)
        return False


def read_events(root: Path, tail: int | None = None) -> list[dict]:
    """回放事件序列（按写入序）。损坏行跳过并计数。"""
    path = events_file(root)
    events: list[dict] = []
    corrupt = 0
    if not path.is_file():
        return events
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except Exception:  # noqa: BLE001 — 单行损坏不阻断回放
            corrupt += 1
    if tail is not None and tail > 0:
        events = events[-tail:]
    return events


def _state_fingerprint(root: Path) -> str:
    """投影指纹：state.yaml + gates.yaml + task_graph.yaml 合并哈希（锚点）。"""
    h = hashlib.sha256()
    for rel in (".ai/state.yaml", ".ai/gates.yaml", ".ai/task_graph.yaml"):
        p = root / rel
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()[:16]


def replay_check(root: Path) -> tuple[bool, str]:
    """投影=事件回放一致性：最新事件的 state_sha256 应与当前投影一致。

    近似校验（事件链锚点法）：若事件链非空，最后一条事件的 state_sha256
    必须等于当前投影指纹；不一致说明状态在事件记录后被外部修改（漂移）。
    """
    events = read_events(root)
    if not events:
        return True, "no events (empty chain)"
    latest = events[-1]
    anchor = latest.get("state_sha256", "")
    current = _state_fingerprint(root)
    if anchor and anchor != current:
        return False, (
            f"projection drifted from event chain: anchor={anchor} current={current}"
        )
    return True, f"replay consistent ({len(events)} events)"


def main() -> int:
    parser = argparse.ArgumentParser(description="T-0155 event log (shadow layer)")
    parser.add_argument("root")
    sub = parser.add_subparsers(dest="command", required=True)

    p_app = sub.add_parser("append")
    p_app.add_argument("--type", required=True, choices=sorted(EVENT_TYPES))
    p_app.add_argument("--task", default=None)
    p_app.add_argument("--gate", default=None)
    p_app.add_argument("--actor", default="system", choices=sorted(ACTORS))
    p_app.add_argument("--detail", default=None, help="JSON string")

    p_read = sub.add_parser("read")
    p_read.add_argument("--tail", type=int, default=None)

    sub.add_parser("replay-check")

    args = parser.parse_args()
    root = Path(args.root).resolve()
    if args.command == "append":
        detail = json.loads(args.detail) if args.detail else None
        ok = append(root, args.type, task_id=args.task, gate_id=args.gate,
                    actor=args.actor, detail=detail)
        print(f"[event-log] appended {args.type}: {'ok' if ok else 'failed (swallowed)'}")
        return 0 if ok else 2
    if args.command == "read":
        for ev in read_events(root, tail=args.tail):
            print(json.dumps(ev, ensure_ascii=False))
        return 0
    if args.command == "replay-check":
        ok, msg = replay_check(root)
        print(f"[event-log] replay-check: {'PASS' if ok else 'FAIL'} — {msg}")
        return 0 if ok else 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
