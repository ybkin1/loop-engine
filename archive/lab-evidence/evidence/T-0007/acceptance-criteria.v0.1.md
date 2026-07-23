# Acceptance Criteria v0.1

Status: candidate discovery draft
Task: T-0007

These criteria are discovery-level acceptance criteria. They describe what a future MVP might need to prove, but they do not approve implementation.

## Product-Level Acceptance Candidate

A future MVP should be considered useful only if a server after-sales team can:

- create a customer problem ticket with customer, device, fault, priority, owner, and due-time information
- record the technical service fault-positioning result and replacement recommendation
- route the ticket to customer service to confirm the maintenance strategy
- record a maintenance strategy such as whole-machine return, faulty-part mail-in repair, RMA, or other
- require maintenance strategy to be provided by customer service or an approved customer-service-owned contract data source
- route RMA cases to a spare-parts engineer for spare-part application and delivery follow-up
- record spare-part information and express/shipping information when applicable
- require spare-part/RMA/logistics information to be provided by the responsible spare-parts role or an approved source system
- route the ticket to a field engineer with repair strategy, spare-part information, and shipping information
- show the source and responsible owner for each key decision or data field
- show current department, current owner, next required action, and blocked/waiting state
- preserve a timeline of department transitions and handoff notes
- let a team lead inspect tickets by department, owner, status, blocked handoff, and strategy type

The initial data authority matrix is directionally confirmed by the user:

- technical service department: fault positioning and replacement recommendation
- customer service department: maintenance contract and maintenance strategy
- spare-parts engineer: RMA, spare-part application, spare-part details, and shipping/logistics information
- field engineer: field execution feedback and on-site repair result

Field-level refinements are still allowed during discovery.

## Valid Input Examples

- customer name or customer code
- server model
- serial number or asset identifier
- fault symptom
- priority or severity
- reported time
- assigned engineer
- diagnosis note
- spare-part or RMA note
- technical service positioning result
- replacement recommendation
- maintenance strategy: whole-machine return, faulty-part mail-in repair, RMA, or other
- maintenance strategy source: contract database or customer service responsible person
- spare-part model or part number
- RMA identifier
- express/shipping carrier and tracking number
- responsible owner for each key data field
- source type: database or responsible person
- field engineer handoff note

## Invalid Or Risky Input Examples

- blank case title
- missing fault symptom
- missing current owner
- missing next required action
- maintenance strategy supplied by a role outside customer service without approved source
- RMA selected without spare-part follow-up owner
- spare-part/logistics information supplied by an unauthorized role
- field engineer handoff without repair strategy
- invalid date or due-time format
- unsupported priority value
- attachment containing secrets or unrelated private data
- customer data imported without approval

## Success States

- each department can understand what it needs to do next from the ticket page
- customer service can record or confirm the maintenance strategy
- the ticket shows whether maintenance strategy came from a contract database or customer service responsible person
- spare-parts engineer can see which RMA/spare-part action is needed
- field engineer can see repair strategy, spare-part information, and shipping information
- dispatcher or lead can see who owns each ticket and where it is blocked
- case timeline preserves handoff history
- no hidden build, deployment, data migration, or external integration is required

## Failure States

- unclear ownership
- status values do not match the real workflow
- maintenance strategy is missing or ambiguous
- maintenance strategy is provided by the wrong department
- key data has no source or responsible owner
- RMA flow does not clearly hand off to spare-parts engineer
- field engineer does not receive enough repair/spare-part/shipping context
- SLA or escalation state is invisible, if those become first-version requirements
- reports are not trusted by the team
- data sensitivity boundaries are unclear

## Manual Verification Candidate

If implementation is approved later, the first manual verification script could use fake sample data to check:

- create a fake customer repair ticket
- record technical service positioning result: replacement needed
- send it to customer service for maintenance strategy confirmation
- select maintenance strategy: RMA, with source marked as customer service responsible person or contract database
- assign a spare-parts engineer to apply for a spare part
- record fake spare-part and express/shipping information
- hand off to a field engineer with repair strategy and shipping details
- confirm the timeline shows each department transition
- confirm dashboard counts show the ticket under the correct department/status

## User Approval Needed

The user must approve or repair these acceptance criteria before any implementation plan can be promoted beyond candidate status.
