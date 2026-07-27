# Loop 工程控制与交付系统设计提案

## 文档状态

- status: `proposed`
- version: `v0.2`
- date: `2026-07-22`
- supersedes: `loop-engineering-system-design.proposed.v0.1.md` as the current design proposal
- authority: product/design proposal only; implementation truth remains in the repository
- project: `C:\Users\Administrator\.codex\loop-engine-lab`

本版本吸收原 `v0.1` 设计和用户补充说明，重点把产品定位、硬约束、角色能力、
角色 Loop、阶段 Loop、跨宿主适配和可执行路线分开定义。它不是已经完成的产品，
也不授权安装、激活、部署或进入外部业务项目。

## 0. 一句话定义

> Loop 是一个可独立运行、也可作为外部 Agent 接入 Codex、Claude Code、Zcode、
> Qoder 等 AI 编程宿主的软件工程控制与交付系统：它识别项目复杂度，在需要时
> 强制进入完整工程流程，并用运行时约束、确定性质量检查、独立评审、证据和人工
> Gate 阻止没有充分依据的结果进入下一阶段。

## 1. 产品身份与用户结果

### 1.1 它不是治理文档项目

`loop-engineering-lab` 本身就是 Loop 产品的真实开发项目。治理、Gate、角色、
证据和交接是产品能力和开发手段，不是产品最终目标。

产品最终要补上 AI 编程工具缺失的软件工程责任，使用户不需要审核代码，也不需要
判断架构、测试和安全方案是否专业。

### 1.2 两种运行形态

Loop 支持两种形态，核心契约不因形态变化：

```text
独立模式：用户 -> Loop Runtime -> Loop Core -> 工具/模型/工作区

外部 Agent 模式：AI 宿主 -> Host Adapter -> Loop Core/Runtime -> 结果与约束
```

独立模式中，Loop 可以承担完整的工程编排和执行。外部 Agent 模式中，宿主可以
承担模型对话或具体工具执行，但必须通过 Loop 的任务、证据和约束契约。

### 1.3 用户只承担业务责任

用户负责：

- 说明目标、痛点和业务事实；
- 确认业务规则、优先级和关键取舍；
- 接受或拒绝明确的风险、成本和范围选项；
- 阅读人类可读的阶段交付包并决定是否放行；
- 确认最终产品是否解决了真实问题。

用户不负责：

- 逐行审核源代码；
- 判断函数、模块或架构是否专业；
- 设计测试、评估 coverage 或判断安全边界；
- 证明某个 AI 角色是否已经履行职责。

### 1.4 成功标准

系统成功不是文档多，也不是每轮 reviewer 都返回 `PASS`，而是：

1. 能根据用户意图识别小任务和大型/高风险项目。
2. 大型、复杂、高风险或不确定项目默认升级到完整 Loop。
3. 用户无需懂代码即可通过阶段交付包做业务和风险决策。
4. 没有需求、设计、确定性验证和独立评审证据的结果不能被称为交付完成。
5. 角色结论有真实边界、工具和否决机制，不是同一模型的口头换名。
6. 需求、架构、代码、测试、评审和发布结果可以跨会话恢复并验证新鲜度。
7. 系统能在真实代码上发现预埋缺陷，阻止错误继续流转，完成修复和回归。
8. 最终交付具备构建、运行、观察、回滚和持续维护所需的证据。

## 2. 要解决的问题

### 2.1 AI 生成能力不等于交付能力

当前 AI 编程工具可以生成视觉上完整、语言上合理、局部能运行的 demo，但通常
没有可靠机制持续保证：

- 需求没有被误解或漂移；
- 系统和模块边界能够演进；
- 接口、函数、数据结构和依赖关系稳定；
- 编码规范、错误处理和可维护性被持续执行；
- 测试覆盖用户行为、失败路径、权限、恢复和并发；
- 测试结果真实、可复现且绑定当前代码；
- 安全、构建、部署、监控和回滚没有被忽略；
- 下一轮修改不会破坏既有能力。

### 2.2 用户不能承担技术验收

让完全不懂代码的用户审核 AI 代码，和让用户亲自写代码一样不可靠。Loop 的
设计前提是：AI 工程团队和确定性工具承担技术责任，用户只承担业务结果、取舍
和风险接受。

### 2.3 角色自证是致命缺陷

如果流程是：

```text
AI 写代码 -> AI 自己评审 -> AI 宣布 PASS -> 进入下一阶段
```

它不是软件工程团队，而是自我确认循环。Loop 必须让角色判断变成权限、状态、
工具和证据的可执行约束。

## 3. 设计原则

### 3.1 用户目标是上位约束

AI 可以提出技术方案和取舍影响，但不能把技术建议伪装成用户的业务决定。

### 3.2 角色有固定立场

角色不是临时换面具。每个角色长期保护一类价值，必要时可以阻塞进度、增加
token 消耗或要求返工。

### 3.3 确定性工具优先

能由机器反复、客观、可重现检查的内容必须由机器检查：测试、lint、类型、构建、
coverage、安全、依赖、架构、schema、迁移和证据完整性。AI 负责理解、设计、
权衡、复杂缺陷发现和解释证据，不替代所有工具。

### 3.4 失败必须阻断

以下情况必须停在阻塞状态，不能用“基本完成”“理论可行”或“后续补测试”
弱化：

- 缺少需求基线、架构约束、任务包或可测试验收标准；
- 关键质量检查未执行、执行失败或结果不可证明；
- 生成者和批准者没有职责分离；
- 需求、架构或代码发生变化后仍复用旧结果；
- 存在未处理的安全、权限、数据、部署或恢复风险；
- 修改超出任务范围；
- 宿主能力不足却声称完成了硬约束。

### 3.5 角色 Loop 和阶段 Loop 都不可跳过

主控不是超级角色。即使一个人或一个模型承担多个角色，也必须分别完成角色
职责、分别产出证据，并在适用时使用独立上下文或确定性工具复核。

### 3.6 垂直切片优先

每两到三个任务必须形成一条可运行、可测试、可观察的完整路径。治理产物不能
无限增长而没有真实产品增量。

### 3.7 跨会话靠长期文档和机器状态

产品目标、架构、契约、质量规则、决策和已知问题必须写入稳定项目文档及结构化
状态。`HANDOFF.md` 只能是当前会话的恢复索引，不能成为唯一的长期记忆。

### 3.8 按可交付结果衡量成本

```text
Delivery-Ready 总成本
= 需求理解 + 设计 + 实现 + 验证 + 评审 + 修复
  + 返工 + 上下文恢复 + 用户等待和决策
```

单 Agent 少用 token 但产生无法上线的代码，不等于成本更低。不能通过删除架构、
测试、独立评审或 Gate 来伪造成本优化。

## 4. 总体架构

### 4.1 架构总览

```text
用户意图与产品结果
        |
意图识别与项目分级
        |
Loop Core：规则、状态、角色、工件、质量、证据、Gate
        |
Loop Runtime：会话、工作区、写入、命令、检查、审计、阻断
        |
Host Adapter：Codex / Claude Code / Zcode / Qoder / standalone
        |
模型、工具、代码仓库和运行环境
```

### 4.2 Loop Core

Loop Core 是宿主无关的控制平面，负责：

- 项目意图识别、复杂度和风险分级；
- 需求、范围、验收和变更基线；
- 系统架构、模块架构、接口和设计约束；
- 任务图、阶段、依赖、角色 Loop 和阶段 Loop；
- 角色合同、能力档案、认证和失效状态；
- Quality Profile、质量门禁和验证结果 envelope；
- 工件版本、fingerprint、lineage 和 freshness；
- finding、repair、regression 和 Gate 状态机；
- 人类可读的阶段交付包；
- token、返工、缺陷逃逸和可交付结果成本指标；
- 宿主能力与 enforcement level 注册表。

Core 只接受结构化输入和证据，不接受角色的口头 `PASS` 作为状态转换依据。

### 4.3 Loop Runtime

Runtime 是控制真正生效的执行边界，负责或协调：

- 会话创建、上下文冻结和角色权限；
- 工作区读写、`allowed_write` 和变更 manifest；
- shell、测试、lint、构建和安全命令执行；
- 结果捕获、身份确认、退出码和运行环境绑定；
- 工件写入、版本和证据登记；
- 阶段转换、Gate 检查和失败阻断；
- 独立评审上下文与只读边界；
- 跨会话恢复、恢复探针和状态审计。

没有 Runtime 或宿主拦截能力时，Core 只能报告建议，不能声称完成硬约束。

### 4.4 Host Adapter

适配器把宿主能力转换为 Loop 契约，包括：

- 意图和用户确认入口；
- 文件读取、写入和 diff；
- shell、测试和构建工具；
- 子 Agent、新会话或独立 reviewer；
- Hook、MCP、插件或命令面；
- 用户 Gate 展示和决定回传。

适配器必须逐操作声明能力：

| 能力级别 | 含义 | 可声明结果 |
| --- | --- | --- |
| `HARD` | 能实际阻止对应操作 | 可以声明该操作受硬约束 |
| `PARTIAL` | 只能阻止或验证部分路径 | 只能声明明确子集 |
| `ADVISORY` | 只能提供提示、任务包或审查 | 不得声明硬约束 |

一次交付的可信等级不能高于其关键操作中最弱的 enforcement level。

## 5. 核心领域对象和状态

### 5.1 必须版本化的工件

```text
IntentRecord
ProjectProfile
RequirementsBaseline
ArchitectureBaseline
DetailedDesignPackage
QualityProfile
TaskDeliveryPacket
RoleRun
PhaseDeliveryPacket
EvidenceEnvelope
ReviewReport
Finding
RepairRecord
GateRecord
ReleaseRecord
HostCapabilityProfile
```

每个工件至少包含：`artifact_id`、`revision`、`created_by`、`created_at`、
`source_inputs`、`fingerprint`、`status`、`supersedes`、`freshness` 和适用范围。

### 5.2 关键状态

```text
candidate
-> reviewed
-> user-approved
-> active
-> installed
```

任务和阶段另有执行状态：

```text
planned -> ready -> in_progress -> review_required
-> repair_required -> verified -> awaiting_human_gate
-> accepted / blocked / cancelled
```

任何状态转换都必须经过 Core 的前置条件检查。验证成功不等于用户接受，用户
接受不等于安装或部署授权。

### 5.3 证据 lineage

证据必须绑定：

- 需求、架构、详细设计和任务版本；
- 被检查代码、测试、配置和依赖的 fingerprint；
- 实际执行的 argv、工作目录、环境摘要和退出码；
- 测试身份、发现数量、执行数量和结果摘要；
- 角色、上下文代次和是否独立；
- 结论范围、未验证内容和失效条件。

任何绑定输入改变，相关证据进入 `STALE`，不能被重命名为当前版本 PASS。

## 6. 意图识别与 Loop 路由

### 6.1 路由原则

意图识别是建议起点，但高风险路由必须由结构化规则兜底。无法确定时升级，
不能静默降级。

### 6.2 升级信号

命中以下任一类，默认进入完整 Loop 或要求用户确认降级理由：

- 多模块、多角色、多用户或复杂业务流程；
- 数据库、迁移、认证、权限、支付、秘密或生产数据；
- 外部 API、异步任务、并发、分布式、性能或高可用；
- 需要部署、监控、告警、回滚或长期维护；
- 需要持续迭代、版本兼容或公共 API；
- 用户无法给出清晰验收标准；
- 需求、架构或技术栈存在重大不确定性；
- 任何角色或工具能力不可用但任务仍要求生产交付。

### 6.3 三种模式

- `LIGHTWEIGHT`: 单文件、低风险、无持久数据和外部影响的小改动；
- `FULL_LOOP`: 大型、复杂、长期、高风险或不确定项目；
- `BLOCKED`: 无法建立最低需求/权限/验证条件，或宿主无法提供必要控制。

`LIGHTWEIGHT` 不是绕过质量，而是缩短阶段。安全、权限、生产数据和迁移相关
的任务不能因为规模小就跳过适用门禁。

## 7. AI 工程角色体系

### 7.1 角色合同统一结构

每个角色必须有机器可读、版本化的合同：

```yaml
role_id:
role_version:
identity_and_experience:
fixed_stance:
mission:
responsibilities:
non_responsibilities:
must_read:
inputs:
required_outputs:
required_tools:
quality_checks:
veto_rights:
forbidden_actions:
allowed_write:
evidence_requirements:
handoff_contract:
stop_conditions:
capability_profile:
```

### 7.2 角色清单和固定立场

| 角色 | 固定立场 | 主要否决点 |
| --- | --- | --- |
| 产品经理 | 保护用户价值、需求清晰、范围和可验收性 | 需求不可验收、目标漂移、无授权扩张 |
| 项目经理 | 保护范围、依赖、资源、进度、风险和恢复性 | 依赖未满足、任务过大、阻塞被掩盖 |
| 交付经理 | 保护交付物完整、发布准备、回滚和交接 | 缺构建物、部署、监控、回滚或交接证据 |
| 系统架构师 | 保护系统边界、一致性、演进性和质量属性 | 架构冲突、循环依赖、不可测试或不可恢复 |
| 模块架构师 | 保护组件、接口、类、函数和数据结构契约 | 职责重叠、接口不完整、调用或依赖违规 |
| 开发工程师 | 保护实现质量、编码规范和任务边界 | 需求/架构未批准、写入越界、测试缺失 |
| 质量工程师 | 保护质量门禁、缺陷暴露和证据可信度 | 测试不足、覆盖失真、结果伪造、blocker 未关 |
| 安全工程师 | 保护权限、输入、数据、秘密和攻击面 | 未处理的高风险安全问题 |
| 独立代码评审员 | 保护新鲜、客观和全面的实现评审 | 发现 P0/P1/P2 或无法证明的结论 |
| 发布/运维工程师 | 保护构建、部署、监控、恢复和运行可见性 | 不可部署、不可观察或不可回滚 |
| 主控会话 | 保护事实、顺序、权限、冲突和用户决策 | 越权、伪造角色结论、跳过阶段 |

角色可以由同一模型或同一人执行，但角色结论、权限和证据仍必须分离。

### 7.3 架构师必须交付什么

系统架构师和模块架构师共同把架构变成可执行约束，至少交付：

- 系统边界、上下文和部署拓扑；
- 模块、组件和职责清单；
- 数据流、控制流和生命周期；
- 接口、schema、错误和恢复契约；
- 数据模型、约束和迁移边界；
- 依赖方向、禁止引用和调用关系；
- 安全边界、权限模型和外部输入边界；
- 可观测性、性能、可维护性和扩展策略；
- 测试边界、架构 fitness functions 和验证计划；
- 每个重要决策的理由、替代方案和 ADR。

设计深度按风险分层：系统/模块必须前置定义，组件/接口必须契约化，高风险
函数必须定义职责、不变量、副作用和测试；普通局部变量和实现细节由开发工程师
在规范和检查器约束下决定，避免逐行预设计造成僵化和 token 浪费。

### 7.4 开发工程师的任务包

开发工程师不能只收到“实现登录功能”，必须收到版本化的
`TaskDeliveryPacket`：

- requirement revision 和验收映射；
- architecture/detailed-design revision；
- 模块、组件、接口和数据结构；
- 函数职责、输入输出、副作用和错误处理；
- 允许依赖、禁止依赖和允许写入路径；
- 编码规范、性能和安全要求；
- 必须添加或执行的测试；
- 偏差、阻塞和回退协议；
- 完成交付所需的证据清单。

开发工程师不得自行改变需求或架构。发现设计问题时提交 `ARCHITECTURE_DELTA`
或 `REQUIREMENT_DELTA`，返回对应角色 Loop。

### 7.5 质量工程师从开始参与

质量工程师不是最后运行一条命令，而是贯穿：

```text
需求评审 -> 架构评审 -> 任务评审 -> 测试策略
-> 测试设计 -> 实现评审 -> 测试执行 -> 缺陷分级
-> 修复复验 -> 回归 -> 交付审查 -> 发布审查
```

质量工程师必须建立需求到测试映射，设计正常、边界、错误、权限、恢复、并发和
性能场景，并使用 seeded defects、mutation testing 或等价挑战证明测试确实能发现
已知错误。

### 7.6 角色能力不能靠提示词宣称

每个角色都要有 `Role Capability Profile`：

```yaml
role_id:
role_version:
supported_stacks:
supported_task_types:
required_knowledge:
required_tools:
required_artifacts:
required_checks:
competency_challenges:
minimum_pass_conditions:
known_failure_modes:
abstention_conditions:
independent_verification:
capability_expiry_policy:
```

能力生效需要六层证据：

1. 角色合同；
2. 正确上下文绑定；
3. 工具绑定；
4. 隔离 fixture 中的能力挑战；
5. 生产任务证据；
6. 其他角色、确定性工具或用户 Gate 的独立验证。

认证只证明进入某类任务的资格，不等于当前任务自动合格。连续无证据 PASS、
重复遗漏同类缺陷、越权、无法解释取舍或工具不可用时，角色必须进入
`CAPABILITY_DEGRADED`、`REVALIDATION_REQUIRED` 或 `ROLE_BLOCKED`。

### 7.7 角色能力的运行时验证

角色认证只解决“是否有资格接任务”，运行时还必须解决“这一次是否具备实际履职
条件”和“这一次产出是否真的履行了职责”。三者必须分开：

```text
Capability Certification
-> Role Admission
-> Runtime Role Verification
-> Production Role Effectiveness
```

#### 运行前 Role Admission

角色开始生产任务前，Runtime 必须检查并记录：

- `role_version`、能力认证版本、支持的技术栈和任务类型；
- 当前需求、架构、详细设计、质量 Profile 和代码的 fingerprint；
- 必需工具是否存在、版本是否符合、命令是否可执行；
- 会话是否使用了正确的角色合同、上下文层级和权限；
- `allowed_read`、`allowed_write`、禁止路径和命令边界；
- 是否存在未消费的需求/架构变化或过期能力认证；
- 是否需要独立上下文、只读评审或第二验证者。

任一关键条件不满足，角色不能进入生产任务，必须返回
`CAPABILITY_UNAVAILABLE`、`ROLE_BLOCKED` 或 `USER_DECISION_REQUIRED`。

#### 运行中 Role Verification

每次角色运行都必须生成 `RoleRunEnvelope`，而不是只保存角色的自然语言答案：

```yaml
role_run_id:
role_id:
role_version:
capability_certification_id:
host_adapter_id:
model_identity:
task_id:
phase_id:
input_fingerprints:
tool_preflight:
permission_preflight:
session_isolation:
actions:
output_artifacts:
deterministic_checks:
independent_verification:
vetoes_or_abstentions:
unverified:
verdict:
```

Runtime 至少验证：角色是否读取了规定输入、是否使用了规定工具、是否只做允许
的动作、输出是否满足 schema、证据是否绑定当前版本、是否触发了应有的阻塞条件。
角色“说得专业”不能替代这些检查。

#### 按角色验证实际履职效果

| 角色 | 运行时必须验证的行为 | 失败示例 |
| --- | --- | --- |
| 系统/模块架构师 | 产物字段完整；依赖图无禁止边；接口可转为 schema/contract；架构规则可被检查器执行 | 只画图、不交付接口契约或存在循环依赖 |
| 开发工程师 | diff 在允许路径；代码可编译；lint/type/test 真实执行；依赖方向和接口契约通过 | 修改越界、绕过契约、只改测试让结果通过 |
| 质量工程师 | 需求到测试可追踪；失败/边界/权限场景存在；seeded defect 或 mutation 能被测试捕获；结果 envelope 可信 | 只测 happy path、接受零测试 PASS 或伪造 coverage |
| 安全工程师 | 威胁模型有对应控制；权限负例、输入攻击、秘密和依赖扫描真实执行 | 只列风险清单、不验证控制是否生效 |
| 独立评审员 | 输入冻结；无实现写权限；能发现隐藏缺陷；不能修改后自我通过 | 读取开发者结论后直接复述 PASS |
| 项目/交付/发布角色 | 依赖、风险、构建物、配置、监控、回滚和交接证据与当前版本绑定 | 用历史构建或旧交接包宣称可发布 |

#### 运行后效果判定

角色运行完成后，至少经过一种独立效果验证：确定性检查、其他角色的受限复核、
隐藏挑战、真实缺陷回放或用户阶段 Gate。高风险角色不能只依赖同一上下文的自评。
能力认证和实际任务通过也不能互相替代：认证通过不代表任务通过，任务通过不代表
产品已经被用户接受。

#### 角色失效和降级

Runtime 应累计以下信号：无证据 PASS、应发现缺陷未发现、输出无法被下游消费、
重复越权、工具未执行却声称执行、同类返工无进展。达到 profile 阈值后自动标记
`CAPABILITY_DEGRADED` 或 `REVALIDATION_REQUIRED`，禁止继续接收同类生产任务，直到
重新认证或用户明确接受替代方案。模型切换、宿主切换、技术栈切换或重大规则升级
也应触发重新验证。

## 8. 三层 Loop 模型

### 8.1 角色 Loop

每个角色的最小执行单元都是 Loop：

```text
读取输入与合同
-> 角色计划
-> 执行职责
-> 角色自检
-> 独立检查或确定性检查
-> 修复/重做
-> 形成角色交付物和证据
-> 交接或阻塞
```

角色不能直接把草稿当成阶段结果，也不能把自己的自检当成独立批准。

### 8.2 阶段 Loop

一个阶段可能只有一个 Agent，也可能是一个团队。团队中每个角色先完成 Role
Loop，随后做阶段集成 Loop：

```text
角色交付物
-> 阶段集成
-> 跨角色冲突处理
-> 阶段质量检查
-> 阶段修复和回归
-> Human Review Packet
-> 用户 Gate
```

阶段不能因为主控认为“已经差不多”自动放行。

### 8.3 项目 Loop

```text
用户批准阶段结果
-> 下一阶段输入冻结
-> 角色团队运行
-> 阶段交付包
-> 用户决定继续、返工、改变方向或停止
```

### 8.4 阶段划分

本提案认可 P0-P12 作为稳定的宏阶段编号。它们是跨项目的生命周期坐标和工件
契约，不要求每个项目都产生 13 个独立会话。实际执行由项目的 `Phase Profile`
决定哪些阶段合并、展开或标记为 `NOT_APPLICABLE`，但不得静默跳过适用门禁。

用户提出的阶段与 P0-P12 的对应关系是：需求分析对应 P1-P2，架构设计对应 P3，
详细设计对应 P4，测试设计对应 P5，编码和单元测试对应 P7，集成和功能测试对应
P8，修改优化通常发生在 P7-P9 的修复 Loop，压力与性能测试对应 P9，阶段交付对应
P10-P11，维护对应 P12。

| 阶段 | 目标 | 主要交付包 | 人工 Gate |
| --- | --- | --- | --- |
| P0 启动与分级 | 恢复上下文、识别意图、确定模式 | Project Profile | 是否进入 Full Loop |
| P1 产品发现 | 澄清目标、用户、业务事实和非目标 | Product Brief | 目标是否正确 |
| P2 需求基线 | 需求 ID、范围、验收、风险和变更规则 | Requirements Baseline | 需求基线 |
| P3 整体架构 | 系统边界、技术路线、模块和质量属性 | Architecture Baseline | 架构基线 |
| P4 详细设计 | 组件、接口、类、函数、数据和调用 | Detailed Design Package | 实现准备度 |
| P5 质量/安全设计 | 测试策略、门禁、威胁模型和性能目标 | Quality/Security Profile | 质量方案 |
| P6 任务规划 | 依赖、任务包、资源、风险和顺序 | Task Graph/Packets | 开发准备度 |
| P7 实现与单测 | 受约束编码、单元测试和局部验证 | Code/Test Change Set | 是否进入集成 |
| P8 集成与功能测试 | 集成、契约、E2E 和用户路径 | Integration Test Report | 功能结果 |
| P9 性能与安全验证 | 压力、性能、安全和恢复检查 | Non-functional Report | 发布准备度 |
| P10 交付准备 | 构建、配置、部署、监控、回滚和交接 | Release Packet | 是否发布 |
| P11 用户验收 | 验收真实产品结果和剩余风险 | User Acceptance Record | 产品接受 |
| P12 运行维护 | 监控、缺陷、变更、回归和版本演进 | Operations/Change Record | 继续维护或退出 |

#### Phase Profile 裁剪规则

每个项目在 P0 必须生成 `Phase Profile`，至少声明：

```yaml
profile_id:
project_mode: LIGHTWEIGHT | FULL_LOOP | BLOCKED
phases:
  - phase_id:
    status: required | merged_into | not_applicable
    merge_target:
    reason:
    required_roles:
    required_checks:
    required_gate:
expansion_triggers:
unresolved_decisions:
```

规则如下：

1. `FULL_LOOP` 默认展开所有适用阶段；数据库、权限、秘密、支付、生产数据、
   外部 API、并发、性能、部署和长期维护相关项目不得因“功能看起来简单”而缩短
   安全、质量、交付或恢复检查。
2. `LIGHTWEIGHT` 可以合并阶段，但合并后的交付包必须覆盖被合并阶段的全部输入、
   输出、检查和 Gate。例如 P1+P2 可以形成一个“产品与需求基线”阶段，P3+P4
   可以形成一个低风险“架构与详细设计”阶段。
3. `P9` 只有在没有适用性能、并发、可用性、安全或恢复目标时才能标记
   `NOT_APPLICABLE`，并必须记录理由、证据和用户是否接受该边界。
4. 阶段可以在同一会话内执行，但角色 Loop、确定性检查和人工 Gate 不能因此
   消失。合并的是交付编排，不是质量责任。
5. 任何阶段被标记为 `NOT_APPLICABLE`、合并或降级，都必须进入阶段交付包并由
   Core 记录；主控不能自行删除阶段记录。

因此，P0-P12 既保持统一，又允许按风险合理裁剪；这是本提案采用的阶段模型。

### 8.5 阶段交付包

每个阶段必须生成面向人的 `Human Review Packet`：

- 结论和请求用户决定；
- 本阶段目标和完成范围；
- 关键产物及版本；
- 用户可观察的结果；
- 关键取舍及影响；
- 已验证、未验证和过期证据；
- blocker、已知风险和剩余成本；
- 下一阶段会发生什么；
- 继续、返工、改变方向或停止的选项。

它应让用户判断业务和风险，不要求用户阅读原始日志或逐行代码。

### 8.6 Human Review Packet 通用模板

每个阶段的交付包必须先给人看结论，再给证据入口。推荐使用以下稳定模板：

```markdown
# Human Review Packet: <phase_id> / <packet_id>

## 需要用户决定
- decision: APPROVE_NEXT_PHASE | REQUEST_REPAIR | CHANGE_SCOPE
  | ACCEPT_RISK | STOP
- plain_language_question:

## 本阶段结果
- phase_goal:
- completed_scope:
- user_observable_result:
- not_completed:

## 关键产物
- artifact_id / revision / status:
- requirement_coverage:
- architecture_or_design_coverage:

## 关键取舍
- option_selected:
- alternatives:
- product_impact:
- cost_impact:

## 质量和风险
- verified:
- unverified:
- stale_or_missing_evidence:
- blockers:
- known_risks:
- residual_risk_and_owner:

## 下一步
- next_phase:
- what_will_happen:
- expected_cost_and_wait:

## 证据入口
- summary_manifest:
- detailed_reports:
- raw_logs:
```

用户的动作是业务和风险决策，不是技术签字。若用户无法理解问题，主控必须重新
解释为“产品影响、选项、成本和风险”，不能要求用户自行阅读代码来补足判断。

### 8.7 各阶段必须回答的用户问题

| 阶段 | 交付包必须让用户决定什么 | 用户不需要判断什么 |
| --- | --- | --- |
| P0 | 是否按 `LIGHTWEIGHT` 或 `FULL_LOOP` 推进；是否补充关键信息 | 分类器实现是否专业 |
| P1 | 解决的问题、目标用户和非目标是否正确 | 需求文档格式 |
| P2 | 范围、优先级、业务规则和验收是否符合意图 | 测试是否能覆盖全部边界的技术细节 |
| P3 | 关键技术取舍、成本、风险和长期方向是否接受 | 模块依赖图是否通过静态检查 |
| P4 | 功能行为和重要例外是否符合预期 | 类、函数和变量是否按专业方式设计 |
| P5 | 质量目标、风险零容忍项和可接受例外 | coverage 工具如何实现 |
| P6 | 交付顺序、时间/成本取舍和是否允许并行 | 任务图算法和资源锁实现 |
| P7 | 已实现的用户行为是否符合验收；是否继续集成 | 代码逐行质量和单测写法 |
| P8 | 关键用户路径是否可用；已知失败是否可接受 | 测试框架和 mock 细节 |
| P9 | 性能、安全、恢复结果和剩余风险是否接受 | 压测脚本和扫描器实现 |
| P10 | 是否具备发布、回滚和交接条件 | 构建流水线内部实现 |
| P11 | 产品是否真正解决问题；是否接受明确剩余风险 | 是否每个函数都达到了技术完美 |
| P12 | 继续维护什么、优先级和退出条件 | 监控系统的内部实现 |

如果阶段只涉及技术修复而没有新的用户决策，交付包仍需说明“用户无需决定”，
并保留验证、未验证和下一步信息，不能省略阶段记录。

## 9. 不可绕过的硬约束

### 9.1 操作前置条件

| 操作 | 必须具备 | 缺失时 |
| --- | --- | --- |
| 正式实现 | 需求基线、架构约束、任务包、质量 Profile | `IMPLEMENTATION_BLOCKED` |
| 写文件 | 角色权限、`allowed_write`、活动任务和交易记录 | 拒绝写入 |
| 执行命令 | 允许命令、工作区、执行身份和结果协议 | 拒绝执行 |
| 宣布验证通过 | 结构化结果、当前 fingerprints、退出码和范围 | `EVIDENCE_MISSING` |
| 代码评审通过 | 新鲜上下文、冻结 diff、评审合同 | `REVIEW_BLOCKED` |
| 进入下一阶段 | 无 blocker、所有必需证据新鲜、阶段包完成 | 阶段阻断 |
| 发布 | 交付、构建、运行、监控和回滚证据 | `RELEASE_BLOCKED` |

### 9.2 写入控制

Runtime 或具备拦截能力的适配器必须在写入前检查：

- 当前角色和会话是否有写权限；
- 路径是否在 `allowed_write` 内；
- 文件是否属于当前任务和版本；
- 是否有未消费的需求/架构变化；
- 是否会修改保护文件、历史证据或禁止边界；
- 是否有可恢复的交易记录。

没有物理拦截能力的宿主只能报告 `PARTIAL` 或 `ADVISORY`，不能伪造 `HARD`。

### 9.3 评审隔离

- developer 不能批准自己的代码；
- reviewer 默认只读，不能修复后自我通过；
- repair 会话不能改变原始 finding；
- 质量报告和代码变更分开写入；
- 评审输入在启动时冻结，代码变化后评审结果自动失效；
- 主控只能汇总角色结论，不能冒充角色签字。

### 9.4 证据可信度

测试工具“执行了命令”不等于测试结果可信。结果至少要绑定：实际 argv、退出码、
测试身份、发现和执行数量、stdout/stderr hash、结果 envelope、测试及代码
fingerprint、环境摘要和时间。stdout 只能是诊断信息，不能单独成为测试权威。

## 10. 确定性质量体系

### 10.1 Quality Profile

每个项目和任务必须有 Quality Profile，明确：

- 技术栈和工具版本；
- test、lint、typecheck、build、coverage、security、architecture 和 contract
  命令；
- 必须运行的测试层级；
- 阈值、例外和用户决定；
- seeded defects 或 mutation testing 要求；
- 证据 envelope 和 freshness 规则；
- 失败分级和阻塞语义。

没有 Quality Profile 时，系统不得称为生产级交付，只能返回
`QUALITY_BASELINE_MISSING`。

### 10.2 测试层级

根据风险组合 unit、integration、contract、E2E、performance、security、recovery
和 migration tests。测试数量不是质量，必须证明关键行为和失败路径被覆盖。

### 10.3 缺陷发现能力

质量系统至少周期性使用：

- seeded defects；
- mutation testing；
- 隐藏边界场景；
- 权限绕过和输入攻击挑战；
- 旧证据、伪造结果和需求变化挑战。

质量角色如果连续漏掉应被发现的缺陷，必须降级或重新认证。

### 10.4 质量结论

```text
PASS        所有适用门禁通过且证据新鲜
REPAIR_REQUIRED  有可修复 finding 或验证失败
BLOCKED     缺工具、权限、输入或无法形成可信证据
USER_DECISION_REQUIRED  技术上可继续但涉及用户取舍/风险接受
```

任何 `PASS` 必须说明检查范围、证据路径和未检查内容。

## 11. 评审、缺陷和修复

### 11.1 评审类型

- 产品/需求评审；
- 系统/模块架构评审；
- 详细设计评审；
- 代码和可维护性评审；
- 质量和测试评审；
- 安全评审；
- 性能评审；
- 发布/运维评审；
- 跨会话和证据连续性审计。

评审类型不能因为主控方便而合并成一个无立场的泛化 `reviewer`。

### 11.2 Finding 生命周期

```text
open -> triaged -> repair_authorized -> repaired
-> independently_verified -> closed
```

finding 不能被生成者自己删除或改成无问题。严重级别、影响、位置、复现、最小
修复、验证方式和适用范围必须结构化记录。

### 11.3 修复规则

```text
reproduce -> failing test/evidence -> fix -> regression -> independent review
```

预算耗尽、无法复现或需要越权时必须停住并说明下一步，不得返回假 PASS。

## 12. 跨会话治理与长期记忆

### 12.1 权威层级

跨会话必须读取和更新长期文档，不依赖聊天记忆或交接文档单独恢复：

1. `.ai/PROJECT.md`：产品身份、最终目标和用户结果；
2. `.ai/ARCHITECTURE.md`：架构、模块和边界；
3. `.ai/CONTRACTS.md`：权限、接口、生命周期和证据合同；
4. `.ai/ACCEPTANCE.md`：产品和任务验收；
5. `.ai/QUALITY_GATES.md`：质量和发布门禁；
6. `.ai/DECISIONS.md`、`docs/decisions/`：决策和理由；
7. `.ai/KNOWN_ISSUES.md`：已知问题和限制；
8. `.ai/PROGRESS.md`：长期进度和当前方向；
9. `.ai/state.yaml`、`.ai/gates.yaml`、`.ai/task_graph.yaml`：机器状态和授权事实；
10. `.ai/HANDOFF.md`：当前会话恢复索引和证据入口。

HANDOFF 可以投影上述信息，不能创造、替代或提升它们。若 HANDOFF 与长期文档
或机器状态冲突，以权威文档和机器状态为准，并进入 `CONTINUITY_CONFLICT`。

### 12.2 会话恢复

新会话必须：

1. 读取用户最新请求；
2. 确认项目根目录；
3. 读取长期文档、当前状态、Gate、任务图和当前任务；
4. 运行确定性状态校验；
5. 检查未消费需求变化、旧证据和当前方向；
6. 生成当前会话契约；
7. 只在活动任务和授权范围内继续。

### 12.3 文档演进

重要目标、架构和决策必须版本化。决策改变时新增 ADR 并标记 supersedes，不能
删除旧决策或把新观点覆盖到历史记录上。

## 13. 宿主适配和能力认证

### 13.1 适配器契约

每个适配器必须声明：

```yaml
adapter_id:
adapter_version:
host_name:
supported_operations:
intercepted_operations:
enforcement_level:
session_isolation:
write_control:
command_control:
approval_surface:
evidence_binding:
known_bypasses:
certification_tests:
```

### 13.2 适配器不能过度承诺

宿主没有写入、命令或阶段拦截能力时，Loop 仍可以提供任务包和审查，但交付包
必须明确：哪些操作由 Loop 硬阻断，哪些只是建议或事后发现。

### 13.3 适配器认证

适配器必须通过：

- 越界写入挑战；
- 未授权命令挑战；
- 阶段跳转挑战；
- 旧证据复用挑战；
- reviewer 自我批准挑战；
- 断线和跨会话恢复挑战。

认证结果只对适配器版本、宿主版本和操作范围有效。

## 14. Token、时间和返工成本

### 14.1 成本预算

预算分四层：项目、阶段、角色、评审/修复。预算耗尽时返回：

```text
BUDGET_EXHAUSTED
-> 保存已有证据
-> 标记未完成项
-> 输出安全的下一步
-> 等待用户决定是否继续投入
```

### 14.2 合法的成本优化

- 按角色加载必要上下文；
- 使用版本化工件引用和片段，而不是重复粘贴全文；
- 先运行确定性工具，再让 AI 分析失败；
- 并行互不依赖的检查；
- 高风险区域优先评审；
- 早发现需求和架构错误；
- 限制无进展重试；
- 记录返工原因和上下文缺失。

### 14.3 不能用来省 token 的内容

- 需求基线；
- 关键架构和详细设计；
- 关键测试和失败路径；
- 安全检查；
- 独立评审；
- 修复后的回归；
- 阶段交付包和人工 Gate；
- 未验证项和已知风险。

### 14.4 核心指标

- `Cost per Delivery-Ready Outcome`；
- `Cost per User-Accepted Outcome`；
- `Rework Ratio`；
- `Escaped Defect Ratio`；
- `First-Pass Quality Rate`；
- 每角色和每阶段的 token 与等待时间。

## 15. 主要风险与对策

| 风险 | 表现 | 必须的对策 |
| --- | --- | --- |
| 角色模拟 | 角色都有名字但没有否决权 | 合同、权限、工具、能力挑战和独立证据 |
| 主控集权 | 主控伪造或覆盖专业结论 | 角色结果独立存储，状态机拒绝越权 |
| 测试假通过 | stdout 或旧结果被当成当前 PASS | 结构化 envelope、fingerprint、退出码和 freshness |
| 架构漂移 | 局部合理导致整体失控 | 版本化架构、依赖检查、fitness functions |
| 需求漂移 | 旧代码和旧测试继续被复用 | requirement revision、delta、generation fence |
| 安全遗漏 | 功能可用但权限和输入不安全 | 独立安全角色、攻击面和阻塞门禁 |
| 治理自循环 | 文档增加但真实产品没有进展 | 真实垂直切片、用户结果和阶段预算 |
| 过度设计 | 前置设计到变量级，成本高且僵化 | 按风险分层设计，详细设计与实现解耦 |
| 宿主能力幻觉 | 弱集成被描述成硬控制 | 适配器能力认证和 enforcement level |
| 角色能力退化 | 重复漏缺陷或无证据 PASS | 失效检测、降级、重新认证和任务阻断 |

## 16. 产品建设路线

### Phase 0：产品基线

完成产品身份、用户结果、Core/Runtime/Adapter 边界、权威文档、角色和质量
设计原则。通过标准是设计不再把 Loop 当作治理文档集合。

### Phase 1：Core 契约与状态内核

实现或验证：

- 领域对象 schema；
- 项目分级和路由；
- 工件 lineage、fingerprint 和 freshness；
- 角色/阶段/任务/Gate 状态机；
- finding/repair/regression 状态；
- 文档权威和 HANDOFF 投影检查。

### Phase 2：确定性 Runtime

实现独立运行所需的：

- workspace 和 `allowed_write`；
- 命令白名单和结果 envelope；
- 交易、恢复和审计；
- 质量 runner；
- 证据 manifest；
- 失败关闭和阻断。

### Phase 3：角色和阶段执行骨架

实现角色合同、能力档案、上下文包、角色 Loop、阶段 Loop、独立评审和 Human
Review Packet。先支持少量高价值角色，必须先验证职责实际生效，再扩展角色数量。

### Phase 4：第一条自举垂直切片

使用已经实现的 Loop 开发 `loop-engineering-lab` 的一个真实产品能力，完整经历
需求、架构、详细设计、质量、实现、测试、评审、修复、回归和阶段 Gate。必须植入
预埋缺陷或伪证据场景，证明系统能发现并阻断。

### Phase 5：第一适配器

选择一个能力最完整的宿主实现适配器，优先支持能验证写入、命令和会话边界的宿主。
认证适配器后，再扩展其他宿主；弱宿主只能提供明确的 advisory 能力。

### Phase 6：发布和自验证

验证跨会话恢复、质量证据、角色失效、发布/回滚、成本指标和用户负担。Loop
必须能够使用自身管理后续版本，而不是只在文档中宣称自举成功。

## 17. 全局 Definition of Done

产品增量只有在适用项全部满足后才可称为技术交付完成：

### 需求与设计

- 需求基线、ID、验收和非目标存在；
- 整体架构、模块、接口和详细设计存在；
- 关键取舍有 ADR；
- 安全、性能、可维护性、部署和恢复边界明确；
- 没有未消费的需求变化。

### 实现与验证

- 修改在任务和 `allowed_write` 范围内；
- 代码符合编码规范和架构依赖；
- 错误、边界、权限和外部输入有处理；
- 测试真实执行且证据绑定当前输入；
- lint、typecheck、build、coverage、安全和架构检查通过或有明确例外；
- 关键用户路径和失败路径通过。

### 评审与交付

- 代码、架构、质量和安全评审已完成；
- 评审具有足够独立性；
- 所有 blocker 已关闭；
- 修复后完成回归；
- 构建物、部署、监控、日志、回滚和恢复可追踪；
- 已知问题和未验证内容透明；
- 阶段交付包已由用户放行；
- 用户可根据可观察结果验收产品。

## 18. 仍需用户决定的事项

以下是业务和产品选择，不能由 AI 自行写成既定事实：

1. 第一适配宿主的优先顺序；
2. 第一版本支持的技术栈和运行环境；
3. 首个自举垂直切片的具体能力；
4. 本地独立运行、外部 Agent 接入和宿主插件的发布顺序；
5. 成本、速度、质量和功能范围的优先级；
6. 哪些风险零容忍，哪些风险可以由用户明确接受；
7. 哪些低风险角色可以复用上下文，哪些角色必须新鲜独立会话。

AI 可以给候选方案、成本和影响分析，但不能替用户做上述决定。

## 19. 不在本提案授权范围内

本提案不授权：

- 修改 `AGENTS.md` 或全局 Codex/宿主配置；
- 安装或启用 runtime、plugin、skill、MCP、agent、automation、protocol 或 hook；
- 自动进入外部真实业务项目；
- 部署、发布、回滚或触碰生产数据；
- 修改数据库、权限、秘密、支付或迁移；
- 把 reviewer、validator、测试或 AI 建议提升为用户验收；
- 把本提案直接写成已实现、已激活或生产可用。

## 20. 最终结论

Loop 要建设的不是“主控 Agent 加几个专业提示词”，而是一套让 AI 软件工程
责任真正生效的控制与交付系统：

```text
意图识别和项目分级
-> 需求与架构基线
-> 角色 Loop
-> 阶段 Loop
-> 确定性 Runtime 和质量门禁
-> 独立评审、修复和回归
-> 证据、freshness 和跨会话恢复
-> 人类阶段 Gate
-> 真实运行和用户验收
```

角色“有灵魂”必须表现为固定立场、不可越权、能够否决、能够停住、能够被能力
挑战和生产证据验证。工程“生产级”不是角色自称的结果，而是确定性检查、独立
评审、真实缺陷挑战、运行证据和用户结果共同建立的结果。

v0.2 的核心收敛是：先建宿主无关的 Core 契约和可执行的硬约束，再建 Runtime、
角色执行骨架和第一适配器，最后用 Loop 自己开发和验证 Loop。这样可以在保证质量
的前提下减少返工，把 token 投入真正降低交付风险的判断和证据。
