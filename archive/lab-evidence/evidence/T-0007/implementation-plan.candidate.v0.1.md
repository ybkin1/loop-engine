# Implementation Plan Candidate v0.1

Status: candidate only
Task: T-0007

This is not an implementation approval. It is a candidate plan for later discussion after product brief, acceptance criteria, and technical approach are confirmed.

## Slice 0: Confirm Product Workflow

User-visible outcome:

- a confirmed business-domain model for customer problem ticket-driven cross-department repair/RMA flow

Verification:

- user reviews and corrects a model-first discovery candidate covering roles, documents, data authority, subflows, exception flows, handoffs, and dashboard needs

Status:

- discovery only

Discovery correction:

- do not continue as a long sequence of tiny workflow-state questions
- first synthesize a candidate domain model
- ask the user to correct the model in larger chunks
- only after that refine acceptance criteria and implementation slices

## Cross-Cutting Candidate: Data Authority Matrix

User-visible outcome:

- each key workflow field has a responsible department/role and accepted source type

Candidate first authority matrix:

- technical service department: fault positioning and replacement recommendation
- customer service department: maintenance contract and maintenance strategy
- spare-parts engineer: RMA, spare-part application, spare-part details, and shipping/logistics information
- field engineer: field execution feedback and on-site repair result

Verification:

- user confirms the matrix before any future build gate
- sample ticket shows source and owner for maintenance strategy, RMA/spare-part information, shipping information, and field execution feedback

Status:

- discovery only; no permission implementation or database integration approved

## Slice 1: Customer Problem Ticket Intake

Candidate outcome:

- users can create and view customer problem tickets with customer, device, fault, priority, owner, and current department/status

Expected areas if a project exists later:

- case form
- case list
- status model
- fake sample data

Verification:

- create, update, and view fake customer problem tickets

## Slice 2: Technical Service Positioning

Candidate outcome:

- technical service can record fault-positioning result and whether spare-part replacement is recommended

Verification:

- sample ticket records positioning result: replacement needed

## Slice 3: Maintenance Strategy Confirmation

Candidate outcome:

- customer service can record or select maintenance strategy: whole-machine return, faulty-part mail-in repair, RMA, or other
- maintenance strategy is marked as sourced from customer service responsible person or approved contract source

Verification:

- sample ticket moves from technical service to customer service and stores the selected maintenance strategy with source and responsible owner

## Slice 4: RMA And Spare-Part Flow

Candidate outcome:

- RMA cases can be assigned to spare-parts engineers, with spare-part and shipping progress recorded

Verification:

- sample RMA ticket records spare-part information and fake express/shipping information

## Slice 5: Field Engineer Handoff

Candidate outcome:

- field engineers can see repair strategy, spare-part information, shipping information, and handoff notes

Verification:

- sample ticket has a complete handoff view for the field engineer

## Slice 6: Team Dashboard And Timeline

Candidate outcome:

- leads can inspect tickets by department, owner, status, strategy type, and blocked handoff
- every ticket shows a timeline of department transitions and handoff notes

Verification:

- dashboard values and timeline match fake sample data

## Slice 7: Future Integrations

Candidate outcome:

- integration plan only, not implementation

Potential integrations:

- ticketing
- contract/customer system
- asset database
- warranty/RMA
- shipping tracking
- AI/LLM assistance
- notifications

Each integration requires a separate explicit gate.

## Recovery Boundary

Before any future build gate, the user must approve:

- target project root
- allowed paths
- forbidden paths
- first implementation slice
- validation commands
- evidence location
- rollback or recovery boundary

No such build gate is approved by T-0007.
