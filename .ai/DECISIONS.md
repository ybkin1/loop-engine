# Decisions

## Active Decisions

- 2026-07-18: The project is formally initialized under `.ai` for Qoder adaptation, but all protocol/design outputs remain candidate until user-approved gates promote them.
- 2026-07-18: Reviewer PASS, validator success, tests, and AI recommendations remain evidence only; they do not replace user approval.
- 2026-07-20: 集成 4 个 Crewlet/superdesigndev 开源项目作为 Loop 工程的辅助 skill（archlet/loopany/tools-registry/loopbase），所有 skill 设计均为 candidate 状态，需用户审批后生效。
- 2026-07-22: Phase 0 cleanup — 修复 state.yaml 损坏、清理重复文档、补全 TBD 文档。开始增强 TypeScript 核心实现。

## Decision Log

| Date | Decision | Reason | Revisit When |
| --- | --- | --- | --- |
| 2026-07-18 | Initialize `C:\Users\Administrator\.qoder-cn\loop-engine-lab` as the project root for "Qoder 一人研发团队式 Loop 软件交付系统". | The work has a stable long-running objective and needs project memory, gates, evidence, and handoff continuity. | Revisit if the project root changes or if the user approves installing/activating a protocol. |
| 2026-07-18 | Keep current work in no-write design mode. | The current task is to set up the Loop governance framework adapted for Qoder. | Revisit only after candidate designs pass review and the user explicitly approves a next-stage gate. |
| 2026-07-20 | 引入 archlet 作为架构治理 skill。 | 解决 Vibe Coding 时代架构漂移问题，提供架构可视化和 PR diff 叠加能力。 | 实际使用后发现不适用或需要调整时。 |
| 2026-07-20 | 引入 loopany 作为持久记忆与自我改进 skill。 | 解决代理跨会话失忆问题，通过 reflect 循环持续改进工作方式。 | 实际使用后发现不适用或需要调整时。 |
| 2026-07-20 | 引入 tools-registry 作为团队工具与密钥管理 skill。 | 解决代理调用外部服务时的密钥安全问题。 | 实际使用后发现不适用或需要调整时。 |
| 2026-07-20 | 引入 loopbase 作为跨会话记忆与可观测性 skill。 | 提供会话索引、成本追踪和自动化洞察。 | 实际使用后发现不适用或需要调整时。 |
| 2026-07-20 | Phase 从 S0-init 升级到 S1-integration。 | 4 个外部 skill 已集成到 loop-engine 调度表，框架扩展完成。 | 用户审批后进入实际任务执行阶段。 |
| 2026-07-22 | 启动 Phase 0 修复 + Phase 1 增强。 | 发现 state.yaml 损坏、多个文档重复/TBD、TypeScript 核心未验证。必须先恢复数据可信度再建设。 | Phase 1 完成后。 |
# Decisions

## Active Decisions

- 2026-07-18: The project is formally initialized under `.ai` for Qoder adaptation, but all protocol/design outputs remain candidate until user-approved gates promote them.
- 2026-07-18: Reviewer PASS, validator success, tests, and AI recommendations remain evidence only; they do not replace user approval.
- 2026-07-20: 集成 4 个 Crewlet/superdesigndev 开源项目作为 Loop 工程的辅助 skill（archlet/loopany/tools-registry/loopbase），所有 skill 设计均为 candidate 状态，需用户审批后生效。

## Decision Log

| Date | Decision | Reason | Revisit When |
| --- | --- | --- | --- |
| 2026-07-18 | Initialize `C:\Users\Administrator\.qoder-cn\loop-engine-lab` as the project root for "Qoder 一人研发团队式 Loop 软件交付系统". | The work has a stable long-running objective and needs project memory, gates, evidence, and handoff continuity. | Revisit if the project root changes or if the user approves installing/activating a protocol. |
| 2026-07-18 | Keep current work in no-write design mode. | The current task is to set up the Loop governance framework adapted for Qoder. | Revisit only after candidate designs pass review and the user explicitly approves a next-stage gate. |
| 2026-07-20 | 引入 archlet 作为架构治理 skill。 | 解决 Vibe Coding 时代架构漂移问题，提供架构可视化和 PR diff 叠加能力。 | 实际使用后发现不适用或需要调整时。 |
| 2026-07-20 | 引入 loopany 作为持久记忆与自我改进 skill。 | 解决代理跨会话失忆问题，通过 reflect 循环持续改进工作方式。 | 实际使用后发现不适用或需要调整时。 |
| 2026-07-20 | 引入 tools-registry 作为团队工具与密钥管理 skill。 | 解决代理调用外部服务时的密钥安全问题。 | 实际使用后发现不适用或需要调整时。 |
| 2026-07-20 | 引入 loopbase 作为跨会话记忆与可观测性 skill。 | 提供会话索引、成本追踪和自动化洞察。 | 实际使用后发现不适用或需要调整时。 |
| 2026-07-20 | Phase 从 S0-init 升级到 S1-integration。 | 4 个外部 skill 已集成到 loop-engine 调度表，框架扩展完成。 | 用户审批后进入实际任务执行阶段。 |
# Decisions

## Active Decisions

- 2026-07-18: The project is formally initialized under `.ai` for Qoder adaptation, but all protocol/design outputs remain candidate until user-approved gates promote them.
- 2026-07-18: Reviewer PASS, validator success, tests, and AI recommendations remain evidence only; they do not replace user approval.

## Decision Log

| Date | Decision | Reason | Revisit When |
| --- | --- | --- | --- |
| 2026-07-18 | Initialize `C:\Users\Administrator\.qoder-cn\loop-engine-lab` as the project root for "Qoder 一人研发团队式 Loop 软件交付系统". | The work has a stable long-running objective and needs project memory, gates, evidence, and handoff continuity. | Revisit if the project root changes or if the user approves installing/activating a protocol. |
| 2026-07-18 | Keep current work in no-write design mode. | The current task is to set up the Loop governance framework adapted for Qoder. | Revisit only after candidate designs pass review and the user explicitly approves a next-stage gate. |
