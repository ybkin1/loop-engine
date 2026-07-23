# Test Review Plan Generation Protocol Candidate v0.1

## Purpose

Generate a delivery-grade test review plan from actual business/project
context before coding or code-complete review begins.

## Required Inputs

- Business goal, target users, success criteria, unacceptable failures.
- Requirement list or PRD, even if it is distilled from conversation.
- Project type: frontend, backend, full-stack, mobile, data, integration,
  automation, infra, migration, or mixed.
- Risk classification: user impact, data sensitivity, security surface,
  operational criticality, integration complexity, release urgency.
- Architecture and changed-surface summary if available.
- Known constraints: environment, dependencies, test tooling, data limits.

## Generation Steps

1. Normalize the business goal into requirements and acceptance criteria.
2. Build a minimum scenario catalog: happy path, error path, edge case,
   security case when applicable, operational/lifecycle case when applicable.
3. Assign risk priority by impact and probability.
4. Choose test strategy by scenario risk and project type.
5. Define test data strategy: fixture, seed, realistic anonymized data, empty
   state, or synthetic PII-safe data.
6. Define environment strategy: local, CI, staging, parity needs, external
   dependency handling.
7. Define review strategy: value, professional, contract gates; independent
   reviewer/subagent expectations; report and receipt requirements.
8. Define execution evidence: commands, coverage, manual evidence, screenshots,
   logs, audit report, and residual risk record.

## Required Plan Sections

- Scope and non-goals.
- Scenario catalog with IDs.
- Risk-priority table.
- Test layer strategy: unit, integration, e2e, contract, security, chaos or
  operational resilience where applicable.
- Test data and privacy controls.
- Environment and dependency plan.
- Regression selection rule.
- Review and audit plan.
- Reporting and final verdict schema.
- Later gate requirements.

## Project Type Strategy

- Frontend/UI: include interaction, responsiveness, accessibility, state,
  browser/device, visual regression, and user-flow tests.
- Backend/API: include contract, auth, permission, validation, persistence,
  concurrency, idempotency, observability, and error semantics tests.
- Full-stack: include API contract plus end-to-end user journeys and data
  consistency across UI/backend boundaries.
- Mobile/desktop: include lifecycle, offline/online, permissions, update, and
  platform-specific differences.
- Data/AI/reporting: include data quality, lineage, privacy, determinism,
  sampling risk, and falsification cases.
- Infra/deployment: include pipeline, artifact immutability, environment
  parity, smoke test, rollback plan, and deployment gate separation.

## Hard Fail Conditions

- No scenario catalog for Standard/Complex work.
- No risk-priority mapping.
- No security/privacy plan when auth, PII, secrets, external input, or external
  surfaces exist.
- No test data or environment strategy.
- No independent review/audit path.
- Plan claims coverage without describing evidence and report format.

## Output

The generated plan should be saved as a project/task artifact only after a
separate real-project-entry or implementation gate permits writing into a real
project. In this lab design, it remains a protocol definition.
