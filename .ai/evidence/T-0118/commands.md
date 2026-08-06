# T-0118 commands

## 执行命令记录

```bash
# 1. 现状确认（T-0109 遗留 #1）
#    subagent_evidence_verifier.py：7 布尔 checks，无 EvidenceState 消费
#    evidence_state.py：七态 + coerce + score_cap（T-0109 F1 已就绪）

# 2. 实现（loop_core/subagent_evidence_verifier.py）
#    + checks_to_evidence_state()（阶梯映射，见 fixes/seven-state-consumption.md）
#    + verify_review_evidence 4 个 return 点加 evidence_state 字段（add-only）
#    + 模块顶层 _ROOT sys.path 注入（独立脚本运行加固）

# 3. 测试
C:/Python312/python.exe -m pytest tests/test_t0118_seven_state.py -q      # 21 passed
C:/Python312/python.exe -m pytest tests/test_t0109_f1_eval_model.py -q     # coerce 消费方零变化
C:/Python312/python.exe -m pytest tests/test_ai_doc_links.py -q            # 8 passed

# 4. 全量回归 + compile + bump
C:/Python312/python.exe -m pytest tests/ -q        # 4205 passed（manifest 在途 + t0108 漂移 repair 后 34 passed）
C:/Python312/python.exe .ai/checkers/compile_gate.py . --output .ai/evidence/T-0118/compile-evidence.json
C:/Python312/python.exe scripts/release.py bump --to 3.12.54 --title "T-0118: subagent_evidence_verifier 七态映射消费"
```

## 环境适配说明

- 脚本独立运行（`python loop_core/subagent_evidence_verifier.py`）在 python312._pth
  隔离模式下需显式项目根注入；注入置于模块顶层（loop_core import 之前）。

## 遗留观察

- `test_manifest_t0095`：active 在途态，closeout 自愈。
- `test_release version_sync`：HEAD 3.12.53 vs 载体 3.12.54，提交后自愈（F-03）。
