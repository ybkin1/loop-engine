# Discovery Q-and-A v0.1

Status: draft discovery artifact
Task: T-0007

## Answers Already Provided

### Q1. What product idea or project name should discovery use?

Answer:

```text
做一个服务器售后团队的智算服务工具(测试)
```

### Q2. Is there an existing target project root?

Answer:

```text
暂无，只做 discovery，不创建项目。
```

### Q3. What may Codex write during this discovery task?

Answer:

Only the approved T-0007 task, governance state files, and discovery evidence files under the current governance project:

```text
C:\Users\Administrator\.codex\loop-engine-lab
```

### Q4. What is explicitly not approved?

Answer:

- creating or modifying real business project files
- build
- implementation
- deployment
- rollback
- database changes
- permission changes
- secret handling
- payment actions
- production data work
- migrations
- skill/MCP/agent/automation/protocol enablement

### Q5. What first-version primary pain point should the tool solve?

Answer:

The first version should focus on cross-department flow of a customer-side problem ticket. A typical example:

- customer reports a repair/service ticket
- technical service department completes fault positioning
- technical service opinion says spare parts need to be replaced
- customer service department checks the customer's maintenance contract and maintenance strategy
- possible strategies include whole-machine return, faulty-part mail-in repair, or RMA
- if RMA is needed, the case flows to a spare-parts engineer to apply for the spare part and arrange delivery to the customer site
- the case also needs to flow to the field engineer with repair strategy, spare-part information, and spare-part express/shipping information

This example is illustrative, but it defines the current main discovery direction: the MVP should support customer problem ticket-driven cross-department repair strategy and spare-part/RMA handoff.

### Q6. Who is allowed to provide maintenance strategy and other workflow data?

Answer:

All data must come from either a system database or the corresponding responsible role/department. The tool must not treat information as valid when it is supplied by an unrelated role.

Example rule:

- maintenance strategy must come from the customer service department, either through a contract database that customer service owns or through the customer service responsible person
- technical service may provide fault positioning and replacement recommendation, but should not provide the maintenance strategy on behalf of customer service
- spare-parts engineers may provide RMA/spare-part application and delivery information, but should not provide contract maintenance strategy
- field engineers may receive repair strategy, spare-part information, and shipping information, and later provide field execution feedback, but should not be the authority for contract policy

This means the MVP needs a data authority rule: each important field should have an accountable owner and an accepted source of truth.

### Q7. Is the candidate data responsibility matrix directionally correct?

Question:

```text
我先按这个数据责任矩阵理解：技术服务部负责故障定位和更换建议，客户服务部负责维保合同/维保策略，备件工程师负责RMA/备件/物流信息，驻场工程师负责现场执行反馈。这个矩阵对吗？需要增删哪个角色或字段？
```

Answer:

```text
差不多就是这样
```

Interpretation:

- The candidate matrix is directionally confirmed.
- Field-level details can still be refined during discovery.
- This confirmation does not approve implementation, permission design, database integration, or workflow automation.

### Q8. Is the current linear workflow-state questioning method sufficient?

Answer:

```text
你的这个理解太简单了。
另外，如果按照我们这么个沟通法，其实这个智算服务平台做不出来的，几天几夜也沟通不完。
```

Interpretation:

- The latest proposed linear flow is too simple for the actual business.
- Continuing discovery as one small question after another is not an effective method for this product.
- The product should not be discovered as a single status chain.
- T-0007 discovery should switch to model-first synthesis: Codex should draft a broader business domain model candidate, then ask the user to correct it in larger chunks.
- The model should cover roles, responsibility boundaries, source-of-truth rules, business documents, workflow events, subflows, exception flows, handoffs, and dashboards.
- This is still discovery only and does not approve implementation.

## Assumptions To Confirm

- The tool is for a server after-sales team, not for end customers directly.
- The first useful product shape is likely an internal cross-department service workflow tool.
- "智算" likely means smart or AI-assisted diagnosis and service operations, but this is not confirmed.
- The MVP should focus on repair workflow coordination, maintenance strategy visibility, source-of-truth clarity, and handoff control before advanced automation.
- Each important workflow field should have an accountable source of truth: database or responsible role/department.
- Maintenance strategy is owned by customer service, not by technical service, spare-parts engineers, or field engineers.
- The initial data responsibility matrix is directionally confirmed by the user, while field-level details remain open for refinement.
- Linear one-question-at-a-time discovery is insufficient for this product; discovery should switch to a model-first business-domain candidate.
- Any AI or external integration would require a later explicit gate, especially if secrets or third-party services are involved.

## Next User Question

The next discovery question should be:

```text
我不继续用单个流程状态追问了。下一步我应该先整理一版“业务域模型候选”：角色/部门、问题单、责任矩阵、数据来源、子流程、异常流、状态事件、交接信息和看板指标，然后你批量纠偏。这个 discovery 方法切换可以吗？
```

## Notes

Discovery should stop relying on one-question-at-a-time linear workflow clarification for this product. Codex should first synthesize a business domain model candidate, then ask the user to correct it in batches. Codex should not ask the user to choose frameworks, databases, or technical architecture until the business model is clearer.
