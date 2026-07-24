# Technical Approach Candidate v0.1

Status: candidate only
Task: T-0007

This document is a technical approach candidate. It does not approve build, implementation, deployment, project creation, database work, permission changes, secret handling, external API use, or protocol/tool enablement.

## Likely App Type

Candidate app type:

- internal web application for customer problem ticket-driven cross-department after-sales workflow management

Possible future surfaces:

- desktop browser dashboard
- mobile-friendly case view
- import/export reports
- AI-assisted diagnosis or knowledge search, only after a separate approved gate

## Candidate Architecture

If implementation is approved later, a conservative candidate architecture could include:

- frontend case-management UI
- backend API for cases, departments, users, statuses, routing steps, notes, and dashboard metrics
- workflow/state model for department handoffs and next required action
- source-of-truth model for key fields, including responsible owner and source type
- candidate role/authority model for who may provide or confirm each field
- relational data store for structured service records
- document or knowledge table for reusable diagnosis notes
- audit log for case status changes
- test data fixtures for discovery and verification

No specific framework is selected yet because no project root exists and implementation is not approved.

## Modeling Approach Candidate

The product should not be designed as one simple linear status chain. A future implementation would likely need a case-centric workflow model:

- `CustomerProblemTicket` as the main business object
- department-owned tasks or subflows under the ticket
- events for transitions, handoffs, waits, returns, escalations, and closures
- source-of-truth metadata for key fields
- audit trail for who provided or confirmed each decision
- dashboard projections by department, owner, blocked state, and exception type

Discovery should therefore produce a business-domain model candidate before any build gate is considered.

## Candidate Data Objects

- ServiceCase
- CustomerProblemTicket
- Customer
- ServerAsset
- FaultCategory
- DiagnosisStep
- TechnicalServiceOpinion
- MaintenanceContract
- MaintenanceStrategy
- RoutingStep
- DataAuthorityRule
- SourceOfTruth
- ResponsibleRole
- FieldProvenance
- VerificationStatus
- KnowledgeEntry
- SLAStatus
- Escalation
- RMARequest
- SparePartRequest
- ShipmentInfo
- FieldEngineerHandoff
- ClosureSummary

These are candidate objects, not final schema.

## Integration Candidates

Potential future integrations, each requiring separate approval:

- existing ticketing system
- inventory or asset database
- contract/warranty system
- RMA system
- express/shipping tracking system
- CRM or ERP
- chat or notification system
- AI/LLM service for diagnosis suggestions

Any integration involving secrets, production data, permissions, or external APIs requires a separate explicit user gate.

## Data Authority Candidate

Each key field should record:

- field name
- responsible department or role
- accepted source type: database or responsible person
- source record identifier when database-backed
- provider or confirmer when person-backed
- timestamp
- verification status

Initial candidate authority matrix:

- technical service department: fault positioning and replacement recommendation
- customer service department: maintenance contract and maintenance strategy
- spare-parts engineer: RMA, spare-part application, spare-part details, and shipping/logistics information
- field engineer: field execution feedback and on-site repair result

This is a product/technical candidate only. It does not approve permission implementation, database changes, or integration work.

## Testing Strategy Candidate

Future verification could include:

- unit tests for case status transitions
- workflow tests for customer ticket creation, technical service positioning, customer service strategy confirmation, RMA routing, spare-part follow-up, field engineer handoff, and closure
- dashboard count tests by department, owner, status, blocked state, and maintenance strategy
- validation tests for required fields
- validation tests for field source and responsible owner
- manual test script using fake sample cases
- security review before any real data is used

## Main Risks

- workflow mismatch with the actual after-sales process
- oversimplifying the business into a single status enum
- sensitive customer or device data handling
- overbuilding AI features before core workflow is clear
- integration complexity with contract, RMA, inventory, and shipping systems
- unclear role and permission model
- unclear ownership when a ticket crosses department boundaries
- untrusted data if a field can be supplied by a non-responsible role

## Alternatives

- start as a lightweight workflow tracker with manual maintenance-strategy selection
- start as a ticket dashboard layer on top of an existing ticketing system
- start as an RMA/spare-part handoff tracker
- start as a team lead reporting tool

The right alternative depends on whether the first version may manually record maintenance strategy or must query an existing contract/customer system.
