# Gate Request: G-T-0017-REAL-PROJECT-DELIVERY-ARCHITECTURE-GOVERNANCE-DESIGN

Status: pending

Requested at: 2026-07-08T17:43:23+08:00

## Decision Needed

Approve or reject a design-only T-0017 task:

```text
G-T-0017-REAL-PROJECT-DELIVERY-ARCHITECTURE-GOVERNANCE-DESIGN
```

## Scope If Approved

- Read relevant prior method evidence from T-0001, T-0002, T-0006, T-0008,
  T-0010, T-0011, and T-0016.
- Produce candidate specifications for real software project delivery and
  architecture governance.
- Define the route from user idea to product discovery, domain model, PRD,
  architecture baseline, detailed design, implementation readiness, review,
  handoff, and iteration.
- Define gate boundaries for real-project entry, architecture baseline
  approval, implementation readiness, build, deployment, rollback,
  runtime/tool enablement, and high-risk actions.
- Define required artifacts, evidence, traceability, and acceptance standards.
- Use subagents only for bounded read-only review or audit; their conclusions
  are evidence only.
- Update only T-0017 governance records and evidence.

## Forbidden Scope

- Do not enter, create, or modify a real business project.
- Do not write business code.
- Do not implement, build, deploy, release, or roll back.
- Do not modify AGENTS.md.
- Do not install or enable skill, MCP, external agent runtime, automation,
  protocol service, or tool behavior.
- Do not change global or project runtime behavior.
- Do not change databases, permissions, secrets, payment systems, production
  data, or migrations.
- Do not treat validator success, reviewer PASS, tests, AI recommendation, or
  subagent conclusions as user approval.

## Expected Artifacts If Approved

- `real-project-entry-protocol.candidate.v0.1.md`
- `product-discovery-protocol.candidate.v0.1.md`
- `domain-model-and-prd-protocol.candidate.v0.1.md`
- `architecture-baseline-template.candidate.v0.1.md`
- `detailed-design-package-template.candidate.v0.1.md`
- `implementation-readiness-gate.candidate.v0.1.md`
- `review-and-quality-gates.candidate.v0.1.md`
- `real-project-boundary-and-risk-rules.candidate.v0.1.md`
- `traceability-and-evidence-schema.candidate.v0.1.md`
- `next-gate-recommendation.v0.1.md`

## Validation Plan

- Run `validate_state.py` after registering this pending gate and expect a
  pending-gate blocker.
- After explicit user approval or rejection, update the gate record and rerun
  `validate_state.py`.
- At closeout, run `close_session.py` and `audit_handoff.py`.
