# F-03 — test_governance_consistency idle 适配 + 新增 idle/损坏态回归测试 — AC-04

## 改动

### `tests/test_governance_consistency.py`

5 个 idle 失败测试（T-0046 时代断言）改造为 repo/idle 双场景参数化，
消除 `None in str` TypeError：

- `test_current_task_in_graph` / `test_current_task_file_exists` /
  `test_current_gate_in_register` / `test_handoff_current_task_matches_state` /
  `test_handoff_current_gate_matches_state`：`@pytest.mark.parametrize("scenario",
  ["repo", "idle"])`。
  - **repo 场景**：读真实 `.ai/` 文件，按实际状态分支——current_task_id 非空 →
    原激活态断言（原样保留）；为 None → idle 契约断言；
  - **idle 场景**：合成 idle fixture（state=null/null；task_graph/gates 有注册项；
    HANDOFF 当前任务段 = "none"、当前 gate 段 = "none"）→ 始终走 idle 分支，
    与仓库实际状态无关。
- idle 契约断言：
  - task_graph 无"当前任务"引用（`current not in task_ids`，None 不触发 TypeError）；
  - 无当前任务即无任务文件要求（不构造 `None.md` 路径）；
  - gate register 无"当前 gate"（`current_gate not in gate_ids`）；
  - HANDOFF null ↔ null 匹配：`## Current Task` 段无 `T-\d+` 引用、
    `## Current Gate` 段无 `G-\d+` 引用（显式规避 `None in handoff`）。
- 辅助：`_read/_load_yaml` 增加 `base` 参数；新增 `_section()`、`_build_idle_fixture()`。
- `test_current_gate_task_matches` / `test_current_gate_is_approved` 增加
  current_gate 为 None 时的 idle 早退（原断言逻辑对激活态不变）。

### `tests/test_idle_semantics.py`（新增）

见 f-01-exit-code.md（idle exit 3 / 损坏 exit 2 / idle+blocker exit 2，共 5 项，
fixture 与 continuity schema 对齐 continuity_producer/continuity_auditor 独立校验）。

### `tests/test_release.py`

见 f-02-release-check.md（rc=3 → PASS 分支 + check rc=3 整体 PASS，共 2 项）。

## 复验证据

- 主树（T-0101 激活态）：`pytest tests/test_governance_consistency.py
  tests/test_idle_semantics.py -q` → **22 passed**（repo 激活分支 + idle fixture
  分支全覆盖，激活态原 5 断言仍通过）；
- **idle worktree**（ecac6a3 提交，current_task_id=null）：同命令 → **22 passed**
  （repo idle 分支 + idle fixture 分支；idle 稳态 0 failed，无 TypeError）；
- `pytest tests/test_release.py -k "validate_state or rc3 or check_validate" -q`
  → **7 passed**。
