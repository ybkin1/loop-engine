# Main-Thread Internal Loop

## 循环节奏

每轮对话执行以下循环：

1. **读取状态** бк 检查 state.yaml、HANDOFF.md、pending gates
2. **判断意图** бк 用户请求属于 L1(只读)/L2(可回滚修改)/L3(不可逆)?
3. **调度角色** бк 按 phase+b 需要激活对应角色 Agent
4. **收集证据** бк 角色产出 бк .ai/evidence/<task-id>/
5. **推进 gate** бк 条件满足 бк advance gate бк 下一阶段
6. **同步状态** бк 更新 state.yaml、task_graph.yaml、HANDOFF.md

## Gate 推进条件检查

每个 gate 推进前必须验证：
- 所有 required_roles 已提交 verdict
- 所有 evidence 存在且 hash 匹配
- 无 BLOCKED gate 或 task
- review packet 已生成

## 角色隔离规则

- developer 和 reviewer 必须使用不同 agent session
- self-review бк immediate BLOCK
- 治理文件修改(.ai/) 在 pending gate 期间只有 gate_guard 豁免路径可写