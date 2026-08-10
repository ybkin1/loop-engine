#!/usr/bin/env python3
"""verify_gate_scope.py — AC-03b 真实 gate 场景：任务范围内写入放行 / 范围外阻断 / pending 阻断"""
import json
import subprocess
import tempfile
import os
import shutil
from pathlib import Path

SCRIPTS = Path(r"C:\Users\Administrator\.qoder-cn\hooks\scripts")
ROOT = r"C:\Users\Administrator\ZCodeProject\loop-engine"

def run_guard(event: dict) -> tuple[int, str]:
    proc = subprocess.run(
        ["node", str(SCRIPTS / "gate-guard.js")],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    return proc.returncode, proc.stderr

def main() -> int:
    ok = True

    # 场景 A/B：真实任务范围验证（临时项目含 active_task_id + allowed_paths）
    # 构造：state 含 active_task_id、任务卡含 allowed_paths，避免依赖未装/无 active 跳过
    tmp = tempfile.mkdtemp(prefix="gate-scope2-")
    os.makedirs(os.path.join(tmp, ".ai/tasks"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "src"), exist_ok=True)
    os.makedirs(os.path.join(tmp, ".venv"), exist_ok=True)  # 避免依赖未装阻断干扰
    with open(os.path.join(tmp, ".ai/state.yaml"), "w", encoding="utf-8") as f:
        f.write("schema_version: 1\ncurrent_task_id: T-9\nactive_task_id: T-9\ncurrent_phase: S4-implementation\n")
    with open(os.path.join(tmp, ".ai/gates.yaml"), "w", encoding="utf-8") as f:
        f.write("schema_version: 1\ngates:\n- id: G-T-9-REQUIREMENTS\n  task_id: T-9\n  phase: S4-implementation\n  status: approved\n")
    with open(os.path.join(tmp, ".ai/tasks/T-9.md"), "w", encoding="utf-8") as f:
        f.write("---\ntask_id: T-9\nallowed_paths:\n  - src/\n---\n# T-9\n")
    # gate-guard 从 task_graph.yaml 读 activeTask（含 allowed_paths）
    with open(os.path.join(tmp, ".ai/task_graph.yaml"), "w", encoding="utf-8") as f:
        f.write("schema_version: 1\ntasks:\n  -\n    id: T-9\n    status: in_progress\n    allowed_paths:\n      - src/\n")
    tmpcwd = tmp.replace("\\", "/")

    # 场景 A：allowed_paths 内写入（src/）→ 放行 exit 0
    evt_in = {
        "tool_name": "Write",
        "tool_input": {"file_path": tmpcwd + "/src/ok.ts", "content": "export const s = 1;"},
        "cwd": tmpcwd,
    }
    rc_in, err_in = run_guard(evt_in)
    print(f"[A] write INSIDE task allowed_paths (src/): exit={rc_in} (expect 0)")
    print(f"   stderr: {err_in[:160] if err_in.strip() else '(empty)'}")
    ok = ok and rc_in == 0

    # 场景 B：allowed_paths 外写入（docs/ 不在 T-9 allowed_paths）→ 阻断 exit 2
    os.makedirs(os.path.join(tmp, "docs"), exist_ok=True)
    evt_out = {
        "tool_name": "Write",
        "tool_input": {"file_path": tmpcwd + "/docs/out.md", "content": "# out"},
        "cwd": tmpcwd,
    }
    rc_out, err_out = run_guard(evt_out)
    print(f"[B] write OUTSIDE task allowed_paths (docs/): exit={rc_out} (expect 2 = allowed_paths block)")
    print(f"   stderr: {err_out[:200] if err_out.strip() else '(empty)'}")
    ok = ok and rc_out == 2

    # 场景 C：pending gate 阶段阻断（临时项目）
    tmp2 = tempfile.mkdtemp(prefix="gate-scope3-")
    os.makedirs(os.path.join(tmp2, ".ai/tasks"), exist_ok=True)
    with open(os.path.join(tmp2, ".ai/state.yaml"), "w", encoding="utf-8") as f:
        f.write("schema_version: 1\ncurrent_task_id: T-1\nactive_task_id: T-1\ncurrent_phase: S4-implementation\n")
    with open(os.path.join(tmp2, ".ai/gates.yaml"), "w", encoding="utf-8") as f:
        f.write("schema_version: 1\ngates:\n- id: G-T-1-REQUIREMENTS\n  task_id: T-1\n  phase: S4-implementation\n  status: pending\n")
    with open(os.path.join(tmp2, ".ai/tasks/T-1.md"), "w", encoding="utf-8") as f:
        f.write("---\ntask_id: T-1\nallowed_paths:\n  - src/\n---\n# T-1\n")
    evt_pending = {
        "tool_name": "Write",
        "tool_input": {"file_path": tmp2.replace("\\", "/") + "/src/x.ts", "content": "export const x = 1;"},
        "cwd": tmp2.replace("\\", "/"),
    }
    rc_pend, err_pend = run_guard(evt_pending)
    print(f"[C] pending gate + phase path write (temp project): exit={rc_pend} (expect 2 = gate pending block)")
    print(f"   stderr: {err_pend[:200] if err_pend.strip() else '(empty)'}")
    ok = ok and rc_pend == 2
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(tmp2, ignore_errors=True)

    print(f"\n[{'PASS' if ok else 'FAIL'}] AC-03b real gate-scope verification (allowed_paths + pending)")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
