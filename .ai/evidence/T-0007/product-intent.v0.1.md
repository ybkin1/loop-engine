# Product Intent v0.1

Status: draft discovery artifact
Task: T-0007
Product idea: 做一个服务器售后团队的智算服务工具(测试)
Target project root: none

## Intent Summary

The user wants to explore a product for a server after-sales team. The first-version pain point is customer problem ticket-driven cross-department flow: after a customer reports a repair/service ticket, technical service positions the fault, customer service confirms the maintenance strategy, spare-parts engineers handle RMA or part delivery when needed, and field engineers receive repair strategy plus spare-part and shipping information.

This is discovery only. No real project is created and no implementation is approved.

## Primary Users

Candidate user groups:

- server after-sales engineers
- technical service department
- customer service department
- support dispatchers or coordinators
- service team leads
- spare-parts or warranty coordinators
- spare-parts engineers
- field engineers
- customer support managers

These roles are assumptions and need user confirmation.

## Candidate Problems

The tool may help with:

- receiving and tracking customer repair/problem tickets
- routing a ticket from technical service fault positioning to customer service maintenance strategy confirmation
- representing maintenance strategies such as whole-machine return, faulty-part mail-in repair, and RMA
- routing RMA cases to spare-parts engineers for spare-part application and delivery follow-up
- passing repair strategy, spare-part information, and shipping information to field engineers
- keeping each department's current owner, required action, and handoff context visible
- enforcing that important data comes from its responsible department or source database
- preserving a traceable case timeline from customer report to field repair follow-up

## Desired Outcome

A successful product should let a server after-sales team:

- see where a customer problem ticket currently sits across departments
- know which department or role owns the next action
- know which department or source database is authoritative for each key piece of information
- avoid losing maintenance strategy, spare-part, RMA, and shipping context during handoff
- avoid invalid handoffs caused by the wrong role providing a non-authoritative answer
- make the repair route clear to technical service, customer service, spare-parts engineers, and field engineers
- reduce repeated manual coordination through chat or spreadsheets
- provide a reliable case timeline for later review

## Known Constraints

- No target project root exists yet.
- Discovery must stay inside the current governance project.
- No product project may be created.
- No real business code may be modified.
- No build, implementation, deploy, rollback, database, permission, secret, payment, production data, or migration action is approved.
- No skill, MCP, agent, automation, or protocol behavior may be enabled.

## Open Intent Questions

- Is this first version internal-only for the after-sales team, or should customers see any ticket status?
- Does "智算服务工具" mean AI-assisted support, compute-resource service management, or a broader smart operations tool?
- Is this data responsibility matrix correct: technical service owns fault positioning and replacement recommendation; customer service owns maintenance contract/strategy; spare-parts engineers own RMA/spare-part/logistics information; field engineers own field execution feedback?
- Which key fields must be sourced from a database, and which may be supplied by the responsible person?
- Which statuses should the cross-department workflow include from customer report to field engineer follow-up?
- What data already exists today: service tickets, contract/warranty data, device inventory, RMA records, express/shipping records, chat logs, spreadsheets, or CRM records?
- What would count as a useful first MVP in one or two weeks of work?
