# Business Quality Role Model v0.1

## Purpose

Define the role perspectives that a quality governance loop must preserve when
turning a business goal into test review evidence and a delivery verdict.

## Project Manager Perspective

Responsibilities:

- Protect the business goal, user value, scope, timeline, and acceptance path.
- Ensure every test and review artifact ties back to a user-visible scenario or
  delivery risk.
- Decide which risks require explicit user tradeoff rather than silent agent
  judgment.

Required evidence:

- Business goal and unacceptable failure list.
- Scope and non-goal boundary.
- Acceptance criteria and user decision points.
- Risk register with business impact.

## Test Manager Perspective

Responsibilities:

- Produce or audit the test strategy before coding.
- Ensure coverage across unit, integration, e2e, contract, security, and
  operational test layers according to project risk.
- Ensure data, environment, and reporting plans are executable.

Required evidence:

- Test review plan and plan audit.
- Scenario-to-test matrix.
- Test data and environment plan.
- Test execution report with coverage and skipped/uncovered scenarios.

## Development Manager Perspective

Responsibilities:

- Ensure implementation boundaries, code ownership, and dependency risks are
  reviewable.
- Ensure changed code can be mapped to requirements, scenarios, and tests.
- Ensure regressions are selected by dependency and scenario impact, not by
  guesswork.

Required evidence:

- Code surface map or changed-path manifest.
- Requirement/scenario/code/test trace matrix.
- Static checks, build checks, and defect remediation evidence where applicable.

## Delivery Manager Perspective

Responsibilities:

- Decide readiness for acceptance, release planning, or later deployment gate.
- Ensure residual risk, rollback implications, environment parity, and release
  prerequisites are visible.
- Keep delivery/release approval separate from test/review evidence.

Required evidence:

- Final quality verdict.
- Open findings and accepted residual risks.
- Release precondition checklist.
- Later gate recommendations for implementation, runtime/tool enablement,
  real-project entry, delivery/release, deployment, rollback, and high-risk
  actions.

## Role Separation Rule

The author may prepare artifacts, but Standard/Complex quality conclusions must
be independently reviewed. Subagent or sidecar review is evidence only and does
not approve gates or expand scope.
