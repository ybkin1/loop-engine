# ZCode Loop 三层代理模型实现方案分析

2026-07-27

## 一、ZCode 当前能力边界（Live-Fire 确认）

```json
主会话可用: Agent, Skill, Read, Write, Edit, Bash, WebFetch, ...
子代理可用: Read, Write, Edit, Bash, Skill, WebFetch, RespondToCoordinator, ...
子代理没有: Agent ← 不能递归
```

**结论：ZCode 不支持代理递归。** 只有主会话能创建 Agent。

## 二、可实施方案：宿主编排模式（Host-Orchestrated）

ZCode 已经具备了实现 Loop 三层模型所需的所有基础设施，只是架构需要从"代理递归"调整为"宿主编排"：

```
┌──────────────────────────────────────────────────┐
│              用户主会话（唯一调度入口）              │
│                                                    │
│  1. Agent("main-thread", "生成阶段编排计划")        │
│     └→ main-thread 产出 SubagentManifest           │
│                                                    │
│  2. 主会话读取 manifest，按批次并行调用 Agent()     │
│     ├→ Agent("developer", manifest.subagents[0])   │
│     ├→ Agent("system-architect", manifest... [1])  │
│     └→ ... (并行批次，max_parallel=5)               │
│                                                    │
│  3. Agent("main-thread", "聚合角色产出")            │
│     └→ main-thread 产出 gate 呈现包                 │
│                                                    │
│  4. 主会话呈现 gate → 等待用户决策                  │
└──────────────────────────────────────────────────┘
```

### 已就绪的组件

| 组件 | 状态 | 说明 |
|------|------|------|
| `subagent_manifest.py` | ✅ 已实现 | 描述子代理规格、批次、聚合提示词 |
| `agent_adapter.py` | ✅ 已实现 | prepare_launch/collect_result 三步工作流 |
| `execution_ledger.py` | ✅ 已实现 | 链式哈希追加写执行账本 |
| `DelegationRequest` | ✅ 已实现 | 委派深度/范围/预算合同 |
| `Agent` 工具（主会话） | ✅ 可用 | `agent_8ef16bad-...` 已证实可创建子代理 |
| `RespondToCoordinator` | ✅ 子代理可用 | 支持结构化结果返回 |

### 缺失组件（仅 1 个）

**`LoopDispatcher`** — 主会话端的调度器。

功能：读取 `SubagentManifest` → 按批次调用 `Agent` 工具 → 收集结果 → 交给 main-thread 聚合。

这可以在 Loop Core 中实现为一个纯 Python 模块，或作为 ZCode Skill 暴露给主会话。

### 伪代码

```python
# loop_core/dispatcher.py
class LoopDispatcher:
    def execute_manifest(self, manifest: SubagentManifest, adapter: AgentAdapter):
        results = []
        for batch in manifest.parallel_batches():
            batch_results = []
            for spec in batch:
                agent_input = adapter.prepare_launch(AgentInput(
                    role_id=spec.subagent_id.split(":")[-1],
                    task_id=manifest.task_id,
                    prompt=spec.prompt,
                    ...
                ))
                # 主会话调用 Agent 工具（这是唯一需要宿主支持的地方）
                raw = Agent(description=spec.subagent_id, prompt=agent_input.prompt)
                output = adapter.collect_result(agent_input, raw)
                batch_results.append(output)
            results.extend(batch_results)
        return adapter.aggregate(manifest, results)
```

### 与递归模型的对比

| 维度 | 递归代理 | 宿主编排（推荐） |
|------|---------|----------------|
| ZCode 支持 | ❌ 子代理无 Agent | ✅ 主会话有 Agent |
| 审计 | 分散在各级代理 | 集中在主会话 ledger |
| 中断 | 需逐层传播 | 用户一键中断 |
| 并行 | 代理内并发 | 主会话统一调度 |
| 死锁风险 | 子代理卡住父代理等 | 主会话超时可控 |
| 安全 | 需逐层验证 | 单点验证 |

## 三、推荐路径

**立即可行（无需等 ZCode 更新）：**

1. 实现 `LoopDispatcher` 模块
2. 修改 `main-thread/SKILL.md`：将"main-thread 拉起角色 Agent"改为"main-thread 生成 SubagentManifest → 交由主会话执行"
3. 更新 `agent_adapter.py` 文档：标注 `launch_agent()` 为"宿主编排模式未实现，当前通过 prepare_launch+Agent工具+collect_result 三步走"

**如果 ZCode 未来开放子代理 Agent 工具：**

4. `AgentCapabilityProbe` 状态从 `NOT_VERIFIED` → `VERIFIED`
5. `launch_agent()` 从桩变为真实实现
6. 无需改架构——两种模式可共存
