# 功能设计包：软件工程与提示词工程素材库

- Feature ID: `T0036-MATERIAL-LIBRARY`
- 用户目标：让未来项目优先复用软件工程规范、案例、模板和输出范式，而不是依赖模型临时自觉。
- 参与角色：项目负责人, 产品经理, 架构师, 质量工程师, Codex 主控
- 前置条件：项目意图已确认, T-0036 catalog 可读, 来源状态可追溯

## 用户怎么使用
- **entry**：Codex 识别项目类型、技术栈、风险和目标后启动 Loop
- **steps**：- 生成 Project Profile
  - 按软件工程问题检索材料
  - 记录采用/拒绝/待验证材料
  - 形成角色和阶段工作包
  - 用户阅读交付包并决定是否继续
- **success**：项目获得可追溯的需求、架构、设计、测试和交付输入
- **failure**：来源不可信、范围不清或证据不足时阻断并列出需要补充的内容
- **navigation**：用户通过 Human Review Packet 查看结论、取舍、风险和下一步

## 前端设计
- **pages**：- Project Profile
  - Material Selection
  - Phase Review
  - Functional Design Packet
- **elements**：- 阶段导航
  - 材料筛选结果
  - 采用/拒绝原因
  - 验证状态
  - 风险列表
  - 用户决策按钮
- **states**：- candidate
  - needs_research
  - repair_required
  - ready_for_review
  - approved
  - blocked
- **validation**：- 用户决策不能为空
  - 未验证来源显示警告
  - 阻断状态不可进入下一阶段
- **accessibility**：- 结论先于证据
  - 每个状态有文本标签
  - 键盘可达的决策控件

## 后端设计
- **modules**：- intent_router
  - material_selector
  - role_registry
  - context_builder
  - phase_planner
  - evidence_checker
  - packet_renderer
- **apis**：- create project profile
  - select materials
  - create work packet
  - run deterministic checks
  - render review packet
- **data_model**：- ProjectProfile
  - MaterialSelection
  - RoleContract
  - WorkPacket
  - RoleRunEnvelope
  - Finding
  - GateRecord
- **state_transitions**：- candidate -> ready_for_review -> approved_by_user
  - repair_required -> repaired -> regression_checked
  - blocked -> user_decision_required
- **errors**：- missing input
  - unknown role/material
  - context budget exceeded
  - write boundary violation
  - pending user gate
- **idempotency**：- same input fingerprint yields same selection/order
  - atomic JSON writes
  - re-running checks does not duplicate findings
- **observability**：- command trace
  - artifact fingerprints
  - role/phase/run IDs
  - check result

## 安全设计
- **boundaries**：- external source is untrusted data
  - role output is not a state transition
  - project root is the write boundary
- **authn_authz**：- Codex host capability is detected
  - role allowed_read/allowed_write is checked
  - independent reviewer is read-only
- **input_protection**：- secret markers rejected
  - prompt-like external content never becomes control instruction
  - path traversal rejected
- **abuse_prevention**：- bounded context
  - bounded task scope
  - no unbounded parallel dispatch
  - blocked states are sticky until decision
- **data_protection**：- no secrets in packets
  - fingerprints instead of raw sensitive values
  - local candidate only
- **audit**：- RoleRunEnvelope
  - finding history
  - Gate decision record

## 性能设计
- **budgets**：- role context budget declared per contract
  - selection loads only matched materials
  - packet rendering is local and deterministic
- **bottlenecks**：- large catalog search
  - independent review context
  - repeated repair loops
- **scaling**：- index catalog by category and terms later
  - cache stable role contracts
  - parallelize disjoint evidence checks
- **degradation**：- reduce selected evidence
  - serialize work
  - return USER_DECISION_REQUIRED instead of guessing

## 可维护性与演进
- **module_boundaries**：- core models do not import CLI
  - role registry does not mutate project state
  - packets render from structured data
- **dependencies**：- Python standard library
  - PyYAML only for external material catalog
- **extension**：- add role contract without changing controller
  - add checker by registry
  - add packet section through schema version
- **runbook**：- validate roles
  - init project
  - run checks
  - inspect review packet

## 测试设计
- **unit**：- role contract validation
  - fingerprints
  - graph cycles
  - packet required sections
- **component**：- context builder
  - path policy
  - material selector
  - store atomic write
- **contract**：- RoleRunEnvelope and WorkPacket fields
  - packet schema
- **integration**：- init -> select -> plan -> packet -> verify
- **e2e**：- T-0036 local candidate exercise
- **security**：- path traversal
  - secret markers
  - role self-approval
  - untrusted source instruction
- **performance**：- bounded context and catalog selection timing
- **recovery**：- atomic write interruption
  - stale fingerprint
  - blocked phase

## 关键取舍
- 软件工程来源优先于提示词技巧
- Codex-only local candidate
- 内部质量 Gate 与用户 Gate 分离
- 结构化交付物优先于长自然语言

## 风险与未验证项
- 素材库候选内容尚未全部独立复核
- Codex host runtime capability is not globally enabled
- 真实模型调用和角色效果尚未认证

## 用户需要决定
- 是否接受该素材库作为 Codex Loop 设计输入
- 是否接受角色/阶段/功能设计包结构
- 是否允许进入下一阶段实现或要求修复
