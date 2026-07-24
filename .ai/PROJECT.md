# Qoder 一人研发团队式 Loop 软件交付系统

## One Sentence

帮助无代码能力、无项目管理背景的用户，借助 Qoder 以 Loop 工程方式，从粗略需求推进到真实可用、可部署、可验收、可持续迭代的软件产品交付。

## User Outcome

用户只负责目标、关键取舍和 gate 批准；Qoder 负责澄清需求、立项、设计、拆任务、执行、评审、修订、验证、交付和交接。

## MVP

先完成 no-write 设计阶段：形成 Loop 工程工作模式、规范架构、Required Reading Policy、Session Contract、任务卡、评审报告和 Skill 入口规则的候选设计。

## Success Criteria

- Loop 工程工作模式和规范架构被清楚区分并能协同工作。
- 每个任务开始前能识别阶段、读取必要规范并生成 Session Contract。
- 每个任务能进入 task card -> execute -> review -> repair -> verify -> handoff 的闭环。
- candidate、reviewed、user-approved、active、installed 不混淆。
- reviewer PASS、测试、CI、validator 只作为 evidence，不替代用户 gate。
- 系统最终目标始终指向真实软件交付，而不是文档自循环。

## Operators

- Owner: user
- AI role: implement inside approved task and gate boundaries
