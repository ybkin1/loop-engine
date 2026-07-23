# Product Brief v0.1

Status: candidate discovery draft
Task: T-0007
Product idea: 做一个服务器售后团队的智算服务工具(测试)

## Target User

Primary assumed users:

- server after-sales engineers who handle technical service cases
- technical service staff who position faults and decide whether replacement is needed
- customer service staff who confirm contract and maintenance strategy
- spare-parts engineers who process RMA or spare-part application and delivery
- field engineers who need repair strategy, spare-part information, and shipping information
- coordinators who dispatch cases, track progress, and follow up with customers or internal teams
- team leads who need workload, SLA, and blocker visibility

This target user definition needs confirmation.

## Problem Statement

Server after-sales work can stall when a customer problem ticket crosses departments. After technical service positions a fault and recommends part replacement, customer service may need to confirm the customer's maintenance strategy, such as whole-machine return, faulty-part mail-in repair, or RMA. If RMA is required, spare-parts engineers need to apply for and ship the part, while field engineers need the repair strategy, spare-part details, and shipping information. Without a shared workflow and clear source-of-truth rules, these handoffs can become scattered across chat, spreadsheets, ticket notes, and personal follow-up, and the wrong role may provide information that should belong to another department. This product cannot be discovered well as a single simple status chain; it needs a broader business-domain model.

## Product Promise

The product should help the server after-sales team move each customer problem ticket through the right cross-department repair path, making ownership, maintenance strategy, RMA/spare-part progress, field handoff information, data authority, and case timeline clear to everyone involved.

## Candidate MVP Scope

The first MVP could include:

- customer problem ticket intake and status tracking
- business domain model covering roles, business documents, source-of-truth rules, workflow events, subflows, exceptions, handoffs, and dashboard views
- technical service fault-positioning result and replacement recommendation
- data authority matrix showing which department or database is allowed to provide each key field
- maintenance strategy field: whole-machine return, faulty-part mail-in repair, RMA, or other
- customer service confirmation step for contract/maintenance strategy
- RMA/spare-part application and delivery follow-up step for spare-parts engineers
- field engineer handoff containing repair strategy, spare-part information, and shipping information
- case timeline showing department transitions, owner, required action, and handoff notes
- basic dashboard for tickets by department, status, owner, and blocked handoff

## Out Of Scope For First Discovery Draft

- production deployment
- real customer data import
- database migration
- permission or role system implementation
- payment or billing
- external AI integration
- automated customer messaging
- inventory-system integration
- CRM or ERP integration
- automatic contract-system lookup
- automatic RMA-system submission
- automatic express/shipping-system integration

These may become future candidates only after separate user gates.

## Assumptions

- The tool is internal-facing.
- The first product value should come from clearer cross-department repair workflow and handoff context.
- The discovery method should be model-first rather than a long sequence of small Q&A turns.
- Integrations are not required for the first discovery draft.
- For a first non-integrated MVP, maintenance strategy may be manually selected or recorded only by customer service or the customer-service-owned contract source.
- The product should distinguish "provided by responsible owner" from "mentioned by another role".
- The initial data responsibility matrix is directionally confirmed by the user, but field-level details may still be adjusted.
- AI assistance, if desired later, should start as a controlled candidate feature rather than a hidden dependency.

## Risks

- The phrase "智算服务工具" may mean something different from AI-assisted after-sales workflow.
- The real team process may already depend on existing tools that are not yet named.
- Data sensitivity may be high if customer, device, serial-number, warranty, or fault data is involved.
- A useful MVP depends heavily on matching the real cross-department routing and responsibility boundaries.
- If contract strategy must be queried automatically, integration risk becomes much higher and needs a separate later gate.
- If source-of-truth rules are unclear, the workflow may still move quickly but produce untrusted or disputed decisions.
- If discovery continues as isolated linear questions, the product shape will remain too shallow and the team may miss core business complexity.

## Confirmation Needed

The user should confirm or correct:

- primary user group
- whether cross-department customer problem ticket flow is the confirmed first-version primary pain point
- whether "智算" means AI-assisted support or another kind of compute service
- exact MVP workflow states and department handoff points
- field-level refinements to the directionally confirmed data responsibility matrix
- which fields require database source and which fields may be supplied by a responsible person
- model-first discovery candidate covering roles, documents, events, subflows, exceptions, handoffs, and metrics
- data sources, if any
