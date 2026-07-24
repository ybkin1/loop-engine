# Machine-Readable Gate Register Schema Candidate v0.1

Status: candidate evidence only
Task: T-0019

## Purpose

Define the candidate schema for a machine-readable gate register that can block
stage progression when required evidence, checks, or user decisions are missing.

## File Location

Candidate location:

```text
.ai/evidence/<task-id>/gate-register.<stage-id>.yaml
```

For real projects with their own `.ai`, the register must live inside the real
project's approved evidence root, not in this governance lab.

## Schema

```yaml
schema_version: 1
register_id: GR-<task-id>-<stage-id>
task_id: T-XXXX
stage_id: S0|S1|S2|S3|S4|S5|S6|S7|S8|S9|S10
stage_name: <human readable stage>
stage_status: pending | in_progress | blocked | ready_for_gate | passed | failed
created_at: <ISO8601>
updated_at: <ISO8601>
frozen: false

target_project:
  project_kind: governance_lab | real_project
  root: <absolute path or null>
  evidence_root: <absolute path>
  entry_gate_id: <gate id or null>

route_profile:
  action_family: clarify | research | authoring | implementation | verification | review | closeout
  artifact_kind: intent | feature-brief | prd | design-spec | contract | code | test-plan | verification-report | review-report | handoff | git-closeout
  lifecycle_stage: <stage id>
  required_gates:
    - <gate type>
  mandatory_checkers:
    - <checker id>

gate_bindings:
  - gate_id: <gate id>
    gate_type: <gate type>
    status: pending | approved | rejected | superseded
    approval_required_from: user
    approval_evidence: <path or null>
    blocks_stage_when: pending | rejected | missing

required_artifacts:
  - artifact_id: <ART-*>
    path: <path>
    status_required: candidate | reviewed | baseline_candidate | user_approved
    owner_stage: <stage id>
    required: true
    freshness_target: file_mtime | declared_last_updated

checker_items:
  - checker_id: <checker id>
    gate_binding:
      - value
      - professional
      - contract
      - <gate id>
    status: pending | passed | failed | blocked | unavailable | excepted | manual_pending
    blocking: direct | indirect | advisory
    required_runtime:
      - shell
    on_unavailable: fail_closed | manual_evidence | warn
    target_refs:
      - <path>
    result_ref: <path or null>
    evidence_ref: <path or null>
    exception_ref: <path or null>
    last_target_update: <ISO8601 or null>
    run_at: <ISO8601 or null>

forbidden_scope:
  action_classes:
    - deployment
    - rollback
    - database_change
    - permission_change
    - secret_handling
    - payment_action
    - production_data_action
    - migration
    - agents_md_change
    - skill_mcp_runtime_tool_enablement
  forbidden_paths:
    - <path or glob>
  forbidden_tools:
    - <tool class or command family>

exceptions:
  - exception_id: <id>
    class: verification_exception | checker_unavailable | scope_exception
    status: requested | approved | expired | resolved
    evidence_ref: <path>
    expires_at_or_revisit_when: <text>

transition_controls:
  pending_is_blocking: true
  missing_required_artifact_blocks: true
  stale_checker_blocks: true
  failed_direct_checker_blocks: true
  unavailable_fail_closed_blocks: true
  reviewer_pass_is_not_approval: true
  validator_success_is_not_approval: true

closeout:
  evidence_lock_ref: <path or null>
  audit_report_ref: <path or null>
  handoff_ref: <path or null>
```

## Status Semantics

| Status | Meaning | Blocks Stage |
| --- | --- | --- |
| `pending` | Required check has not run or required user decision is absent. | yes |
| `passed` | Checker ran and produced valid evidence. | no |
| `failed` | Checker ran and found a blocking issue. | yes for direct bindings |
| `blocked` | Checker could not determine result because prerequisite evidence is missing. | yes |
| `unavailable` | Runtime or checker implementation is unavailable. | depends on `on_unavailable` |
| `excepted` | Approved exception with compensating controls exists. | no if exception is valid |
| `manual_pending` | Manual evidence is required but not complete. | yes |

## Transition Rules

- A register may be created with `checker_items.status: pending`.
- Stage promotion may not occur while any direct checker is `pending`,
  `failed`, `blocked`, or `manual_pending`.
- `unavailable` blocks when `on_unavailable: fail_closed`.
- `unavailable` with `manual_evidence` blocks until a structured manual
  evidence record exists.
- A register becomes immutable when `frozen: true`.
- Any artifact modified after its checker result requires checker rerun.

## Minimal Validation Algorithm

```text
load register
assert schema_version is supported
assert every required gate exists in gates.yaml
assert no required gate is pending or rejected
assert every required artifact exists
assert every direct checker has result status passed or valid exception
assert no fail_closed checker is unavailable
assert result run_at is newer than target artifact updates
assert forbidden_scope has not been crossed by recorded actions
assert handoff current task and gate match state.yaml
allow transition only if all assertions pass
```

## Boundary

This schema is a design candidate only. It is not installed and is not consumed
by current tooling.
