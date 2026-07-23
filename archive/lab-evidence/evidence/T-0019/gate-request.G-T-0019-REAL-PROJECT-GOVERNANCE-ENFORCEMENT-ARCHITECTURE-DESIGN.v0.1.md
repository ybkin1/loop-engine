# Gate Request: G-T-0019-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-DESIGN

Status: pending
Task: T-0019
Requested by: ai
Approval required from: user

## Gate

```text
G-T-0019-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-DESIGN
```

## Purpose

Authorize a design/repair task to address `FIND-T0018-P1-001`: the T-0017
governance package remains Markdown-only and lacks a concrete enforcement
architecture.

## Allowed Scope After Explicit Approval

- Read current `.ai` governance context.
- Read T-0018 review evidence and relevant T-0017 candidate package evidence.
- Produce candidate enforcement architecture artifacts.
- Design a machine-readable gate register for lifecycle stages.
- Define mandatory checker catalog and blocking semantics.
- Define how `validate_state.py` or later scripts detect missing evidence,
  pending checks, forbidden scope, and stale handoff.
- Define policy guard / wrapper behavior for real-project entry and high-risk
  actions.
- Define tool-entry restrictions for deployment, rollback, database,
  permission, secret, payment, production-data, migration, `AGENTS.md`, skill,
  MCP, automation, protocol, runtime, and tool behavior changes.
- Define unavailable-checker failure modes.
- Define evidence paths and closeout/audit behavior.
- Distinguish AI self-discipline, script checks, MCP/skill guardrails,
  wrappers, and true tool-entry enforcement.
- Define phased adoption from design-only to a later possible implementation
  gate.
- Update T-0019 governance records and evidence.
- Run `validate_state.py`, `close_session.py`, and `audit_handoff.py` as
  appropriate after approval.

## Allowed Paths After Explicit Approval

- `.ai/tasks/T-0019.md`
- `.ai/evidence/T-0019/`
- `.ai/state.yaml`
- `.ai/task_graph.yaml`
- `.ai/gates.yaml`
- `.ai/PROGRESS.md`
- `.ai/HANDOFF.md`

## Allowed Read Paths

- `.ai/evidence/T-0018/`
- `.ai/tasks/T-0018.md`
- `.ai/evidence/T-0017/`
- `.ai/tasks/T-0017.md`
- `.ai/state.yaml`
- `.ai/task_graph.yaml`
- `.ai/gates.yaml`
- `.ai/PROGRESS.md`
- `.ai/HANDOFF.md`

## Forbidden Scope

- Do not approve this gate without explicit user approval.
- Do not treat this pending gate as approval.
- Do not perform T-0019 enforcement architecture design before explicit user
  approval.
- Do not install or enable any skill, MCP, policy guard, wrapper, automation,
  protocol, runtime, or tool behavior.
- Do not modify `AGENTS.md`.
- Do not enter, create, or modify a real business project.
- Do not write business code.
- Do not implement, build, deploy, release, or roll back.
- Do not change databases, permissions, secrets, payment systems, production
  data, or migrations.
- Do not treat T-0018 review, validator success, tests, AI recommendation, or
  subagent conclusions as user approval.
- Do not promote T-0017 or T-0019 to baseline, active, installed, or
  real-project-applicable state.

## High-Risk Flags

```yaml
deployment: false
rollback: false
database: false
permission: false
secret: false
payment: false
production_data: false
migration: false
runtime_behavior: false
```

## Required Evidence For Gate Presentation

- `.ai/evidence/T-0019/commands.md`
- `.ai/evidence/T-0019/startup-validation.v0.1.md`
- `.ai/evidence/T-0019/gate-request.G-T-0019-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-DESIGN.v0.1.md`
- `.ai/evidence/T-0019/user-decision-packet.real-project-governance-enforcement-architecture-design.v0.1.md`

## Candidate Evidence After Explicit Approval

- `.ai/evidence/T-0019/enforcement-architecture.candidate.v0.1.md`
- `.ai/evidence/T-0019/machine-readable-gate-register-schema.candidate.v0.1.md`
- `.ai/evidence/T-0019/checker-catalog-and-blocking-semantics.candidate.v0.1.md`
- `.ai/evidence/T-0019/policy-guard-and-wrapper-design.candidate.v0.1.md`
- `.ai/evidence/T-0019/tool-entry-restriction-model.candidate.v0.1.md`
- `.ai/evidence/T-0019/evidence-and-audit-enforcement-design.candidate.v0.1.md`
- `.ai/evidence/T-0019/failure-mode-and-recovery-design.candidate.v0.1.md`
- `.ai/evidence/T-0019/t0017-repair-coverage-map.v0.1.md`
- `.ai/evidence/T-0019/next-gate-recommendation.v0.1.md`

## Validation Required

- `validate_state.py` must pass before this gate is recorded.
- `validate_state.py` must report the pending gate blocker after this gate is
  recorded.
- After explicit user decision, `validate_state.py` must be rerun.

## Exit Criteria

- User explicitly approves, rejects, or requests repair of this gate.
- No enforcement architecture design work, implementation, real-project entry,
  installation, `AGENTS.md` change, runtime/tool enablement, deployment,
  rollback, database, permission, secret, payment, production-data, or migration
  action occurs while this gate is pending.
