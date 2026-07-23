# Artifact Schema Catalog For Real Projects Candidate v0.1

Status: candidate evidence only
Task: T-0017

## Common Fields

Every real-project artifact should include:

```yaml
artifact_id:
status: candidate | reviewed | baseline_candidate | user_approved | active_reference | installed | superseded
owner_role:
scope:
non_goals:
sources:
assumptions:
confidence:
open_questions:
related_ids:
review_status:
last_updated:
forbidden_interpretations:
```

## PRD Schema

Required sections:

- target users
- core scenarios
- functional requirements with IDs and priorities
- quantified non-functional requirements where relevant
- exclusions and non-goals
- risks and mitigations
- machine-verifiable success metrics
- acceptance criteria
- value evidence reference

## Architecture Schema

Required sections:

- system context and boundaries
- business capability map
- module responsibilities and interfaces
- data model and ownership
- ADR candidates
- verification strategy
- rollback and isolation strategy
- architecture nodes
- node traceability matrix

## Detailed Design Schema

Required sections:

- architecture blueprint mapping
- API/request/response contracts
- data validation and state transitions
- UX states where applicable
- security and privacy controls
- observability and error handling
- test strategy
- implementation-level behavior steps
- dependency injection table when applicable
- exception propagation boundary
- state change tracking
- communication protocol
- merge and rollback plan

## Dev Plan Schema

Required sections:

- work packet list
- dependency graph
- owner or agent assignment
- read/write scope
- validation condition per packet
- milestones
- PRD coverage
- Design-to-plan bidirectional reference matrix
- risk and evidence plan

## Security And Data Schema

Required sections:

- data classification
- PII inventory
- trust boundaries
- authn/authz model
- permission matrix
- input validation rules
- secret handling
- dependency vulnerability plan
- log redaction
- retention and deletion policy
- DPIA trigger assessment when applicable

## Deployment Schema

Required sections:

- environment assumptions
- artifact hash and provenance
- pipeline evidence chain
- preflight checklist
- smoke checklist
- monitoring window
- no-go conditions
- rollback or forward-fix plan
- approval requirements

## Review Schema

Required sections:

- review pack
- review baseline
- value gate evidence
- professional gate evidence
- contract gate evidence
- findings
- review receipt
- unchecked items
- residual risks

## Handoff Schema

Required sections:

- current phase and task
- allowed scope
- forbidden scope
- recent changes
- verified items
- unverified items
- evidence location
- integration impact
- pending gates and blockers
- next startup prompt
