# Traceability ID System v0.1

Status: candidate repair evidence
Task: T-0010

## Purpose

Create stable cross-document IDs so requirements, workflows, APIs, data, UX, security, tests, operations, risks, decisions, gates, findings, and artifacts can be reviewed as a connected system.

## ID Prefixes

| Prefix | Meaning | Example |
| --- | --- | --- |
| `ART-*` | Artifact | `ART-PRD-001` |
| `GOAL-*` | Business goal | `GOAL-001` |
| `ROLE-*` | Actor or responsibility | `ROLE-CS-001` |
| `OBJ-*` | Business object | `OBJ-TICKET-001` |
| `REQ-*` | Functional requirement | `REQ-ORDER-001` |
| `NFR-*` | Non-functional requirement | `NFR-PERF-001` |
| `AC-*` | Acceptance criterion | `AC-REQ-001-A` |
| `WF-*` | Workflow or state transition | `WF-RMA-001` |
| `DATA-*` | Entity, field, or data authority item | `DATA-CONTRACT-001` |
| `API-*` | API endpoint or operation | `API-TICKET-001` |
| `EVT-*` | Event, webhook, or stream message | `EVT-STATUS-001` |
| `ERR-*` | Error code | `ERR-AUTH-001` |
| `UI-*` | Screen, component, or user interaction | `UI-TICKET-001` |
| `SEC-*` | Security requirement or threat | `SEC-RBAC-001` |
| `TEST-*` | Test case or test suite | `TEST-CONTRACT-001` |
| `OBS-*` | Metric, alert, dashboard, or runbook | `OBS-LATENCY-001` |
| `RISK-*` | Product, technical, delivery, or operational risk | `RISK-DATA-001` |
| `DEC-*` | User or architecture decision | `DEC-SCOPE-001` |
| `GATE-*` | Gate decision reference | `GATE-BASELINE-001` |
| `FIND-*` | Review finding | `FIND-P1-001` |

## Required Link Rules

- Every `REQ-*` links to at least one `GOAL-*`, `AC-*`, `WF-*`, and `TEST-*`.
- Every `WF-*` links to owner `ROLE-*`, relevant `DATA-*`, user-visible `UI-*` if applicable, and implementation-facing `API-*` or `EVT-*` where applicable.
- Every `API-*` links to `REQ-*`, `WF-*`, `DATA-*`, `ERR-*`, and `TEST-*`.
- Every sensitive `DATA-*` links to `SEC-*`, owner, source, confidence, and audit requirement.
- Every `UI-*` links to `REQ-*`, `WF-*`, `API-*` or `EVT-*`, and accessibility notes.
- Every `SEC-*` links to mitigation, test, owner, and high-risk gate if needed.
- Every `RISK-*` links to mitigation, test or monitor, owner, and residual risk decision.
- Every unresolved `FIND-*` links to a repair plan or explicit deferral.

## Traceability Matrix Columns

Minimum columns:

```text
source_id | target_id | relation | owner | source | confidence | conflict_status | review_status | evidence_path
```

Allowed `relation` values:

```text
drives | satisfies | depends_on | implements | verifies | mitigates | monitors | blocks | supersedes | defers
```

Allowed `conflict_status` values:

```text
none | suspected | confirmed | resolved | deferred
```

Allowed `review_status` values:

```text
unreviewed | reviewed | repair_required | repaired | accepted | deferred
```

## Conflict Handling

When two artifacts disagree:

1. Create `FIND-*`.
2. Mark affected rows `conflict_status: suspected` or `confirmed`.
3. Identify owner and source for each side.
4. Repair if structural or ask the user if business truth is needed.
5. Mark resolved or deferred with rationale.

## Completeness Checks

Before baseline recommendation:

- no orphan `REQ-*`
- no orphan `WF-*`
- no orphan `API-*` in MVP scope
- no sensitive `DATA-*` without `SEC-*`
- no release risk without `TEST-*` or `OBS-*`
- no unresolved P0/P1 `FIND-*`
- all major P2 `FIND-*` repaired or explicitly deferred

## Candidate Boundary

This ID system is candidate evidence only. It becomes a standing project rule only after a later explicit baseline and installation/rule-change gate.
