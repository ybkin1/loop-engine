# T-0127 命令记录

- 2026-08-07 登记与批准：G-T-0127-REQUIREMENTS 由用户批准（"按顺序完成全量处理"）；
  T-0127 推进 in_progress（task_graph/任务卡同步）；approval/execution/compile evidence 生成
- 2026-08-07 实现：
  - `.zcode/tools/governor_lib.py`：`project_root_arg` 增加 `--auto-sync` 参数
  - `.zcode/tools/validate_state.py`：`repair_mode` 识别 `--auto-sync`；新增 auto-sync 块
    （repair → render_handoff → continuity 哈希同步，幂等）
  - `tests/test_governance_invariants.py`：9 用例（正例 1 + 反例 8：状态不一致/Status
    缺失/gate 错配/节点缺失/重复节点/approval/execution evidence 缺失/pending gate 指针）
  - `docs/08-registration-flow.md`：登记流程标准步骤（--auto-sync 一步同步）
- 2026-08-07 实测：制造 continuity 漂移 → `--auto-sync` 修复 1 哈希 + HANDOFF 重生成 +
  收敛（普通校验 state usable）
- 2026-08-07 验证：test_governance_invariants 9/9；test_version_consistency +
  test_governance_consistency 33 passed；bump 3.12.62（8 载体）
- 全量回归：运行中（预期 0 failed）
- 独立审查 + 验收：待执行
