# T-0037 Fresh Independent Review After T-0036 Baseline Gate Request v0.1

Gate ID: `G-T-0037-FRESH-INDEPENDENT-REVIEW-AFTER-T0036-BASELINE-V0-1`

Status: `pending / user_decision_required / review_not_started`

## Gate 目标

对已完成的 Codex-only Loop 候选实现进行全新、只读、独立审查，确认其是否具备进入后续用户决策或单独修复流程的证据基础。

Gate 创建不是批准，用户批准不是审查执行。批准后仍必须收到后续精确执行请求，才可启动新的独立 reviewer。

- 批准：`批准 G-T-0037-FRESH-INDEPENDENT-REVIEW-AFTER-T0036-BASELINE-V0-1`
- 拒绝：`拒绝 G-T-0037-FRESH-INDEPENDENT-REVIEW-AFTER-T0036-BASELINE-V0-1`
- 批准后执行：`执行 G-T-0037-FRESH-INDEPENDENT-REVIEW-AFTER-T0036-BASELINE-V0-1`

## 前置条件

- T-0036 task 与 `.ai/task_graph.yaml` 均为 `completed`。
- T-0036 候选基线已接受，`research-baseline-v0.1` 已冻结。
- 最终 manifest 为 `.ai/evidence/T-0036/material-library-version-freeze-manifest.v0.1.md`，`10202` bytes，SHA-256 `24DDC5434B0FFE3D078AED5B8A2101CF6A0A4C97DF73553E949FB668BDE98F20`。
- 最终 manifest 声明、解析、唯一对象和磁盘匹配均为 `65/65`，mismatch `0`。
- `G-T-0037-CODEX-LOOP-CANDIDATE-IMPLEMENTATION-V0-1` 为 `approved / implementation_completed_review_pending`。
- `G-T-0038-T0037-FRESH-INDEPENDENT-REVIEW-V0-1` 已 `superseded / superseded_before_user_decision`，不得复用。
- isolated candidate-path verification gap 仍为 `open / unwaived`。
- T-0037 尚未经过本 Gate 要求的全新独立审查。

`.ai/evidence/T-0037/fresh-read-only-review.v0.1.md` 与 `.ai/evidence/T-0037/human-review-packet-review.v0.1.md` 仅是历史 implementation 阶段背景证据，不是本 Gate 的独立 verdict，也不得作为 `PASS` 的替代品。

## 独立性合同

- reviewer 必须是全新上下文。
- reviewer 不得参与 T-0037 implementation。
- reviewer 不得参与 T-0036 素材修复、复审、基线决策、版本冻结或行政收口。
- reviewer 不得参与本 Gate 准备。
- reviewer 必须披露 agent/session、是否继承父历史、可见输入、只读边界、限制和未验证项。
- 无法证明独立性时，必须在实质审查前返回 `BLOCKED` 或 `USER_DECISION_REQUIRED`。
- reviewer verdict 仅是证据，不能批准 Gate、关闭 T-0037、执行修复或授权下游动作。

## 冻结审查对象

T-0037 控制清单为 `.ai/evidence/T-0037/fresh-independent-review-after-t0036-control-manifest.v0.1.md`。

- 精确对象数：`62`。
- 范围：`codex_loop/`、`tests/codex_loop/`、`docs/codex-loop/`、注册前既有 `.ai/evidence/T-0037/`、`.ai/tasks/T-0037.md`。
- 包含 T-0037 implementation Gate 请求、验证、命令、changed-path manifest 和本地 fixture 证据。
- 历史两个 review 文件包含在冻结输入中，但只能作为背景材料，不具有本 Gate verdict 身份。
- 排除 `__pycache__`、`.pyc`、`.pytest_cache`、本 Gate 注册文件和未来审查输出。
- 任一 path、byte size 或 SHA-256 漂移要求 `BLOCKED`；不得静默重建基线。

T-0036 `research-baseline-v0.1` 仅作为只读输入基线。未来审查前后均须验证最终 manifest 及其 65 个冻结对象零漂移。

## 必须独立检查

1. Core 数据模型、Schema、Store 和状态边界。
2. 11 个稳定角色的合同、提示词、权限、停止条件、能力探针和交接协议。
3. registry、context、permission 和 run envelope。
4. routing、phase profile、task graph 和 work packet。
5. quality/security/cost checker 以及 finding/repair/regression loop。
6. Human Review Packet 的可读性和用户 Gate 边界。
7. T-0036 fixture 的端到端本地演练与可重复性。
8. 输入、输出、写入路径、工具权限和越界行为。
9. 测试覆盖、错误处理、确定性和回滚边界。
10. 是否错误宣称 Runtime、真实模型、Agent、Host 或生产能力。
11. T-0036 冻结基线引用是否保持 `research-baseline-v0.1`。
12. isolated candidate-path verification gap 是否仍明确记录且未被错误声称已关闭。

## 必须明确的未验证项

- 真实模型调用。
- 真实 Agent 能力。
- 生产项目代码编译、部署、恢复和性能。
- Codex 全局安装或 Host Integration。
- isolated candidate-path 的独立边界行为。

## Verdict 合同

允许 verdict：`PASS`、`REPAIR_REQUIRED`、`BLOCKED`、`USER_DECISION_REQUIRED`、`SCOPE_VIOLATION`。

`PASS` 仅表示候选实现通过本次证据性独立审查，可进入后续用户决策或单独修复流程；不代表生产认证、用户验收、全局安装、Host Integration 或 T-0037 最终关闭。

## 注册阶段 Allowlist

- `.ai/evidence/T-0037/fresh-independent-review-after-t0036-gate-request.v0.1.md`
- `.ai/evidence/T-0037/fresh-independent-review-after-t0036-changed-path-baseline.v0.1.md`
- `.ai/evidence/T-0037/fresh-independent-review-after-t0036-control-manifest.v0.1.md`
- `.ai/evidence/T-0037/fresh-independent-review-after-t0036-registration-commands.v0.1.md`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`

实际注册变更路径必须是以上 allowlist 的严格子集。注册阶段不得创建 reviewer 或审查 verdict。

## 批准并收到精确执行请求后的 Allowlist

- `.ai/evidence/T-0037/fresh-independent-review-after-t0036.v0.1.md`
- `.ai/evidence/T-0037/fresh-independent-review-after-t0036-commands.v0.1.md`
- `.ai/evidence/T-0037/fresh-independent-review-after-t0036-validation.v0.1.md`
- `.ai/evidence/T-0037/fresh-independent-review-after-t0036-changed-path-manifest.v0.1.md`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`

## 禁止范围

- 不在本 Gate 内修复发现。
- 不修改 T-0036 的 65 个冻结对象、最终 manifest 或任何既有 T-0036 证据。
- 不修改 T-0037 implementation、tests、docs 或 `codex_loop/`。
- 不修改 candidate/global Project Governor。
- 不执行真实模型、部署、安装、激活或 Host Integration。
- 不创建 T-0037 closeout、发布或下游 Host Gate。
- 不把历史 T-0037 review 文件升级为本 Gate verdict。
- 不修复或豁免 isolated candidate-path verification gap。
- 不执行数据库、权限、密钥、支付、生产数据或迁移动作。

## 验证与恢复

1. 审查执行前后验证 T-0037 62/62 control manifest。
2. 审查执行前后验证 T-0036 final manifest 和 65/65 冻结对象零漂移。
3. 使用 `PYTHONDONTWRITEBYTECODE=1` 和禁用 pytest cache 运行 T-0037 focused tests、相关 YAML/Markdown/schema checks。
4. 运行 `validate_state.py`、`audit_handoff.py` 和 `git diff --check`。
5. 实际变更路径必须是当前阶段 allowlist 的严格子集。
6. 漂移返回 `BLOCKED`，路径/效果越界返回 `SCOPE_VIOLATION`。
7. 保留无关 dirty-worktree 变更和真实的部分增量证据；不得自动删除、reset、checkout、静默重建基线或破坏性恢复。
8. 修复、豁免、回滚执行、范围扩张和下游动作均需单独显式 Gate。

当前结论：`pending / user_decision_required / review_not_started`。
