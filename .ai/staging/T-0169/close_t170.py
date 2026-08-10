#!/usr/bin/env python3
"""close_t170.py — T-0170 收口 + 启动 T-0171"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\ZCodeProject\loop-engine")

def main() -> int:
    # 清理 T-0170.md 残留尾节
    p = ROOT / ".ai/tasks/T-0170.md"
    t = p.read_text(encoding="utf-8")
    idx = t.find("\n## Status")
    if idx > 0:
        t = t[:idx] + "\n"
        p.write_text(t, encoding="utf-8")
        print("[task] T-0170.md tail cleaned")

    # gates G-T-0170 -> completed（宽松匹配）
    g = (ROOT / ".ai/gates.yaml").read_text(encoding="utf-8")
    import re as _re
    g2 = _re.sub(r"(- id: G-T-0170-REQUIREMENTS\n  task_id: T-0170\n  gate_type: user-approval\n  status: approved\n  execution_status: )in_progress",
                 r"\1completed", g, count=1)
    assert g2 != g, "G-T-0170 anchor not found"
    (ROOT / ".ai/gates.yaml").write_text(g2, encoding="utf-8")
    print("[gates] G-T-0170 -> completed")

    # task_graph T-0170 -> completed
    tg = (ROOT / ".ai/task_graph.yaml").read_text(encoding="utf-8")
    old_t = "    id: T-0170\n    title: Python Parity：OQA-5D 语义对齐 ZCode 侧\n    phase: S6-delivery\n    status: in_progress"
    new_t = "    id: T-0170\n    title: Python Parity：OQA-5D 语义对齐 ZCode 侧\n    phase: S6-delivery\n    status: completed"
    assert tg.count(old_t) == 1, f"task_graph anchor={tg.count(old_t)}"
    tg = tg.replace(old_t, new_t)
    (ROOT / ".ai/task_graph.yaml").write_text(tg, encoding="utf-8")
    print("[task_graph] T-0170 -> completed")

    # state -> T-0171
    s = (ROOT / ".ai/state.yaml").read_text(encoding="utf-8")
    s = re.sub(r"current_task_id: T-\d+\ncurrent_gate_id: G-T-\d+-REQUIREMENTS",
               "current_task_id: T-0171\ncurrent_gate_id: G-T-0171-REQUIREMENTS", s, count=1)
    marker = "notes:\n- 'T-0169 COMPLETED"
    add = "notes:\n- 'T-0170 COMPLETED 2026-08-10: Python Parity 落地 — 五维 12 检查器 + CLI + 22/22 测试；与 TS 语义对齐。'\n- 'T-0169 COMPLETED"
    if "T-0170 COMPLETED" not in s:
        assert s.count(marker) == 1, "state notes marker"
        s = s.replace(marker, add, 1)
    (ROOT / ".ai/state.yaml").write_text(s, encoding="utf-8")
    print("[state] -> T-0171")

    # T-0171 evidence
    (ROOT / ".ai/evidence/T-0171").mkdir(parents=True, exist_ok=True)
    (ROOT / ".ai/evidence/T-0171/approval-evidence.json").write_text(json.dumps({
        "gate_id": "G-T-0171-REQUIREMENTS", "task_id": "T-0171", "status": "approved",
        "approved_at": "2026-08-10T15:00:00+08:00", "approval_actor": "user",
        "approval_source": "explicit_user_message",
        "approval_text": "排布下，只要是要做的就都要走（批准 T-0171）",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[evidence] T-0171 approval written")

    r = subprocess.run([r"C:\Python312\python.exe", r".ai\checkers\compile_gate.py", ".", "--output", r".ai\evidence\T-0171\compile-evidence.json"],
                       capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
    print("[compile] T-0171:", "ok" if r.returncode == 0 else r.stdout[:80])

    r2 = subprocess.run([r"C:\Python312\python.exe", r".zcode\tools\validate_state.py", ".", "--auto-sync"],
                        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
    out = r2.stdout.strip() or r2.stderr.strip()
    print("[validate]", out.splitlines()[-1] if out else "no output")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
