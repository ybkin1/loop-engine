# T-0052 全面治理修复证据

日期：2026-07-27

## 执行摘要

T-0052 全面修复完成。所有 HANDOFF 中记录的残余问题已修复，63 个 legacy lab 回归全部通过，0 个测试失败。

## 修复内容

### 1. 主控 Read 拦截 (`hooks/hooks.json` + `loop_enforcement.py`)

- `hooks/hooks.json` PreToolUse matcher 从 `Write|Edit|Bash|ApplyPatch|Agent` 扩展为 `Read|Write|Edit|Bash|ApplyPatch|Agent`
- `loop_enforcement.py` 新增：
  - `MINIMAL_METADATA_READ` 列表定义可读取的治理元数据路径
  - `is_minimal_metadata_read()` 判定函数
  - 无 `current_task_id` 时 Read 工具只允许 `.ai/*`、`AGENTS.md`、`.zcode/*` 等治理元数据；项目源代码读取被阻断

### 2. 只读 Bash 探索阻断 (`loop_enforcement.py`)

- Bash readonly 检查从早期无任务 ID 直接放行，改为在加载 state 后执行
- 无 `current_task_id` 时：只读 Bash 命令（find/grep/git status/ls 等）被阻断
- 有 `current_task_id` 时：只读 Bash 命令保持放行（向后兼容）

### 3. Bootstrap/Proposal 入口保护 (`loop_enforcement.py`)

- Agent/Skill/Task 编排工具豁免移至 `task_id` 检查之前
- 无任务时可正常调用 Bootstrap、Work Package Proposal
- 子代理的每次文件写入仍被独立拦截

### 4. GOVERNANCE_RECOVERY 通道 (`loop_enforcement.py`)

- 新增 `GOVERNANCE_RECOVERY` recovery_mode
- 只能写治理骨架（.ai/、.zcode/tools/），不能写业务代码
- Runtime Controller 损坏时，recovery_mode 允许绕过来自 controller 的 caller_class 检查
- 所有恢复操作通过日志记录审计

### 5. 新旧治理模型统一 (`loop_enforcement.py`)

- Runtime-managed 项目（有 `.ai/runtime/runtime-state.json`）走 controller 授权
- 未 Bootstrap 项目走 legacy 分支
- Read/Bash/Agent/MCP/Executor 入口授权语义一致

### 6. EnforcementHub 用户 Gate 接入 (`enforcement_hub.py`)

- 新增 `_has_approved_user_gate()` 方法
- `check_phase_advance()` 接入 `phase_needs_user_gate()` 判定
- S1/S6 要求显式用户 gate 审批；S2-S5/S7-S11 不要求用户 gate
- `check_phase_constraints()` 增加 `user_gate_approved` 参数

### 7. Legacy lab 合同修复

- `continuity_producer.py` + `continuity_auditor.py`：语义哈希同时接受 modern（不含 lifecycle）和 legacy（完整 payload）两种格式
- `continuity_producer.py` `render_handoff()`：补全审计要求的 9 个必备标题
- `validate_state.py`：`[legacy]` 错误从静默丢弃改为打印警告
- `test_validate_state_inventories_non_current_historical_mismatch`：更新期望匹配 T-0046 设计（历史不匹配为非阻断警告）
- `test_readonly_bash_passes_even_without_task`：重写为 `_blocked_without_task` + `_allowed_with_active_task` 两条测试

### 8. 受限 Agent 委派合同 (`agent_adapter.py`)

- `DelegationRequest`：父执行、深度、工具、路径范围、预算验证
- 默认只读、单层、不可继续委派
- 拒绝 developer 派生 reviewer
- `AgentCapabilityProbe` + `probe_agent_capability()`：保守能力探针

### 9. 用户 Gate 阶段标记 (`state_machine.py`)

- `USER_GATE_PHASES = {S1_REQUIREMENTS, S6_DELIVERY}`
- `phase_needs_user_gate()`

## 测试结果

### 全量测试

```text
2397 passed
61 skipped
16 xfailed
1 xpassed
0 failed
13 warnings
```

### 编译检查

```text
python -m compileall -q loop_core hooks tests
→ 通过
```

### 状态校验

```text
python .zcode/tools/validate_state.py .
→ state is usable
```

### 针对性测试（Hook + StateMachine + Controller）

```text
123 passed (agent_adapter + state_machine + runtime_controller)
172 passed (enforcement + bash_readonly + hook_integration + cross_layer_safety)
```

## 已知残余风险

1. 真实 ZCode Host live-fire 仍未执行；递归 Agent 能力保持 `NOT_VERIFIED`
2. CONTEXT_CONTROLLER_STALE 警告表明部分任务文件状态与 task_graph 不一致（legacy 历史问题）
3. Checkpoint 状态为 `NOT_ESTABLISHED`（`TRANSACTION_REGISTRY_MISSING`）
4. 16 个历史任务文件缺少 status 字段
5. 历史任务 T-0002/T-0004/T-0005/T-0007/T-0009/T-0041 的 task 文件与 task_graph 状态不一致

以上均为 [legacy] 警告，不阻断当前工作。
