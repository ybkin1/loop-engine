# T-0119 commands

## 执行命令记录

```bash
# 1. 全仓 grep 复核（已删 14 工具路径）
grep -rn --include="*.py" -E "tool_quality_gates|tool_security_scan|..." loop_core/ hooks/ tools/ agents/ tests/ scripts/ src/ docs/
#    → 活动代码区 4 处全为历史说明注释（无引用）；治理登记/历史证据保留

# 2. hooks 死注释清理（注释级）
#    hooks/scripts/loop_enforcement_constants.py:33-34
#    tool_evidence_chain.py/tool_cost_tracker.py 死引用 → 改为 T-0119 清除记录

# 3. SCANNER_SELF_FILES 终态确认（T-0117 已清 2 条）
grep -A5 "SCANNER_SELF_FILES" agents/security-engineer/scripts/run_security_scan.py
#    → 2 条现存文件（run_security_scan.py 自身 + loop_core/security_scanner.py）

# 4. hooks 白名单状态断言适配（tests/）
#    test_hooks_zero_changes：零改动 → "仅白名单注释级改动"（T-0119 用户 gate 例外）
#    C:/Python312/python.exe -m pytest tests/test_t0109_f5_tool_capability.py -q   # 29 passed

# 5. 全量回归 + compile + bump
C:/Python312/python.exe -m pytest tests/ -q      # 4207 passed（仅 manifest 在途态）
C:/Python312/python.exe .ai/checkers/compile_gate.py . --output .ai/evidence/T-0119/compile-evidence.json
C:/Python312/python.exe scripts/release.py bump --to 3.12.55 --title "T-0119: agents 残留清理（排除表 + 死注释 + 全仓复核）"
```

## 登记口径说明

已删工具路径保留出现的三类豁免：
1. 历史说明注释（evidence_chain.py 收敛史等）——解释删除历史，非引用
2. 治理登记（state/gates/task_graph 历史任务描述）——审计轨迹不可改写
3. 历史证据（.ai/evidence/）——证据不可变

## 遗留观察

- `test_manifest_t0095`：active 在途态，closeout 自愈。
- `test_release version_sync`：HEAD 3.12.54 vs 载体 3.12.55，提交后自愈（F-03）。
