# T-0078 Handoff Control Plane Status

## 结论

**BLOCKED_UNTIL_HOST_BRIDGE_AND_USER_GATE**

本状态是只读审查当前工作树与已有 T-0078 Phase 2 证据后的交接摘要。不得将本摘要解释为 PASS、完成交付、宿主接管或自动 Agent 执行证明。

## 已修复：主会话 fail-closed 门禁

当前 `FULL` 模式且存在 `current_task_id` 时，主会话业务工具 `Read`、`Edit`、`Write`、`Bash`、`ApplyPatch` 在 runtime projection 缺失或损坏时会阻断，并记录 `SETUP_INCOMPLETE` 与 `DISPATCH_REQUIRED`。runtime projection 存在但缺少 caller identity 时也会阻断。Agent/Skill/Task 的无目标编排调用可被记录为 `DISPATCH_REQUIRED`，但不构成执行接管证据；治理元数据读取保持允许。

工作树中对应实现位于 `hooks/scripts/loop_enforcement.py`。当前存在一个明确限定到旧 `tests/test_enforcement.py::` subprocess fixture 的兼容路径；该路径不是对未标记真实宿主的信任放行。已有 Phase 2 证据还记录了 dispatch runtime contract schema 的 fail-closed 语义：缺失或非 `PASS` 的 receipt 不能声称 takeover。

## 测试结果

已有证据记录：

- `python -m pytest -q tests/test_runtime_delivery_gate.py`：修复后先记录 `6 passed`，随后加入 contract/schema 覆盖后记录 `15 passed`。
- `python -m pytest -q tests/test_enforcement.py`：`20 passed`。
- 相关测试合并运行在兼容修复后：`29 passed`。
- 未运行全量 pytest。

按当前工作树重新执行用户要求的相关测试命令：

```text
python -m pytest -q tests/test_runtime_delivery_gate.py tests/test_enforcement.py tests/test_hook_integration.py tests/test_hooks.py tests/test_runtime_controller.py
```

结果为 **84 passed, 2 failed**，不能声称 PASS。两个失败均在 `tests/test_hook_integration.py`：旧集成 fixture 期望在缺少 runtime projection 时允许写入，但当前 fail-closed 门禁按设计阻断并输出：

```text
BLOCKED: SETUP_INCOMPLETE: runtime projection missing; DISPATCH_REQUIRED for active task T-0001
```

失败项为：

- `LoopEnforcementHardConstraintsIntegration.test_allows_valid_write_with_active_task_and_scope`
- `GracefulDegradationTest.test_loop_enforcement_fallback_works`

`tests/test_runtime_controller.py` 当前 6 项通过，但这不等于真实宿主 bridge 或 takeover 已接入。

## validate_state 结果

当前执行：

```text
C:/Python312/python.exe .zcode/tools/validate_state.py C:/Users/Administrator/ZCodeProject/loop-engine
```

结果：`[ok] state is usable`，并有 6 条标记为 `[legacy]` 的历史任务状态不一致警告，0 条 blocking error：T-0003、T-0006、T-0067、T-0070、T-0071、T-0075。该结果只说明治理状态可用，不是运行时交付或宿主接管的 PASS。

已有 `compile-evidence.json` 记录的是治理/配置/测试类改动的 compile gate 不适用，`status: pass`；它不覆盖本交接所需的宿主 bridge、自动 Agent 启动或真实 takeover。

## 当前不能声称的内容

以下内容当前均没有足够证据，不能声称已实现、已接入、已验证或已通过：

1. 自动 Agent 启动。
2. 真实宿主接管（包括有效 dispatch receipt、child session 与 takeover 证明）。
3. `harness-agentic` 已接入当前 gate 或已纳入本次测试覆盖。
4. 端到端真实宿主运行已通过。
5. 本任务或相关测试整体 PASS。

已有证据明确指出 ZCode adapter / 宿主 bridge 尚未提供；`HostAgentInvoker` 仍未集成，且当前 T-0078 允许路径不包含宿主/adapter/runtime_controller 文件。Agent/Skill/Task 编排放行仅表示编排调用没有被该门禁误判为业务执行，不是自动执行或接管证明。

## 必须单独 gate 的剩余改动

以下每一项都必须在独立、明确的用户 gate 下完成并留下可核验的证据，不能借用本次 Phase 2 门禁、相关单元测试或 `validate_state` 结果替代：

- `runtime_controller`：完成并验证真实 runtime 状态/dispatch 生命周期及其边界。
- `zcode_adapter`：实现并验证 ZCode 到宿主/运行时的适配与身份传递。
- hooks 宿主 bridge：接入真实宿主调用链、caller identity、dispatch receipt 与阻断/放行闭环。
- `harness-agentic`：单独完成接入、配置、测试与 gate 证据，不得将当前编排允许或 schema 存在解释为已接入。

在上述宿主 bridge 与用户 gate 完成前，控制面交接保持：**BLOCKED_UNTIL_HOST_BRIDGE_AND_USER_GATE**。

## 证据索引

- 当前 Phase 2 证据：`.ai/evidence/T-0078/phase2-runtime-gate-evidence.md`
- 当前测试命令记录：`.ai/evidence/T-0078/commands.md`
- 当前状态校验记录：`.ai/evidence/T-0078/phase2-runtime-gate-evidence.md`
- 当前 compile 记录：`.ai/evidence/T-0078/compile-evidence.json`
- 当前门禁实现：`hooks/scripts/loop_enforcement.py`
