# Traceability And Evidence Schema Candidate v0.1

Status: candidate
Task: T-0017

## Purpose

Define the minimum traceability and evidence schema for real software project
delivery.

## Required ID Prefixes

| Prefix | Meaning |
| --- | --- |
| `ART-*` | artifact |
| `GOAL-*` | business goal |
| `ROLE-*` | actor or responsibility |
| `OBJ-*` | business object |
| `REQ-*` | functional requirement |
| `NFR-*` | non-functional requirement |
| `AC-*` | acceptance criterion |
| `WF-*` | workflow or state transition |
| `DATA-*` | entity, field, or data authority item |
| `API-*` | API endpoint or operation |
| `EVT-*` | event, webhook, or stream message |
| `ERR-*` | error code |
| `UI-*` | screen, component, or user interaction |
| `SEC-*` | security requirement or threat |
| `TEST-*` | test case or test suite |
| `OBS-*` | metric, alert, dashboard, or runbook |
| `RISK-*` | product, technical, delivery, or operational risk |
| `DEC-*` | user or architecture decision |
| `GATE-*` | gate decision reference |
| `FIND-*` | review finding |

## Link Rules

- Every `REQ-*` links to `GOAL-*`, `AC-*`, `WF-*`, and `TEST-*`.
- Every `WF-*` links to owner `ROLE-*`, relevant `DATA-*`, terminal state,
  and UI/API/event where applicable.
- Every `API-*` links to `REQ-*`, `WF-*`, `DATA-*`, `ERR-*`, and `TEST-*`.
- Every sensitive `DATA-*` links to `SEC-*`, owner, source, confidence, and
  audit requirement.
- Every `UI-*` links to `REQ-*`, `WF-*`, API/event dependency, and
  accessibility notes.
- Every `SEC-*` links to mitigation, test, owner, and high-risk gate if needed.
- Every `RISK-*` links to mitigation, test or monitor, owner, and residual risk
  decision.
- Every unresolved `FIND-*` links to repair or explicit deferral.

## Matrix Columns

```text
source_id | target_id | relation | owner | source | confidence | conflict_status | review_status | evidence_path
```

Allowed relations:

```text
drives | satisfies | depends_on | implements | verifies | mitigates | monitors | blocks | supersedes | defers
```

## Evidence Requirements

Every task should record:

- user gate text
- scope and forbidden scope
- commands and validation output
- generated artifacts
- review findings
- repair history
- changed-path baseline when writes are possible
- validation or test evidence
- boundary checks
- handoff or startup prompt

## Baseline Completeness Checks

- no orphan MVP requirement
- no orphan workflow in MVP scope
- no orphan API in MVP scope
- no sensitive data without security treatment
- no release risk without test, monitor, or rollback path
- no unresolved P0/P1 finding
- major P2 findings repaired or explicitly deferred
- all gates referenced by artifacts exist in gate evidence

## Evidence Location Rule

Evidence lives under:

```text
.ai/evidence/<task-id>/
```

If a real project has its own `.ai`, its evidence must live in that project's
approved evidence directory. Governance-lab evidence must not be mistaken for
real-project approval.
