# Gate Request Template v0.1

Status: candidate repair evidence
Task: T-0010

## Purpose

Provide a reusable gate request format that separates user decision, allowed work, forbidden work, evidence, validation, lifecycle transition, and high-risk boundaries.

## Gate Request

```yaml
id: G-<task-id>-<short-purpose>
task_id: <T-XXXX>
gate_type: <design-only|review-only|repair-only|baseline-review|baseline-approval|activation-reference|installation|real-project-entry|implementation|release|high-risk|closeout>
requested_lifecycle_transition:
  artifact_id: <artifact-or-method-id>
  from: <candidate|reviewed|repair_required|repaired|baseline_candidate|baseline_approved|active_reference|installed|superseded|null>
  to: <candidate|reviewed|repair_required|repaired|baseline_candidate|baseline_approved|active_reference|installed|superseded|null>
status: pending
decision: pending
requested_at: <timestamp>
requested_by: ai
approval_required_from: user
scope: <plain-language scope>
allowed_paths:
  - <path or directory>
forbidden_paths:
  - <path or directory>
allowed_actions:
  - <specific action>
forbidden_actions:
  - <specific forbidden action>
high_risk_flags:
  deployment: false
  rollback: false
  database: false
  permission: false
  secret: false
  payment: false
  production_data: false
  migration: false
  runtime_behavior: false
evidence_required:
  - commands.md
  - <artifact-or-report>
validation_required:
  - validate_state.py
exit_criteria:
  - <condition>
expiry_or_boundary: <optional time, task, path, or stage boundary>
notes:
  - Validator success is evidence only.
  - Reviewer PASS is evidence only.
  - Tests are evidence only.
  - AI recommendation is evidence only.
```

## Approval Recording

When the user explicitly approves, update the gate record:

```yaml
status: approved
decision: approved
recorded_at: <timestamp>
approval_text: <short quote or paraphrase of user approval>
```

When the user rejects:

```yaml
status: rejected
decision: rejected
recorded_at: <timestamp>
rejection_reason: <if provided>
```

## Required Gate Checks

Before proceeding after a gate request:

- Confirm the latest user request.
- Confirm project root.
- Read `.ai/state.yaml`, `.ai/HANDOFF.md`, current task file, `.ai/gates.yaml`, and `.ai/task_graph.yaml`.
- Run `validate_state.py`.
- Search for pending gates.
- If any pending gate remains without explicit user approval or rejection, stop.
- Continue only inside the approved scope.

## High-Risk Addendum

Any gate with a high-risk flag set to `true` must include:

- risk summary
- owner or approving user
- dry-run or preview plan when possible
- rollback or recovery plan
- verification plan
- affected systems and paths
- no-go conditions
- exit criteria

## Candidate Method Boundary

This template is candidate evidence only. It is not an installed gate policy until a later explicit installation or rule-change gate approves it.
