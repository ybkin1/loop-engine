#!/usr/bin/env python3
"""close_t171.py — T-0171 收口 + 三任务全部完成"""
import re
import subprocess
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\ZCodeProject\loop-engine")

def main() -> int:
    g = (ROOT / ".ai/gates.yaml").read_text(encoding="utf-8")
    g2 = re.sub(r"(- id: G-T-0171-REQUIREMENTS\n  task_id: T-0171\n  gate_type: user-approval\n  status: approved\n  execution_status: )in_progress",
                r"\1completed", g, count=1)
    assert g2 != g, "G-T-0171 gates anchor"
    (ROOT / ".ai/gates.yaml").write_text(g2, encoding="utf-8")
    print("[gates] G-T-0171 -> completed")

    tg = (ROOT / ".ai/task_graph.yaml").read_text(encoding="utf-8")
    old_t = "    id: T-0171\n    title: 语义级验证扩展：AC 实现真实性 + AI 偷懒模式库\n    phase: S6-delivery\n    status: in_progress"
    new_t = "    id: T-0171\n    title: 语义级验证扩展：AC 实现真实性 + AI 偷懒模式库\n    phase: S6-delivery\n    status: completed"
    assert tg.count(old_t) == 1, f"task_graph anchor={tg.count(old_t)}"
    tg = tg.replace(old_t, new_t)
    (ROOT / ".ai/task_graph.yaml").write_text(tg, encoding="utf-8")
    print("[task_graph] T-0171 -> completed")

    s = (ROOT / ".ai/state.yaml").read_text(encoding="utf-8")
    marker = "notes:\n- 'T-0170 COMPLETED"
    add = "notes:\n- 'T-0171 COMPLETED 2026-08-10: 语义级验证扩展收口 — AI-03 + 模式库接入引擎；两轮审查修复后 PASS（P0=0,P1=0）；634 测试全过。'\n- 'T-0170 COMPLETED"
    if "T-0171 COMPLETED" not in s:
        assert s.count(marker) == 1, "state marker"
        s = s.replace(marker, add, 1)
    (ROOT / ".ai/state.yaml").write_text(s, encoding="utf-8")
    print("[state] T-0171 completed noted")

    r2 = subprocess.run([r"C:\Python312\python.exe", r".zcode\tools\validate_state.py", ".", "--auto-sync"],
                        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
    out = r2.stdout.strip() or r2.stderr.strip()
    print("[validate]", out.splitlines()[-1] if out else "no output")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
