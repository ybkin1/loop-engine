# Human Review Packet：T-0036 Loop 模拟排布

状态：`ready_for_user_review / simulation_only`

## 需要用户决定

是否认可下面这套排布，作为正式 Loop 设计的输入：

1. T-0036 按高风险设计输入项目处理，采用 Full/Controlled Loop 的阶段治理。
2. 角色保留产品、项目、交付、系统架构、模块架构、开发、质量、安全、独立评审、发布/运维、主控，并增加项目专用研究员。
3. P1/P2、P3/P4 允许合并执行，但交付物、检查器和用户决策不能被静默合并掉。
4. P7 只代表素材库文档资产构建，不代表开始 Loop Runtime/Host Adapter 编码。
5. P9 的运行时性能对 T-0036 不适用，但来源新鲜度、成本、输入安全和证据可信度检查继续执行。
6. 用户 Gate 是外部决定，任何 AI 角色、主控、检查器都不能代写批准。

## 本阶段结果

已形成模拟架构、角色排布、阶段任务图、素材选择、质量 Profile、架构决策和成本/并行策略。

## 关键产物

- [架构基线](architecture-baseline.v0.1.md)
- [角色排布](role-roster.v0.1.yaml)
- [任务图](task-graph.v0.1.yaml)
- [模拟执行方案](loop-simulation-plan.v0.1.md)
- [素材选择记录](material-selection.v0.1.yaml)
- [质量 Profile](quality-profile.v0.1.yaml)
- [架构决策](simulation-architecture-decisions.v0.1.md)

## 关键取舍

- 以可确定 Workflow 为默认，只有能力探针证明自主 Agent 有收益时才增加自主性。
- 以外部来源、方法、模板、执行控制四层组合，不把来源正文拼成巨型提示词。
- 以角色和阶段双层 Loop 管理失败，主控只编排事实和状态。

## 风险和未决事项

- 角色能力目前只有探针设计，没有真实 Runtime 执行结果。
- OpenAI/Google 部分提示词官方来源仍受访问限制，不能成为硬约束。
- T-0036 的素材库仍是候选基线，不是用户已接受的正式 Loop 规范。
- 多宿主能力差异尚未实测，Codex/Claude Code/Zcode/Qoder 适配仍是后续任务。

## 用户不需要判断什么

用户不需要审核 YAML 语法、函数级设计、检查器实现细节或 Agent 内部推理。用户只需要判断目标是否正确、关键取舍是否接受、风险是否可接受，以及是否批准进入下一阶段。

## 决策记录

- [ ] 批准模拟排布作为正式 Loop 设计输入
- [ ] 要求修复后再评审
- [ ] 拒绝该排布
- [ ] 暂缓决定

用户决定：

日期：
