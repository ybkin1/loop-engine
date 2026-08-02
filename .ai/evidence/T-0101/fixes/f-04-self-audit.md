# F-04 — loop_self_audit rc 判定对齐（0/2 → 0/2/3）+ 文档同步 — AC-05

## 改动

### `tools/loop_self_audit.py`（L310-314 区域）

- validate_state rc 判定 `(0, 2)` → `(0, 2, 3)`：
  - 0 = state usable（正常）；
  - 2 = 真实治理损坏（fail-closed 阻断，审计层面属"工具按预期返回"）；
  - 3 = idle 合法阻塞态（NO_ACTIVE_TASK：current_task_id=null，等待任务发起，
    T-0101 分流）；
  - 三者均为合法结果（非工具自身失败），视为审计 OK；其余 rc 视为失败。
- 注释同步更新为 0/2/3 三态语义说明。

### `.ai/HANDOFF-NEXT.md`（文档同步，2 处）

- L69-72 区域：NO_ACTIVE_TASK 语义描述更新 —— 独立 exit code 3（不再与治理
  损坏共用 exit 2）；rc=3 为合法 idle 阻塞态（非损坏、非成功）；rc=2 才表示
  真实治理损坏（fail-closed 阻断）；新会话须继续处理 NO_ACTIVE_TASK 基线状态。
- L440-445 区域：预期输出示例更新为 `[info] NO_ACTIVE_TASK: ...（合法阻塞态：
  等待任务发起；state 不可开工）` + "退出码 3（idle 合法阻塞态，与治理损坏
  exit 2 分流；不输出 usable）"；"这不是成功状态、也不是损坏"。

> 说明：docs/ 下未发现其他 NO_ACTIVE_TASK 语义描述（grep 无命中），无需改动。

## 三处约定对齐（AC-05）

| 消费端 | 判定 | 语义 |
|--------|------|------|
| validate_state / audit_handoff | rc 0 / 2 / 3 | usable / 损坏（fail-closed）/ idle 合法阻塞态 |
| release.py check step_validate_state | rc 0/3 → PASS，rc 2 → FAIL | idle 稳态 6/6 可达 |
| loop_self_audit | rc ∈ {0,2,3} → 审计 OK | 工具按预期返回 |

## 复验证据

- `tests/test_idle_semantics.py` 5 passed（rc 0/2/3 输出与退出码断言）；
- `tests/test_release.py` rc=3/rc=2 分支测试 7 passed；
- idle worktree 端到端：validate_state rc=3 + release check 6/6 PASS + consistency
  22 passed（三处约定在 idle 稳态下一致生效）。
