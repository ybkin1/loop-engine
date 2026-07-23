# Implementation Readiness Gate Candidate v0.1

Status: candidate
Task: T-0017

## Purpose

Define the gate that must pass before Codex may write real project code or
configuration for a named implementation slice.

Implementation readiness is not deployment readiness.

## Required Preconditions

- Real-project entry is approved for the target root.
- Product brief or PRD baseline is approved.
- Acceptance criteria are approved.
- Architecture baseline is approved or explicitly scoped as not required.
- Detailed design package exists for the slice.
- Work packets are derived from architecture nodes.
- Allowed paths and forbidden paths are explicit.
- Validation commands are named.
- Rollback or recovery boundary is stated.
- High-risk actions are excluded or separately gated.

## Build Gate Fields

```yaml
id: G-<task-id>-IMPLEMENTATION-READINESS
task_id: <T-XXXX>
gate_type: implementation-readiness
target_project_root: <absolute path>
slice_id: <SLICE-*>
allowed_paths:
  - <path>
forbidden_paths:
  - <path or pattern>
source_artifacts:
  prd: <path>
  architecture: <path>
  detailed_design: <path>
  work_packets: <path>
validation_commands:
  - <command>
evidence_path: <path>
rollback_boundary: <description>
high_risk_exclusions:
  deployment: true
  rollback: true
  database: true
  permission: true
  secret: true
  payment: true
  production_data: true
  migration: true
```

## Work Packet Rules

Each work packet must include:

- packet ID
- linked architecture node
- linked requirement and acceptance criterion
- expected files or modules
- validation method
- risk note
- owner agent or role
- dependency list
- completion evidence

Forbidden coarse names:

- `backend`
- `frontend`
- `business_logic`
- `fix everything`
- `implement feature`

If a slice crosses multiple implementation layers, split it into multiple
verifiable packets.

## Readiness Checklist

- [ ] no orphan MVP requirement
- [ ] no orphan architecture node in implementation scope
- [ ] no orphan work packet
- [ ] every packet has test or manual verification
- [ ] every sensitive data path has security treatment
- [ ] every external integration has failure behavior
- [ ] every state transition has terminal-state handling
- [ ] every high-risk action is forbidden or separately gated
- [ ] user-owned dirty files are identified
- [ ] generated/ignored paths policy is clear

## Allowed Outcomes

- `ready_for_build_gate_request`
- `repair_required`
- `blocked_needs_user_decision`
- `blocked_missing_artifact`
- `out_of_scope`

## Boundary

Passing this gate allows only the named implementation slice if the user
explicitly approves it. It does not authorize deployment, rollback, database
changes, permission changes, secret handling, payment actions, production-data
access, migrations, AGENTS.md changes, or runtime/tool enablement.
