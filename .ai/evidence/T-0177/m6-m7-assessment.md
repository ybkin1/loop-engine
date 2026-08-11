# M6/M7 评估留档（T-0177 / AC-P2-4）

> 结论：两项均**留档不修复**，理由如下（评审发现为低风险设计权衡，非直接
> 绕过；完全修复需宿主级身份验证，超出本任务范围）。

## M6: loop_approve_and_execute 的 user_actor_id 默认 "user"

**位置**：`loop_core/runtime_controller.py:198-245`（approve_and_execute，
`user_actor_id: str = "user"`）；入口 `tools/server.py` 的 MCP 工具
loop_approve_and_execute。

**评审主张**：攻击者可伪造用户批准（传 user_actor_id="user"）。

**评估**：
1. **双层防线兜底**：runtime 层 approve 只更新 controller snapshot 并签发
   execution capability，**不写 gates.yaml**。治理层的 pending gate 仍由
   gate_guard 按 gates.yaml 状态阻断写入（fail-closed）。伪造 runtime
   批准无法消除 pending gate 阻断。
2. **实际风险是审计完整性问题**："approved_by: user" 无法区分真实用户与
   AI 传参，审计追溯性弱。
3. **完全修复的成本**：需要宿主级不可伪造身份（hook 上下文的
   actor_id/caller_class 注入验证，评审 M5 同源）。M5 已在评审中单独列出，
   属于"MCP Server 调用者身份验证"架构项——与本项同根。立项修复将触及
   server.py 调用链 + 身份注入协议，超出 T-0177 范围。

**决定**：留档。观察项：MCP 调用者身份验证（M5）作为独立架构项登记
backlog，与本项一并解决。

## M7: GOVERNANCE_RECOVERY 允许修改 loop_mode FULL → LIGHTWEIGHT

**位置**：`hooks/scripts/loop_enforcement.py:820-825`（recovery_mode 输入 →
仅允许 governance 路径写入）。

**评审主张**：GOVERNANCE_RECOVERY 模式允许降级 loop_mode。

**评估**：
1. **recovery 是设计意图**：T-0058/T-0059 引入 recovery 模式用于修复治理
   状态死锁（hook 误伤时自救）。state.yaml 属于 decision_recording_exempt
   治理路径，recovery 写它符合设计。
2. **作用域受限**：recovery_mode 只放行 `is_governance_write(rel)`（.ai/、
   AGENTS.md 等治理路径），业务代码写入仍被拦截。降级 loop_mode 属于
   "修改治理配置"，是 recovery 语义的一部分，不是绕过业务保护。
3. **审计链完整**：状态变更全部落入 state-events.jsonl（T-0155 事件溯源），
   降级动作可追溯。
4. **真正的改进**：recovery 触发应记录更明确的 reason（谁/何时/为什么），
   属增强项。

**决定**：留档。观察项：recovery 触发原因记录增强，登记 backlog。

## 关联

- 评审 M5（MCP 调用者身份验证）与本档 M6 同根，backlog 合并登记。
- 本档写入 `KNOWN_ISSUES` 或 backlog register 的迁移由 P3 文档同步处理。
