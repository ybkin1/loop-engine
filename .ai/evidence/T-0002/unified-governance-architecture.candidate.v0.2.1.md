# Codex 一人研发团队式 Loop 软件交付系统：统一规范架构 Candidate v0.2.1

Status: candidate
User-approved: false
Approved: false
Active: false
Installed: false
Write authority: evidence-only for T-0002

本文件是 T-0002 的候选证据。它不是 approved、active 或 installed 协议；Reviewer PASS、测试通过、validator 通过都只能作为 evidence，不能替代用户 gate。

## 1. 项目章程 Candidate

使命：帮助无代码能力、无项目管理背景的用户，让 Codex 以一人研发团队式 Loop 工程方式，从粗略需求推进到真实可用、可部署、可验收、可持续迭代的软件产品。

用户职责：

- 提出目标和业务背景。
- 回答关键业务问题。
- 在多个产品或治理方向之间做取舍。
- 明确批准或拒绝 user gate。

Codex 职责：

- 澄清需求、识别风险、拆分任务、设计方案。
- 在已授权范围内实现、评审、修复、验证和交接。
- 承担技术架构、项目管理和质量检查细节。
- 在权限不清、上下文缺失或需要用户取舍时停止并请求 gate。

MVP：

- 先形成可评审、可执行、可安装前检查的候选规范包。
- 不把候选规范直接安装到入口规则。
- 不进入真实业务项目，除非用户另行批准 gate。

成功标准：

- 每个任务能进入 `task card -> candidate/output -> review -> repair -> verify -> handoff -> close or user gate` 闭环。
- `candidate`、`reviewed`、`user-approved`、`approved`、`active`、`installed` 不混淆。
- 文档产物服务真实软件交付，不形成纯文档自循环。

非目标：

- 不自动批准、启用或安装任何候选协议。
- 不让用户承担技术实现、项目管理或评审细节判断。
- 不用 Reviewer PASS、测试结果或 validator 结果替代用户批准。

## 2. 状态生命周期表 Candidate

| 状态 | 含义 | 进入条件 | 允许操作者 | 必需 evidence | 禁止自动转换 |
| --- | --- | --- | --- | --- | --- |
| `candidate` | 候选草案，可供讨论和评审 | Author 在授权范围内产出 | Codex | 草案正文、来源材料、任务卡 | 不得自动变为 `approved`、`active` 或 `installed` |
| `reviewed` | 已被 Reviewer/Auditor 审查 | 评审报告已产出 | Reviewer/Auditor | findings、severity、recommendation、residual risk | Reviewer PASS 不等于 `user-approved` |
| `user-approved` | 用户明确通过 gate 批准 | 用户给出清晰批准 | 用户 | 用户批准记录、批准对象、批准范围 | Codex、Reviewer、测试、CI、validator 不可生成 |
| `approved` | 已被批准，可作为后续启用候选 | `user-approved` 后由 Codex 记录 | 用户授权下的 Codex | 批准版本、范围、时间、限制 | 不自动变为 `active` 或 `installed` |
| `active` | 已被明确选为当前执行依据 | 用户或已批准规则明确启用 | 用户授权下的 Codex | 启用范围、适用项目、入口来源 | 不自动变为 `installed` |
| `installed` | 已实际写入、配置或安装 | 独立安装 gate 已批准并完成 | 用户授权下的 Codex | 安装位置、变更记录、验证结果 | 不由 `candidate`、`reviewed` 或 `approved` 自动推出 |

状态提升必须遵守 user gate。任何状态不清时，Codex 必须使用 `NEED_USER_GATE` 或 `BLOCKED_AUTHORITY_CONFLICT`，不得自行补授权。

## 3. Artifact Registry 与 Latest Version Rule Candidate

同一规范可能同时存在多个候选版本，例如 v0.1、v0.2、v0.2.1。为避免 Codex 误读旧版本，候选包采用以下规则：

| 项目 | 规则 |
| --- | --- |
| artifact identity | 每个候选包必须有稳定标题、版本号、状态和 evidence 路径 |
| latest candidate | 同一 artifact family 下，语义版本最高且未被明确废弃的 `candidate` 可作为当前候选最新版 |
| authority limit | latest candidate 只表示“最新候选”，不表示 `approved`、`active` 或 `installed` |
| approved source | 若存在 `approved` 或 `active` registry，Codex 必须优先使用 registry 指定版本 |
| conflict handling | 若聊天、任务卡、registry、磁盘 evidence 指向不同版本，Codex 必须列出冲突并请求用户或 Coordinator 决定 |
| deprecation | 旧候选版本不得删除；可标注 superseded-by，用于保留历史和审计 |

建议 registry 字段：

```yaml
artifact_id:
family:
title:
version:
status: candidate | reviewed | user-approved | approved | active | installed
path:
supersedes:
superseded_by:
review_evidence:
approval_evidence:
installed_location:
notes:
```

## 4. 规范架构协议 Candidate

规则层级从高到低：

1. 平台、系统、开发者约束。
2. 用户最新明确授权和禁止项。
3. 已安装并有效的入口规则。
4. `approved` 或 `active` 项目规则。
5. 阶段级规则和角色级规则。
6. Session Contract。
7. Task Card。
8. `candidate` evidence。

低层规则只能收窄高层规则，不能覆盖用户禁止项、项目 gate、已安装入口规则或系统/工具权限边界。

规范架构回答“开始前必须读什么、相信什么、禁止什么”。Loop 工程回答“一个任务如何产出、评审、修复、验证和交接”。两者通过 Required Reading、Context Assembly、Session Contract 和 Task Card 连接。

## 5. Required Reading Matrix Candidate

| intent | phase | role | must_read | optional_read | authority_priority | stop_if_missing |
| --- | --- | --- | --- | --- | --- | --- |
| 简单问答/临时只读 | any | any | 用户最新请求 | 被问到的单个文件或片段 | 用户最新请求优先 | 无法回答时询问用户 |
| 设计/规划 | S0/S1 | Coordinator/Author | `.ai/state.yaml`、`.ai/HANDOFF.md`、`.ai/PROJECT.md`、当前任务、相关 evidence | `.ai/DECISIONS.md`、`.ai/CONVENTIONS.md`、`.ai/PROGRESS.md` | 用户最新请求 > active 规则 > 当前任务 > evidence | `BLOCKED_MISSING_CONTEXT` |
| 实现/修复 | S2+ | Author/Repair | 当前任务、Session Contract、相关源码、测试入口、`.ai/QUALITY_GATES.md` | `.ai/CODEMAP.md`、历史 issue、设计文档 | 用户批准的 phase/task/mode/write set > active 规则 > Task Card | 缺写入授权时 `NEED_USER_GATE` |
| 评审 | any | Reviewer/Auditor | 被评审产物、acceptance criteria、review plan、相关 evidence | diff、测试日志、运行截图 | acceptance criteria > review plan > evidence | 缺产物时 `BLOCKED_MISSING_CONTEXT` |
| 交接 | any | Handoff | `.ai/state.yaml`、当前任务、evidence、已验证/未验证项 | diff、progress、known issues | state > task > evidence | 缺关键状态时 `BLOCKED_MISSING_CONTEXT` |
| 状态提升/安装 | any | Coordinator/Auditor | 候选包、评审报告、gate 条件、用户授权、目标位置 | registry、历史版本、安装说明 | 用户 gate > approved registry > candidate evidence | 必须 `NEED_USER_GATE` |

冲突规则：

- Task Card 与高层禁止项冲突时，停止为 `BLOCKED_AUTHORITY_CONFLICT`。
- 缺少必读上下文时，停止为 `BLOCKED_MISSING_CONTEXT`。
- 无法判断是否越权时，停止为 `NEED_USER_GATE`。

## 6. Context Assembly Protocol Candidate

Context Assembly 必须产出可检查字段，而不是只画流程。

| step | input | output fields | checker | failure state |
| --- | --- | --- | --- | --- |
| Intent Recognition | 用户最新请求 | `task_intent`、`risk_level`、`requested_output` | Coordinator | 无法识别则询问用户 |
| Phase Detection | state、任务、用户请求 | `phase`、`phase_confidence` | Coordinator | `BLOCKED_MISSING_CONTEXT` |
| Role Selection | intent、phase | `assigned_role` | Coordinator | `BLOCKED_AUTHORITY_CONFLICT` |
| Required Reading | matrix、role、phase | `read_set`、`missing_context` | Author/Coordinator | `BLOCKED_MISSING_CONTEXT` |
| Authority Check | rules、task card、gate | `allowed_actions`、`forbidden_actions`、`gate_needed` | Auditor | `NEED_USER_GATE` 或 `BLOCKED_AUTHORITY_CONFLICT` |
| Session Contract | prior outputs | `session_contract` | Coordinator | `BLOCKED_MISSING_CONTEXT` |
| Task Card Check | session contract、task card | `intended_scope`、`authority_source`、`acceptance_criteria` | Coordinator/Auditor | `BLOCKED_AUTHORITY_CONFLICT` |
| Loop Entry | all outputs | `loop_ready: true/false` | Coordinator | false 时不得执行 |

标准路径：

```text
User Request
-> Intent Recognition
-> Phase Detection
-> Role Selection
-> Required Reading
-> Authority Boundary Check
-> Session Contract
-> Task Card
-> Loop Run
```

## 7. Loop 工程协议 Candidate

标准闭环：

```text
task card -> candidate/output -> review -> repair -> verify -> handoff -> close or user gate
```

角色边界：

- Coordinator：识别目标、拆任务、生成或验证 Task Card、判断 gate。
- Author：按 Task Card 产出 candidate 或实现结果。
- Reviewer：审查产物并给出 findings 与 recommendation。
- Repair：在 reviewer 指定范围内修复。
- QA：验证 acceptance criteria 与证据完整性。
- Handoff：总结状态、证据、风险、下一步。
- Auditor：审查权限边界、状态混淆和 gate 是否被绕过。

Loop 控制：

| 项目 | 默认规则 |
| --- | --- |
| design task iteration limit | 最多 2 轮 repair |
| implementation task iteration limit | 最多 3 轮 repair |
| repair policy | 只修复 findings 指向的问题，不借 repair 扩大范围 |
| evidence policy | 每轮必须记录已验证、未验证和残余风险 |
| escalation | 超过 loop limit、权限不清、业务取舍不清时停止并请求 gate |

Stop states 判定：

| stop state | 触发条件 |
| --- | --- |
| `PASS_RECOMMENDED` | 无 P0、无未修复 P1、acceptance criteria 可检查且已满足或有清楚 evidence、无缺失上下文、无权限冲突 |
| `FAIL_REPAIRABLE` | 存在可修 findings，仍在任务范围内，且剩余 loop 足以修复 |
| `BLOCKED_MISSING_CONTEXT` | 必读文件、输入、任务状态或评审对象缺失 |
| `BLOCKED_AUTHORITY_CONFLICT` | Task Card、Session Contract、用户请求或高层规则之间存在权限冲突 |
| `NEED_USER_GATE` | 状态提升、安装、真实项目启用、高风险操作、权限不清、业务取舍需要用户决定 |
| `LOOP_LIMIT_REACHED` | repair 轮次达到上限仍未满足 pass conditions |
| `OUT_OF_SCOPE` | 请求或发现的问题超出当前 phase/task/mode |

## 8. 写入权限模型 Candidate

普通代码或文档写入不应每次都要求用户 gate。正确模型是：用户批准某个 phase/task/mode 后，Codex 可在明确 write set、风险等级和 acceptance criteria 内写入。

必须 user gate 的动作：

- 状态提升：`candidate` -> `user-approved`、`approved`、`active`、`installed`。
- 安装或启用入口规则、AGENTS.md、skill、MCP、agent、automation、protocol。
- 部署、rollback、数据库、权限、密钥、支付、生产数据、迁移。
- 跨项目应用候选规范或进入真实业务软件项目。
- 超出已批准 write set 的修改。
- Codex 无法判断某动作是否会真实生效。

本 T-0002 写入仅限 evidence 保存，不表示候选包被批准、启用或安装。

## 9. Session Contract 模板 Candidate

Session Contract 是当前会话的临时工作合同。它只能收窄权限，不能授予真实权限。

```yaml
session_id:
task_id:
phase:
role:
task_intent:
objective:
source_status: candidate | reviewed | user-approved | approved | active | installed
must_read:
context_summary:
inherited_rules:
authority_boundary:
forbidden_actions:
allowed_output:
expected_artifacts:
acceptance_criteria:
review_plan:
pass_conditions:
stop_conditions:
user_gate_conditions:
loop_controls:
  iteration_limit:
  repair_policy:
  stop_states:
handoff_requirements:
```

## 10. Task Card 模板 Candidate

Task Card 描述本轮 intended scope，不是真实权限来源。真实权限必须来自用户授权、已批准 gate、active 规则和环境权限。

```yaml
task_id:
task_title:
phase:
mode:
intended_scope:
authority_source:
assigned_role:
objective:
background_sources:
must_read:
allowed_output:
forbidden:
expected_artifacts:
acceptance_criteria:
review_required:
reviewer_role:
review_plan_required:
pass_conditions:
stop_conditions:
user_gate_required:
need_user_gate_conditions:
next_instruction_for_user:
```

## 11. Review Report 模板 Candidate

Review Report 只能给 recommendation，不能把 PASS 写成 approved、active 或 installed。

```yaml
review_id:
reviewed_artifact:
reviewer_role:
scope_checked:
findings:
  - severity: P0 | P1 | P2 | P3
    evidence:
    required_repairs:
pass_fail_recommendation:
residual_risk:
unchecked_items:
user_gate_needed:
final_recommendation:
```

Severity：

- P0：阻断，必须修复。
- P1：阻断或必须修复，修复后可继续。
- P2：建议修复，不阻断 candidate 继续评审。
- P3：非阻塞建议，可记录为后续改进。

## 12. Review Plan Candidate

Review Plan 是评审方案，不是评审结论。

必须检查：

- 是否覆盖项目章程、Loop 工程协议、规范架构协议、Required Reading Policy、Context Assembly Protocol、Session Contract 模板、Task Card 模板、Review Report 模板、AGENTS.md 入口规则、Review Plan。
- 是否混淆 `candidate`、`reviewed`、`user-approved`、`approved`、`active`、`installed`。
- 是否把 Reviewer PASS、测试、validator 当成用户批准。
- 是否让 Task Card 或 Session Contract 自授权真实权限。
- 是否能走完 loop closure。
- 是否服务真实软件交付，而不是纯文档工程。

报告格式必须包含 findings、severity、evidence、required_repairs、pass/fail recommendation、residual_risk。

## 13. AGENTS.md 入口规则 Candidate

启动时先读取用户最新请求，再判断任务类型。

- 简单问答、单文件解释、临时只读命令：直接处理，不加载项目记忆。
- 实现、评审、排障、设计、交接：确认项目根目录，使用 project-governor，读取项目状态和必读文件，运行状态校验。
- 存在 pending gate：停止，请用户批准或拒绝。
- 涉及状态提升、安装、部署、数据库、权限、密钥、支付、生产数据、迁移、真实业务项目：必须 user gate。
- 低风险不确定可记录假设后继续；高风险不确定必须询问用户。

## 14. 无代码用户 Gate 提示模板 Candidate

```text
你只需要决定业务层面的批准，不需要判断技术细节。

目标：
范围：
主要风险：
Codex 建议：
下一步会发生什么：
不会发生什么：
需要你批准的是：
可选回答：
- 批准进入下一步
- 不批准
- 先修改这些点：...
```

## 15. 真实软件交付锚点 Candidate

每个实现类任务最终必须关联：

- 可运行产物。
- 测试证据。
- 验收方式。
- 必要的部署、回滚或运行说明。
- 交接记录。

每个设计或文档任务必须说明它服务哪个后续软件交付环节。任何“完成”不得只靠文档存在，必须能追溯到后续可运行、可验证、可验收的软件结果。

## 16. 下一步推荐

建议对本 Candidate v0.2.1 进行基于磁盘 evidence 的正式 Reviewer-Auditor 评审。

即使评审结果为 PASS，也只表示 evidence。若要提升为 `approved`、`active` 或 `installed`，必须由用户明确批准 gate。
