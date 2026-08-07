#!/usr/bin/env python3
"""
rounds_heartbeat.py — T-0129 E4 心跳悬空检测（最小落地；完整心跳随 T-0134）。

检测 .ai/evidence/<task>/rounds/*.jsonl 中是否存在悬空轮次（末行状态非终态：
CHECKING / FOUND / FIXING 而未闭合到 PASS / ESCALATE / NEXT）。

自治执行的心跳语义（D-03 §3）：每 checkpoint 检查 rounds 闭合 + 状态校验，
任一失败 → fail-stop（暂停当前动作），恢复后从 checkpoint 续跑。
本工具为其中"rounds 闭合"检测的最小实现。

用法：
    python rounds_heartbeat.py <project_root> [--task <task_id>]

退出码：
    0  全部闭合（或无可检 rounds）
    2  存在悬空轮次（fail-closed：自治执行应暂停）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

TERMINAL_STATES = {"PASS", "ESCALATE", "NEXT", "ABORTED"}
# 悬空：末行状态处于进行中（动作未闭合）
NON_TERMINAL_STATES = {"CHECKING", "FOUND", "FIXING", "RE-CHECK", "PENDING"}


def dangling_rounds(root: Path, task_id: str | None = None) -> list[dict]:
    """返回悬空轮次列表 [{task, round_file, last_state, last_ts}]。"""
    rounds_root = root / ".ai" / "evidence"
    if task_id:
        candidates = [rounds_root / task_id / "rounds"]
    else:
        candidates = sorted((rounds_root / t / "rounds") for t in
                            (rounds_root.iterdir() if rounds_root.is_dir() else []))
    dangling: list[dict] = []
    for rdir in candidates:
        if not rdir.is_dir():
            continue
        for rf in sorted(rdir.glob("*.jsonl")):
            lines = [l for l in rf.read_text(encoding="utf-8").splitlines() if l.strip()]
            if not lines:
                continue
            try:
                last = json.loads(lines[-1])
            except json.JSONDecodeError:
                dangling.append({"task": rdir.parent.name, "round_file": str(rf),
                                 "last_state": "UNPARSEABLE", "last_ts": ""})
                continue
            state = str(last.get("state", ""))
            if state in NON_TERMINAL_STATES:
                dangling.append({"task": rdir.parent.name, "round_file": str(rf),
                                 "last_state": state, "last_ts": str(last.get("ts", ""))})
    return dangling


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    root = Path(sys.argv[1]).resolve()
    task_id = None
    if "--task" in sys.argv:
        task_id = sys.argv[sys.argv.index("--task") + 1]
    dangling = dangling_rounds(root, task_id)
    if dangling:
        for d in dangling:
            print(f"[heartbeat] DANGLING round: {d['round_file']} state={d['last_state']} "
                  f"(task {d['task']})")
        print("[heartbeat] FAIL — 悬空轮次存在，自治执行应 fail-stop")
        return 2
    print("[heartbeat] PASS — 全部 rounds 闭合")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
