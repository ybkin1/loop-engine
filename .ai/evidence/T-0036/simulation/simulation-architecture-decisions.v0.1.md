# T-0036 模拟架构决策记录 v0.1

状态：`simulation_only / proposed`

## ADR-SIM-001：先使用可确定 Workflow，再增加 Agent 自主性

### Context

T-0036 需要研究、分类、模板化和验证；这些工作大部分可以用明确阶段和检查器表达。Agent 自主规划会增加上下文漂移、工具越权和难以复现的风险。

### Decision

采用 `FULL_LOOP` 的阶段治理，但每个阶段优先使用可确定的工作包、Schema、命令和人工 Gate。只有当 capability probe 证明自主 Agent 能减少返工且不降低证据可信度时，才允许增加自主编排。

### Consequences

- 初始 token 可能高于单 Agent 直接生成，但返工和错误自证风险更低。
- 主控负责路由和状态，不负责代替专业角色给出专业结论。
- 后续可用运行数据决定哪些阶段可以自动化或降级。

## ADR-SIM-002：生命周期素材和敏捷方法分层组合

### Context

ISO/IEC/IEEE 12207 提供生命周期过程参考，Agile Manifesto 强调反馈和可工作的增量。二者若混为一谈，容易变成“敏捷所以可以省掉需求、设计和质量证据”。

### Decision

生命周期来源定义阶段和交付物边界；敏捷方法只影响迭代节奏、反馈频率和 WIP 管理。任何适用的安全、测试、追溯和用户 Gate 不得因为采用敏捷而静默删除。

### Consequences

- 阶段可以合并，但必须覆盖被合并阶段的全部输入、输出、检查和用户决定。
- 返工以增量方式执行，但必须重新通过受影响的 Gate。

## ADR-SIM-003：素材目录和 Loop 适配层分离

### Context

外部标准、官方指南、方法论和 Loop 自定义约束的权威性不同。混在一起会导致 AI 把项目偏好伪装成行业标准。

### Decision

`catalog.yaml` 与 `source-register.md` 只记录外部/原始材料；角色合同、Phase Profile、Quality Profile 和 Gate 组合属于 Loop 适配层，必须通过 `material-selection-record` 显式引用来源并记录裁剪。

### Consequences

- 每个项目都要有选择记录，不能只加载整个目录。
- 来源变更时可以定位受影响的 Loop 规则和项目。
