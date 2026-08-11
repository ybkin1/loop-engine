# 01 — 需求规格

> Loop Engine v1.0 需求规格 | 状态: draft | 阶段: S0-init → S1-requirements

---

## 1. 产品概述

Loop Engine 是一个 ZCode 插件，把 AI 编码从"对话式代码生成"升级为具备完整软件工程纪律的可交付系统。它提供：

- **执行层**（hooks）：在 ZCode 会话中自动拦截工具调用，强制执行质量门禁和授权边界
- **知识层**（skill）：为 AI 模型注入治理启动程序、角色协作规则和状态机逻辑
- **工具层**（MCP tools）：质量扫描、安全审计、证据冻结、成本追踪等 7 个可调用工具
- **命令层**（slash commands）：快速查询治理状态、校验证据链、估算 token 成本

**一句话目标**：让无代码能力的用户在 AI 辅助下，从粗略需求得到可交付、可验证、可迭代的软件。

---

## 2. 用户画像

| 属性 | 描述 |
|------|------|
| **角色** | 产品 Owner（也是唯一用户） |
| **技术能力** | 无编程能力，无项目管理背景 |
| **职责** | 定义目标、确认业务规则、做关键取舍、批准阶段 Gate |
| **不负责** | 编码、测试、部署、架构设计、代码评审——全部由 AI 角色团队承担 |
| **工作方式** | 在 ZCode 中与 AI 对话，偶尔批准 gate 或确认保护区操作 |

---

## 3. 功能需求

### 3.1 治理 Hook 系统（执行层）

三个 ZCode Hook，在特定事件触发时自动运行，不经 AI 模型干预：

#### FR-H01: 会话启动摘要（SessionStart）

- **触发时机**：每次 ZCode 会话启动
- **行为**：读取 `.ai/state.yaml` 和 `.ai/gates.yaml`，向会话注入当前阶段、当前任务、pending gate 列表、HANDOFF 下一步
- **失败策略**：fail-open（任何异常放行，仅 stderr 警告），不阻塞会话
- **实现**：`hooks/scripts/session_brief.py`
- **前置条件**：项目根存在 `.ai/state.yaml`（否则跳过不注入）

#### FR-H02: Gate 阻断（PreToolUse）

- **触发时机**：AI 执行 Write / Edit 操作前
- **行为**：检查是否存在 `status: pending` 的 gate；存在则 exit 2 阻断写入
- **豁免规则**：`.ai/gates.yaml` 的写入始终豁免（避免决策死锁）
- **失败策略**：fail-closed（状态文件不可读时阻断，安全姿态）
- **实现**：`hooks/scripts/gate_guard.py`
- **前置条件**：项目根存在 `.ai/state.yaml`

#### FR-H03: 路径保护（PreToolUse）

- **触发时机**：AI 执行 Write / Edit 操作前
- **行为**：目标路径命中保护区 → 返回 `permissionDecision: ask`，由用户在客户端当场确认
- **保护区列表**（可配置）：
  - `AGENTS.md` — 项目启动规则
  - `stable/` — 稳定产物目录
  - `registry/` — 注册表目录
  - `.zcode/config.json` — ZCode 配置
  - `.zcode/tools/` — 治理工具脚本
- **决策模式**：默认 `ask`（用户确认），可切换 `deny`（硬阻断）
- **实现**：`hooks/scripts/path_guard.py`

### 3.2 治理技能系统（知识层）

#### FR-S01: 治理启动器 Skill

- **位置**：`skills/loop-governance/SKILL.md`
- **触发条件**：AI 检测到项目级治理任务（存在 `.ai/state.yaml` 且非简单问答）
- **行为**：
  1. 读取用户请求，确认项目根
  2. 依次读取 state.yaml、HANDOFF.md、当前任务文件、gates.yaml、task_graph.yaml
  3. 运行 `validate_state.py`
  4. 存在 pending gate → 停止并向用户展示
  5. 只在已批准的任务和 gate 范围内继续

#### FR-S02: 治理配置

- **位置**：`skills/loop-governance/config.yaml`
- **可配置项**：
  - `gate_guard`：启用/禁用、失败策略、决策记录豁免路径
  - `path_guard`：启用/禁用、决策模式（ask/deny）、受保护路径列表
  - `session_brief`：启用/禁用、最大 pending 列表长度
  - `quality_gates`：项目类型、六项检查的命令和阈值
  - `certification`：认证要求、严格模式、过期/降级规则
  - `degradation`：14 条降级规则（从 CAPABILITY_UNAVAILABLE 到 ROLE_BLOCKED）

#### FR-S03: 治理参考文档

- `references/governance-lifecycle.md` — 任务/gate/产物状态机
- `references/decision-rules.md` — evidence 与批准的边界
- `references/hook-protocol.md` — ZCode hook 协议与排障

### 3.3 斜杠命令（命令层）

三个自定义斜杠命令，用户可在对话中直接调用：

#### FR-C01: `/loop-validate`

- **功能**：运行 `validate_state.py` 并展示当前治理状态
- **输出**：phase、current_task_id、pending gates、错误列表

#### FR-C02: `/loop-verify-chain`

- **功能**：验证证据链完整性，检测 stale 证据

#### FR-C03: `/loop-cost`

- **功能**：按角色/阶段聚合 token 消耗，生成成本报告

### 3.4 MCP 工具（工具层）

7 个通过 JSON-RPC over stdio 暴露的工具：

#### FR-T01: `quality_gates_run`

- **功能**：运行六项质量门禁（lint / typecheck / test / coverage / audit / build）
- **输入**：project_root, output_dir（可选）
- **输出**：结构化 JSON 质量报告

#### FR-T02: `security_scan_run`

- **功能**：运行安全扫描（CVE、密钥泄露、注入面、权限）
- **输入**：project_root, output_dir（可选）
- **输出**：结构化 JSON 安全报告

#### FR-T03: `dependency_analysis`

- **功能**：分析模块依赖图，检测循环依赖和边界违规
- **输入**：project_root, rules_file（可选）
- **输出**：依赖图和违规列表

#### FR-T04: `contract_validate`

- **功能**：验证接口契约 JSON schema 完整性
- **输入**：project_root, contract_file, check_actual（可选）
- **输出**：契约校验结果

#### FR-T05: `evidence_verify`

- **功能**：验证证据链完整性——检查 input_hashes 与上游 SHA256 一致性
- **输入**：project_root, strict（可选）
- **输出**：证据链状态报告

#### FR-T06: `evidence_freeze`

- **功能**：冻结证据——计算并写入 content_sha256
- **输入**：project_root, file
- **输出**：冻结确认

#### FR-T07: `cost_report`

- **功能**：生成 token 成本报告——按角色/阶段聚合
- **输入**：project_root
- **输出**：结构化成本报告

### 3.5 项目适配安装

#### FR-I01: 一键安装脚本

- **脚本**：`scripts/install.py --project-root <目标>`
- **行为**：
  1. 创建 `.ai/` 模板目录（state.yaml、gates.yaml、task_graph.yaml、HANDOFF.md、PROJECT.md）
  2. 创建 `.ai/tasks/` 和 `.ai/evidence/` 目录
  3. 复制治理 skill 配置到 `.zcode/skills/loop-governance/`
  4. 复制工具脚本到 `.zcode/tools/`（validate_state.py、audit_handoff.py 等）

#### FR-I02: 一键卸载脚本

- **脚本**：`scripts/uninstall.py --project-root <目标>`
- **行为**：移除治理运行时文件，保留用户数据（`.ai/tasks/`、`.ai/evidence/`）

### 3.6 Agent 角色体系（知识层）

Loop Engine 内置 11 个专业角色，每个角色有完整合同（12 字段：身份/立场/职责/禁止/输入/输出/质量标准/否决权/证据/交接/冲突处理/工作流）。角色通过独立子 agent 调用，上下文隔离。

#### FR-A01: 角色清单

| 角色 | 职责 | 否决权 |
|------|------|--------|
| `main-thread` | 编排角色、维护事实和状态、任务拆分 | 不可替其他角色伪造结论 |
| `product-manager` | 澄清用户目标、需求、范围、优先级和验收 | 拒绝模糊需求 |
| `project-manager` | 管理阶段、任务依赖、资源、风险、进度、阻塞和交接 | 依赖失控时阻止排新任务 |
| `system-architect` | 设计整体架构、技术边界、模块划分、数据流、依赖和演进 | 代码违反架构时拒绝实现结果 |
| `module-architect` | 拆到组件、接口、类、函数、数据结构和调用关系 | 接口契约不符时拒绝 |
| `developer` | 严格依据批准架构/接口/规范实现，不改需求和架构 | 不能自行宣布架构合理 |
| `quality-engineer` | 设计测试策略、门禁、评审方案、覆盖标准、缺陷分级 | 测试/覆盖率/证据不足时拒绝交付 |
| `security-engineer` | 检查权限、输入、数据、密钥、依赖、攻击面 | 发现风险时阻止发布 |
| `independent-reviewer` | fresh context 检查实现/架构/可维护性/缺陷 | 不修复，只报告；每条发现逐行引用证据 |
| `delivery-manager` | 判断交付物齐全、发布条件、回滚和交接准备 | 文档/部署/监控/回滚不完整时拒绝上线 |
| `release-engineer` | 检查构建、部署、配置、监控、日志、回滚和可观测性 | 构建失败或配置缺失时阻止 |

#### FR-A02: 角色调用约束

- 每个角色 = 独立 ZCode Agent 调用，隔离上下文，不共享会话记忆
- 角色只能看到角色合同（SKILL.md）+ 主控分配的输入材料
- 角色不知道项目历史、其他角色的结论、主控的设计意图
- 角色只能写入主控指定的输出文件，不能修改项目代码
- 角色间不直接通信——所有输出经主控汇总
- 同一角色不得同时出现在决策链的两端（如：不能既是架构师又是实现该架构的开发者）

#### FR-A03: 角色交付物标准

| 角色 | 必须交付 |
|------|---------|
| 系统架构师 | 整体架构 + 模块清单 + 组件清单 + 接口定义 + 数据模型 + 依赖关系 + 调用关系 + 错误处理边界 + 安全边界 + 扩展方式 + 部署结构 + 测试边界 + 每个设计选择理由 |
| 模块架构师 | 组件职责 + 接口契约（input/output/error） + 数据结构 + 函数签名 + 允许/禁止依赖 + 调用时序 |
| 开发工程师 | 基于批准架构的代码 + 单元测试 + 实现说明（为什么这样实现） |
| 质量工程师 | 测试策略 + 测试用例 + 覆盖率报告 + 缺陷分级 + 修复验证 + 交付质量判断 |
| 独立评审员 | review_report.json（每条发现含文件/行号/代码/类型/严重级别/影响）+ review_summary.md |

### 3.7 阶段 Loop 状态机（治理层）

Loop Engine 定义 12 个软件工程阶段，每个阶段本身是一个 mini-Loop——有输入、角色协作、输出、评审 Gate、人审批。

#### FR-P01: 阶段定义

| 阶段 | 名称 | 输入 | 关键角色 | 输出 | Gate 类型 |
|------|------|------|---------|------|-----------|
| S0 | 项目初始化 | 用户目标一句话 | 产品经理、项目经理 | PROJECT.md、state.yaml | 人审阅 |
| S1 | 需求分析 | PROJECT.md | 产品经理→架构师评审→质量评审 | 需求规格 + 验收标准 | Human Review Packet |
| S2 | 架构设计 | 需求规格 | 系统架构师→模块架构师→评审员 | 架构文档 + 模块设计 + 接口契约 | Human Review Packet |
| S3 | 详细设计 | 架构文档 | 模块架构师→开发评审 | 组件设计 + 函数签名 + 数据结构 | Human Review Packet |
| S4 | 实现 | 详细设计 | 开发工程师→评审员→质量 | 代码 + 单元测试 + 实现说明 | 代码评审 Gate |
| S5 | 质量门禁 | 代码 + 测试策略 | 质量工程师→安全工程师 | 测试报告 + 覆盖率 + 安全报告 | 质量 Gate |
| S6 | 交付准备 | 全部通过产物 | 交付经理→发布工程师 | 交付清单 + 部署方案 + 回滚方案 | 交付 Gate |
| S7 | 集成 | 通过测试的模块 | 开发工程师→质量工程师 | 集成代码 + 集成测试 | 集成 Gate |
| S8 | 功能测试 | 集成产物 | 质量工程师→产品经理验收 | 功能测试报告 | 验收 Gate |
| S9 | 修复优化 | 缺陷列表 | 开发→评审→质量（mini-Loop） | 修复代码 + 回归测试 | 修复 Gate |
| S10 | 性能测试 | 功能完整产物 | 质量工程师→架构师 | 性能报告 + 瓶颈分析 | 性能 Gate |
| S11 | 维护迭代 | 线上反馈 | 产品经理→全角色 | 迭代计划 | 人审阅 |

#### FR-P02: 阶段门禁规则

- 每个阶段结束时输出 **Human Review Packet**——人能读懂的交付物摘要
- 前一阶段的 Gate 未批准，不得进入下一阶段
- Gate 批准需要：所有角色输出 + 独立评审结论 + 质量门禁结果
- 任一角色行使否决权 → Gate 不能通过
- 阶段内允许 mini-Loop（如 S4 中开发→评审→修复→重评审）

### 3.8 角色能力认证（质量保障层）

确保每个角色不是"同一模型换名字"，而是通过独立挑战验证其实际能力。

#### FR-CERT01: 认证机制

- 每个角色在上岗前必须通过隔离的**能力挑战测试**
- 挑战测试是预埋缺陷的代码/设计，角色必须在隔离上下文中独立发现问题
- 测试结果由机器裁决（hash 匹配、exit code、结构化输出校验），不依赖 AI 自评

#### FR-CERT02: 认证状态

| 状态 | 含义 | 对生产任务的影响 |
|------|------|-----------------|
| `CERTIFIED` | 通过挑战，在有效期内 | 可接受生产任务 |
| `CERTIFIED_WITH_NOTES` | 通过但有观察项 | 可接受，产出标注 |
| `REVALIDATION_REQUIRED` | 认证过期或连续失败 | 不可接受生产任务 |
| `CAPABILITY_DEGRADED` | 特定 task_type 连续失败 | 该 task_type 不可接 |
| `CAPABILITY_UNAVAILABLE` | 核心工具不可用 | 完全不可接任务 |
| `ROLE_BLOCKED` | 生产事故或伪造证据 | 人工恢复前不可用 |

#### FR-CERT03: 认证降级规则

- 同一 task_type 连续 3 次被下游拒收 → 降级
- 认证过期超过宽限期 → 要求重新认证
- 生产事故（安全漏检、伪造证据、越权行为） → ROLE_BLOCKED
- 恢复需要人工批准 + 60 天观察期

---

## 4. 非功能需求

### NFR-01: 可靠性

- Hook 脚本异常不得瘫痪 ZCode 会话（gate_guard 的 fail-closed 除外，因其为安全设计）
- MCP 服务器崩溃时返回标准 JSON-RPC 错误，不输出裸 traceback
- PyYAML 不可用时自动退化为正则行扫描（fail-closed 保守姿态）

### NFR-02: 性能

- Hook 脚本超时：gate_guard / path_guard 5 秒，session_brief 10 秒
- MCP 工具无超时限制（阻塞式执行，待需求明确后添加）
- 不在 hook 中添加网络请求或重量级计算

### NFR-03: 安全性

- 不硬编码密钥、密码、token 或 API key
- 不请求网络访问（除 MCP 工具按需外）
- 工具执行在项目根范围内，不越权访问上级目录

### NFR-04: 兼容性

- Python 3.10+
- 依赖：PyYAML >= 6.0（可选，缺失时退化）
- 平台：Windows 10+, macOS, Linux（通过 ZCode 跨平台）
- ZCode 版本：支持 hook 协议的版本（`hooks.enabled` + `events` schema）

### NFR-05: 可维护性

- 代码风格：PEP 8
- Hook 脚本禁止生成 `__pycache__`（`sys.dont_write_bytecode = True`）
- 治理配置与技能逻辑分离（config.yaml vs SKILL.md）
- 每个 hook 独立脚本，互不依赖（共享 hook_common.py 工具库）

### NFR-06: 可用性

- 对非治理项目零影响（hook 检测无 `.ai/state.yaml` 即跳过）
- 错误信息用中文（面向中文用户），技术字段用英文 ID
- config.yaml 注释即文档

---

## 5. 验收标准

### AC-01: 插件注册

- [x] 在 ZCode Plugin Management 中可发现并注册本插件
- [x] 注册后 `skills/loop-governance` 在 AI 会话中可被调用
- [x] 注册后三个斜杠命令可用
- [x] 注册后 MCP 工具在 `tools/list` 中可见

### AC-02: Hook 系统

- [x] SessionStart: 会话启动时自动注入治理状态摘要（新会话验证）
- [x] gate_guard: 存在 pending gate 时 Write/Edit 被阻断（exit 2）
- [x] gate_guard: `.ai/gates.yaml` 的写入在 pending gate 期间被豁免
- [x] path_guard: 写入保护区时弹出用户确认
- [x] 非治理项目（无 `.ai/state.yaml`）中所有 hook 不生效

### AC-03: 治理技能

- [x] AI 在治理项目中按 SKILL.md 启动检查清单执行
- [x] 发现 pending gate 时 AI 停止并展示 gate 内容
- [x] AI 不绕过 hook 阻断或代替用户批准 gate

### AC-04: 项目安装

- [x] `install.py` 在空项目中正确创建所有模板文件
- [x] `install.py` 在已有 `.ai/` 的项目中不覆盖已有文件
- [x] `validate_state.py` 安装后可运行并通过

### AC-05: 测试覆盖

- [x] Hook 脚本：所有关键路径有测试覆盖（≥ 80%）
- [x] MCP 工具：每个工具有独立的单元测试
- [x] 集成测试：完整治理工作流可从头走到尾

### AC-06: 角色体系

- [x] 12 个角色均有完整的 12 字段角色合同（SKILL.md）（T-0177 修正：11→12）
- [x] 每个角色可通过独立 ZCode Agent 调用，上下文隔离
- [x] 独立评审员能在隔离上下文中发现主控 AI 遗漏的缺陷
- [x] 角色否决权由结构化输出强制执行（非自然语言建议）

### AC-07: 阶段 Loop

- [x] 12 个阶段每个阶段有明确的输入/输出/Gate 定义
- [x] 每阶段结束时输出 Human Review Packet
- [x] 前一阶段 Gate 未批准时，下一阶段的任务创建被阻断
- [x] 阶段内 mini-Loop（开发→评审→修复→重评审）可执行

### AC-08: 角色认证

- [x] 每个角色上岗前通过隔离的能力挑战测试
- [x] 认证状态机正确执行（CERTIFIED → DEGRADED → BLOCKED）
- [x] 连续失败达到阈值时自动降级
- [x] ROLE_BLOCKED 恢复需要人工批准

### AC-09: 独立验证

- [x] 在已知位置预埋缺陷（seeded defects），Loop Engine 能发现并阻断
- [x] 同一 AI 不能同时担任开发者和该代码的评审员
- [x] Gate 批准需要至少一个独立角色的 PASS 结论（不可自评自审）

---

## 6. 不做（Non-Goals）

- 不是通用 CI/CD 工具（不替代 GitHub Actions / Jenkins）
- 不是项目管理 SaaS（不提供 Web UI、数据库、多用户协作）
- 不是代码生成器（不替用户写业务逻辑）
- 不做真实的部署、回滚、数据库变更、权限管理、密钥处理、支付、生产数据操作或数据迁移——这些始终需要单独的用户 gate
- 不替代用户做业务决策（gate 始终由用户批准）

---

## 7. 术语定义

| 术语 | 定义 |
|------|------|
| **Gate** | 用户决策点。AI 不得自行批准；reviewer PASS、测试通过仅为 evidence |
| **Hook** | ZCode 事件拦截器。在 SessionStart、PreToolUse 等事件触发时执行脚本 |
| **Skill** | AI 知识注入。通过 SKILL.md 为模型提供治理行为程序 |
| **保护区** | 受 path_guard 保护的路径（AGENTS.md、stable/、registry/ 等） |
| **证据链** | 从需求到交付的 hash 链路。任一环节输入变更 → 下游证据 stale |
| **ProjectContinuity** | 项目连续性文档（v1 schema），冻结治理事实以供审计 |
| **pending gate** | 等待用户决策的 gate。存在时 gate_guard 阻断写入 |
