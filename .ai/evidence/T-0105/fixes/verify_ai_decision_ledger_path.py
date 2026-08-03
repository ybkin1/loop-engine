#!/usr/bin/env python3
"""verify_ai_decision_ledger_path.py — C-2 真实 S4 路径验证（T-0105 批 4）

覆盖验证（T-0104 设计-3 §3.3.4 AiDecisionLedger 真实写入路径）：
1. 通过 AiDecisionLedger 自身 API（append 语义 + chain_hash）追加一条真实
   AI 决策记录到 .ai/ledger/ai-decisions.jsonl（不得手写文件）。
2. ledger.verify_chain() 链校验通过。
3. 以 ZCode hook 调用方式子进程运行 hooks/scripts/ledger_guard.py
   （Write 工具写 ai-decisions.jsonl）→ 期望 exit 0（append + 链校验通过）。

用法: C:/Python312/python.exe verify_ai_decision_ledger_path.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))  # 项目根

from loop_core.approval_ledger import AiDecisionLedger, AiDecisionRecord  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]
LEDGER_GUARD = ROOT / "hooks" / "scripts" / "ledger_guard.py"


def run_ledger_guard_write() -> subprocess.CompletedProcess:
    """模拟 ZCode PreToolUse(Write) 调用 ledger_guard（追加读全量内容校验）。"""
    ledger = ROOT / ".ai" / "ledger" / "ai-decisions.jsonl"
    existing = ledger.read_text(encoding="utf-8") if ledger.exists() else ""
    hook_input = json.dumps({
        "cwd": str(ROOT),
        "tool_name": "Write",
        "tool_input": {"file_path": str(ledger), "content": existing},
    })
    env = {**os.environ, "ZCODE_PROJECT_DIR": str(ROOT)}
    return subprocess.run(
        [sys.executable, str(LEDGER_GUARD)],
        input=hook_input, capture_output=True, text=True, timeout=15, env=env,
    )


def main() -> int:
    ledger = AiDecisionLedger(ROOT)
    before = len(ledger.read_all())

    record = AiDecisionRecord.create(
        task_id="T-0105",
        phase="S6-delivery",
        role_id="developer",
        decision=("[AI判断] C-1 安装副本同步采用'源最新内容合并同步'而非全量覆盖："
                  "config.yaml 保留安装副本专有的 runtime_delivery/compile_threshold/"
                  "compile_command 节，templates/SKILL 保持安装副本精简"),
        why_not_ask=("方向由任务卡与消费方证据确定（slo_gate/quality_gates 仅读安装副本，"
                     "template_injector 仅读源目录），无需要用户裁决的新分歧"),
        impact_if_wrong=("若合并遗漏安装副本专有节，则 slo_gate/runtime_delivery 读旧配置；"
                         "S5 质量门（compile/test/audit）可发现"),
        reason_ref="BATCH4-C1-SYNC-DECISION",
    )
    chain_hash = ledger.append(record)
    print(f"appended: {record.decision_id} -> chain_hash={chain_hash[:16]}...")

    valid, reason = ledger.verify_chain()
    print(f"verify_chain: valid={valid} reason={reason}")
    assert valid, "chain verification failed"

    p = run_ledger_guard_write()
    print(f"ledger_guard exit={p.returncode}")
    if p.returncode != 0:
        print("ledger_guard stderr:", p.stderr)
    assert p.returncode == 0, "ledger_guard should allow append+chain-valid write"

    entries = ledger.read_all()
    print(f"ledger entries: {before} -> {len(entries)}")
    print("last entry decision:", entries[-1]["decision"][:60], "...")
    print("OK: AiDecisionLedger real write path verified (append + chain + guard)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
