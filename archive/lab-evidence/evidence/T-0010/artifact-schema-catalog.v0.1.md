# Artifact Schema Catalog v0.1

Status: candidate repair evidence
Task: T-0010

## Purpose

Define minimum schemas for AI-generated design packages deep enough to approach the Harness benchmark while keeping the user focused on business truth, tradeoffs, and gate decisions.

Every artifact must include:

- `artifact_id`
- `status`
- `owner_role`
- `scope`
- `non_goals`
- `sources`
- `assumptions`
- `confidence`
- `open_questions`
- `related_ids`
- `review_status`
- `last_updated`

Use confidence values:

```text
high | medium | low | unknown
```

Each factual row that affects product behavior, data, security, operations, or cost should include:

```text
source | owner | confidence | conflict_status | decision_needed
```

## Package Index Schema

Required sections:

- package purpose
- artifact list
- reading path by role
- lifecycle state
- gate history
- cross-document ID index
- known gaps
- deferred scope
- validation and review evidence

## PRD Schema

Required sections:

- problem statement
- target users and roles
- goals and non-goals
- MVP scope
- later-phase scope
- functional requirements with `REQ-*` IDs
- non-functional requirements with `NFR-*` IDs
- acceptance criteria with `AC-*` IDs
- business rules with owner and source
- assumptions and conflicts
- user decisions required

## Domain Model Schema

Required sections:

- actors and departments
- responsibility matrix
- business object catalog
- source-of-truth matrix
- workflow map
- exception map
- data authority table
- assumptions ledger
- conflict register

Required columns for authority tables:

```text
field_or_fact | authoritative_source | responsible_owner | confidence | conflict_status | affected_artifacts | decision_needed
```

## Architecture Schema

Required sections:

- context and constraints
- component map
- integration map
- deployment shape candidate
- data ownership model
- trust boundaries
- dependency inventory
- build-vs-buy decisions
- ADR candidates with `ADR-*` IDs
- risk and tradeoff register

## API Schema

Required sections:

- API conventions
- auth and permission model
- endpoint catalog with `API-*` IDs
- request and response schemas
- pagination and filtering
- idempotency
- transactions and consistency
- event/SSE/webhook catalog with `EVT-*` IDs
- error code catalog with `ERR-*` IDs
- rate limits
- contract-test references

Each endpoint row must link to:

```text
REQ-* | WF-* | DATA-* | UI-* | TEST-* | SEC-* when applicable
```

## Data Model Schema

Required sections:

- entity catalog with `DATA-*` IDs
- field catalog
- source system
- ownership and stewardship
- lifecycle and retention
- privacy/sensitivity classification
- migration candidate notes
- indexes and constraints
- audit requirements
- unresolved source conflicts

## Workflow And State Schema

Required sections:

- workflow catalog with `WF-*` IDs
- state machine
- triggers
- owners
- data sources
- terminal states
- exception paths
- manual override rules
- SLA/SLO candidate where relevant
- linked UI/API/test/security IDs

## UX Schema

Required sections:

- page map with `UI-*` IDs
- user journeys
- screen states: default, loading, empty, error, disabled, success, permission denied
- responsive behavior
- accessibility requirements
- keyboard and focus behavior where relevant
- form validation and error copy requirements
- API/event dependencies
- analytics or audit events
- open design decisions

## Security Schema

Required sections:

- data classification
- threat model
- trust boundaries
- authn/authz/RBAC matrix
- permission review
- secrets handling
- sensitive data redaction
- audit logging
- input validation and abuse cases
- high-risk action checklist
- security test references

High-risk action checklist:

```text
deployment | rollback | database | permission | secret | payment | production_data | migration
```

## Test And QA Schema

Required sections:

- test strategy
- requirement-to-test matrix
- unit/integration/contract/E2E/security/regression coverage
- fixtures and seed data
- design-review tests
- contradiction scan
- traceability scan
- release criteria
- residual risks

Design-level QA gates:

- required artifacts exist
- required IDs exist
- P0/P1 findings resolved
- major P2 fixed or explicitly deferred
- every `REQ-*` links to acceptance and test evidence
- every high-risk item links to security and verification evidence

## Observability And SRE Schema

Required sections:

- service and dependency inventory
- metrics with `OBS-*` IDs
- SLO/SLA assumptions
- dashboards
- alert rules and thresholds
- log and trace requirements
- runbooks
- incident ownership
- smoke checks
- operational risks

Alert rows must include:

```text
signal | threshold | severity | owner | user impact | runbook | rollback_or_mitigation
```

## Release And Rollback Schema

Required sections:

- release scope
- environment assumptions
- preflight checklist
- deployment plan candidate
- rollback plan
- smoke tests
- monitoring window
- no-go conditions
- approval requirements
- post-release verification

## Risk Register Schema

Required sections:

- risk ID with `RISK-*`
- description
- severity
- likelihood
- owner
- source
- affected IDs
- mitigation
- test or monitor
- residual risk decision

## Sprint Plan Schema

Required sections:

- milestone map
- sprint goals
- task breakdown
- dependencies
- sequencing rationale
- test evidence plan
- gate checkpoints
- risk burndown
- complexity band

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
- quarantined test cases
- pending gates and blockers
- next session first step
- copyable startup prompt

## Baseline Readiness Schema

Required sections:

- lifecycle state
- artifact coverage checklist
- traceability coverage
- role-review status
- repair status
- P0/P1/P2 status
- user decision packet
- residual risks
- next gate recommendation

## Deferred But Recommended

The next review-rerun may request expanded per-artifact examples and a dry-run test plan. This T-0010 repair provides the schema catalog but does not execute a real project dry run.
