# Gate Request: G-T-0020-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-REVIEW

Status: pending
Task: T-0020
Requested by: ai
Approval required from: user

## Gate

```text
G-T-0020-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-REVIEW
```

## Purpose

Authorize a review-only task to assess whether the T-0019 enforcement
architecture candidate package sufficiently repairs the T-0018 P1 enforcement
gap and whether it can move to later baseline consideration.

## Primary Review Targets After Explicit Approval

- `.ai/evidence/T-0019/enforcement-architecture.candidate.v0.1.md`
- `.ai/evidence/T-0019/machine-readable-gate-register-schema.candidate.v0.1.md`
- `.ai/evidence/T-0019/checker-catalog-and-blocking-semantics.candidate.v0.1.md`
- `.ai/evidence/T-0019/policy-guard-and-wrapper-design.candidate.v0.1.md`
- `.ai/evidence/T-0019/tool-entry-restriction-model.candidate.v0.1.md`
- `.ai/evidence/T-0019/evidence-and-audit-enforcement-design.candidate.v0.1.md`
- `.ai/evidence/T-0019/failure-mode-and-recovery-design.candidate.v0.1.md`
- `.ai/evidence/T-0019/t0017-repair-coverage-map.v0.1.md`
- `.ai/evidence/T-0019/self-review.v0.1.md`
- `.ai/evidence/T-0019/next-gate-recommendation.v0.1.md`

## Supporting Review Targets After Explicit Approval

- `.ai/evidence/T-0018/review-summary.v0.1.md`
- `.ai/evidence/T-0018/enforcement-gap-review.v0.1.md`
- `.ai/evidence/T-0018/role-review-findings.v0.1.md`
- `.ai/evidence/T-0018/next-gate-recommendation.v0.1.md`

## Allowed Scope After Explicit Approval

- Read current `.ai` governance context.
- Read the listed T-0019 primary review targets.
- Read the listed T-0018 supporting review targets.
- Review whether T-0019 sufficiently repairs `FIND-T0018-P1-001`.
- Review distinction between AI self-discipline, script checks, MCP or skill
  guardrails, wrappers or policy guards, and true tool-entry enforcement.
- Review gate register schema coverage for lifecycle, approval, scope,
  allowed and forbidden actions, evidence, blocking checks, and high-risk
  flags.
- Review checker catalog and blocking semantics for fail-closed/fail-open,
  missing evidence, pending gate, out-of-scope action, stale handoff, and
  unavailable-checker cases.
- Review policy guard, wrapper, tool-entry restriction, evidence, audit, and
  failure recovery design.
- Produce T-0020 review evidence and a next-gate recommendation.
- Update T-0020 governance records and handoff.
- Run `validate_state.py`, `close_session.py`, and `audit_handoff.py` after
  approval and review work as appropriate.

## Allowed Paths After Explicit Approval

- `.ai/tasks/T-0020.md`
- `.ai/evidence/T-0020/`
- `.ai/state.yaml`
- `.ai/task_graph.yaml`
- `.ai/gates.yaml`
- `.ai/PROGRESS.md`
- `.ai/HANDOFF.md`

## Allowed Read Paths

- `.ai/evidence/T-0019/`
- `.ai/tasks/T-0019.md`
- `.ai/evidence/T-0018/`
- `.ai/tasks/T-0018.md`
- `.ai/state.yaml`
- `.ai/task_graph.yaml`
- `.ai/gates.yaml`
- `.ai/PROGRESS.md`
- `.ai/HANDOFF.md`

## Forbidden Scope

- Do not approve this gate without explicit user approval.
- Do not treat this pending gate or the user request prompt as approval.
- Do not perform T-0020 review work before explicit user approval.
- Do not implement any checker.
- Do not install or enable MCP, skill, policy guard, wrapper, automation,
  protocol, runtime, or tool behavior.
- Do not modify `AGENTS.md`.
- Do not enter, create, or modify a real business project.
- Do not write business code.
- Do not build, deploy, release, or roll back.
- Do not change databases, permissions, secrets, payment systems, production
  data, or migrations.
- Do not treat validator success, reviewer PASS, AI recommendation, or
  subagent conclusions as user approval.
- Do not promote T-0019 to baseline, active, installed, or
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

- `.ai/evidence/T-0020/commands.md`
- `.ai/evidence/T-0020/startup-validation.v0.1.md`
- `.ai/evidence/T-0020/gate-request.G-T-0020-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-REVIEW.v0.1.md`
- `.ai/evidence/T-0020/user-decision-packet.real-project-governance-enforcement-architecture-review.v0.1.md`

## Review Evidence After Explicit Approval

- `.ai/evidence/T-0020/review-scope.v0.1.md`
- `.ai/evidence/T-0020/t0019-package-coverage-review.v0.1.md`
- `.ai/evidence/T-0020/enforcement-architecture-review.v0.1.md`
- `.ai/evidence/T-0020/gate-register-schema-review.v0.1.md`
- `.ai/evidence/T-0020/checker-and-blocking-semantics-review.v0.1.md`
- `.ai/evidence/T-0020/policy-guard-and-wrapper-review.v0.1.md`
- `.ai/evidence/T-0020/tool-entry-restriction-review.v0.1.md`
- `.ai/evidence/T-0020/evidence-and-audit-enforcement-review.v0.1.md`
- `.ai/evidence/T-0020/failure-mode-and-recovery-review.v0.1.md`
- `.ai/evidence/T-0020/t0018-repair-coverage-verdict.v0.1.md`
- `.ai/evidence/T-0020/residual-risk-register.v0.1.md`
- `.ai/evidence/T-0020/review-summary.v0.1.md`
- `.ai/evidence/T-0020/next-gate-recommendation.v0.1.md`

## Allowed Review Conclusions

- `PASS_FOR_BASELINE_CONSIDERATION`
- `REPAIR_REQUIRED`
- `BLOCKED_BY_SCOPE_OR_MISSING_EVIDENCE`

## Validation Required

- `validate_state.py` must pass before this gate is recorded.
- `validate_state.py` must report the pending gate blocker after this gate is
  recorded.
- After explicit user decision, `validate_state.py` must be rerun.

## Exit Criteria

- User explicitly approves, rejects, or requests repair of this gate.
- No review body, implementation, real-project entry, installation,
  `AGENTS.md` change, runtime/tool enablement, deployment, rollback, database,
  permission, secret, payment, production-data, or migration action occurs
  while this gate is pending.
