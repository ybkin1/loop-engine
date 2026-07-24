# Domain Model And PRD Protocol Candidate v0.1

Status: candidate
Task: T-0017

## Purpose

Define the required bridge from business-domain understanding to PRD baseline.
The bridge reduces user burden by letting Codex infer a model first, then ask
the user to correct business truth.

## Domain Model Requirements

The domain model must include:

- actor and role map
- responsibility and approval matrix
- business object catalog
- source-of-truth matrix
- workflow catalog
- exception workflow catalog
- data authority table
- assumptions ledger
- conflict register

Every fact that affects behavior, data, security, operations, or cost should
include:

```text
source | owner | confidence | conflict_status | decision_needed
```

Allowed confidence values:

```text
high | medium | low | unknown
```

## PRD Requirements

The PRD must include:

- target users
- product promise
- goals and non-goals
- MVP scope
- later-phase scope
- functional requirements with `REQ-*` IDs
- non-functional requirements with `NFR-*` IDs
- acceptance criteria with `AC-*` IDs
- business rules with owner and source
- assumptions and conflicts
- user decisions required

Each feature must have:

- ID
- priority
- user-visible behavior
- acceptance condition
- linked goal
- linked workflow
- linked test placeholder

## Traceability Rules

- Every `REQ-*` links to at least one `GOAL-*`, `WF-*`, `AC-*`, and `TEST-*`.
- Every workflow links to owner role, business data, terminal state, and
  relevant UI/API/event if known.
- Every sensitive data item links to a security requirement.
- Every unresolved conflict links to `FIND-*` and a repair or decision path.

## PRD Baseline Gate

Before PRD baseline approval, Codex must present a user decision packet with:

- summary in product language
- what Codex assumed
- decisions needed
- risks or conflicts
- recommended gate
- exact reply format
- what approval does not authorize

## Quality Gate

PRD baseline is not ready if:

- features lack IDs
- acceptance criteria are not verifiable
- non-functional requirements are vague where they matter
- sensitive data exists without privacy/security expectations
- product scope and non-goals conflict
- high-risk actions are hidden inside normal requirements

## Boundary

PRD baseline approval authorizes downstream architecture design only if the
gate says so. It never authorizes implementation, build, deployment, rollback,
database changes, permission changes, secret handling, payment actions,
production-data access, or migrations.
