# Evidence And Audit Enforcement Design Candidate v0.1

Status: candidate evidence only
Task: T-0019

## Purpose

Define how evidence, checker results, gate receipts, handoff, and audit should
be structured so future real-project governance is resumable and verifiable.

## Evidence Directory Layout

Candidate layout:

```text
.ai/evidence/<task-id>/
  commands.md
  startup-validation.v0.1.md
  gate-request.<gate-id>.v0.1.md
  user-decision-packet.<slug>.v0.1.md
  <gate-slug>.approval.record.v0.1.md
  gate-register.<stage-id>.yaml
  checkers/
    <checker-id>.<run-id>.yaml
  exceptions/
    <exception-id>.yaml
  receipts/
    gate-receipt.<gate-id>.yaml
  audit/
    audit.<trigger>.<timestamp>.yaml
  evidence-lock.<stage-id>.yaml
```

## Required Evidence by Event

| Event | Required Evidence |
| --- | --- |
| Startup | State reads, current task, current gate, validation output, boundary confirmation. |
| Gate request | Gate ID, scope, allowed paths/actions, forbidden scope, risk flags, validation plan, exit criteria. |
| Gate approval | Exact user approval text, timestamp, approval actor, non-authorization list. |
| Stage work | Produced artifacts, source inputs, assumptions, related IDs, checker runs. |
| Checker run | Structured checker result file plus raw command output when available. |
| Exception | Exception object, compensating controls, approval source, expiry/revisit point. |
| Gate receipt | Links to all evidence and checker results used by the gate. |
| Closeout | Validate output, evidence index, current state, next gate, handoff audit. |

## Gate Receipt Shape

```yaml
receipt_id: <id>
gate_id: <gate id>
task_id: <task id>
created_at: <ISO8601>
gate_status: approved | rejected | superseded
approval_evidence: <path>
scope_evidence: <path>
checker_results:
  - <path>
exceptions:
  - <path>
required_artifacts:
  - <path>
findings_summary:
  P0: 0
  P1: 0
  P2: 0
  P3: 0
non_authorizations:
  - <text>
```

## Audit Triggers

| Trigger | Timing | Audit Questions |
| --- | --- | --- |
| `phase_transition` | Before lifecycle stage promotion. | Is the register complete, unfrozen, and all direct checks clear? |
| `gate_verdict` | After recording user decision. | Does gate receipt cite the exact user decision and scope? |
| `high_risk_preflight` | Before high-risk action. | Is a separate gate present for the exact action class? |
| `closeout` | Before marking task completed. | Are state, task graph, progress, handoff, gates, and evidence consistent? |

## Handoff Enforcement

A future `stale-handoff-check` should fail when:

- `.ai/HANDOFF.md` current task differs from `.ai/state.yaml`
- handoff says no pending gates while gates.yaml contains pending gates
- handoff recommends a next gate that has already been superseded
- handoff omits forbidden scope for high-risk actions
- handoff references old real-project details as if they are current authority

## Closeout Rules

Before a task can be marked completed:

1. `validate_state.py` or successor validator must pass.
2. All direct checker results must be `passed` or validly `excepted`.
3. No unintended pending gate may remain.
4. PROGRESS and HANDOFF must name the current task.
5. Evidence index must list generated artifacts.
6. Next recommended gate must be explicit.
7. Non-authorization boundaries must be stated.

## Boundary

This document designs evidence and audit structure only. It does not install or
enable any validator, auditor, hook, MCP, wrapper, or tool behavior.
