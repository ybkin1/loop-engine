# T-0035 文档优化摘要

## 输入

- 用户附件：`C:\Users\Administrator\.codex\attachments\6ee129c2-27a5-406e-bdea-c1543d1bce69\pasted-text.txt`
- 原始设计提案的已读取内容：`loop-engineering-system-design.proposed.v0.1.md`
- 用户后续澄清：Loop 是独立工具或可插拔外部 Agent，面向 Codex、Claude Code、Zcode、Qoder 等宿主；`loop-engineering-lab` 是产品本身的真实开发项目。

## v0.2 主要优化

### 产品身份

从“治理和 Loop 设计提案”收敛为“宿主无关的软件工程控制与交付系统”，并明确独立模式、外部 Agent 模式和 `loop-engineering-lab` 自举开发关系。

### 架构边界

明确拆成 `Loop Core`、`Loop Runtime` 和 `Host Adapter`。角色规则属于 Core，真正的写入、命令、证据和阶段阻断属于 Runtime 或宿主可验证的适配器能力。

### 角色实际生效

把“深度角色扮演”转换为角色合同、权限、工具、能力挑战、生产证据、独立验证和失效降级六层机制，并将角色 Loop 与阶段 Loop 分开。

本次补强进一步增加运行时闭环：`Capability Certification -> Role Admission -> Runtime Role Verification -> Production Role Effectiveness`，要求每次角色运行记录工具预检、权限预检、输入 fingerprint、实际动作、输出 schema、确定性检查、独立验证和未验证项，并按角色检查架构、开发、质量、安全和交付行为是否真的发生。

角色认证只证明有资格接任务；Role Admission 证明本次具备执行条件；Production Role Effectiveness 才证明本次实际履行了职责。

### 硬约束

新增操作前置条件表、写入控制、评审隔离、测试结果可信度和 enforcement level，防止角色意见被主控包装成 PASS。

### 工程生命周期

将需求、架构、详细设计、质量/安全、任务、实现、集成、性能安全、交付、验收和维护划分为阶段，并要求每阶段生成 Human Review Packet，由用户 Gate 放行。

本次明确认可 P0-P12 为稳定宏阶段编号，并增加 `Phase Profile`：低风险项目可以合并阶段，高风险项目必须展开适用阶段；阶段不能静默跳过。新增 Human Review Packet 通用模板和 P0-P12 各阶段用户决策问题，明确用户只做业务/风险决策，不做技术签字。

### 跨会话

明确长期项目文档和机器状态的权威层级；`HANDOFF.md` 只做会话恢复索引，不能单独承担产品目标、架构和长期决策。

### 成本

用 `Cost per Delivery-Ready Outcome`、返工率和缺陷逃逸率衡量 token 投入，明确不能通过删除质量证据换取短期 token 节省。

## 未解决事项

- 首个宿主适配器和宿主能力仍需用户决定并单独设计。
- Loop Core、Runtime、Quality Profile 和第一条自举垂直切片尚未实现。
- 文档提案不等同于产品生产就绪；后续必须用真实代码和预埋缺陷验证。
