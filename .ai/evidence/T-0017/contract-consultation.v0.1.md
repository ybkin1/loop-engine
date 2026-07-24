# Contract Consultation v0.1

Status: evidence
Task: T-0017

## Purpose

Record the external contract families consulted because T-0017 designs
governance for architecture, security, data, deployment, testing, review, and
implementation readiness.

## Consulted Contracts

- `architecture-blueprint.md`
- `architecture-breakdown-spec.md`
- `prd-output-spec.md`
- `design-output-spec.md`
- `dev-plan-output-spec.md`
- `execution-traceability.md`
- `review-gates.md`
- `testing-standards.md`
- `security-governance.md`
- `data-protection.md`
- `data-management.md`
- `deployment-governance.md`
- `work-packet-governance.md`
- `scenario-traceability.md`
- `document-depth.md`
- `closeout.md`

## Applied Constraints

- Architecture nodes must exist before build work packets.
- PRD, architecture, design, and dev plan artifacts need testable quality gates.
- Intent, design, plan, code, tests, scenarios, and evidence need traceability.
- Review has value, professional, and contract layers; review PASS is evidence
  only.
- Security and privacy must be designed before implementation when external
  input, authentication, authorization, secrets, or sensitive data are involved.
- Database and migration work require separate high-risk gates.
- Deployment and rollback require separate gates and release evidence.
- Closeout requires verified state, evidence, and handoff.

## Boundary

Contract consultation shapes the candidate design. It does not activate these
contracts as new runtime behavior, install rules, enter a real project, or
authorize implementation.
