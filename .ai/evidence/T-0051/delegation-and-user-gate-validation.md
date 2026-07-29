# T-0051 子代理委派与用户 Gate 验证

日期：2026-07-27

## 实现结果

- `loop_core/state_machine.py` 新增 `USER_GATE_PHASES` 与 `phase_needs_user_gate()`。
- S1-requirements、S6-delivery 被明确标记为用户决策阶段；S2-S5、S7-S11 不要求用户 gate。
- `check_phase_constraints()` 增加可选 `user_gate_approved` 参数；显式传入 `False` 时，S1/S6 fail-closed，内部阶段不受该参数阻断。
- `loop_core/agent_adapter.py` 新增受限 `DelegationRequest` 和 `AgentCapabilityProbe`。
- 默认委派为只读、单层、无继续委派权限；拒绝无上下文、非法深度、预算、developer 派生 reviewer 等路径。
- 能力探针保守返回 `CAPABILITY_UNAVAILABLE` 或 `NOT_VERIFIED`，不会伪造 ZCode 递归能力。

## 验证结果

### 针对性测试

命令：

```text
C:/Python312/python.exe -m pytest tests/test_agent_adapter.py tests/test_state_machine_enhanced.py tests/test_runtime_controller.py -q
```

结果：`123 passed, 2 warnings`。

### 编译检查

命令：

```text
C:/Python312/python.exe -m compileall -q loop_core tests
```

结果：通过。

### 状态校验

命令：

```text
C:/Python312/python.exe .zcode/tools/validate_state.py .
```

结果：state usable；current task T-0051；无 pending gate。

### 全量测试

命令：

```text
C:/Python312/python.exe -m pytest -q
```

结果：`2333 passed, 61 skipped, 16 xfailed, 1 xpassed, 63 failed`。

63 个失败集中在既有 `tests/lab/test_project_governor_consistency.py`，与本次新增状态机/委派针对性测试不重合，主要涉及历史 continuity fixture、旧治理合同和 lab fixture。该结果不能标记为全量通过。

## ZCode 子代理递归能力结论

当前仓库代码不能证明 ZCode 子智能体可以递归调用 `Agent`：

- `ZCodeAgentAdapter.launch_agent()` 仍是不可用桩；实际调用依赖宿主 Agent 工具。
- UI 中存在内置 general-purpose/Explore 配置，只能证明宿主存在子智能体配置，不能证明子会话拥有 Agent 工具或允许递归。
- 未执行真实宿主递归 live-fire；因此 `recursive_launch` 与 `governed_recursive_launch` 保持 `None`。

## 残余风险

1. 本次用户 gate 判定已在核心 `state_machine` 提供，但由于 T-0051 的 approved_paths 不包含 `loop_core/enforcement_hub.py`，未修改 EnforcementHub 接入层；调用方必须显式传递 `user_gate_approved` 才能启用新判定。
2. `DelegationRequest` 是能力合同和负面校验，不是实际宿主调度器；不能据此宣称递归委派已可用。
3. 能力探针目前是非侵入式保守探针，尚未完成真实 ZCode Host 的父→child 只读 live-fire。
4. 全量 lab 回归仍有 63 个历史失败，不能将当前仓库描述为全绿。
5. 未开放任意递归；默认单层、只读、最小范围是有意的安全边界。
