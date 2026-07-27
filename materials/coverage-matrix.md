# 工程领域覆盖矩阵

状态：`research-baseline-v0.1`

“覆盖”表示已经定义素材类别、至少一条候选来源和对应模板，不表示已穷尽该领域或已达到生产合规。正式 Loop 开发前，所有进入硬约束的素材都必须再次核验、锁版本并经过项目化裁剪。

| 领域 | 当前登记素材 | 已有模板/产物 | 基线状态 | 主要缺口 |
| --- | --- | --- | --- | --- |
| 提示词工程 | PROMPT-001..004 | prompt contract | 候选且部分不可访问 | 模型版本差异、提示词回归、注入测试、成本基线 |
| Agent / 工具 / 上下文 | AGENT-001..004, EVAL-001..002 | run envelope, host adapter, feedback, capability probe | 已有基础 | 权限模型、工具沙箱、跨宿主实测、评分器校准 |
| AI 风险治理 | AI-GOV-001..002 | risk register, quality profile | 框架已登记 | 生成式 AI 测量、行业合规、模型卡/数据卡 |
| 产品发现/需求 | REQ-001, PM-001 | requirements baseline, acceptance matrix | 入口与原则 | 领域需求模式、用户研究、变更影响自动化 |
| 生命周期/过程 | LIFE-001, PM-002..004 | project plan, phase profile | 基础覆盖 | 阶段退出准则、依赖/资源模型、规模裁剪规则 |
| 系统架构 | ARCH-001..004 | architecture description, ADR | 架构文档基线 | 质量属性场景、架构一致性检查、代码图验证 |
| API/数据契约 | API-001..004 | API contract, JSON Schema | 机器契约基线 | 版本兼容、异步语义、契约测试执行器 |
| 编码规范/变更 | CODE-001..003 | work packet, change record | 评审和追溯基线 | 语言 Profile、静态分析、复杂度、依赖许可证 |
| 测试设计/执行 | TEST-001..005 | test strategy, test report, performance plan | 多层测试基线 | 测试 oracle、flaky 管理、E2E、恢复和环境管理 |
| 安全工程 | SEC-001..004 | threat model, security review | 安全来源较强 | 密钥、隐私、身份、运行时防护、合规映射 |
| 交付/供应链 | SEC-004, OPS-003..004 | release readiness, metrics plan | 初始覆盖 | CI/CD、制品签名、回滚演练、变更失败分类 |
| 运维/可观测性 | OPS-001..003 | observability plan, release readiness | 已有框架 | SLO 实测、告警疲劳、容量、灾备和故障演练 |
| 文档/人工评审 | DOC-001..002 | human review packet | 已有骨架 | 各阶段具体阅读任务、可读性测试、决策记录 |
| Loop 自定义层 | LOOP-001..002 | role/phase/quality profiles | 候选设计 | 真实运行时验证、角色能力认证、独立性证明 |

## 待补素材队列

1. 厂商无关的 prompt regression、LLM-as-judge 限制、模型评估和数据集版本化。
2. 任务/上下文工程：长上下文预算、检索、压缩、缓存、跨会话事实状态。
3. 软件配置管理、基线、变更控制、追溯和发布签名的正式来源。
4. 数据库迁移、备份恢复、隐私、数据保留、删除和脱敏标准。
5. 可访问性、前端性能、移动端、国际化和本地化测试素材。
6. 领域特定安全/合规：支付、医疗、个人信息、关键基础设施等。
7. AI Agent 互操作协议的版本比较和 Codex/Claude Code/Zcode/Qoder Adapter 能力实测。
8. 真实项目试运行后，用缺陷、返工、交付和用户评审数据校准质量门禁。
