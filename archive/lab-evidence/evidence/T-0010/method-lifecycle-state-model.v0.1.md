# Method Lifecycle State Model v0.1

Status: candidate repair evidence
Task: T-0010

## Purpose

Define exact lifecycle states for method artifacts so future sessions do not confuse candidate evidence with approved baseline, active reference, installed behavior, or superseded work.

## Status Rules

- Method lifecycle state describes an artifact or method package.
- Gate `status` describes a user decision: `pending`, `approved`, `rejected`, or `superseded`.
- Task `status` describes execution: `in_progress`, `completed`, `blocked`, or `superseded`.
- `validator success`, reviewer PASS, tests, and AI recommendations are evidence only.
- User approval is always a separate explicit gate decision.

## Lifecycle Table

| State | Meaning | Allowed Actions | Forbidden Interpretations | Required Evidence | Transition Gate |
| --- | --- | --- | --- | --- | --- |
| `candidate` | Draft method evidence exists. | Read, review, repair under approved task scope. | Not approved, not active, not installed, not applicable to real projects. | Candidate artifacts, scope, commands. | Creation/design gate. |
| `reviewed` | A review has assessed the candidate. | Use findings to decide repair or rejection. | Review result is not approval. PASS is not installation. | Review scope, findings, severity table, residual risk. | Review-only gate. |
| `repair_required` | Review found blockers or important gaps. | Open repair-only gate, create repair evidence. | Cannot baseline, install, or apply. | Findings, P0/P1/P2 list, next repair recommendation. | Repair gate approval. |
| `repaired` | Repair evidence addresses findings. | Run review rerun or readiness review. | Repair is not baseline approval. | Repair plan, changed artifact list, diff summary, coverage matrix. | Review-rerun gate. |
| `baseline_candidate` | Repaired package is ready to be considered as a baseline. | Run final baseline-readiness review and ask user for baseline decision. | Still not approved or installed. | Readiness checklist, traceability matrix, role-review rerun. | Baseline-review gate. |
| `baseline_approved` | User explicitly approves the method as a baseline reference. | Use as a reference in approved governance work. | Not installed into startup/runtime behavior unless separately gated. | Baseline approval gate, approved package ID, known limitations. | Baseline approval gate. |
| `active_reference` | Approved method may guide project-local governance evidence. | Reference in `.ai` process records within approved scope. | Does not modify `AGENTS.md` or runtime behavior by itself. | Activation/reference gate, scope and boundaries. | Activation/reference gate. |
| `installed` | Method or instruction has been written into an operating rule, startup file, plugin, automation, or runtime behavior. | Follow installed behavior only inside the approved installed scope. | Installation cannot be inferred from baseline approval. | Installation gate, changed-path audit, exact installed diff, validation. | Installation/rule-change gate. |
| `superseded` | Later approved artifact replaces this one. | Keep for audit; point to successor. | Do not use as current baseline unless explicitly revived. | Supersession record, successor ID, migration notes. | Supersession gate or approved replacement record. |

## Allowed Transitions

| From | To | Required Condition |
| --- | --- | --- |
| none | `candidate` | User approves candidate design or repair task. |
| `candidate` | `reviewed` | Review-only gate completed with findings. |
| `reviewed` | `repair_required` | Review records unresolved P0/P1 or major P2. |
| `repair_required` | `repaired` | Repair-only gate completes with evidence and coverage summary. |
| `repaired` | `baseline_candidate` | Review rerun finds no unresolved P0/P1 and major P2 are fixed or explicitly deferred. |
| `baseline_candidate` | `baseline_approved` | User explicitly approves baseline gate. |
| `baseline_approved` | `active_reference` | User explicitly approves activation/reference gate. |
| `active_reference` | `installed` | User explicitly approves installation or rule-change gate and changed-path audit passes. |
| any non-installed state | `superseded` | Later approved candidate or baseline replaces it by explicit record. |
| `installed` | `superseded` | Separate deprecation/removal/migration gate records replacement and installed-state handling. |

## Disallowed Transitions

- `candidate` directly to `installed`.
- `reviewed` directly to `baseline_approved`.
- `repair_required` directly to `baseline_approved`.
- `repaired` directly to `installed`.
- Any transition into a real business project without a real-project entry gate.
- Any transition into database, permission, secret, payment, production-data, migration, deployment, rollback, or runtime behavior change without a specific high-risk gate.

## Completion Criteria For T-0010

T-0010 may only claim `repaired` candidate status when:

- P1 findings are mapped to repair artifacts.
- Major P2 findings are fixed or explicitly deferred.
- Repair evidence is written under `.ai/evidence/T-0010/`.
- `validate_state.py` passes.
- Next gate recommendation is review-rerun or baseline-readiness review, not installation or real-project application.
