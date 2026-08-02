# F-02 — release.py check 感知合法阻塞态（step_validate_state rc=3 → PASS）— AC-03

## 改动

### `scripts/release.py`

- `step_validate_state`（L283-313 区域）新增 rc=3 分支：
  - `proc.returncode == 3` → **PASS**，输出标注
    "validate_state.py 通过（rc=3：idle 合法阻塞态，current_task_id=null，
    无活动任务，等待任务发起；非治理损坏）" + 校验器输出尾部摘要；
  - `returncode == 0` → PASS（原样）；`returncode != 0`（含 2=真实损坏）→
    FAIL（fail-closed 原样）；超时/缺失/无法启动 → FAIL（原样）。
- docstring 与模块头部 `check` 说明补充：check 支持 idle 稳态运行
  （validate_state rc=3 视为合法阻塞态，不阻断）。

## 测试（tests/test_release.py 新增 2 项）

- `test_validate_state_rc3_idle_passes`：mock subprocess returncode=3 →
  `ok is True` 且消息含 "rc=3" + "idle 合法阻塞态"；
- `test_check_validate_state_rc3_passes`：全部 6 步骤 mock 为 PASS（validate_state
  步骤返回 rc=3 语义）→ `cmd_check == 0`（idle 稳态下 check 整体 PASS，6/6 可达）。
- 既有 `test_validate_state_nonzero_blocks`（rc=2 → FAIL）不变，语义保持。

## 复验证据

- 主树：`pytest tests/test_release.py -k "validate_state or rc3 or check_validate" -q`
  → **7 passed**（含既有 rc=0/rc=2/超时/缺失阻断测试）。
- **idle worktree 端到端**：`python scripts/release.py check`（idle 稳态，修复后
  工具）→ **6/6 PASS、exit 0**，validate_state 步骤明确标注"idle 合法阻塞态"。
  修复前同一 worktree：validate_state rc=2 → check 阻断（validate_state 步骤
  FAIL）。idle 稳态 6/6 在提交后由主会话做最终复验。
