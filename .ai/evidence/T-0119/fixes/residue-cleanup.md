# T-0119 修复记录：residue-cleanup

## 背景

T-0113 P3-5 + developer 遗留事项 5：安全扫描排除表与注释中的已删工具路径残留。
T-0117 已顺带完成 SCANNER_SELF_FILES 2 条清除（T-0113 P3-5 主体）；本任务完成
剩余残留清理 + 全仓 grep 复核 + hooks 死注释。

## 修改清单

| 文件 | 修改 |
|------|------|
| `hooks/scripts/loop_enforcement_constants.py` | L33-34 死注释清除（tool_evidence_chain.py/tool_cost_tracker.py 已删，改为注明 T-0119 清除记录）——注释级，零逻辑变化 |
| `tests/test_t0109_f5_tool_capability.py` | `test_hooks_zero_changes` 预期适配（T-0119 用户 gate 批准 hooks 注释级例外：断言改为"hooks diff 为空或仅 loop_enforcement_constants.py 且新增行为注释/空行"） |

## 全仓 grep 复核结果（已删 14 工具路径）

| 类别 | 命中 | 处置 |
|------|------|------|
| 活动代码区（loop_core/hooks/tools/agents/tests/scripts/src/docs） | 4 处（全为历史说明注释：evidence_chain.py 收敛史、loop_enforcement_constants.py T-0119 注释、run_security_scan.py T-0117 注释、deep_probe_v35.py 删除史） | 保留（说明性注释，非引用） |
| 治理登记（state.yaml/gates.yaml/task_graph.yaml 历史任务/gate 定义） | 若干（T-0113/T-0114 任务描述、历史 gate scope） | 保留（审计轨迹，不可改写） |
| 历史证据（.ai/evidence/） | 若干（T-0025/S6/T-0082 commands、security_audit.json） | 保留（历史证据不可变） |

**结论：无活动代码引用残留；SCANNER_SELF_FILES 终态 2 条现存文件。**

## 验证

- 全量回归 4207 passed / 1 failed（仅 manifest 在途态，closeout 自愈）
- f5 29 passed（白名单状态断言新预期）；t0108 34 passed
- hooks diff 仅 loop_enforcement_constants.py 注释级（新测试断言锁定）
