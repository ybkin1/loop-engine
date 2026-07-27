# T-0036 素材库候选交付包完成验证 v0.1

Gate：`G-T-0036-COMPLETE-MATERIAL-LIBRARY-REVIEW-PACKET-V0-1`

## 执行边界

本验证只证明 T-0036 候选素材库的用户可读评审包、覆盖/重复检查和完成证据已生成。它不执行 T-0036 独立评审、修复、复审、候选基线接受或版本冻结，也不授权 T-0037 评审或 Host Integration。

## 输入

- `materials/catalog.yaml`
- `materials/material-schema.yaml`
- `materials/source-register.md`
- `materials/coverage-matrix.md`
- `materials/templates/`
- `materials/frameworks/`
- `materials/profiles/`
- `.ai/evidence/T-0036/source-validation.v0.1.md`
- `.ai/evidence/T-0036/coverage-matrix.v0.1.md`
- `.ai/evidence/T-0036/simulation/`

## 确定性结果

- PyYAML 解析 catalog 和 schema：`PASS`。
- 材料数量：`46`。
- schema 声明的 17 个必填字段：`46/46` 条材料通过，缺失项为 `0`。
- `material_id`、标准化 `title`、标准化 `source_url` 精确重复：均为 `0`。
- `problem_solved`、`when_to_use`、`when_not_to_use`、`adaptation_notes` 精确重复：均为 `0`。
- 标准化 `problem_solved + adaptation_notes` 序列相似度 `>=0.72` 的材料对：`0`。
- `template_or_schema` 引用：`67` 次、`29` 个唯一路径、悬空路径 `0`。
- 磁盘资产：28 个模板、3 个 framework、2 个 profile。
- 用户评审包必需章节编号 `4/5/8/9`：`PASS`。
- 覆盖/重复报告必需章节编号 `2/3/6`：`PASS`。
- `git diff --check`：`PASS`。
- `validate_state.py`：执行前 `PASS`；完成状态同步后再次执行并记录最终结果。

## 已明确的开放事实

- 来源状态为 `access_blocked`、`url_verified_only` 或 `not_yet_checked` 的材料共 `17` 条，不能当作已读取正文。
- catalog 顶层有 `retrieved_at: 2026-07-22`，但单条材料没有单独 `retrieved_at`；是否补齐留给独立评审和用户基线决定。
- 覆盖矩阵的“交付/供应链”领域当前通过 `SEC-004`、`OPS-003..004` 表达，是否拆分独立 category 留给独立评审。
- 结构化零重复不等于语义上没有重叠；语义适用性和基线质量必须由后续独立评审判断。

## 证据边界

- `materials/material-library-review-packet.md`：用户可读候选评审包。
- `materials/coverage-duplication-review.md`：覆盖缺口与重复内容的可复现检查。
- `.ai/evidence/T-0036/material-library-completion-changed-path-manifest.v0.1.md`：本次执行 changed-path manifest。
- `.ai/evidence/T-0036/commands.md`：本次执行命令记录。

当前结论：`completion-package-complete / independent-review-required / baseline-not-accepted`

## Post-execution governance validation

- `python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab`：`PASS`，state is usable。
- `python C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py C:\Users\Administrator\.codex\loop-engine-lab`：`PASS`，handoff audit passed。
- `git diff --check`：`PASS`。
- Gate execution status：`completion_package_completed_awaiting_independent_review`。
- T-0036 status：`active`；没有创建或执行独立评审、修复、复审或基线决策 Gate。
