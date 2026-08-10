#!/usr/bin/env python3
"""register_t0169_71.py — 登记 T-0169/T-0170/T-0171 gates + state + task_graph"""
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\ZCodeProject\loop-engine")
GATES = ROOT / ".ai/gates.yaml"
STATE = ROOT / ".ai/state.yaml"
GRAPH = ROOT / ".ai/task_graph.yaml"

GATE_TMPL = """- id: {gate}
  task_id: {task}
  gate_type: user-approval
  status: approved
  execution_status: in_progress
  decision: approved
  requested_at: '2026-08-10T15:00:00+08:00'
  requested_by: ai
  approval_required_from: user
  recorded_at: '2026-08-10T15:00:00+08:00'
  approval_actor: user
  approval_source: explicit_user_message
  approval_text: 排布下，只要是要做的就都要走（批准 {task}）
  approval_evidence: .ai/evidence/{task}/approval-evidence.json
  execution_evidence: .ai/evidence/{task}/execution-evidence.json
  scope: >-
    {scope}
  allowed_paths:
  - {paths}
  forbidden_actions:
  - modify loop-engine zcode 分支产品代码（loop_core/hooks/agents 任何文件，T-0170 仅限 .zcode/tools 新增）
  - deploy / rollback / database / permission / secret / payment / production
    data / migration / real business project entry
  high_risk_flags:
    deployment: false
    rollback: false
    database: false
    permission: false
    secret: false
    payment: false
    production_data: false
    migration: false
    runtime_behavior: false
  exit_criteria:
  - AC-01~AC-06 全部达成
  - 独立审查 P0/P1 = 0
  notes:
  - 用户指令（2026-08-10）：三项后续方向全部执行
"""

TASKS = [
    ("T-0169", "G-T-0169-REQUIREMENTS",
     "Qoder 接线：loop hooks + MCP 注册进 Qoder 真实配置（保留 clawd-on-desk），验证写入拦截/上下文注入/MCP 工具生效。",
     "C:\\\\Users\\\\Administrator\\\\AppData\\\\Roaming\\\\QoderCN\\\\User\\\\settings.json 等（见任务卡）"),
    ("T-0170", "G-T-0170-REQUIREMENTS",
     "Python Parity：OQA-5D 语义对齐 ZCode 侧（.zcode/tools/output_quality.py + validate_state --oqa + 测试）。",
     ".zcode/tools/output_quality.py 等（见任务卡）"),
    ("T-0171", "G-T-0171-REQUIREMENTS",
     "语义级验证扩展：AI-03 AC 实现真实性检查器 + AI 偷懒模式库（.ai/oqa-patterns.yaml + loop_oqa_patterns MCP 工具）。",
     ".qoder-cn 引擎/工具/标准 + .ai/oqa-patterns.yaml（见任务卡）"),
]

def main() -> int:
    # gates
    g = GATES.read_text(encoding="utf-8")
    for task, gate, scope, paths in TASKS:
        if gate in g:
            print(f"[same] {gate} already registered")
            continue
        block = GATE_TMPL.format(gate=gate, task=task, scope=scope, paths=paths)
        g = g.replace("delegations:", block + "delegations:", 1)
        print(f"[gate] {gate} registered")
    GATES.write_text(g, encoding="utf-8")

    # evidence dirs
    for task, _, _, _ in TASKS:
        d = ROOT / ".ai/evidence" / task
        d.mkdir(parents=True, exist_ok=True)
        (d / "approval-evidence.json").write_text(
            '{\n  "gate_id": "PLACEHOLDER",\n  "status": "approved",\n  "approved_at": "2026-08-10T15:00:00+08:00",\n  "approval_actor": "user",\n  "approval_source": "explicit_user_message",\n  "approval_text": "排布下，只要是要做的就都要走"\n}\n',
            encoding="utf-8")
    print("[evidence] dirs + approval placeholders created")

    # state
    s = STATE.read_text(encoding="utf-8")
    new_state = """current_phase: S6-delivery
current_task_id: T-0169
current_gate_id: G-T-0169-REQUIREMENTS
loop_mode: FULL
last_handoff_at: '2026-08-10T15:00:00+08:00'
notes:
- 'T-0169~T-0171 ACTIVE 2026-08-10: 用户指令批（三项后续全部执行）— T-0169 Qoder 接线 / T-0170 Python Parity / T-0171 语义级验证扩展；按序执行，每任务独立审查。'"""
    import re
    s = re.sub(r"current_phase: S6-delivery\ncurrent_task_id: T-\d+\ncurrent_gate_id: G-T-\d+-REQUIREMENTS\nloop_mode: FULL\nlast_handoff_at: '[^']*'\nnotes:\n", new_state + "\n", s, count=1)
    STATE.write_text(s, encoding="utf-8")
    print("[state] current_task -> T-0169")

    # task_graph
    gr = GRAPH.read_text(encoding="utf-8")
    anchor_node = """    gates:
      - G-T-0168-REQUIREMENTS"""
    for task, title in [("T-0169", "Qoder 接线：loop hooks + MCP 注册进 Qoder 真实配置"), ("T-0170", "Python Parity：OQA-5D 语义对齐 ZCode 侧"), ("T-0171", "语义级验证扩展：AC 实现真实性 + AI 偷懒模式库")]:
        if f"id: {task}" in gr:
            continue
        node = f"""
  -
    id: {task}
    title: {title}
    phase: S6-delivery
    status: in_progress
    description: >-
      用户指令批（三项后续全部执行）。
    depends_on:
      - T-0168
    gates:
      - G-{task}-REQUIREMENTS"""
        # 在 T-0168 节点之后插入
        marker = "    gates:\n      - G-T-0168-REQUIREMENTS"
        gr = gr.replace(marker, marker + node, 1)
    # 边
    if "- from: T-0168\n      to: T-0169" not in gr:
        gr = gr.replace("    - from: T-0167\n      to: T-0168",
                        "    - from: T-0167\n      to: T-0168\n    - from: T-0168\n      to: T-0169\n    - from: T-0168\n      to: T-0170\n    - from: T-0168\n      to: T-0171")
    GRAPH.write_text(gr, encoding="utf-8")
    print("[task_graph] T-0169/70/71 nodes + edges")

    print("\n[ok] registration complete")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
