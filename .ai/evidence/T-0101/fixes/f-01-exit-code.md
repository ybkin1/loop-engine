# F-01 — exit code 分流：NO_ACTIVE_TASK（idle）exit 3 vs 治理损坏 exit 2 — AC-01/AC-02

## 根因

validate_state / audit_handoff 的 NO_ACTIVE_TASK 与真实治理损坏共用 exit 2 +
`[error]` 级输出（v2.0.0 起），消费端无法区分"合法 idle 阻塞"与"治理损坏"：
release check 在 idle 稳态必然 FAIL（6/6 不可达）、loop_self_audit 与
release check 判定约定分裂。v2.0.0 计划要求的分流从未实现。

## 改动

### `.zcode/tools/validate_state.py`（main() 报告段，L425-445 区域）

- 判定 `idle_legal_block`：`task_id is None`（current_task_id=null）**且**
  blocker 错误**恰好只有** `"NO_ACTIVE_TASK: state.current_task_id is null"`
  一条（去重后）→ 打印独立 `[info]` 输出段（标注"合法阻塞态：state 无活动
  任务，等待任务发起；state 不可开工"）并 `return 3`；
- idle 合法态**不打印** `[error] NO_ACTIVE_TASK`、**不输出** `[ok] state is usable`
  （v2.0.0 安全意图保留：新会话不得误以为可开工）；
- 存在其他 blocker（连续性漂移/缺文件/损坏/待决 gate）→ 保持逐条 `[error]`
  输出 + `return 2`（fail-closed 语义不变；此时 NO_ACTIVE_TASK 错误行可保留）；
- 无 blocker → `[ok] state is usable` + `return 0`（原样）。

### `.zcode/tools/audit_handoff.py`（main() 报告段）

- 同语义分流：`current_task_id(root) is None` 且 blocker 恰好只有
  NO_ACTIVE_TASK 一条 → 独立 `[info]` 段 + `return 3`；否则 `[error]` + `return 2`。
- 新增 `from governor_lib import current_task_id`。

### `.zcode/tools/continuity_auditor.py` — **零改动**

`audit_handoff_model`（L147-224）保持返回 `"NO_ACTIVE_TASK: state.current_task_id
is null"` 字符串不变；分流逻辑全部放在调用方（validate_state / audit_handoff
的 main）。

## 测试

`tests/test_idle_semantics.py`（新增，5 项）：
- `test_validate_state_idle_exit_3`：idle fixture → rc=3、`[info] NO_ACTIVE_TASK`
  独立段、无 `[ok] state is usable`、无 `[error]`；
- `test_audit_handoff_idle_exit_3`：同语义 rc=3、无 `[ok] handoff audit passed`；
- `test_validate_state_corruption_exit_2`：project_continuity `semantic_sha256`
  篡改 → `[error] ProjectContinuity ...` + rc=2（AC-02）；
- `test_audit_handoff_corruption_exit_2`：同损坏 → rc=2；
- `test_validate_state_idle_with_other_blocker_exit_2`：idle + 待决 gate →
  rc=2，`[error] NO_ACTIVE_TASK` 行保留、无 usable（fail-closed 不被分流吞掉）。

fixture 构造：最小完整治理根（16 个必需文件 + state idle + 有效
project_continuity.yaml（与 continuity_producer/continuity_auditor 同 schema，
source_manifest 指向真实文件）+ HANDOFF.md（13 个必需 heading + 4 个结构化
JSON 块））。

## 复验证据

- 主树（T-0101 激活态）定向测试：`tests/test_idle_semantics.py` 5 passed。
- **idle worktree 实测对照**（git worktree add @ ecac6a3，修复 continuity 后）：
  - 旧工具：`[error] NO_ACTIVE_TASK: state.current_task_id is null` → **rc=2**
  - 新工具：`[info] NO_ACTIVE_TASK: state.current_task_id is null（合法阻塞态：...）`
    → **rc=3**，无 usable、无 error；audit_handoff 同 → rc=3
- **损坏态实测**（真实发生）：主树修改 `.ai/HANDOFF-NEXT.md`（任务文档同步）后，
  validate_state 如实拦截 `Continuity source drift: .ai/HANDOFF-NEXT.md` → rc=2
  （fail-closed 生效，恢复路径见下）。
- **恢复路径实证**（worktree）：`repair_continuity.py .`（就地重算 1 个漂移
  哈希）+ `close_session.py .`（重生成 HANDOFF.md 内嵌哈希）→ validate_state
  回到干净 idle rc=3。主会话在 T-0101 完成流程中按此恢复主树连续性。
