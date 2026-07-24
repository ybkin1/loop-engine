# T-0007 Commands And Validation Evidence

Status: evidence
Task: T-0007
Recorded at: 2026-07-07T15:39:31+08:00
Scope: real-product discovery only in current governance project

## User Gate

The user explicitly approved:

```text
批准 real-product discovery gate。
产品想法/项目名称是：做一个服务器售后团队的智算服务工具(测试)。
目标项目根目录：暂无，只做 discovery，不创建项目。
```

Allowed updates:

- `.ai/tasks/<task-id>.md`
- `.ai/state.yaml`
- `.ai/task_graph.yaml`
- `.ai/gates.yaml`
- `.ai/PROGRESS.md`
- `.ai/HANDOFF.md`
- `.ai/evidence/<task-id>/commands.md`
- `.ai/evidence/<task-id>/product-intent.v0.1.md`
- `.ai/evidence/<task-id>/discovery-q-and-a.v0.1.md`
- `.ai/evidence/<task-id>/product-brief.v0.1.md`
- `.ai/evidence/<task-id>/acceptance-criteria.v0.1.md`
- `.ai/evidence/<task-id>/technical-approach.candidate.v0.1.md`
- `.ai/evidence/<task-id>/implementation-plan.candidate.v0.1.md`
- `.ai/evidence/<task-id>/next-gate-recommendation.v0.1.md`

Forbidden scope:

- do not create or modify real business project files
- do not build, implement, deploy, or roll back
- do not touch database, permission, secret, payment, production data, or migration resources
- do not enable skill, MCP, agent, automation, or protocol behavior

## Pre-T-0007 Validation

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0006
[ok] state is usable
```

## Completed Updates

- Created `.ai/tasks/T-0007.md`.
- Created `.ai/evidence/T-0007/commands.md`.
- Created `.ai/evidence/T-0007/product-intent.v0.1.md`.
- Created `.ai/evidence/T-0007/discovery-q-and-a.v0.1.md`.
- Created `.ai/evidence/T-0007/product-brief.v0.1.md`.
- Created `.ai/evidence/T-0007/acceptance-criteria.v0.1.md`.
- Created `.ai/evidence/T-0007/technical-approach.candidate.v0.1.md`.
- Created `.ai/evidence/T-0007/implementation-plan.candidate.v0.1.md`.
- Created `.ai/evidence/T-0007/next-gate-recommendation.v0.1.md`.
- Updated `.ai/state.yaml` to `current_task_id: T-0007`.
- Added T-0007 to `.ai/task_graph.yaml`.
- Recorded `G-T-0007-REAL-PRODUCT-DISCOVERY` in `.ai/gates.yaml`.
- Updated `.ai/PROGRESS.md`.
- Updated `.ai/HANDOFF.md`.

## Boundary Checks

- Target project root: none.
- Product project created: no.
- Real business project entered: no.
- Real business project files modified: no.
- `AGENTS.md` modified: no.
- skill/MCP/agent/automation/protocol behavior enabled: no.
- build/implementation/deploy/rollback performed: no.
- database/permission/secret/payment/production-data/migration action performed: no.

## Post-T-0007 Validation

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0007
[ok] state is usable
```

## Post-T-0007 Handoff Audit

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0007
```

## Post-T-0007 File Checks

```text
.ai/tasks/T-0007.md exists: True
.ai/evidence/T-0007 files:
- acceptance-criteria.v0.1.md
- commands.md
- discovery-q-and-a.v0.1.md
- implementation-plan.candidate.v0.1.md
- next-gate-recommendation.v0.1.md
- product-brief.v0.1.md
- product-intent.v0.1.md
- technical-approach.candidate.v0.1.md
AGENTS.md SHA256 DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87
```

## Wording Repair After User Feedback

Recorded at: 2026-07-07T15:52:21+08:00

The user recommended two wording repairs:

- Avoid saying or implying that T-0007 discovery is completed; use `T-0007 discovery 初始证据已创建，当前进入 discovery Q&A 阶段。`.
- Make the next discovery question softer and allow an unlisted pain point.

Updated files:

- `.ai/PROGRESS.md`
- `.ai/HANDOFF.md`
- `.ai/evidence/T-0007/discovery-q-and-a.v0.1.md`
- `.ai/evidence/T-0007/next-gate-recommendation.v0.1.md`

Boundary preserved:

- no real business project entered
- no product project created
- no real business project files modified
- no build, implementation, deploy, rollback, database, permission, secret, payment, production data, or migration action
- no skill/MCP/agent/automation/protocol enablement

## Post-Discovery-Method-Correction Validation

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0007
[ok] state is usable
```

## Post-Discovery-Method-Correction Handoff Audit

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0007
```

## Post-Discovery-Method-Correction Search Check

```text
Current T-0007 evidence records that linear workflow-state Q&A is insufficient.
Current next recommendation is to switch to model-first business-domain discovery.
HANDOFF.md was repaired to accurately reflect current T-0007 state after a simplified closeout-style handoff was detected.
```

## Post-Data-Matrix-Confirmation Validation

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0007
[ok] state is usable
```

## Post-Data-Matrix-Confirmation Handoff Audit

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0007
```

## Post-Data-Matrix-Confirmation Search Check

```text
Current T-0007 evidence records that the data responsibility matrix is directionally confirmed.
Current next discovery question asks the user to confirm first-version workflow states and exception states.
```

## Discovery Method Correction

Recorded at: 2026-07-07T16:22:42+08:00

The user corrected the latest discovery approach:

```text
你的这个理解太简单了。
另外，如果按照我们这么个沟通法，其实这个智算服务平台做不出来的，几天几夜也沟通不完。
```

Interpretation recorded:

- the proposed linear workflow-state model is too simple
- one-question-at-a-time workflow-state clarification will not scale for this product
- T-0007 should switch to model-first business-domain discovery before more detailed Q&A
- the next candidate should cover roles/departments, business documents, data authority, source systems, subflows, exception flows, workflow events, handoff payloads, and dashboard metrics

Updated files:

- `.ai/evidence/T-0007/discovery-q-and-a.v0.1.md`
- `.ai/evidence/T-0007/product-brief.v0.1.md`
- `.ai/evidence/T-0007/technical-approach.candidate.v0.1.md`
- `.ai/evidence/T-0007/implementation-plan.candidate.v0.1.md`
- `.ai/evidence/T-0007/next-gate-recommendation.v0.1.md`
- `.ai/PROGRESS.md`
- `.ai/HANDOFF.md`

Recommended next question:

```text
我不继续用单个流程状态追问了。下一步我应该先整理一版“业务域模型候选”：角色/部门、问题单、责任矩阵、数据来源、子流程、异常流、状态事件、交接信息和看板指标，然后你批量纠偏。这个 discovery 方法切换可以吗？
```

Boundary preserved:

- no real business project entered
- no product project created
- no real business project files modified
- no build, implementation, deploy, rollback, database, permission, secret, payment, production data, or migration action
- no skill/MCP/agent/automation/protocol enablement

## Post-Data-Authority-Update Validation

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0007
[ok] state is usable
```

## Post-Data-Authority-Update Handoff Audit

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0007
```

## Post-Data-Authority-Update Search Check

```text
Current T-0007 discovery evidence records:
- key data must come from a database or corresponding responsible role/department
- maintenance strategy belongs to customer service or a customer-service-owned contract source
- unrelated roles must not provide authoritative data outside their responsibility boundary
- next question asks the user to confirm or repair the candidate data authority matrix

The previous maintenance-strategy source question remains only in historical commands evidence.
```

## Discovery Q&A Update: Data Matrix Direction Confirmed

Recorded at: 2026-07-07T16:15:23+08:00

The user answered the candidate data responsibility matrix question:

```text
差不多就是这样
```

Interpretation recorded:

- the candidate matrix is directionally confirmed
- field-level details remain open for refinement during discovery
- this does not approve implementation, permission design, database integration, or workflow automation

Updated files:

- `.ai/evidence/T-0007/discovery-q-and-a.v0.1.md`
- `.ai/evidence/T-0007/product-brief.v0.1.md`
- `.ai/evidence/T-0007/acceptance-criteria.v0.1.md`
- `.ai/evidence/T-0007/next-gate-recommendation.v0.1.md`
- `.ai/PROGRESS.md`
- `.ai/HANDOFF.md`

Next discovery question:

```text
第一版流程状态我先理解为：客户报修/建单 -> 技术服务定位 -> 客服确认维保策略 -> 备件/RMA处理 -> 驻场维修执行 -> 关闭。这个主流程对吗？需要加“退回补充信息、等待客户、等待备件、升级处理、取消/作废”这类状态吗？
```

Boundary preserved:

- no real business project entered
- no product project created
- no real business project files modified
- no build, implementation, deploy, rollback, database, permission, secret, payment, production data, or migration action
- no skill/MCP/agent/automation/protocol enablement

## Post-Discovery-QA-Update Validation

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0007
[ok] state is usable
```

## Post-Discovery-QA-Update Handoff Audit

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0007
```

## Post-Discovery-QA-Update Search Check

```text
Current T-0007 handoff, Q&A, and next-gate recommendation now ask:
第一版为了先跑通流程，维保策略（整机返回/故障件寄修/RMA）是由客户服务部在单子里手动选择即可，还是必须从现有合同/客户系统自动查询？

The previous broad pain-point question remains only in historical commands evidence.
```

## Discovery Q&A Update: Data Authority Rule

Recorded at: 2026-07-07T16:07:43+08:00

The user clarified that all data must come from either a database or the corresponding responsible person/department. Example:

- maintenance strategy must be provided by customer service
- the source can be a customer-service-owned contract database or the customer service responsible person
- unrelated roles must not provide authoritative data for fields they do not own

Interpretation recorded:

- technical service department owns fault positioning and replacement recommendation
- customer service department owns maintenance contract and maintenance strategy
- spare-parts engineer owns RMA, spare-part application, spare-part details, and shipping/logistics information
- field engineer owns field execution feedback and on-site repair result

Updated files:

- `.ai/evidence/T-0007/discovery-q-and-a.v0.1.md`
- `.ai/evidence/T-0007/product-intent.v0.1.md`
- `.ai/evidence/T-0007/product-brief.v0.1.md`
- `.ai/evidence/T-0007/acceptance-criteria.v0.1.md`
- `.ai/evidence/T-0007/technical-approach.candidate.v0.1.md`
- `.ai/evidence/T-0007/implementation-plan.candidate.v0.1.md`
- `.ai/evidence/T-0007/next-gate-recommendation.v0.1.md`
- `.ai/PROGRESS.md`
- `.ai/HANDOFF.md`

Next discovery question:

```text
我先按这个数据责任矩阵理解：技术服务部负责故障定位和更换建议，客户服务部负责维保合同/维保策略，备件工程师负责RMA/备件/物流信息，驻场工程师负责现场执行反馈。这个矩阵对吗？需要增删哪个角色或字段？
```

Boundary preserved:

- no real business project entered
- no product project created
- no real business project files modified
- no build, implementation, deploy, rollback, database, permission, secret, payment, production data, or migration action
- no skill/MCP/agent/automation/protocol enablement

## Post-Wording-Repair Validation

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0007
[ok] state is usable
```

## Post-Wording-Repair Handoff Audit

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0007
```

## Wording Search Check

```text
.ai\PROGRESS.md: T-0007 discovery 初始证据已创建，当前进入 discovery Q&A 阶段。
.ai\HANDOFF.md: T-0007 discovery 初始证据已创建，当前进入 discovery Q&A 阶段。
.ai\HANDOFF.md: 这个工具第一版先只解决一个最主要痛点就好。你更想先解决：工单流转、故障诊断、SLA/超时跟踪、备件/RMA、知识库复用、管理报表，还是别的痛点？
.ai\evidence\T-0007\discovery-q-and-a.v0.1.md: 这个工具第一版先只解决一个最主要痛点就好。你更想先解决：工单流转、故障诊断、SLA/超时跟踪、备件/RMA、知识库复用、管理报表，还是别的痛点？
.ai\evidence\T-0007\next-gate-recommendation.v0.1.md: 这个工具第一版先只解决一个最主要痛点就好。你更想先解决：工单流转、故障诊断、SLA/超时跟踪、备件/RMA、知识库复用、管理报表，还是别的痛点？
```

## Discovery Q&A Update: First-Version Pain Point

Recorded at: 2026-07-07T15:59:18+08:00

The user answered that the first version should focus on a customer-side problem ticket flowing across after-sales departments. Example flow:

- customer reports a repair ticket
- technical service completes fault positioning and recommends spare-part replacement
- customer service checks the customer's maintenance contract and maintenance strategy
- maintenance strategy may be whole-machine return, faulty-part mail-in repair, or RMA
- if RMA is needed, spare-parts engineer applies for the spare part and arranges delivery to the customer site
- field engineer receives repair strategy, spare-part information, and shipping information

Updated files:

- `.ai/evidence/T-0007/discovery-q-and-a.v0.1.md`
- `.ai/evidence/T-0007/product-intent.v0.1.md`
- `.ai/evidence/T-0007/product-brief.v0.1.md`
- `.ai/evidence/T-0007/acceptance-criteria.v0.1.md`
- `.ai/evidence/T-0007/technical-approach.candidate.v0.1.md`
- `.ai/evidence/T-0007/implementation-plan.candidate.v0.1.md`
- `.ai/evidence/T-0007/next-gate-recommendation.v0.1.md`
- `.ai/PROGRESS.md`
- `.ai/HANDOFF.md`

Next discovery question:

```text
第一版为了先跑通流程，维保策略（整机返回/故障件寄修/RMA）是由客户服务部在单子里手动选择即可，还是必须从现有合同/客户系统自动查询？
```

Boundary preserved:

- no real business project entered
- no product project created
- no real business project files modified
- no build, implementation, deploy, rollback, database, permission, secret, payment, production data, or migration action
- no skill/MCP/agent/automation/protocol enablement
