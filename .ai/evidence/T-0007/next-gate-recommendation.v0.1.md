# Next Gate Recommendation v0.1

Status: recommendation only
Task: T-0007

## Current Discovery Status

T-0007 created the first discovery package for:

```text
做一个服务器售后团队的智算服务工具(测试)
```

No target project root exists. No project was created.

The first-version primary pain point has been narrowed to customer problem ticket-driven cross-department repair/RMA flow:

- customer reports a repair/service ticket
- technical service positions the fault and may recommend spare-part replacement
- customer service confirms maintenance strategy from the customer's contract
- maintenance strategy may be whole-machine return, faulty-part mail-in repair, RMA, or other
- RMA cases flow to spare-parts engineers for spare-part application and delivery
- field engineers receive repair strategy, spare-part information, and shipping information

The latest user answer adds a source-of-truth rule:

- each important data field must come from a database or the corresponding responsible person/department
- maintenance strategy must come from customer service, either through a customer-service-owned contract database or a customer service responsible person
- unrelated roles must not provide or confirm information outside their responsibility boundary

The candidate data responsibility matrix has been directionally confirmed by the user. Field-level details remain open for refinement.

The user rejected the current linear workflow-state questioning as too simple and too slow for this product. Discovery should switch to model-first synthesis before continuing detailed Q&A.

## Recommended Next Gate

Recommended next gate:

```text
G-T-0007-MODEL-FIRST-DISCOVERY
```

Purpose:

- continue discovery by asking the user one important product question at a time
- refine `product-brief.v0.1.md`
- refine `acceptance-criteria.v0.1.md`
- keep technical approach and implementation plan as candidates only
- stop linear one-question-at-a-time workflow-state discovery
- produce a business-domain model candidate before further detailed Q&A
- cover roles/departments, business documents, data authority, subflows, exception flows, handoff payloads, workflow events, and dashboard metrics
- keep the directionally confirmed data authority matrix available for field-level refinement

## Recommended User Decision

The next user decision should answer:

```text
我不继续用单个流程状态追问了。下一步我应该先整理一版“业务域模型候选”：角色/部门、问题单、责任矩阵、数据来源、子流程、异常流、状态事件、交接信息和看板指标，然后你批量纠偏。这个 discovery 方法切换可以吗？
```

## Not Recommended Yet

Do not approve build yet.

Reasons:

- model-first discovery method has not yet been approved as the next step
- target project root does not exist
- data sources and integration needs are not fully known
- field-level data authority details are not fully enumerated
- "智算" meaning is not confirmed
- acceptance criteria are still candidate

## Explicit Non-Approval

This recommendation does not approve:

- project creation
- real business project file changes
- build
- implementation
- deployment
- rollback
- database, permission, secret, payment, production data, or migration action
- skill/MCP/agent/automation/protocol enablement
