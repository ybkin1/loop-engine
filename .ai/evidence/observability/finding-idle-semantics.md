# Finding: idle 稳态语义割裂（NO_ACTIVE_TASK exit code 未分流）

- 记录时间：2026-08-02（T-0100 提交后复验发现，T-0100 验收报告留待裁决）
- 状态：CLOSED
- 关闭记录：T-0101 已完成 idle 语义修复（NO_ACTIVE_TASK exit 3 分流 + 消费端对齐，v3.12.40）
- 优先级：P2（不阻断任何已交付功能，但阻塞 idle 稳态下的发布复验与全量回归洁净度）

## 现象

任务完成后状态收敛为 idle（current_task_id=null）时：

1. `python .zcode/tools/validate_state.py .` → `[error] NO_ACTIVE_TASK` + **exit 2**（与真实治理损坏共用 exit code）
2. `scripts/release.py check` 的 validate_state 步骤（只看 exit code）→ **必然 FAIL** → "提交后 6/6 复验"在 idle 稳态不可达（T-0098/99 从未复验，T-0100 首次暴露）
3. `tests/test_governance_consistency.py` 5 个测试（T-0046 时代，v3.4.0 未改）在 idle 下失败，其中 2 个直接 TypeError（`None in str`）
4. 项目内部判定约定分裂：`loop_self_audit` 认 rc 0/2 为 OK（idle 正常），release check 认 rc≠0 为 FAIL

## 根因

- **validate_state 的 NO_ACTIVE_TASK（exit 2）本身是设计意图**：v2.0.0 计划要求 idle 返回结构化 NO_ACTIVE_TASK（不输出 usable、不读 None.md）；continuity_auditor.py:160 注释称 idle 是 "a valid blocked governance state"；RuntimeController 定义 NO_ACTIVE_TASK 为一等运行时状态（结构化拒绝非错误）；hook 为 idle 铺设豁免通道（git/治理工具/编排），阻断消息为操作指引。
- **消费端设计缺陷**：v2.0.0 计划要求"区分 no_active_task / pending_gate / invalid_state / blocked"（exit code 分流）**从未实现**——NO_ACTIVE_TASK 与真实损坏共用 exit 2 + `[error]` 级，消费端无法区分"合法 idle 阻塞"与"治理损坏"。
- 时间归属修正：该逻辑由 **v2.0.0（commit 0612217）** 引入，T-0078（c15e65c）为后续加固，非 T-0078 首创。

## 修复方向（若立项，遵循 T-0100 验收报告留待裁决建议）

1. validate_state：NO_ACTIVE_TASK 独立 exit code（如 3）+ 独立输出段，与治理损坏（exit 2）分流；**保留"idle 不输出 [ok] state is usable"安全意图**
2. release.py check：step_validate_state 感知合法阻塞态（rc=3 → 明确标注而非 FAIL），或文档化"check 需活动任务态"
3. test_governance_consistency：idle 适配（None 指针断言 idle 契约，消除 TypeError）
4. 三处判定约定对齐（self-audit / release check / consistency 测试）

## 证据

- .ai/evidence/T-0100/acceptance/acceptance-report.md（第六节：提交后复验记录 + 留待裁决）
- .zcode/plans/plan-sess_59848a7a-90ee-414e-b39d-cc008eed7cb2.md（v2.0.0 计划，L122/L127-128/L133-136）
- .zcode/plans/plan-sess_78484031-b2d6-4c1d-9974-4c2c0f7e757f.md（T-0082 计划，L20-27）
- .ai/HANDOFF-NEXT.md（L69-72、L440-445：NO_ACTIVE_TASK 为预期阻断非成功）
- loop_core/runtime_controller.py（L26/L139/L250-256）
- hooks/scripts/loop_enforcement.py（L1729 DISPATCH 门；L1822-1900 idle 豁免通道）
- tools/loop_self_audit.py（L310-314：rc 0/2 为 OK）
- .zcode/tools/validate_state.py（L408-411）、.zcode/tools/continuity_auditor.py（L147-224）
- .zcode/tools/audit_handoff.py（L31-38）
- scripts/release.py（L283-313 step_validate_state 纯 exit code 判定）
- tests/test_governance_consistency.py（5 个断言）
