# Architecture Baseline Template Candidate v0.1

Status: candidate
Task: T-0017

## Purpose

Define the architecture baseline package that must exist before detailed
design or implementation planning for a real project.

Architecture baseline is a decision package. It is not build approval.

## Required Sections

### 1. System Context

- product boundary
- external users and systems
- operating environment
- constraints
- assumptions

### 2. Business Capability Map

- capability IDs
- linked requirements
- owner or responsible role
- MVP vs later phase

### 3. Component Map

Each component should include:

```text
node_id | node_type | level | responsibility | inputs | outputs | data_owned | dependencies | validation_path | linked_ids
```

### 4. Integration Map

- internal interfaces
- third-party services
- event/webhook/message flows
- sync vs async boundaries
- idempotency and retry expectations

### 5. Data Ownership Model

- source of truth by entity
- stewardship owner
- privacy/sensitivity classification
- retention and deletion expectations
- migration candidates

### 6. Trust Boundaries

- authentication boundary
- authorization model
- sensitive data zones
- external input surfaces
- audit logging expectations

### 7. Technology And Build-Vs-Buy Decisions

Each major decision should include:

```text
decision_id | options | recommendation | rationale | tradeoffs | risks | revisit_when
```

### 8. ADR Candidates

Architecture decisions that affect cost, risk, data, operations, or future
flexibility require ADR candidates.

### 9. Risk And Tradeoff Register

Record product, technical, security, delivery, and operational risks with
owner, severity, likelihood, mitigation, and residual-risk decision.

### 10. Node Traceability Matrix

Every architecture node must link to:

- business goal or PRD requirement
- workflow
- data item
- test strategy
- security requirement when applicable
- later work packet when planning begins

## Architecture Review Gate

Architecture baseline can be recommended only when:

- all required sections have substantive content
- every MVP requirement maps to at least one architecture node
- module dependencies are acyclic or explicitly justified
- major decisions have ADR candidates
- sensitive data has security treatment
- deployment shape is clear enough to assess risk
- unresolved P0/P1 findings are absent

## Forbidden Interpretations

- Architecture baseline is not implementation approval.
- Architecture review PASS is not user approval.
- Architecture baseline does not authorize tool/runtime enablement.
- Architecture baseline does not authorize deployment, rollback, or migration.
