# Lifecycle Stage Model Candidate v0.1

Status: candidate evidence only
Task: T-0017

## Purpose

Define the reusable route from raw idea to usable software while preserving
hard gates between discovery, design, implementation, release, and operations.

## Stages

| Stage | Goal | Primary Output | Gate |
| --- | --- | --- | --- |
| S0 Idea Intake | Capture goal, boundaries, and initial risk. | product intent, initial gate | discovery/design gate |
| S1 Domain Model | Build visible business model before deep questioning. | domain model, assumption ledger | user correction gate |
| S2 Discovery Baseline | Stabilize problem, users, scenarios, MVP, risks. | discovery baseline | discovery baseline gate |
| S3 PRD Baseline | Define product behavior and acceptance. | PRD, acceptance, traceability | PRD baseline gate |
| S4 Architecture Baseline | Define system boundaries and technical direction. | architecture baseline, ADR candidates | architecture baseline gate |
| S5 Detailed Design | Make design implementable. | design package, gap assessment | design baseline gate |
| S6 Implementation Planning | Convert design into sequenced packets. | work packets, dev plan | implementation readiness gate |
| S7 Coding | Change code/config only inside approved scope. | diff, tests, evidence | slice build gate |
| S8 Testing And Repair | Prove behavior and repair findings. | test report, review report | review/repair gate |
| S9 Release Gate | Decide whether to release or hold. | readiness, rollback, monitoring | release/deployment gate |
| S10 Operate And Handoff | Preserve continuity and operational evidence. | handoff, evidence index | closeout or iteration gate |

## Transition Rules

- Each stage may loop back when review finds material gaps.
- A gate may narrow scope but cannot silently widen it.
- Passing validation or review does not approve the next stage.
- Architecture baseline does not authorize implementation.
- Implementation does not authorize deployment, rollback, migration, permission,
  secret, payment, or production-data action.

## Stop States

```text
PASS_RECOMMENDED
FAIL_REPAIRABLE
BLOCKED_MISSING_CONTEXT
BLOCKED_AUTHORITY_CONFLICT
NEED_USER_GATE
LOOP_LIMIT_REACHED
OUT_OF_SCOPE
```

## User Role

The user owns goals, business truth, tradeoffs, and explicit gate decisions.

## Codex Role

Codex owns modeling, artifact generation, technical decomposition, review,
repair, validation, and handoff inside approved boundaries.
