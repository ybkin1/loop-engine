# T-0116 commands

## 执行命令记录

```bash
# 1. P3 修正定位（grep 各旧口径）
grep -rn "51 场景" .ai/evidence/T-0110/     # → commands.md×2 + fixes/batch-c-enforcement.md
grep -rn "36→28" .ai/                       # → execution-evidence.json + 任务卡 + gate scope + task_graph
grep -rn "38/58" .ai/                       # → T-0113.md + T-0111 acceptance
grep -rn "exit 非 0" .ai/evidence/T-0106/   # → design-bh-integration.md + plan-task-roadmap.md

# 2. 逐项修正（详见 fixes/p3-wording-fixes.md）
#    硬修正 10 处 + 说明记录 4 任务 commands 追加 + KNOWN_ISSUES 登记 2 条
#    （T-0104 P3×4 建议类 + 快照数字）

# 3. 历史卡状态同步
sed -i 's/^in_progress$/completed/' .ai/tasks/T-0113.md .ai/tasks/T-0114.md

# 4. AC-02 grep 复核
grep -rn "51 场景\|36→28\|exit 非 0\|38/58" .ai/   # 仅审查报告原文引用（已注明修正）
```

## 遗留说明

- `tests/t0110_c_golden.py` 文档串（51 场景）不在本任务 allowed_paths（tests/ 零改动），
  已记录说明，行为等价结论不受影响。
- 各任务 review/independent-review.md 中的 P3 原文引用保留（历史记录不可改写），
  修正记录在 commands.md "T-0116 P3 措辞修正记录"节可追溯。

## 审查瞬态登记（CONDITIONAL_GO 条件 3）

- 版本 bump 改写 .ai/version-manifest.yaml 后未 repair → validate EXIT=2 +
  test_t0108_fixes 2 项 drift 失败（T-0110 P3-3 同款模式，非任务缺陷）；
  已执行 `validate_state --repair` + HANDOFF 重生成 → **t0108 34 passed，
  validate EXIT=0，0 errors**。
- `test_pyproject_version_matches_git_head`：pyproject 3.12.52 vs HEAD 3.12.51
  为 F-03 提交前必然状态，提交后自愈。
