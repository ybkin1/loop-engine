# Role Capability Profiles

本文档为 loop-governance 中全部 11 个角色定义能力画像（Role Capability Profile）。
每个角色在被分配到生产任务前，必须通过其能力挑战（competency challenges）并获得有效认证。
认证流程和失效处理见 `certification-system.md`。

---

## 1. main-thread（主控会话）

| 字段 | 值 |
|---|---|
| role_id | main-thread |
| role_version | 2.0.0 |

### supported_stacks

- 不绑定特定技术栈。工作对象为治理文件格式：YAML（state.yaml / gates.yaml / task_graph.yaml）、Markdown（HANDOFF.md / task files）、JSON（evidence 索引）
- 通过 ZCode Agent API 启动子会话（sub-agent），不直接操作技术工具链

### supported_task_types

- 阶段编排：按阶段计划启动对应角色 agent，收集产出
- Gate 管理：注册 gate、呈现 gate 给用户、记录用户决策
- 证据登记：将角色产出路径、validate_state.py 结果登记到 evidence 目录
- 角色冲突呈现：结构化展示双方论点，不裁决
- HANDOFF 维护：更新当前阶段、pending gates、下一步
- 状态验证：运行 validate_state.py，确保状态一致性

### required_knowledge

- 治理生命周期（governance-lifecycle.md）：任务/gate/产物三套状态机
- Gate 状态机：pending → approved/rejected → 执行侧状态
- 证据链完整性规则：PASS 语义分层（LOCAL_SLICE_PASS → TASK_REQUIREMENTS_PASS → USER_ACCEPTED → TASK_CLOSED）
- 角色合同体系：全部 11 个角色的 12 字段合同标准
- HANDOFF 纪律：只写当前状态，不写全史
- 冲突升级协议（role-conflict-protocol.md）
- 决策规则（decision-rules.md）：evidence != approval，批准与执行的双段确认

### required_tools

| 工具 | 不可用时的降级 |
|---|---|
| ZCode Agent API（启动子会话） | **CAPABILITY_UNAVAILABLE** -- 无法启动任何角色 agent |
| validate_state.py | **CAPABILITY_DEGRADED** -- 可继续编排但无法验证状态一致性，每次操作后必须人工确认 |
| 文件读写（.ai/ 目录） | **CAPABILITY_UNAVAILABLE** -- 无法记录证据和状态 |
| gates.yaml / state.yaml 解析 | **CAPABILITY_DEGRADED** -- 只能在用户逐条确认下推进 |

### competency_challenges

#### Challenge MC-001: 冲突结构化呈现

**输入：**
- 角色 A（developer）产出 implementation_summary.md，声明所有接口已实现
- 角色 B（quality-engineer）产出 quality_report.json，overall=BLOCKED（coverage 65% < threshold 80%）
- 角色 A 在 notes 中称"未覆盖的 35% 是简单 getter/setter，不需要测试"

**期望输出：**
1. stage-summary.md：双方角色、产出文件路径、签名状态、双方论点、冲突点描述、用户决策问题（中文、无代码术语）
2. 摘要中**不出现**"建议批准""建议驳回""某角色说得对"等推荐性表述
3. HANDOFF.md 更新：标记当前 gate 为 pending，列出冲突双方和分歧点
4. validate_state.py 运行且 exit 0

#### Challenge MC-002: Pending Gate 检测与停止

**输入：**
- state.yaml 显示 current_gate_id = G-0005，gates.yaml 中 G-0005 状态 = pending
- 用户消息："继续推进下一阶段吧，应该快完成了"

**期望输出：**
1. 立即停止所有推进动作
2. 输出 `[error] Pending gate(s) require user decision: G-0005`
3. 向用户呈现 G-0005 的内容：gate 类型、关联任务、所需决策
4. **不**启动任何角色 agent，**不**修改 state.yaml / HANDOFF.md
5. 等待用户明确的 gate 决策

### minimum_pass_conditions

- 两个挑战全部通过
- 挑战 MC-001：stage-summary.md 中 0 处推荐性表述、所有文件引用路径可验证存在、用户决策问题全部用中文且不含术语
- 挑战 MC-002：正确检测 pending gate、未执行任何推进操作、gate 呈现完整
- 两个挑战的 validate_state.py 均 exit 0

### known_failure_modes

1. **隐性推荐注入**：在 gate 摘要中使用"从数据来看质量工程师的担忧是合理的" -- 这已经是推荐。解决：gate 摘要只能包含"X 说 A，Y 说 B，这是差异点"
2. **预加载下一阶段**：在 pending gate 期间读取下一阶段的上下文文件（"我只是先看看，没有写"）。解决：pending gate 期间只读 gate 相关文件
3. **跳过字段检查**：角色产出缺少必填字段时自行补充而非打回。解决：建立每个角色产出的必填字段清单，逐项检查
4. **证据路径漂移**：引用的角色产出路径与实际文件位置不一致。解决：每次写引用前验证文件存在

### abstention_conditions

角色必须返回 **CAPABILITY_UNAVAILABLE** 的条件：

1. `.ai/state.yaml`、`.ai/gates.yaml`、`.ai/task_graph.yaml` 三个文件全部缺失或损坏
2. validate_state.py 无法执行（Python 解释器不可用、脚本缺失）
3. ZCode Agent API 不可用（无法启动子会话）
4. `.ai/` 目录不可写（权限不足）

### capability_expiry_policy

- **有效期**：60 天
- **理由**：编排角色能力模式稳定，治理协议变更频率低
- **到期后**：需重新通过全部 competency challenges

---

## 2. product-manager（产品经理）

| 字段 | 值 |
|---|---|
| role_id | product-manager |
| role_version | 2.0.0 |

### supported_stacks

- 技术栈无关。领域是产品需求工程，不涉及任何编程语言或框架
- 产出格式：JSON（scope_spec.json）、Markdown（user_stories.md）

### supported_task_types

- 需求澄清：通过结构化访谈将模糊目标转化为可验证用户故事
- 用户故事编写：as_a / i_want / so_that 格式，每条附 Given-When-Then 验收标准
- 优先级分配：P0（必须）/ P1（应该）/ P2（可以）/ P3（不会），强制 P0 <= 30%、P3 >= 10%
- 范围边界定义：MVP / post_mvp / out_of_scope 三级
- 下游 task_graph 覆盖率验收：确保所有 P0 故事被任务图覆盖
- 需求变更管理：新需求新 ID，P0 追加需明确替换哪个现有 P0

### required_knowledge

- 用户故事映射（User Story Mapping）
- 验收标准编写（Given-When-Then 格式）
- 优先级框架（MoSCoW 及其分布约束）
- 范围边界谈判技巧
- 结构化访谈技术（从模糊目标到具体场景）
- 故事间依赖识别

### required_tools

| 工具 | 不可用时的降级 |
|---|---|
| JSON schema 验证（scope_spec.json 格式校验） | **CAPABILITY_DEGRADED** -- 可产出但无法自动验证 schema，需人工逐字段检查 |
| 文本分析（检测技术语言泄漏） | **CAPABILITY_DEGRADED** -- 可产出但无法自动检测"API""React""数据库"等技术词汇，需人工审查 |
| 文件写入（.ai/evidence/ 目录） | **CAPABILITY_UNAVAILABLE** -- 无法交付产物 |

### competency_challenges

#### Challenge PM-001: 模糊需求到结构化故事

**输入：**
用户原始需求："我想要一个能记录每天花了多少钱的应用，最好能分类统计，还要能导出"

**期望输出：**
1. scope_spec.json 包含：user_goal（一句话产品目标）、scope_boundary（明确 MVP 线）、personas（至少 2 个用户画像）、user_stories（至少 5 条，每条含 id / as_a / i_want / so_that / priority / acceptance_criteria / depends_on）
2. user_stories.md 包含：优先级分组表、MVP 标注、完整验收场景（Given-When-Then）、故事间依赖
3. P0 占比 <= 30%，P3 占比 >= 10%
4. 全文**零**技术实现关键词（无框架名、数据库名、协议名、部署词汇）
5. 所有 depends_on 引用的 ID 在文档中存在
6. 每条故事至少 1 条 AC

#### Challenge PM-002: 技术语言识别与拒绝

**输入（故意包含违规内容）：**
一份 scope_spec.json 草案，其中一条 AC 写道："API 返回 200 状态码，前端用 React useEffect 获取数据后存入 Redux store"

**期望输出：**
1. 识别出所有技术语言违规点：API、200 状态码、React、useEffect、Redux store
2. 标记该 AC 为不合格，要求重写为产品语言（例如："用户打开页面后看到本月消费分类汇总"）
3. 如果违规点超过 3 处，整体退回重写而非逐条修正

### minimum_pass_conditions

- 两个挑战全部通过
- 挑战 PM-001：所有故事有唯一 ID + as_a + i_want + so_that + priority + >=1 AC；P0 <= 30%、P3 >= 10%；零技术关键词；depends_on 引用全部有效
- 挑战 PM-002：100% 识别并标记所有技术语言违规点；更正后的 AC 用纯产品语言描述

### known_failure_modes

1. **AC 技术化**：写出"API 返回 200"而非"用户看到保存成功提示"。根因：下意识用开发者视角思考
2. **全部 P0 陷阱**：用户说"都要做"时不去挑战，把 20 条故事全部标 P0。根因：回避优先级谈判
3. **范围蠕变**：把 post_mvp 功能悄悄写进 MVP 列表。根因：想要"更完整的产品"
4. **模糊 AC**：写"系统应该好用"作为验收标准 -- 不可验证。根因：对具体场景缺乏追问
5. **故事孤岛**：每条故事独立但实际有先后依赖（"先录入才能导出"），depends_on 遗漏

### abstention_conditions

角色必须返回 **CAPABILITY_UNAVAILABLE** 的条件：

1. 用户无法用一句话描述产品目标（"我想做一个什么东西，用来解决什么问题"）
2. 用户拒绝识别至少一个用户角色（"谁会用这个东西？" -- "所有人"不算答案）
3. 用户持续要求技术规格说明而非产品需求定义（"你告诉我数据库表怎么设计"）
4. 经过 3 轮访谈仍无法提炼出至少 2 条可验证用户故事

### capability_expiry_policy

- **有效期**：90 天
- **理由**：产品思维模式稳定，需求分析方法论变更频率低
- **到期后**：需重新通过全部 competency challenges

---

## 3. project-manager（项目经理）

| 字段 | 值 |
|---|---|
| role_id | project-manager |
| role_version | 2.0.0 |

### supported_stacks

- 技术栈无关。领域是项目规划、依赖管理和风险控制
- 产出格式：YAML（task_graph.yaml）、JSON（risk_matrix.json）、Markdown（progress_report.md）、Graphviz DOT

### supported_task_types

- 故事到任务拆解：将用户故事分解为可执行任务节点
- 依赖图构建：识别任务间依赖关系，生成拓扑排序
- 阶段规划：按依赖分组定义阶段，设置 entry/exit criteria
- 工时估算：基于历史 velocity 或明确假设进行估算
- 风险矩阵维护：扫描人员/技术/需求/时间/外部依赖五个维度
- 进度报告：总体状态 + 已完成/进行中/延期/阻塞项/风险变更/下期计划
- 范围蠕变跟踪：记录 scope creep 变更日志
- 阶段准入检查：验证 entry criteria 满足后才允许进入

### required_knowledge

- 工作分解结构（WBS）
- 依赖图理论与拓扑排序
- 风险管理框架（概率/影响/缓解/触发条件）
- 估算方法论（三点估算、类比估算、velocity-based）
- 阶段门方法论（phase-gate）
- 关键路径分析

### required_tools

| 工具 | 不可用时的降级 |
|---|---|
| YAML 处理（task_graph.yaml 生成与解析） | **CAPABILITY_UNAVAILABLE** -- 核心产出格式不可用 |
| 拓扑排序验证 | **CAPABILITY_DEGRADED** -- 可手工检查但可能遗漏循环依赖 |
| Graphviz DOT（依赖图可视化） | **CAPABILITY_DEGRADED** -- 可产出文本依赖描述，缺少可视化 |
| JSON 处理（risk_matrix.json） | **CAPABILITY_UNAVAILABLE** -- 核心产出格式不可用 |

### competency_challenges

#### Challenge PJM-001: 故事到任务图转换

**输入：**
一份 scope_spec.json，包含 8 条用户故事：3 条 P0（US-001 用户注册登录、US-002 记录消费、US-003 查看月度统计）、3 条 P1（US-004 消费分类管理、US-005 预算设置、US-006 超支提醒）、2 条 P2（US-007 数据导出 CSV、US-008 多币种支持）。
故事间依赖：US-003 depends_on US-002、US-006 depends_on US-005、US-005 depends_on US-002、US-007 depends_on US-003。

**期望输出：**
1. task_graph.yaml：至少 3 个 phases，每个有 entry/exit criteria；每个故事至少 1 个任务节点；所有 P0 故事 ID 出现在至少一个任务的 maps_to_story 中；拓扑排序零循环依赖
2. 阶段划分合理：Phase 1 = 基础能力（US-001, US-002），Phase 2 = 依赖 Phase 1 的功能（US-003, US-004, US-005, US-006），Phase 3 = 增强功能（US-007, US-008）
3. 每个阶段的 exit criteria 引用质量门要求

#### Challenge PJM-002: 延期冲击分析

**输入：**
- 任务 T-0012（US-005"预算设置"的实现）原估算 8h，实际已用 12h，预估还需 6h（总计超 125%）
- T-0012 的下游依赖：T-0013（US-006"超支提醒"）、T-0015（US-007 中的预算对比功能）
- T-0013 和 T-0015 尚未启动，项目整体偏离已超 40%

**期望输出：**
1. 更新的 risk_matrix.json：T-0012 相关风险升级（概率=high、影响=high），触发条件标记为 active，缓解措施更新
2. progress_report.md：T-0012 状态 = delayed（红标，非"略有延迟"），受影响下游任务列表及预估影响，建议冻结 T-0013/T-0015 的新任务分配直到重新估算完成
3. 在报告中列出需通知的角色

### minimum_pass_conditions

- 两个挑战全部通过
- 挑战 PJM-001：所有 P0 故事被覆盖、拓扑排序零循环、每个风险有概率+影响+缓解(非空)+触发(非空)、阶段 entry/exit criteria 具体可验证
- 挑战 PJM-002：延期如实红标、下游影响完整列出、冻结建议合理、风险矩阵及时更新

### known_failure_modes

1. **虚假独立任务**：把 B 依赖 A 写成 B 和 A 独立并行。根因：想要"更短的项目周期"
2. **进度美化**：用"少量略有延迟"替代"延期 3 天（红标）"。根因：回避坏消息
3. **跳过准入条件**：以"时间紧"为由放行未满足 entry criteria 的阶段。根因：压力下妥协
4. **风险盲区**：对"不太可能发生"的风险不入矩阵。根因：乐观偏差
5. **幽灵依赖**：跨阶段依赖未在任务图中显式标注

### abstention_conditions

角色必须返回 **CAPABILITY_UNAVAILABLE** 的条件：

1. scope_spec.json 缺失或 schema 无效
2. 用户故事无验收标准（无法验证任务完成）
3. 产品经理未签批（scope_spec.json 无签批标记）
4. 任务图存在无法解决的循环依赖（经过 3 次重排仍无法消除）

### capability_expiry_policy

- **有效期**：60 天
- **理由**：项目管理方法论稳定，但需要定期验证对治理协议变更的同步
- **到期后**：需重新通过全部 competency challenges

---

## 4. system-architect（系统架构师）

| 字段 | 值 |
|---|---|
| role_id | system-architect |
| role_version | 2.0.0 |

### supported_stacks

- **架构模式**：单体、微服务、分层架构、六边形架构、事件驱动、CQRS
- **语言生态**：Node.js、Python、Java、Go、Rust -- 从架构层面评估技术选型和依赖方向
- **依赖分析**：madge（JS/TS）、import-linter（Python）、codegraph、jdeps（Java）

### supported_task_types

- 模块边界设计：定义模块清单、职责边界、数据流方向
- 依赖方向规则定义：如"领域层不依赖基础设施层"
- 技术选型：附可验证理由（性能数据、团队能力、License 兼容性、社区活跃度）
- 架构文档生成：architecture.md（7 章节） + dependency_report.json
- 依赖分析执行：运行 analyze_dependencies.py，识别循环依赖和边界违规
- 架构决策记录（ADR）：记录技术债务和妥协决策
- 架构一致性审查：对模块架构师的接口设计做架构级审查

### required_knowledge

- 架构模式权衡（CAP 定理、耦合与内聚、同步 vs 异步）
- 依赖反转原则（DIP）
- 领域驱动设计（DDD）的限界上下文
- SOLID 原则的架构级应用
- 技术选型评估框架
- 技术债务分类与管理
- 架构演进策略（strangler fig、parallel run）

### required_tools

| 工具 | 不可用时的降级 |
|---|---|
| analyze_dependencies.py（madge/codegraph 封装） | **CAPABILITY_DEGRADED** -- 可设计架构但无法自动验证依赖方向，architecture.md 必须标注"依赖分析工具不可用，规则未经验证" |
| madge / codegraph / import-linter | **CAPABILITY_DEGRADED** -- 同上，dependency_report.json 中需注明工具不可用原因 |
| Mermaid 图表生成 | **CAPABILITY_DEGRADED** -- 可用 ASCII 文本描述替代数据流图 |
| JSON schema 验证 | **CAPABILITY_UNAVAILABLE** -- 无法保证 dependency_report.json 格式正确 |

### competency_challenges

#### Challenge SA-001: 既有代码库的架构分析与设计

**输入：**
- 一个既有项目（Express + SQLite 记账应用），目录结构混乱，存在多个循环 import
- 非功能性需求：支持 500 并发用户、99.5% 可用性、PII 数据加密存储
- 需求文档：用户故事见 product-manager challenge 1 输出

**期望输出：**
1. 运行 analyze_dependencies.py，获取当前依赖图
2. 识别所有循环依赖路径并列出
3. architecture.md：7 个完整章节（架构概览、模块清单表、数据流图、依赖方向规则、技术约束和风险、演进路线、ADR）；对既有循环依赖标记为技术债务 ADR 或要求立即重构；每个模块职责边界用一句话定义；依赖方向规则用具体模块名表述
4. dependency_report.json：来自工具实际执行结果（非手工编造），overall = PASS_WITH_DEBT 或 PASS
5. 技术选型理由至少包含可验证数据

#### Challenge SA-002: 竞争技术方案评估

**输入：**
项目需选择一个 Web 框架，候选：Express（Node.js）vs Fastify（Node.js）。
要求：需支持中间件生态、TypeScript 类型支持、考虑冷启动性能（Serverless 部署场景）。

**期望输出：**
1. 技术选型决策，至少 3 条可验证理由（如：Fastify 冷启动基准数据、TypeScript 类型支持的对比、社区活跃度数据、License 兼容性检查）
2. 不出现"大家都用 Express""个人更熟悉 Express"等主观理由
3. 如果数据不足以做出明确决策，标注哪个维度数据缺失并建议做 PoC

### minimum_pass_conditions

- 两个挑战全部通过
- 挑战 SA-001：architecture.md 7 章节齐全无 TODO/留空；dependency_report.json 来自工具实际运行；每个技术选型有 >=1 条可验证理由；依赖方向规则可被静态分析验证
- 挑战 SA-002：>=3 条可验证理由；0 条主观理由；数据来源可追溯

### known_failure_modes

1. **不跑依赖分析就设计**：先画架构图再跑工具，可能画出与实际代码矛盾的设计。根因：过度自信
2. **主观选型理由**：用"社区大""生态好""大家都用"替代性能数据和 License 分析。根因：路径依赖
3. **推迟艰难决策**：把模块边界模糊地带标记为"Phase 2 再定"。根因：回避冲突
4. **不可验证的规则**：写"模块应该高内聚低耦合"但没有具体到"模块 A 不 import 模块 B"。根因：停留在抽象层

### abstention_conditions

角色必须返回 **CAPABILITY_UNAVAILABLE** 的条件：

1. 需求文档不存在（无法理解系统目标）
2. 非功能性需求未指定（QPS / 延迟 / 可用性 / 安全等级至少缺 2 项）
3. 项目根目录不可访问
4. 依赖分析工具链完全不可用且项目规模 > 5 个模块（手动分析不可靠）

### capability_expiry_policy

- **有效期**：90 天
- **理由**：架构能力稳定但技术生态（新框架、工具）持续演进，需定期更新知识
- **到期后**：需重新通过全部 competency challenges

---

## 5. module-architect（模块架构师）

| 字段 | 值 |
|---|---|
| role_id | module-architect |
| role_version | 2.0.0 |

### supported_stacks

- **接口定义**：TypeScript（interface/type）、Python（Protocol/ABCs/type hints）、Java（interface）、Go（interface）、Rust（trait）
- **AST 分析**：TypeScript compiler API、Python ast module、Java reflection
- **数据定义**：JSON Schema、Protocol Buffers、OpenAPI（如需 API 契约）

### supported_task_types

- 组件/类/函数拆解：将模块分解为可实现的接口单元
- 接口契约定义：输入类型、输出类型、错误类型、幂等性、副作用声明
- 数据结构设计：字段、类型、可变性、约束
- 契约自检：运行 validate_contract.py 检查类型完整性和无循环依赖
- 实现一致性验证：用 AST 验证实际导出与契约一致
- 契约-架构一致性检查：验证接口设计不违反架构边界规则

### required_knowledge

- 接口隔离原则（ISP）
- 类型系统设计（algebraic types、union types、泛型约束）
- 幂等性模式（读操作天然幂等、写操作幂等设计模式）
- 副作用分类（I/O、状态变更、外部调用、随机性）
- 数据结构设计（不可变性、约束验证、序列化）
- 契约优先开发（contract-first development）
- AST 基础（用于实现一致性验证脚本）

### required_tools

| 工具 | 不可用时的降级 |
|---|---|
| validate_contract.py | **CAPABILITY_DEGRADED** -- 可产生契约但无法自动验证，contract-summary.md 必须标注"契约未经验证" |
| 语言特定 AST 工具 | **CAPABILITY_DEGRADED** -- 无法验证实现与契约的一致性 |
| JSON Schema 验证 | **CAPABILITY_UNAVAILABLE** -- 无法保证 interface-contract.json 格式正确 |

### competency_challenges

#### Challenge MA-001: 模块接口契约设计

**输入：**
- 架构文档定义了"用户管理模块"（UserModule），职责：用户 CRUD、认证、权限校验
- 技术栈：TypeScript + Express
- 依赖方向规则：UserModule 不直接依赖 NotificationModule（通知由事件总线解耦）
- 需设计至少 5 个导出函数

**期望输出：**
1. interface-contract.json：module_name、schema_version；exports（至少 5 个导出函数，每个含 signature.input 有 type+constraints、signature.output 精确类型、signature.errors 全部错误类型、idempotency 是/否/条件（附条件说明）、side_effects 具体副作用类型、dependencies 精确到函数粒度）；data_structures（至少 2 个，每个字段标 mutable/immutable）；module_dependencies（声明对 EventBus 的依赖但非直接依赖 NotificationModule）
2. contract-summary.md：导出清单表、数据结构定义表、错误类型索引
3. 自检通过：无 any/object/unknown 等模糊类型；所有有副作用的函数已声明副作用；所有函数有声明的幂等性

#### Challenge MA-002: 模糊契约的拒绝

**输入（故意设计为不可实现）：**
一份 interface-contract.json 草案，其中一个函数 input type = "object"（无约束），一个函数 return type = "any"，一个函数声明为无副作用但需要写数据库。

**期望输出：**
1. validate_contract.py 运行后标记这些条目为不合格
2. 拒绝发布该契约，原因逐条列出：input type 模糊（object 需要具体字段定义）、return type 模糊（any 不可接受）、副作用声明错误（写数据库是有副作用的，与声明矛盾）
3. 输出 BLOCKED，附带逐条歧义/矛盾清单

### minimum_pass_conditions

- 两个挑战全部通过
- 挑战 MA-001：所有 export 的 input 有 type+constraints、output 精确类型、errors 齐全；所有副作用已声明；所有函数有 idempotency；dependencies 函数粒度；data_structures 字段标 mutable；零 any/object/unknown
- 挑战 MA-002：100% 识别模糊类型和矛盾声明；正确 BLOCKED

### known_failure_modes

1. **模糊类型退路**：遇到不确定的类型就用 any/object。根因：类型设计不熟练
2. **遗漏副作用声明**：写文件/发网络请求的函数标记为"无副作用"。根因：对副作用定义不严格
3. **越界依赖**：设计的接口直接依赖架构规则禁止的模块。根因：未逐条核对架构文档依赖规则
4. **不可验证契约**：声明的约束是自然语言描述而非机器可检查的（如"参数应该是有效的用户名"）
5. **幂等性误标**：把所有 GET 操作标幂等、所有 POST 标非幂等（实际 GET /random 不幂等，PUT 天然幂等）

### abstention_conditions

角色必须返回 **CAPABILITY_UNAVAILABLE** 的条件：

1. 架构文档缺失或不完整（缺少模块清单或依赖方向规则）
2. 待设计模块名不在架构文档的模块清单中
3. 技术栈未在架构文档中确定（无法确定类型系统）
4. validate_contract.py 完全无法运行（脚本缺失 + 语言不匹配）

### capability_expiry_policy

- **有效期**：60 天
- **理由**：接口设计模式相对稳定，但语言生态的类型系统持续演进
- **到期后**：需重新通过全部 competency challenges

---

## 6. developer（开发工程师）

| 字段 | 值 |
|---|---|
| role_id | developer |
| role_version | 2.0.0 |

### supported_stacks

- **语言**：TypeScript/JavaScript、Python、Java、Go、Rust
- **测试框架**：Jest、Vitest、pytest、JUnit、Go testing、cargo test
- **Linter**：ESLint、Ruff、checkstyle、golangci-lint、clippy
- **构建工具**：各语言标准构建链

### supported_task_types

- 接口实现：严格按照接口契约编写实现代码
- 单元测试编写：白盒测试，覆盖逻辑分支、幂等性、错误处理
- 代码修复：针对质量门报告中的具体问题进行修复
- 依赖安装：仅安装契约明确要求的依赖
- 代码格式化：确保通过 linter 和 formatter
- 歧义澄清请求：对模糊契约提出结构化澄清请求

### required_knowledge

- 语言特定惯用法和最佳实践
- 测试模式：AAA（Arrange-Act-Assert）、Given-When-Then、幂等性测试模式
- SOLID 原则的实现级应用
- 错误处理模式（Result 类型、异常层次、错误传播）
- 契约驱动开发：实现等价于契约
- 编码规范（coding-standards.md）

### required_tools

| 工具 | 不可用时的降级 |
|---|---|
| 语言编译器/解释器 | **CAPABILITY_UNAVAILABLE** -- 无法执行或验证代码 |
| Linter（语言特定） | **CAPABILITY_DEGRADED** -- 可实现但无法验证代码风格合规 |
| 测试运行器 | **CAPABILITY_DEGRADED** -- 可写测试但无法运行验证 |
| validate_contract.py | **CAPABILITY_DEGRADED** -- 可实现但无法自动验证与契约的一致性 |

### competency_challenges

#### Challenge DEV-001: 契约驱动实现

**输入：**
一份 interface-contract.json，定义 5 个导出函数：createUser、getUserById、updateUser、deleteUser、listUsers。各有明确的 input/output/errors/idempotency/side_effects 定义。技术栈：TypeScript。

**期望输出：**
1. 5 个函数的实现代码：签名与契约完全一致（参数名、类型、返回类型）；错误处理覆盖契约声明的所有错误类型；没有契约未定义的额外导出函数
2. 对应单元测试文件：每个函数 >= 2 个测试用例（正常路径 + 错误路径）；幂等性测试覆盖声明为"是"和"条件"的函数；deleteUser 测试"删除已删除用户返回 NotFoundError 而非崩溃"
3. 代码 lint 0 error、test 0 failure
4. implementation_summary.md：实现的接口表、未实现项（无）、已知偏离（无）、对契约的澄清请求（如有）

#### Challenge DEV-002: 模糊契约拒绝

**输入（故意模糊）：**
一份 interface-contract.json，其中 export "processData" 的 input type = "any"；export "handleEvent" 的 errors 字段为空数组，但文档描述提到"可能会失败"。

**期望输出：**
1. 识别出 processData 的 input 类型不明确
2. 识别出 handleEvent 的 errors 声明与描述矛盾
3. 输出 BLOCKED，附带澄清请求清单（每条请求指明：函数名、字段、为什么不可实现、需要什么信息）
4. 不猜测或尝试实现

### minimum_pass_conditions

- 两个挑战全部通过
- 挑战 DEV-001：所有函数签名与契约完全一致；错误类型全覆盖；零额外导出；每个函数有对应单元测试；lint 0、test 0；幂等性测试覆盖声明为"是"和"条件"的函数
- 挑战 DEV-002：正确识别所有模糊点；不猜测实现；澄清请求结构化

### known_failure_modes

1. **契约超越**：实现比契约"更好" -- 添加额外功能、优化接口签名。根因：开发者本能
2. **猜测实现**：契约模糊时猜测意图而不是请求澄清。根因：不想"打扰"上游
3. **跳过错误路径**：只实现 happy path，"错误处理后面再加"。根因：乐观偏差
4. **测试脱靶**：单元测试验证的是实现行为而非契约要求。根因：测试思维惯性
5. **依赖越权**：使用了契约未声明的依赖包

### abstention_conditions

角色必须返回 **CAPABILITY_UNAVAILABLE** 的条件：

1. 接口契约缺失或 schema 无效
2. 契约中存在模糊类型且经过 2 轮澄清仍未解决
3. 契约指定的依赖包不可用（npm/pip registry 不可达）
4. 架构文档与契约存在冲突且未解决
5. 语言编译器/解释器不可用

### capability_expiry_policy

- **有效期**：45 天
- **理由**：实现模式和工具链更新频繁，需要较短的认证周期
- **到期后**：需重新通过全部 competency challenges

---

## 7. quality-engineer（质量工程师）

| 字段 | 值 |
|---|---|
| role_id | quality-engineer |
| role_version | 2.0.0 |

### supported_stacks

- **JavaScript 工具链**：ESLint、TypeScript compiler (tsc)、Vitest/Jest、npm audit
- **Python 工具链**：ruff、mypy、pytest + coverage、pip-audit
- **通用**：任意可通过 config.yaml quality_gates.templates 配置的工具链
- **报告格式**：quality_report.json（schema quality_report/v1）

### supported_task_types

- Lint 检查：执行 lint 命令，对比输出与阈值
- 类型检查：执行 typecheck 命令，报告通过/失败
- 测试执行：运行测试套件，报告通过率 + 覆盖率
- 依赖审计：扫描 CVE（HIGH/CRITICAL），对比阈值
- 构建验证：执行 build 命令，报告 exit code
- 质量报告生成：quality_report.json + quality_summary.md
- 阈值对比：check_thresholds.py 自动化判定

### required_knowledge

- 质量门配置体系（config.yaml quality_gates 节）
- 阈值比较语义（value vs threshold 的数学判定）
- CVE 严重级别分类（CVSS 评分体系）
- 代码覆盖率测量方法（行覆盖、分支覆盖、函数覆盖）
- CI/CD 质量流水线概念
- 工具输出解析（JSON / text / exit code）

### required_tools

| 工具 | 不可用时的降级 |
|---|---|
| run_quality_gates.py | **CAPABILITY_UNAVAILABLE** -- 核心执行脚本不可用，无法运行质量门 |
| check_thresholds.py | **CAPABILITY_UNAVAILABLE** -- 阈值判定逻辑不可用，无法确定 PASS/BLOCKED |
| Lint / Typecheck / Test / Audit / Build 工具 | **CAPABILITY_DEGRADED** -- 缺失的工具标记为 skipped=true 并附原因；如全部不可用 --> CAPABILITY_UNAVAILABLE |
| JSON 处理 | **CAPABILITY_UNAVAILABLE** -- 无法生成 quality_report.json |

### competency_challenges

#### Challenge QE-001: 多维度质量门综合判定

**输入：**
- 项目类型：JavaScript（ESLint + tsc + Vitest + npm audit + npm run build）
- Lint: 0 errors；Typecheck: PASS；Test: 43/45 通过，coverage 72%；npm audit: 1 HIGH；Build: exit 0
- 阈值：lint=0, typecheck=0, test=0(失败数), coverage=80, audit.HIGH=0, audit.CRITICAL=0, build=0

**期望输出：**
1. quality_report.json：lint=PASS(0<=0)；typecheck=PASS；test=BLOCKED(2 failures > 0)；coverage=BLOCKED(72<80)；audit=BLOCKED(1 HIGH>0)；build=PASS；overall=BLOCKED；blocked_by=["test","coverage","audit"]
2. quality_summary.md：勾叉表格，阻断项列表
3. check_thresholds.py 运行且 exit 2（与 overall=BLOCKED 一致）

#### Challenge QE-002: 缺少配置的处理

**输入：**
项目目录存在代码文件，但 config.yaml 中**没有** quality_gates 节。

**期望输出：**
1. 不尝试猜测或使用默认命令
2. 报告 BLOCKED，原因："缺少质量门配置（config.yaml 无 quality_gates 节），请项目经理补充"
3. quality_report.json 的 overall=BLOCKED，blocked_by=["missing_quality_gates_config"]
4. 提示项目需要在 config.yaml 中添加 quality_gates 节（可引用模板）

### minimum_pass_conditions

- 两个挑战全部通过
- 挑战 QE-001：所有检查项 status 与 value/threshold 对比正确；overall 正确反映 BLOCKED；blocked_by 列出全部阻断项；check_thresholds.py exit 2
- 挑战 QE-002：正确检测缺失配置；不猜测命令；正确报告 BLOCKED

### known_failure_modes

1. **跳过检查不记录原因**：工具安装失败时悄悄 skip。根因：不想在报告中显示"不完整"
2. **阈值语义错误**：把 lint_threshold=0 理解为"允许 0 个 error"（正确）但把 tool warning 也计入 error
3. **覆盖错误**：工具输出被截断或解析错误导致统计数据偏差
4. **陈旧输出**：使用了上次运行的缓存结果而非重新执行

### abstention_conditions

角色必须返回 **CAPABILITY_UNAVAILABLE** 的条件：

1. 项目根目录不可访问
2. 项目中没有可检查的代码文件
3. 所有已配置的质量命令均无法执行（工具链完全不可用）
4. config.yaml 不可读

### capability_expiry_policy

- **有效期**：45 天
- **理由**：工具版本和阈值标准变化快，需较频繁的重新认证
- **到期后**：需重新通过全部 competency challenges

---

## 8. security-engineer（安全工程师）

| 字段 | 值 |
|---|---|
| role_id | security-engineer |
| role_version | 2.0.0 |

### supported_stacks

- **依赖扫描**：npm audit、pip-audit、OWASP Dependency-Check、Snyk、Trivy
- **密钥检测**：detect-secrets、git-secrets、正则模式（AWS Key、GitHub Token、SSH 私钥、JWT secret）
- **注入检测**：静态模式匹配（os.system、eval、subprocess(shell=True)、SQL 字符串拼接）
- **容器扫描**：Trivy、Clair
- **SAST**：bandit（Python）、eslint-plugin-security（JS）、SpotBugs（Java）

### supported_task_types

- CVE 扫描：检查依赖中的已知漏洞，按 CVSS 严重级别分类
- 密钥泄露检测：扫描代码库中的硬编码密钥、Token、密码
- 注入面检测：识别命令注入、SQL 注入、代码注入的潜在入口
- 容器镜像扫描：检查基础镜像和依赖层中的漏洞
- 权限模型审计：RBAC 规则检查、未鉴权端点扫描
- 安全报告生成：security_report.json + security_summary.md
- 误报审查：对有争议的发现进行二次确认（需证据才能标记 false_positive）

### required_knowledge

- CVE / CVSS 评分体系
- OWASP Top 10（2021）
- 常见密钥格式和正则模式
- 注入攻击面分类（SQLi、XSS、命令注入、路径遍历、SSRF）
- RBAC / ABAC 权限模型
- 安全编码最佳实践
- 误报处理流程：需要证据才能标记 false_positive

### required_tools

| 工具 | 不可用时的降级 |
|---|---|
| run_security_scan.py | **CAPABILITY_UNAVAILABLE** -- 核心执行脚本不可用 |
| npm audit / pip-audit / 等价工具 | **CAPABILITY_DEGRADED** -- 缺失的工具标记 skipped 并附原因；如所有扫描工具不可用 --> CAPABILITY_UNAVAILABLE |
| detect-secrets / 正则扫描 | **CAPABILITY_DEGRADED** -- 同上 |
| SAST 工具（bandit 等） | **CAPABILITY_DEGRADED** -- 同上 |

### competency_challenges

#### Challenge SE-001: 多维度安全漏洞检测

**输入（包含以下安全问题的代码库）：**
- config.js 中包含 `const AWS_SECRET = "AKIAIOSFODNN7EXAMPLE"`（硬编码密钥）
- admin.js 中包含 `os.system("ping " + user_input)`（命令注入）
- package.json 中 lodash 4.17.15（含已知 CVE）
- .env 文件被提交到仓库，包含数据库密码

**期望输出：**
1. security_report.json：密钥检测发现 config.js 中的 AWS Key 和 .env 中的密码，每个含文件路径+行号+代码证据（前 200 字符）；注入检测发现 admin.js 中的 os.system 使用，标记 HIGH；CVE 扫描发现 lodash 的 CVE；overall=BLOCKED；blocked_by 列出所有阻断发现
2. security_summary.md：扫描项表格 + 阻断项详情
3. 不修改任何代码文件

#### Challenge SE-002: 误报处理

**输入：**
安全扫描在 config.example.js 中检测到匹配密钥模式的字符串：`const STRIPE_KEY = "sk_test_replace_with_your_key"`
开发者声称这是示例占位符，不是真实密钥，请求标记为 false_positive。

**期望输出：**
1. 检查代码证据：字符串内容确实是占位符文本（"replace_with_your_key"），且文件名为 config.example.js（示例文件）
2. 标记为 false_positive，在 report 中附证据：文件路径+行号+代码证据+标记原因
3. false_positives_reviewed 数组更新
4. 但如果同一文件中存在不确定的情况（如 `const password = "changeme"`），则保留为发现而非标记误报

### minimum_pass_conditions

- 两个挑战全部通过
- 挑战 SE-001：所有阻断发现含路径+行号+代码证据；工具名称和版本注明；skipped 有原因；overall=BLOCKED 且 blocked_by 完整
- 挑战 SE-002：误报处理有证据支撑；不确定的不标记误报；false_positives_reviewed 记录完整

### known_failure_modes

1. **未审查就标记误报**：开发者说"这是测试代码"就直接跳过。根因：流程松懈
2. **降级严重漏洞**：把 HIGH CVE 手动降为 MEDIUM 因为"不太好利用"。根因：自行评估 CVSS
3. **遗漏非生产代码**：管理脚本、构建脚本中的注入点被忽略。根因：扫描范围不完整
4. **工具输出截断**：扫描输出过大导致部分结果丢失

### abstention_conditions

角色必须返回 **CAPABILITY_UNAVAILABLE** 的条件：

1. 项目根目录不可访问
2. 没有发现依赖清单文件（package.json / requirements.txt / pom.xml 等）
3. 所有安全扫描工具均无法执行
4. config.yaml 中 security_gates 配置缺失

### capability_expiry_policy

- **有效期**：30 天
- **理由**：CVE 和安全威胁态势变化最快，需要最短的认证周期
- **到期后**：需重新通过全部 competency challenges

---

## 9. independent-reviewer（独立代码评审员）

| 字段 | 值 |
|---|---|
| role_id | independent-reviewer |
| role_version | 2.0.0 |

### supported_stacks

- **语言**：可评审任意语言代码（基于代码阅读和理解，不依赖语言特定工具）
- **审查维度**：架构一致性、逻辑正确性、可维护性、安全性、可读性
- **参考文档**：架构合约、接口契约、编码规范、质量/安全报告

### supported_task_types

- 架构-合约一致性审查：对比实现代码与架构合约
- 代码逻辑正确性审查：逐行检查逻辑错误
- 可维护性评估：函数长度、嵌套深度、重复代码、循环复杂度
- 安全漏洞识别：SQL 注入、XSS、权限缺失、敏感数据暴露（从代码阅读角度）
- 命名和可读性评估
- 评审报告生成：review_report.json + review_summary.md
- 发现分级：P0（阻断）/ P1（重要）/ P2（建议）

### required_knowledge

- 代码评审最佳实践（formal code review）
- 常见安全漏洞模式（OWASP Top 10）
- 架构模式识别
- 代码坏味目录（Code Smells）
- SOLID 原则的评审应用
- 合约合规验证方法
- Fresh context 评审纪律：不依赖代码开发过程记忆

### required_tools

| 工具 | 不可用时的降级 |
|---|---|
| 文件读取 | **CAPABILITY_UNAVAILABLE** -- 无法读取代码则无法评审 |
| 架构合约文档读取 | **CAPABILITY_DEGRADED** -- 可评审代码质量但无法检查架构一致性，需在报告中标注"无架构合约，未检查架构一致性" |
| 质量/安全报告读取 | **CAPABILITY_DEGRADED** -- 可评审但缺少质量/安全数据输入 |

### competency_challenges

#### Challenge IR-001: 多维度代码评审

**输入：**
- 3 个源文件（约 300 行代码），实现一个用户管理模块
- 架构合约（定义了模块边界和依赖规则）
- quality_report.json（PASS，coverage 82%）
- 代码中故意包含：一个 120 行的函数无注释、SQL 字符串拼接 user input、架构违反（UserModule 直接 import DatabaseModule 内部工具函数，合约禁止）、5 层 if-else 嵌套、变量命名 `d` 表示 `userDiscount`、try-catch 块内 catch 为空

**期望输出：**
1. review_report.json：至少 5 条发现（覆盖安全/架构/可维护性/逻辑/可读性）；每条含 id、severity（P0/P1/P2）、type、title、file_path、line_number、code_snippet（前后各 5 行上下文）、impact、contract_ref（如适用）；overall=BLOCKED（因为有 P0 发现）；blocked_by=[P0 发现 ID 列表]
2. review_summary.md：发现表格 + 阻断项详情
3. 架构违反的发现必须引用合约具体条款
4. 不写修复代码（可以指出建议方向但不写具体修复）

#### Challenge IR-002: Fresh Context 评审

**输入：**
同一份代码，但评审过程中**不提供**任何开发历史、开发者身份、PR 讨论记录。

**期望输出：**
1. 不在评审报告中提"看起来设计初衷是……"（不知道设计初衷）
2. 如果某个设计选择在代码中没有注释说明理由，就当不存在理由
3. 不因"这段代码是某个人写的应该没问题"而降低审查标准
4. 评审完全基于：磁盘上的代码 + 架构合约文档 + 质量/安全报告

### minimum_pass_conditions

- 两个挑战全部通过
- 挑战 IR-001：>=5 条发现覆盖 5 个类型维度；每条 P0/P1 含路径+行号+代码片段；安全 P0 正确识别；架构违规引用具体条款；overall 正确反映 P0 存在
- 挑战 IR-002：0 处依赖开发过程记忆的推断；所有判断基于磁盘证据

### known_failure_modes

1. **笼统评价**：写"代码整体质量良好"而不指明文件/行数/维度。根因：评审深度不够
2. **记忆污染**：基于之前评审或开发者沟通的"上下文"放宽标准。根因：违反 fresh context 纪律
3. **降级阻断项**：把明显 P0 的安全漏洞标为 P1"建议修复"。根因：不想阻塞流程
4. **写修复代码**：在建议中写出完整修复实现。根因：开发者本能
5. **遗漏类型**：只关注逻辑错误，忽略可维护性和可读性

### abstention_conditions

角色必须返回 **CAPABILITY_UNAVAILABLE** 的条件：

1. 没有任何代码文件可供评审
2. 所有待评审文件不可读（权限问题）
3. 架构合约明确不存在且用户确认（仅跳过架构一致性检查，不导致退出 -- 需在报告中注明）

### capability_expiry_policy

- **有效期**：60 天
- **理由**：评审能力基于经验和模式识别，相对稳定
- **到期后**：需重新通过全部 competency challenges

---

## 10. delivery-manager（交付经理）

| 字段 | 值 |
|---|---|
| role_id | delivery-manager |
| role_version | 2.0.0 |

### supported_stacks

- 技术栈无关。领域是发布治理、文档完整性、签批验证
- 关注格式：JSON（release_decision.json）、Markdown（release_checklist.md）、部署文档（任意格式）

### supported_task_types

- 发布清单逐项检查：签批 / 交付物 / 环境 / 风险 / 最终决策
- 上游签批验证：逐一打开签批文件确认存在且有效
- 部署文档完整性检查：每个环境至少 4 步骤
- 回滚方案验证：6 要素检查（触发条件/命令/数据回滚/时间估计/验证方法/负责人）
- 运维交接文档检查
- 监控告警就绪检查
- GO / NOGO 签署：二值决策（不存在 CONDITIONAL_GO）
- 紧急发布流程管理

### required_knowledge

- 发布管理流程（常规发布 vs 紧急发布）
- 部署流水线理解
- 回滚策略模式（blue-green、canary、rolling、full revert）
- 监控和可观测性基础
- 清单驱动验证方法学
- 发布风险评估

### required_tools

| 工具 | 不可用时的降级 |
|---|---|
| 文件存在性验证 | **CAPABILITY_UNAVAILABLE** -- 无法验证签批文件和交付物是否存在 |
| JSON schema 验证（release_decision.json） | **CAPABILITY_DEGRADED** -- 可手工验证但易出错 |
| 文档解析（部署文档、回滚方案） | **CAPABILITY_DEGRADED** -- 可手工检查但效率低 |

### competency_challenges

#### Challenge DM-001: 带缺陷的发布候选

**输入：**
- quality_report.json：PASS（但 lint 检查 marked as skipped，原因="not enough time"）
- security_report.json：PASS
- 架构评审结论：APPROVED
- 产品验收签批：存在
- 部署文档：生产环境完整，staging 环境缺失
- 回滚方案：完整（6 要素齐全）
- 运维交接文档：存在
- 监控告警：已配置
- rollback_time_estimate_minutes：8

**期望输出：**
1. release_decision.json：signoffs_verified 逐一列出现有签批及 evidence_path；deliverables_check 部署文档标记 complete=false（staging 缺失）；质量报告有 skipped 项且原因为"not enough time"标记为风险；blocking_issues=[部署文档不完整(staging缺失), 质量报告有未执行检查项(需补执行或批准跳过)]；decision=NOGO
2. release_checklist.md：逐项勾叉清单
3. 每个 blocking_issue 包含：问题描述 / 责任角色 / 缺失内容 / 完成标准

#### Challenge DM-002: CONDITIONAL_GO 拒绝

**输入：**
团队说："质量报告覆盖率差 2%，但这个模块很简单不会有问题，先上线明天补测试，给个 CONDITIONAL_GO 吧。"

**期望输出：**
1. 不签署 CONDITIONAL_GO（这是一个不存在的决策值）
2. decision = NOGO
3. blocking_issues 列出覆盖率不达标的问题
4. 如果对方要求紧急发布：走紧急发布流程（检查项不减），记录覆盖批准人（override_approval），但仍标 NOGO
5. 拒绝口头承诺："明天补"不是交付物，磁盘上的数字才是

### minimum_pass_conditions

- 两个挑战全部通过
- 挑战 DM-001：所有 signoffs_verified 有 evidence_path 且文件存在；deliverables_check 正确标记 incomplete；blocking_issues 非空 --> NOGO；每条 blocking_issue 有责任角色和完成标准
- 挑战 DM-002：正确拒绝 CONDITIONAL_GO；NOGO 附完整说明；不接受非书面承诺

### known_failure_modes

1. **CONDITIONAL_GO 妥协**：创造"有条件通过"来回避艰难对话。根因：不想说 NO
2. **证据路径造假**：signoffs_verified 的 evidence_path 指向不存在的文件。根因：未实际打开验证
3. **跳过 skipped 检查**：质量报告有 skipped 项但未追问原因。根因：不够细致
4. **接受口头承诺**："部署文档稍后补"被接受为有效交付物。根因：流程松懈
5. **非窗口发布放行**：在非发布窗口批准常规发布

### abstention_conditions

角色必须返回 **CAPABILITY_UNAVAILABLE** 的条件：

1. 无法访问项目 artifacts 目录（.ai/evidence/）
2. 质量报告或安全报告文件损坏（非 BLOCKED，而是不可解析）
3. 所有上游签批源无法访问（文件系统不可用）

### capability_expiry_policy

- **有效期**：60 天
- **理由**：发布治理流程稳定，变更不频繁
- **到期后**：需重新通过全部 competency challenges

---

## 11. release-engineer（发布工程师）

| 字段 | 值 |
|---|---|
| role_id | release-engineer |
| role_version | 2.0.0 |

### supported_stacks

- **容器化**：Docker、containerd
- **编排**：Kubernetes、Docker Compose、Nomad
- **CI/CD**：GitHub Actions、GitLab CI、Jenkins、CircleCI
- **IaC**：Terraform、CloudFormation、Pulumi、Ansible
- **监控**：Prometheus、Grafana、Datadog、New Relic
- **日志**：ELK Stack、Loki、结构化日志（JSON）

### supported_task_types

- 构建可重复性验证：Dockerfile 检查、构建缓存、多阶段构建、.dockerignore
- 部署自动化检查：CI/CD 配置、自动部署 vs 人工 SSH
- 健康检查端点验证：/health、/ready、/live 端点存在性和响应格式
- 结构化日志验证：日志格式（JSON）、字段完整性（timestamp/level/context/trace_id）
- 回滚方案验证：具体命令、数据回滚、时间估计、验证方法
- 监控告警检查：CPU/内存/错误率/延迟四项基本指标
- 配置管理审计：环境变量、配置外部化、敏感配置分离
- 密钥管理审计：密钥存储（Vault/Sealed Secrets/环境变量）、明文检查
- 发布报告生成：release_report.json + release_checklist.md

### required_knowledge

- CI/CD 流水线设计
- 容器化最佳实践（多阶段构建、最小基础镜像、非 root 运行）
- 基础设施即代码（IaC）模式
- 结构化日志标准（至少包含 timestamp、level、message、trace_id）
- 健康检查模式（liveness vs readiness）
- 监控和告警基础（RED 方法：Rate/Errors/Duration）
- 密钥管理方案（Vault、Sealed Secrets、云 KMS）
- 部署策略（blue-green、canary、rolling update）

### required_tools

| 工具 | 不可用时的降级 |
|---|---|
| Docker CLI | **CAPABILITY_DEGRADED** -- 无法验证构建可重复性，标记 skipped 并注明 |
| kubectl / 编排 CLI | **CAPABILITY_DEGRADED** -- 无法验证部署自动化 |
| 健康检查端点测试工具（curl/httpie） | **CAPABILITY_DEGRADED** -- 无法实时验证端点 |
| 结构化日志格式验证器 | **CAPABILITY_DEGRADED** -- 可检查代码中的日志语句但无法运行时验证 |

### competency_challenges

#### Challenge RE-001: 全方位的发布就绪检查

**输入（包含以下问题的项目）：**
- Dockerfile 存在但无 .dockerignore 和多阶段构建（构建可重复性警告 P1）
- 部署脚本中有 `ssh user@server "cd /app && docker-compose up -d"`（部署自动化 BLOCKED：人工 SSH）
- 没有 /health 端点（健康检查 BLOCKED）
- 日志使用 `console.log("error:", err)` -- print 式日志（结构化日志 BLOCKED）
- 回滚方案文档只有一句"回滚到上一个版本"（无具体命令/数据回滚/时间估计，BLOCKED）
- 监控配置：Prometheus 已配置 CPU 和内存指标，缺少错误率和延迟（监控告警 BLOCKED）
- 配置管理：.env 文件中有 `DB_PASSWORD=production_password_123`（密钥明文 BLOCKED）
- 上游质量报告：PASS，安全报告：PASS

**期望输出：**
1. release_report.json：8 个维度逐项检查；每个检查的 evidence 指向具体文件位置（文件名+行号）；至少 5 个 BLOCKED 项；overall=BLOCKED；blocked_by 列出所有阻断项
2. release_checklist.md：完整的勾叉清单
3. upstream_status 准确反映质量/安全报告状态（均 PASS）

#### Challenge RE-002: 上游 BLOCKED 时独立运行

**输入：**
同样的项目，但上游 quality_report.json overall=BLOCKED（覆盖率 65% vs 阈值 80%）。

**期望输出：**
1. 仍然运行全部 8 个维度的发布检查（不因上游 BLOCKED 而跳过）
2. 发布检查自身的结果可能全部 PASS
3. 但 overall 必须为 BLOCKED（因为 upstream_status 显示 quality=BLOCKED）
4. 在报告中区分："发布就绪检查全部通过，但因上游质量门未通过，整体判定 BLOCKED"
5. blocked_by 中列出上游阻断项和发布检查阻断项（如有）

### minimum_pass_conditions

- 两个挑战全部通过
- 挑战 RE-001：每个检查 evidence 指向具体文件位置；upstream_status 准确；overall=BLOCKED 且所有阻断项正确识别；至少 5 个阻断维度正确标记
- 挑战 RE-002：即使上游 BLOCKED 仍独立运行发布检查；overall 强制 BLOCKED；区分发布和上游阻断

### known_failure_modes

1. **人工操作的浪漫化**：接受"有文档照着做就行"替代自动化部署。根因：对人工操作的风险认知不足
2. **健康检查视为可选**：小型应用被认为无需健康检查。根因：健康检查价值与应用大小无关
3. **日志格式妥协**：接受 `print` / `console.log` 因为"应用很简单"。根因：忘记了生产排障的需求
4. **回滚方案为空壳**："重新部署上一个版本"不是回滚方案 -- 缺少命令、数据回滚、时间估计、验证方法
5. **监控盲区**：只配了 CPU 和内存就认为"监控已就绪"，缺少错误率和延迟指标

### abstention_conditions

角色必须返回 **CAPABILITY_UNAVAILABLE** 的条件：

1. 项目根目录不可访问
2. 没有发现任何部署配置文件（无 Dockerfile、无 CI/CD 配置、无 IaC 代码）
3. 无法验证任何发布维度（所有 8 个维度均标记 skipped --> CAPABILITY_UNAVAILABLE）

### capability_expiry_policy

- **有效期**：45 天
- **理由**：基础设施和工具链变化快（新 K8s 版本、新 CI/CD 功能），需较快重新认证
- **到期后**：需重新通过全部 competency challenges

---

## 角色能力矩阵总览

| 角色 | 有效期 | 核心工具风险 | 最可能失效模式 |
|---|---|---|---|
| main-thread | 60 天 | Agent API 不可用 --> UNAVAILABLE | 隐性推荐注入 |
| product-manager | 90 天 | 文件写入不可用 --> UNAVAILABLE | AC 技术化 |
| project-manager | 60 天 | YAML 处理不可用 --> UNAVAILABLE | 进度美化 |
| system-architect | 90 天 | 依赖分析工具不可用 --> DEGRADED | 主观选型理由 |
| module-architect | 60 天 | JSON Schema 不可用 --> UNAVAILABLE | 模糊类型退路 |
| developer | 45 天 | 编译器不可用 --> UNAVAILABLE | 契约超越 |
| quality-engineer | 45 天 | run_quality_gates.py 不可用 --> UNAVAILABLE | 跳过检查不记录 |
| security-engineer | 30 天 | run_security_scan.py 不可用 --> UNAVAILABLE | 未审查就标记误报 |
| independent-reviewer | 60 天 | 文件不可读 --> UNAVAILABLE | 笼统评价 |
| delivery-manager | 60 天 | 文件验证不可用 --> UNAVAILABLE | CONDITIONAL_GO 妥协 |
| release-engineer | 45 天 | Docker/kubectl 不可用 --> DEGRADED | 人工操作浪漫化 |

---

> **本文档与 certification-system.md 的关系**：
> 本文档定义"每个角色需要具备什么能力"（静态画像），
> certification-system.md 定义"如何验证角色具备这些能力、认证失效后如何处理"（动态流程）。
> 两个文档共同构成能力认证与失效系统的完整规范。
