# ZCode Agent 递归能力 Live-Fire 探针结果

2026-07-27

## 探针方法

从主会话启动 `general-purpose` 子代理，要求其：
1. 列举可用工具
2. 检查 Agent 工具可用性
3. 尝试创建子代理
4. 读取治理状态文件

## 结果

```json
{
  "agent_tool_available": false,
  "recursive_launch_tested": false,
  "recursive_launch_result": "NOT_TESTED",
  "available_tools": [
    "AskUserQuestion", "Bash", "Edit", "Read", "Skill", "TaskStop",
    "TodoRead", "TodoWrite", "WebFetch", "Write", "RespondToCoordinator",
    "ReadSessionContext", "mcp__node_repl__js",
    "mcp__node_repl__js_add_node_module_dir", "mcp__node_repl__js_reset"
  ]
}
```

## 结论

- ZCode 子代理 **不具有** `Agent` 工具
- 子代理 **无法** 递归创建子代理
- `Skill` 工具在子代理中**可用**（支持 Loop 角色 Skill 加载）
- `RespondToCoordinator` 存在，表明宿主支持协调器模式
- 当前架构：宿主 → Agent（一层），不可递归

## 对 Loop 设计的影响

1. **主会话** 是唯一的 Agent 调度入口
2. 阶段 main-thread Agent 通过 Skill 工具加载角色能力，但**不能**独立创建角色 Agent
3. 角色 Agent 的调度需要主会话显式调用 Agent 工具
4. 受限委派模型（`DelegationRequest`）的设计前提是正确的：保守假设递归不可用，fail-closed

## 后续

若 ZCode 未来版本为子代理开放 Agent 工具，需通过独立的 capability gate 重新评估并更新：
- `AgentCapabilityProbe` 状态从 `NOT_VERIFIED` 更新为 `VERIFIED`
- 委派深度限制验证
- 治理通道全链路测试
