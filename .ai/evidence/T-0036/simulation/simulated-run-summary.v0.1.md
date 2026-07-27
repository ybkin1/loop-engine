# T-0036 模拟 Loop 运行摘要 v0.1

状态：`simulation_only`

说明：下表把已经存在的 T-0036 研究资产映射到“如果按 Loop 执行，应该由哪个角色、在什么阶段、用什么证据产生”。它不是补写角色运行日志；本次没有启动真实子 Agent，所有角色状态均为 `not_executed`。

| 阶段 | 计划角色 | 计划产物 | 当前对应资产 | 模拟判定 |
| --- | --- | --- | --- | --- |
| P0 | 主控/项目经理 | Project Profile、路由记录 | `project-profile.v0.1.yaml` | 设计完成，未走用户 Gate |
| P1-P2 | 产品/研究/质量 | 需求、来源、覆盖和验收基线 | `materials/source-register.md`, `materials/coverage-matrix.md` | 候选资产已存在，独立角色未执行 |
| P3-P4 | 系统/模块架构师 | 架构、Schema、接口和模板边界 | `architecture-baseline.v0.1.md`, `materials/material-schema.yaml` | 模拟设计完成，未批准 |
| P5 | 质量/安全/主控 | Quality Profile、威胁和角色能力探针 | `quality-profile.v0.1.yaml`, `materials/templates/role-capability-probe.yaml` | 设计完成，未运行探针 |
| P6 | 项目经理 | 任务图、工作包、WIP/token 预算 | `task-graph.v0.1.yaml`, `loop-simulation-plan.v0.1.md` | 计划完成，未派发任务 |
| P7 | 开发/研究 | 目录、模板、框架和 Profile | `materials/` | 文件已由当前主控创建，不等于模拟 Agent 执行 |
| P8 | 质量/独立评审/安全 | 结构检查、独立评审、安全复核 | `T-0036/commands.md`, `source-validation.v0.1.md` | 确定性检查已通过；独立评审和安全红队未执行 |
| P9 | 质量/安全 | 适用性、成本、新鲜度和安全裁剪 | `project-profile.v0.1.yaml` 的 tailoring | 仅形成模拟结论，待正式评审 |
| P10 | 交付/发布运维 | Human Review Packet、交接、回滚准备 | `human-review-packet.v0.1.md` | 交付包草案完成，未宣布 READY |
| P11 | 用户/主控 | 用户接受、修复、拒绝或暂缓 | 决策栏为空 | 阻断，必须由用户决定 |
| P12 | 研究/项目经理 | 来源刷新、退役和反馈回归 | `materials/coverage-matrix.md` 待补队列 | 未启动 |

## 模拟结论

1. 架构上，T-0036 不是“一个 Agent 写一堆提示词”，而是来源、模板、角色、阶段、检查器和人工 Gate 组成的资产链。
2. 任务上，研究、架构、质量、安全和实现可以有受控并行，但 P0/P2/P3/P6/P11 必须保持顺序。
3. 角色上，主控不能替代架构师、质量工程师或独立评审员；角色结论必须由运行证据支撑。
4. 质量上，YAML 解析通过只是结构证据，不能宣称来源质量、角色能力或生产级 Loop 已验证。
5. 当前正确状态应是 `candidate / ready_for_user_review`，不是 `approved`、`active runtime` 或 `production ready`。
