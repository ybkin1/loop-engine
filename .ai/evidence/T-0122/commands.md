# T-0122 commands

## 执行命令记录

```bash
# 1. 执行中核实（范围调整：实施包 → 核实关闭包）
grep -n "memory_gate_id\|memory_tag" loop_core/context_packager.py   # B-4-1 已透传过滤
grep -n "_validated_phases" loop_core/role_orchestrator.py           # B-4-2 已校验回退
grep -n "_CONFIG_CACHE" loop_core/role_orchestrator.py               # B-4-4 已缓存（mtime）
grep -n "Completion Flow Conventions" .ai/CONTRACTS.md               # B-4-3 已文档化
#    → 4 项全部已由 T-0105 批 2 实施（test_t0105_batch2.py 21 测试）

# 2. 核实测试
C:/Python312/python.exe -m pytest tests/test_t0105_batch2.py -q     # 21 passed

# 3. 登记修正
#    KNOWN_ISSUES：T-0104 P3 建议类 → 已实施说明（T-0116 重复登记修正）
#    T-0116 fixes 补充重复登记说明

# 4. 全量回归 + compile + bump
C:/Python312/python.exe -m pytest tests/ -q
C:/Python312/python.exe .ai/checkers/compile_gate.py . --output .ai/evidence/T-0122/compile-evidence.json
C:/Python312/python.exe scripts/release.py bump --to 3.12.57 --title "T-0122: T-0104 P3 核实关闭（已由 T-0105 实施，登记修正）"
```

## 范围调整说明

原任务卡为"3 项实施 + 1 项登记"；执行中核实 B-4-1~4 已全部落地 →
调整为核实关闭（零产品代码改动），任务卡/AC 已同步更新。

## 遗留观察

- `test_manifest_t0095`：active 在途态，closeout 自愈。
- `test_release version_sync`：HEAD 3.12.56 vs 载体 3.12.57，提交后自愈（F-03）。

## 审查 closeout 补记（CONDITIONAL_GO 条件 2）

- 全量回归 3 项在途失败（审查时点）：
  1. `test_manifest_t0095`：active 在途态（HANDOFF 引用 T-0122 manifest 未生成），closeout 自愈
  2. `test_release version_sync`：HEAD 3.12.56 vs 载体 3.12.57，F-03 提交后自愈
  3. `test_t0108_fixes ×2`：bump 后 version-manifest 连续性漂移 → `validate_state --repair` + HANDOFF 重生成 → t0108 34 passed（T-0121 同款模式）
