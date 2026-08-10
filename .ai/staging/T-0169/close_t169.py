#!/usr/bin/env python3
"""close_t169.py — T-0169 收口：gates/state/task_graph + 启动 T-0170"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\ZCodeProject\loop-engine")

def main() -> int:
    g = (ROOT / ".ai/gates.yaml").read_text(encoding="utf-8")
    old = "- id: G-T-0169-REQUIREMENTS\n  task_id: T-0169\n  gate_type: user-approval\n  status: approved\n  execution_status: in_progress"
    new = "- id: G-T-0169-REQUIREMENTS\n  task_id: T-0169\n  gate_type: user-approval\n  status: approved\n  execution_status: completed"
    assert g.count(old) == 1, f"gates anchor={g.count(old)}"
    g = g.replace(old, new)
    (ROOT / ".ai/gates.yaml").write_text(g, encoding="utf-8")
    print("[gates] G-T-0169 -> completed")

    tg = (ROOT / ".ai/task_graph.yaml").read_text(encoding="utf-8")
    old_t = "    id: T-0169\n    title: Qoder 接线：loop hooks + MCP 注册进 Qoder 真实配置\n    phase: S6-delivery\n    status: in_progress"
    new_t = "    id: T-0169\n    title: Qoder 接线：loop hooks + MCP 注册进 Qoder 真实配置\n    phase: S6-delivery\n    status: completed"
    assert tg.count(old_t) == 1, f"task_graph anchor={tg.count(old_t)}"
    tg = tg.replace(old_t, new_t)
    (ROOT / ".ai/task_graph.yaml").write_text(tg, encoding="utf-8")
    print("[task_graph] T-0169 -> completed")

    s = (ROOT / ".ai/state.yaml").read_text(encoding="utf-8")
    s = re.sub(r"current_task_id: T-\d+\ncurrent_gate_id: G-T-\d+-REQUIREMENTS",
               "current_task_id: T-0170\ncurrent_gate_id: G-T-0170-REQUIREMENTS", s, count=1)
    s = s.replace("notes:\n- 'T-0169~T-0171 ACTIVE",
                  "notes:\n- 'T-0169 COMPLETED 2026-08-10: Qoder 接线收口 — 三轮审查修复后 PASS（P0=0,P1=0）；gates 119/tasks 150/3 场景阻断/37 tools；clawd 保留。'\n- 'T-0169~T-0171 ACTIVE")
    (ROOT / ".ai/state.yaml").write_text(s, encoding="utf-8")
    print("[state] -> T-0170")

    r = subprocess.run([r"C:\Python312\python.exe", r".ai\checkers\compile_gate.py", ".", "--output", r".ai\evidence\T-0170\compile-evidence.json"],
                       capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
    print("[compile] T-0170:", "ok" if r.returncode == 0 else r.stdout[:100])

    (ROOT / ".ai/evidence/T-0170").mkdir(parents=True, exist_ok=True)
    (ROOT / ".ai/evidence/T-0170/approval-evidence.json").write_text(json.dumps({
        "gate_id": "G-T-0170-REQUIREMENTS", "task_id": "T-0170", "status": "approved",
        "approved_at": "2026-08-10T15:00:00+08:00", "approval_actor": "user",
        "approval_source": "explicit_user_message", "approval_text": "排布下，只要是要做的就都要走（批准 T-0170 Python Parity）",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[evidence] T-0170 approval written")

    r2 = subprocess.run([r"C:\Python312\python.exe", r".zcode\tools\validate_state.py", ".", "--auto-sync"],
                        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
    out = r2.stdout.strip() or r2.stderr.strip()
    print("[validate]", out.splitlines()[-1] if out else "no output")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
