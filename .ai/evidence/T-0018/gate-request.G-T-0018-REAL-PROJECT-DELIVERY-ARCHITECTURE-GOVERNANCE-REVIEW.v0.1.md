# Gate Request: G-T-0018-REAL-PROJECT-DELIVERY-ARCHITECTURE-GOVERNANCE-REVIEW

## Status

pending

## Decision Required

User must explicitly approve, reject, or request repair of this review-only
gate before any T-0018 review work begins.

Approval phrase:

```text
批准 G-T-0018-REAL-PROJECT-DELIVERY-ARCHITECTURE-GOVERNANCE-REVIEW
```

## Purpose

Authorize a review-only task for the T-0017 candidate package:

```text
.ai/evidence/T-0017/package-index.real-project-delivery-architecture-governance.candidate.v0.1.md
```

The review should decide whether the T-0017 package is ready for repair,
baseline consideration, rejection / supersession, or later dry-run.

## Allowed Actions After Approval

- Read current `.ai` governance records.
- Read T-0017 evidence under `.ai/evidence/T-0017/`.
- Review lifecycle and gate consistency.
- Review real-project entry isolation.
- Review product discovery usefulness.
- Review domain model and PRD completeness.
- Review architecture baseline quality.
- Review detailed design package depth.
- Review implementation readiness boundaries.
- Review review and quality gates.
- Review traceability and evidence schema.
- Review security, data, deployment, and high-risk boundaries.
- Review handoff and context hygiene.
- Review residual risks from T-0017.
- Review whether Markdown-only rules are sufficient.
- Identify controls that rely on AI self-discipline.
- Recommend whether later skill, MCP, wrapper, policy guard, or tool-entry
  restriction design is needed.
- Create T-0018 review evidence artifacts.
- Update `.ai` governance records for T-0018 review closeout.
- Run `validate_state.py`, `close_session.py`, and `audit_handoff.py`.

## Forbidden Actions

- Approve this gate without explicit user approval.
- Treat this pending gate as approval.
- Perform the T-0018 review before explicit user approval.
- Repair T-0017 artifacts without a later separate repair gate.
- Enter, create, or modify a real business project.
- Write business code.
- Implement, build, deploy, release, or roll back.
- Modify `AGENTS.md`.
- Install or enable skill, MCP, external agent runtime, automation, protocol
  service, policy guard, wrapper, or tool behavior.
- Change global or project runtime behavior.
- Change databases, permissions, secrets, payment systems, production data, or
  migrations.
- Treat reviewer PASS, validator success, tests, AI recommendation, or
  subagent conclusions as user approval.

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

## Evidence Required If Approved

- `.ai/evidence/T-0018/commands.md`
- `.ai/evidence/T-0018/startup-validation.v0.1.md`
- `.ai/evidence/T-0018/gate-request.G-T-0018-REAL-PROJECT-DELIVERY-ARCHITECTURE-GOVERNANCE-REVIEW.v0.1.md`
- `.ai/evidence/T-0018/user-decision-packet.real-project-delivery-architecture-governance-review.v0.1.md`
- `.ai/evidence/T-0018/review-scope.v0.1.md`
- `.ai/evidence/T-0018/package-coverage-review.v0.1.md`
- `.ai/evidence/T-0018/lifecycle-and-gate-review.v0.1.md`
- `.ai/evidence/T-0018/real-project-boundary-review.v0.1.md`
- `.ai/evidence/T-0018/architecture-and-design-depth-review.v0.1.md`
- `.ai/evidence/T-0018/enforcement-gap-review.v0.1.md`
- `.ai/evidence/T-0018/role-review-findings.v0.1.md`
- `.ai/evidence/T-0018/residual-risk-register.v0.1.md`
- `.ai/evidence/T-0018/review-summary.v0.1.md`
- `.ai/evidence/T-0018/next-gate-recommendation.v0.1.md`

## Validation Required

- `validate_state.py` must pass before this gate is recorded.
- `validate_state.py` must report the pending gate blocker after this gate is
  recorded.
- After explicit user decision, `validate_state.py` must be rerun.

## Exit Criteria

- User explicitly approves, rejects, or requests repair of this gate.
- No review work, real-project entry, implementation, installation,
  `AGENTS.md` change, runtime/tool enablement, deployment, rollback, database,
  permission, secret, payment, production-data, or migration action occurs
  while this gate is pending.
