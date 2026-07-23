# Codex 一人公司式 Loop 软件交付系统 立项汇总 Candidate v0.1

Status: candidate
Approved: false
Installed: false
Write authority: none

## 1. 项目总目标

帮助一个无代码能力、无项目管理背景的用户，借助 Codex，以 loop 工程方式，从粗略需求开始，最终产出真实可用、可部署、可验收、可持续迭代的生产级软件产品。

本项目不是为了写一套漂亮规则，而是为了让 Codex 像一个小型软件公司一样稳定工作：能澄清需求、立项、设计、拆任务、实现、评审、验证、交付和持续迭代。

## 2. 当前必须同时推进的两个方向

### 方向 A：Loop 工程工作模式设计

解决“Codex 每个任务怎么做完”的问题。

核心内容：

- 主线程 Coordinator 如何拆任务。
- 每个任务如何生成 task card。
- Author / Reviewer / Repair / QA 如何分工。
- 每个任务如何执行、评审、修订、验证、交接。
- loop 如何设置上限、刹车、状态。
- 怎么防止 reviewer PASS 被当成用户批准。
- 怎么保证每个任务都保质保量完成。

标准流程：

```text
Coordinator -> Task Card -> Author -> Candidate -> Reviewer -> Findings -> Repair -> Revised Candidate -> Verification -> Run Summary -> User Gate
```

### 方向 B：规范架构设计

解决“Codex 每次开始任务前必须遵守什么”的问题。

核心内容：

- 全局中心思想包。
- 项目级规范。
- 阶段级规范。
- 角色级规范。
- 任务/会话级 Session Contract。
- Required Reading Matrix。
- AGENTS.md 入口规则。
- 文档生命周期。
- registry。
- authority boundary。
- gate policy。

标准流程：

```text
Intent Recognition -> Phase Detection -> Required Reading -> Session Contract -> Task Card -> Loop Run
```

## 3. 两个方向如何结合

规范架构是轨道，Loop 工程是运行方式。

每个任务开始前，Codex 必须先识别当前意图和阶段，然后读取对应规范，生成当前会话的 Session Contract，再进入 loop 执行。

也就是说：

1. 规范决定该读什么、信什么、禁止什么。
2. Session Contract 决定当前会话具体怎么工作。
3. Loop 工程决定任务如何产出、评审、修订和验证。
4. Gate 机制决定什么时候必须交给用户批准。

## 4. 必须防止的问题

- 多会话上下文混乱。
- Codex 忘记用户出发点。
- 每个会话自己发明规范。
- candidate 冒充 approved。
- reviewer PASS 冒充用户批准。
- task card 冒充真实权限。
- 文档越来越多但软件不可用。
- 局部完成冒充产品完成。
- 旧工具、旧规则、旧 handoff 抢权威。
- 用户被迫承担项目经理和技术判断责任。

## 5. 立项后的第一批产物

第一批只做设计，不进入真实软件开发。

需要产出：

1. 《项目章程 Candidate》
2. 《Loop 工程协议 Candidate》
3. 《规范架构协议 Candidate》
4. 《Required Reading Policy Candidate》
5. 《Session Contract 模板 Candidate》
6. 《Task Card 模板 Candidate》
7. 《Review Report 模板 Candidate》
8. 《AGENTS.md 入口规则 Candidate》
9. 《评审方案 Candidate》

## 6. 当前完成定义

本阶段完成，不是指系统已经安装，也不是指能交付生产软件。

本阶段完成标准是：

- 两个方向都被清楚定义。
- 二者如何结合被清楚定义。
- 每个阶段该读什么规范被清楚定义。
- 每个任务如何进入 loop 被清楚定义。
- 用户 gate、candidate、approved、installed 不混淆。
- 评审会话认为无阻塞 P0/P1。
- 用户明确批准进入下一阶段。
