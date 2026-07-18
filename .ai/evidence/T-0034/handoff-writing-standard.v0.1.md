# 交接文档写作规范 v0.1

## 1. 文档身份

- Artifact ID: `T-0034-HANDOFF-WRITING-STANDARD-v0.1`
- Status: `design_evidence_only`
- Applicable roles: L0 项目/计划主控、L1 任务主控、L2 执行/修复/验证/审计代理，以及 successor probe。
- Authority: 本规范定义交接文档如何写、如何读取、如何验证；它不安装、不激活、不自动调度任何代理，也不替代用户 gate。
- Governing task: `T-0034`
- Governing gate: `G-T-0034-DESIGN-PROJECT-CONTINUITY-CONTROLLER-HIERARCHY-LOOP-ASSURANCE`

## 2. 目标

合格交接不是把旧聊天复制给新会话，而是让新主控在不依赖旧会话记忆的情况下恢复与旧主控**控制语义等价**的状态：知道服务谁、最终目标是什么、现在处于哪里、用户批准了什么、没有批准什么、哪些事实不可漂移、当前证据是什么、唯一安全下一动作是什么。

交接必须同时解决四类风险：

1. **信息缺失**：新会话不知道关键事实、边界或 blocker。
2. **注意力过载**：交接过厚，读完即失去执行余量。
3. **阶段混淆**：把创建、批准、执行、测试、验收、安装、激活混为一体。
4. **累计漂移**：每次交接只有微小偏差，但长期偏离产品北极星、架构、技术选型、接口、编码风格或用户目标。

## 3. 核心原则

### 3.1 磁盘事实优先

事实优先级从高到低为：

1. 用户最新明确指令和明确 gate 决策；
2. 磁盘原始字节及其显式 UTF-8 读取结果；
3. canonical governance records：`state.yaml`、任务文件、`gates.yaml`、`task_graph.yaml`；
4. 已批准的长期基线、决策、合同、规范和验收标准；
5. 确定性命令、测试、validator、audit 及原始证据；
6. HANDOFF、checkpoint、代理报告和人工摘要；
7. 聊天记忆、模型自信或未经磁盘复核的口头结论。

若终端显示乱码，必须先按 UTF-8 重新读取磁盘文件；不得仅凭显示乱码认定文件损坏，也不得自动修复或重编码。

### 3.2 HANDOFF 不是完整项目记忆

- HANDOFF 只保存当前控制现场和下一动作。
- 长期不变量必须存放在版本化 `Project Continuity Baseline`、ADR、合同、编码规范、API/协议、测试与交付基线中。
- HANDOFF 通过 ID、版本、路径和必要时的 SHA-256 引用 canonical records，不复制完整历史。
- 缺少长期基线时必须标记 `BASELINE_MISSING` 或 `BASELINE_INCOMPLETE`，不能由新旧主控自行补造事实。

### 3.3 授权与证据分离

- 用户 gate 是授权；测试 PASS、review PASS、validator、audit、subagent 和 AI 推荐只是证据。
- `implementation`、`installation`、`activation`、`real-project entry` 必须分别陈述。
- “已批准”不等于“已开始执行”；“执行完成”不等于“用户验收”；“candidate”不等于“installed”；“installed”不等于“activated”。
- 子层 scope 必须是父层 scope 与用户授权 scope 的子集。

### 3.4 稳定检查点交接

正常交接只允许发生在以下稳定检查点：

- iteration 尚未启动；
- 写入已完成且结果已冻结；
- 测试或验证已完成且证据已落盘；
- audit 已完成且 findings 已冻结；
- repair 已完成且等待复审；
- 阶段已收口且无 active transaction。

正常交接禁止发生在：

- 文件写入、测试、状态迁移或证据生成进行中；
- 存在 partial evidence、未分类写入或未确认 diff；
- 存在 in-flight agent、锁、租约或 active transaction；
- installation、activation、migration、deployment、rollback 进行中。

若发生崩溃或上下文紧急耗尽，只能生成 `emergency_handoff`，明确列出未可信写入、恢复动作和禁止继续执行的边界，不得伪装成正常交接。

### 3.5 不压缩事实，只控制读入

- 不用有损摘要替代 canonical facts。
- 通过 Tier 0/1/2 分层读取、引用和按需展开管理上下文。
- 新主控先读小型 Bootstrap Capsule；只有当前动作需要时才读 Tier 1；发生冲突、审计或恢复时才读 Tier 2。
- 如果 Bootstrap 本身已超出项目配置的准入预算，必须先做结构性瘦身或拆分 canonical records，不能刚接班就继续启动 iteration。

## 4. 交接类型

### 4.1 `normal_handoff`

适用于稳定检查点。必须满足：无 active transaction、无 in-flight agent、当前写入已冻结、验证结果已记录、唯一下一动作明确。

### 4.2 `task_controller_rotation`

L1 主控换代。必须额外记录 task iteration、finding lifecycle、repair 次数、当前 VerificationPlan、未关闭 blocker 与下一 iteration admission 结果。

### 4.3 `program_controller_rotation`

L0 主控换代。必须额外记录产品北极星、roadmap、跨任务依赖、当前阶段、任务准入、gate 边界和下游禁止项。

### 4.4 `emergency_handoff`

只用于非稳定状态。状态必须是 `UNTRUSTED_PARTIAL_STATE`，下一动作只能是恢复、盘点或回滚决策，不能直接继续原执行。

## 5. 必填结构

每份交接文档必须按以下顺序书写。字段不适用时写 `not_applicable`，事实缺失时写 `unknown` 或 `BASELINE_MISSING`，不得静默省略。

### 5.1 Identity

- 文档 ID、版本、生成时间、交接类型；
- predecessor role/session generation；
- intended successor role；
- 项目根目录；
- governing task、gate 和授权来源。

### 5.2 Mission And User Position

- 最终服务对象；
- 产品北极星与用户期望体验；
- 用户负责的业务事实、关键取舍和 gate；
- Codex 负责的技术分析、实施、验证、审计和返修；
- 治理是降低风险与用户负担的工具，不是产品本身。

### 5.3 Current Control State

至少包含：

- `current_phase`
- `current_task_id` 与 task status
- `current_gate_id` 与 gate status
- 当前 iteration/phase slice
- task graph 状态
- pending gate 数量
- active transaction / in-flight agent / partial write
- 最近稳定检查点

### 5.4 Authorization Matrix

必须逐项写 `authorized / not_authorized / not_applicable`：

- design
- implementation
- candidate modification
- installation
- activation
- runtime behavior change
- agent orchestration / automation
- downstream task creation
- real-project entry
- deployment / rollback / database / permission / secret / payment / production data / migration

### 5.5 Allowed Scope And Forbidden Scope

- Allowed scope 使用可执行动词和精确对象；
- Forbidden scope 明确列出最可能被误解或越权的动作；
- 若用户当前回合缩小了已批准 gate 的执行范围，以用户当前回合为准；
- 不得用“相关工作”“必要修改”等开放式措辞扩张范围。

### 5.6 Protected Anchors

同时列出短期和长期锚点：

- 用户目标、产品身份、non-goals；
- protected decisions 与不可重议条件；
- 设计语言、golden references；
- 架构不变量、依赖方向、state/data authority；
- 技术选型与依赖政策；
- API、协议、schema、兼容性规则；
- 编码规范、代码风格、目录结构、测试约定；
- 安全、性能、部署、回滚和交付约束。

每个锚点应引用 canonical ID/版本/路径；不存在正式基线时明确标记缺口，不得从聊天推断为已批准标准。

### 5.7 Recent Changes

只写从上一个稳定 checkpoint 到当前 checkpoint 的变化：

- 新增、修改、删除的精确路径；
- 状态迁移；
- 新证据、findings 或 decisions；
- 明确说明未发生的高风险变化。

不得复制整个项目历史，也不得把计划中的未来动作写成已完成事实。

### 5.8 Verification And Evidence

对每个关键结论写明：

- requirement / invariant；
- evidence path；
- command 或比较方法；
- observed result；
- verified / unverified；
- 时间、环境与限制；
- 原始证据是否保留；
- 修复结果是否通过 addendum 追加。

### 5.9 Findings, Blockers And Residual Risk

- finding ID、severity、状态和证据；
- blocker 的解除条件；
- 已知历史不一致；
- 不影响当前动作但必须保留的 residual risk；
- 禁止通过重写历史、覆盖失败证据或降低标准消除 finding。

### 5.10 Context Admission And Reading Plan

必须列出：

- Tier 0：接班必读，保持最小；
- Tier 1：当前下一动作所需；
- Tier 2：仅在冲突、审计、恢复时读取；
- Bootstrap Admission 结论；
- 下一 iteration 的 admission 前置条件；
- 为验证、错误处理和下一次 closeout 保留的上下文余量。

数值预算必须来自项目已批准配置。未配置时写 `BUDGET_NOT_YET_BASELINED`，不得虚构 token 上限；但仍必须执行“不能在无法完成并收口时启动 iteration”的原则。

### 5.11 ExpectedControllerState

predecessor 必须输出结构化期望状态，至少包含：

```yaml
expected_controller_state:
  user_goal: <canonical reference or exact statement>
  controller_role: <L0|L1|L2-role>
  phase: <phase>
  task_id: <task-id>
  task_status: <status>
  gate_id: <gate-id|null>
  gate_status: <status|null>
  authorization_summary: <exact summary>
  allowed_scope: [<item>]
  forbidden_scope: [<item>]
  protected_anchors: [<id/path/version>]
  blockers: [<id>]
  open_findings: [<id>]
  active_transaction: false
  in_flight_agents: []
  unique_next_safe_action: <one action>
```

### 5.12 Counterfactual Traps

至少要求 successor 明确回答：

1. gate 已批准是否代表当前回合可自动执行？
2. tests PASS 是否代表用户验收或 gate 批准？
3. candidate 是否已 installed 或 activated？
4. 当前阶段完成是否代表产品完成？
5. 另一个会话的文字报告是否可替代磁盘验证？
6. 缺少编码、架构、API 或设计基线时是否可自行发明？

任一答案偏离 canonical records，交接不得通过。

### 5.13 Unique Next Safe Action

- 只能有一个主动作；
- 必须说明开始条件、停止条件和禁止项；
- 若需要用户决策，给出精确、可复制的批准/拒绝或执行提示词；
- 不得把多个阶段串联成一个“下一步”。

### 5.14 Attestations

- Producer attestation：声明文档对应的磁盘状态、验证时间、已知限制和未执行事项；
- Successor attestation：fresh successor 独立读取磁盘后输出 `RecoveredControllerState`；
- 比较结果：`SEMANTIC_EQUIVALENCE_PASS / REPAIR_REQUIRED / BLOCKED`；
- 双签未完成前，旧主控只能声明“交接包已生成”，不能声明“接班成功”。

## 6. 语义等价检查

successor probe 必须比较 `ExpectedControllerState` 与 `RecoveredControllerState`：

| 维度 | 通过标准 | 拦截条件 |
|---|---|---|
| 用户目标 | 同一 canonical 目标 | 目标被缩小、扩大或替换 |
| phase/task/gate | ID 与状态一致 | 创建、批准、执行混淆 |
| 授权 | 每一项逐项一致 | 从 evidence 推导授权 |
| scope | successor scope 是授权子集 | 出现新增路径或动作 |
| protected anchors | ID/版本/路径一致 | 基线被静默替换 |
| blockers/findings | 无丢失、无降级 | 严重项被摘要掉 |
| transaction | 稳定检查点一致 | 未识别 partial/in-flight 状态 |
| next action | 唯一且相同 | 多动作串联或 stale action |

任何高风险字段不一致，结论必须是 `REPAIR_REQUIRED` 或 `BLOCKED`，不能用相似度百分比掩盖语义差异。

## 7. 抗漂移要求

每次交接必须执行三种对齐：

- `step drift`：当前 checkpoint 对比上一稳定 checkpoint；
- `anchor drift`：当前状态对比批准的长期基线；
- `goal drift`：当前产出对比用户业务目标。

代码相关连续性必须明确覆盖：

- 技术选型与依赖版本策略；
- 架构边界、模块职责和依赖方向；
- API、协议、schema 与兼容性；
- 编码规范、命名、格式、错误处理和日志约定；
- 测试策略、测试数据、覆盖维度与执行证据；
- 安全、性能、部署、回滚和可观测性；
- UI/视觉语言与 golden references（适用时）。

如果这些基线尚未建立，交接文档必须保留缺口并阻止相关审计者自行发明标准。

## 8. 写作质量规则

- 使用短句、表格、清单和精确状态值；避免散文式叙事。
- 一条陈述只表达一个事实或约束。
- 区分 `verified`、`reported`、`inferred`、`planned`、`unknown`。
- 使用绝对日期、精确 ID、绝对路径或项目根相对路径。
- 引用大文件而不是复制；Tier 0 不得包含完整历史日志。
- 中文说明与代码标识分离；命令、字段、错误信息保持原文。
- 不写“应该没问题”“大概完成”“基本通过”等不可验证措辞。

## 9. 禁止模式

- 把聊天摘要当唯一事实源；
- 为了缩短文档删除 blocker、finding、forbidden scope 或未授权项；
- 为了显得连续而覆盖原始证据或改写历史；
- 在未稳定状态生成 normal handoff；
- 把 future plan 写成 recent change；
- 把 reviewer PASS 写成用户接受；
- 让 successor 一次性读取所有历史文件；
- 复制旧主控的主观判断但不提供证据路径；
- 交接文档同时包含多个互相依赖的下一任务并要求连续执行；
- 缺少基线时自行补造编码规范、接口、架构或产品风格。

## 10. 最小模板

```markdown
# <Project/Task> Controller Handoff <version>

## Identity
## Mission And User Position
## Current Control State
## Authorization Matrix
## Allowed Scope
## Forbidden Scope
## Protected Anchors
## Recent Changes
## Verified
## Unverified
## Evidence And Commands
## Findings, Blockers And Residual Risk
## Active Transaction And In-flight Work
## Tier 0 / Tier 1 / Tier 2 Reading
## Context Admission
## ExpectedControllerState
## Counterfactual Traps
## Unique Next Safe Action
## Copyable Startup Prompt
## Producer Attestation
## Successor Attestation
```

## 11. 验收标准

一份交接文档只有同时满足以下条件才可判定为 `HANDOFF_PACKAGE_READY`：

1. 生成于稳定检查点，或明确标识 emergency state；
2. 用户目标、task、gate、授权、allowed/forbidden scope 完整；
3. 长期基线与短期 checkpoint 分离；
4. 技术选型、架构、API/协议、编码规范和测试连续性被引用或明确标记缺失；
5. blocker、finding、历史不一致和 residual risk 未丢失；
6. evidence 与命令可由 fresh session 独立复核；
7. Bootstrap Capsule 足够小，且没有要求全量读取历史；
8. `ExpectedControllerState` 与 counterfactual traps 齐全；
9. 只有一个下一安全动作，并提供可复制提示词；
10. Producer attestation 已完成；successor 双签仍需 fresh session 独立完成。

`HANDOFF_PACKAGE_READY` 仅表示交接包可供接班验证，不表示 successor 已接班、任务已完成或用户已验收。
