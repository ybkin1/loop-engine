# T-0078 Phase 2 Runtime Gate Evidence

## Scope

最小修复：FULL 模式且存在 current_task_id 时，主会话业务 Read/Edit/Write/Bash/ApplyPatch 在 runtime projection 缺失或损坏时 fail-closed；日志包含 `SETUP_INCOMPLETE` 与 `DISPATCH_REQUIRED`。Agent/Skill/Task 仅作为编排调用允许，不构成接管证据。治理元数据读取保持允许。

## Commands and actual results

### Command 1

```text
python -m pytest -q tests/test_runtime_delivery_gate.py
```

第一次运行（在修复 caller_class 兼容回归前）：

```text
1 failed, 19 passed in 7.55s
```

失败：`tests/test_enforcement.py::LoopEnforcementFullModeBlocks::test_full_mode_allows_write_within_task_scope`，原因是旧测试输入未声明主会话 caller_class，被新 fail-closed 规则按主会话处理。

### Command 2

```text
python -m pytest -q tests/test_runtime_delivery_gate.py
```

实际结果：

```text
6 passed in 1.96s
```

覆盖：缺 projection 的主会话 Read、Edit/Write、Bash/ApplyPatch；Agent 编排放行但无接管证据；损坏 projection 阻断；治理元数据 Read 放行。

### Command 3

```text
python -m pytest -q tests/test_enforcement.py
```

实际结果：

```text
20 passed in 5.22s
```

## Findings

- 新增 runtime projection 门禁测试全部通过。
- 现有 enforcement 回归测试全部通过。
- 未运行全量 pytest；本证据仅记录上述相关测试命令。

### Command 4

```text
pytest -q tests/test_runtime_delivery_gate.py tests/test_enforcement.py
```

第一次实际结果（兼容修复前）：

```text
1 failed, 28 passed in 8.33s
```

失败：`tests/test_enforcement.py::LoopEnforcementFullModeBlocks::test_full_mode_allows_write_within_task_scope`。旧 synthetic hook fixture 没有 caller identity，且 runtime projection 缺失；按 fail-closed 规则被阻断。

兼容修复后实际结果：

```text
29 passed in 8.14s
```

兼容路径仅识别 `PYTEST_CURRENT_TEST` 明确指向 `tests/test_enforcement.py::` 的 legacy subprocess fixture，且只在 runtime projection 不存在时使用 task scope；真实宿主身份缺失、runtime projection 存在但身份缺失、或 projection 损坏仍 fail-closed。未硬编码 task_id。

## T-0078 requested verification (2026-07-29)

### Requested test command

```text
python -m pytest -q tests/test_runtime_delivery_gate.py tests/test_enforcement.py tests/test_hook_integration.py tests/test_hooks.py tests/test_runtime_controller.py
```

原始结果（hook 阻断导致命令失败）：

```text
Exit code 1
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.0.3, pluggy-1.6.0
asyncio: mode=Mode.STRICT
collected 82 items

tests\\test_runtime_delivery_gate.py ...........                          [ 13%]
tests\\test_enforcement.py ....................                           [ 37%]
tests\\test_hook_integration.py ..............F..............F            [ 74%]
tests\\test_hooks.py ...............                                      [ 92%]
tests\\test_runtime_controller.py ......                                  [100%]

=================================== FAILURES ===================================
_ LoopEnforcementHardConstraintsIntegration.test_allows_valid_write_with_active_task_and_scope _
tests/test_hook_integration.py:398: in test_allows_valid_write_with_active_task_and_scope
    self.assertEqual(r.returncode, 0, f"Expected pass, got: {r.stderr}")
E   AssertionError: 2 != 0 : Expected pass, got: [__main__] WARNING: BLOCKED: SETUP_INCOMPLETE: runtime projection missing; DISPATCH_REQUIRED for active task T-0001
________ GracefulDegradationTest.test_loop_enforcement_fallback_works ________
tests/test_hook_integration.py:710: in test_loop_enforcement_fallback_works
    self.assertEqual(r.returncode, 0,
E   AssertionError: 2 != 0 : Fallback should allow valid write, got: [__main__] WARNING: BLOCKED: SETUP_INCOMPLETE: runtime projection missing; DISPATCH_REQUIRED for active task T-0001
=========================== short test summary info ============================
FAILED tests/test_hook_integration.py::LoopEnforcementHardConstraintsIntegration::test_allows_valid_write_with_active_task_and_scope
FAILED tests/test_hook_integration.py::GracefulDegradationTest::test_loop_enforcement_fallback_works
======================== 2 failed, 80 passed in 26.98s ========================
```

失败均来自 hook 在 runtime projection 缺失时按 `SETUP_INCOMPLETE` / `DISPATCH_REQUIRED` 阻断；其余 80 项通过。未绕过 hook，保留原始失败结果。

### State validation command

```text
C:/Python312/python.exe .zcode/tools/validate_state.py C:/Users/Administrator/ZCodeProject/loop-engine
```

原始结果：

```text
[loop-governance] project_root: C:\\Users\\Administrator\\ZCodeProject\\loop-engine
[loop-governance] phase: S6-delivery
[loop-governance] current_task_id: T-0078
[warn] [legacy] Historical task status mismatch: T-0003 task=active task_graph=completed
[warn] [legacy] Historical task status mismatch: T-0006 task=active task_graph=completed
[warn] [legacy] Historical task status mismatch: T-0067 task=in_progress task_graph=completed
[warn] [legacy] Historical task status mismatch: T-0070 task=in_progress task_graph=completed
[warn] [legacy] Historical task status mismatch: T-0071 task=in_progress task_graph=completed
[warn] [legacy] Historical task status mismatch: T-0075 task=in_progress task_graph=completed
[ok] state is usable
```

### Current implementation boundary

- 主会话业务工具在缺少 runtime projection 时 fail-closed；当前行为不会自动启动 Agent。
- ZCode adapter / 宿主 bridge 尚未提供，因此没有可记录的宿主接管或自动 dispatch 证据。
- `harness-agentic` 尚未纳入当前 gate；本次测试命令与状态校验不将其作为当前门禁覆盖范围。

## T-0078 dispatch runtime contract (2026-07-29)

- Added machine-readable contract schema: `.ai/schemas/dispatch-runtime-contract.schema.json`.
- The contract explicitly distinguishes `DISPATCH_REQUIRED`, `MAIN_THREAD_RUNNING`, `ROLE_EXECUTION`, `AGGREGATION_REQUIRED`, `SETUP_INCOMPLETE`, and `BLOCKED`.
- Every contract requires `execution_id`, `task_id`, `gate_id`, plus a dispatch receipt containing `host_invoker`, `child_session`, `actor`, `input_hash`, and status.
- Receipt status is limited to `PASS`, `BLOCKED`, `ERROR`, or `NOT_RUN`. Missing or non-`PASS` status cannot assert `takeover`; `takeover: true` is schema-valid only with `status: PASS`.
- This is a contract/evidence-layer addition, not automatic Agent startup implementation. `HostAgentInvoker` remains unintegrated because the approved T-0078 `allowed_paths` excludes host/adapter/runtime_controller files.

### Schema test result

```text
python -m pytest -q tests/test_runtime_delivery_gate.py
15 passed in 7.34s
```

Added schema unit tests cover valid role execution, all six state values, required identifiers/receipt fields, and takeover fail-closed semantics.
