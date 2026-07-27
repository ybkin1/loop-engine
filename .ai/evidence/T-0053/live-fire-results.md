# T-0053 Live-Fire Test: 两层模型端到端验证

2026-07-27

## 测试场景

S2-architecture 阶段，两层模型：ZCode 会话调度 → main-thread（军师）+ boundary-analyzer（角色 Agent）。

## 测试步骤和结果

### Step 1: 生成执行计划 ✅
`python tools/loop_execute_phase.py S2-architecture --task-id T-LIVEFIRE`
→ 产出 1 batch, 1 agent (system-architect), 完整 prompt 带 INPUT_HASH

### Step 2: main-thread 产出 SubagentManifest ✅
`Agent("main-thread", "生成 S2 编排计划")`
→ 产出完整 SubagentManifest:
  - 2 个 sub-agents: boundary-analyzer, loop-architect
  - 每个有详细 prompt + input_files + expected_output_schema
  - aggregation_prompt 完整
  - input_fingerprint 有效
  - validate() 通过

### Step 3: Dispatcher 验证 ✅
`LoopDispatcher.prepare(manifest, adapter)`
→ 1 batch, 2 parallel steps, session_id + actor_id 已生成

### Step 4: 角色 Agent 真实执行 ✅
`Agent("boundary-analyzer", manifest.subagents[0].prompt)`
→ 成功执行，产出结构化 JSON 分析报告
→ 发现了 6 个真实架构问题（见下方）

## 角色 Agent 发现的架构问题

| 严重度 | 问题 |
|--------|------|
| **CRITICAL** | `loop_core/agent_adapter.py` 包含完整的 `ZCodeAgentAdapter` 实体类——违反了 loop_core 宿主无关原则 |
| **CRITICAL** | `tools/loop_execute_phase.py` 直接 import `ZCodeAgentAdapter`——固化了 ZCode 依赖 |
| HIGH | `context_controller.py` 硬编码 `.zcode/*` 路径 |
| HIGH | `hard_constraints.py` 硬编码 `.zcode/*` 路径 |
| MEDIUM | 两个抽象接口并存：`HostAdapter` vs `AgentAdapter` |
| MEDIUM | hooks/tools 直接 import loop_core 内部模块而非通过 HostAdapter |

**Boundary Score: 3/10** —— 诚实地说，loop_core 的宿主独立性目前只是纸面原则，代码没有遵守。

## 残余风险评估

### 已验证（低风险）
- ✅ 两层模型端到端可跑：会话 → main-thread（出计划）→ 角色 Agent（执行）→ 产出有效
- ✅ SubagentManifest 生成、验证、dispatch 全链路正常
- ✅ INPUT_HASH 机制在真实 Agent 调用中可用（子代理报告中包含哈希）
- ✅ 角色 Agent 可以读取项目文件、产出结构化 JSON

### 未验证（高风险）
- ⚠️ 并行 Agent 调度未测试（只调了一个）
- ⚠️ main-thread 汇总步骤未测试（需要两个 Agent 都跑完）
- ⚠️ Agent 超时/失败重试未测试
- ⚠️ 文件冲突未测试
- ⚠️ 大规模上下文膨胀未测试（boundary-analyzer 单次消耗 229K tokens）

### 已知架构债（本次发现）
- 🔴 loop_core 代码不遵守自己的宿主无关原则——需要后续 gate 修复

## 结论

两层模型**已证明可跑**。从"设计"到"真实跑通"的跨越已完成。残余风险主要是：并行调度、异常恢复、架构债清理——这些需要独立 gate。
