# Review And Quality Gates Candidate v0.1

Status: candidate
Task: T-0017

## Purpose

Define review and quality gates for real software delivery so Codex cannot
self-certify by producing documents, passing tests, or receiving subagent
agreement.

## Gate Principles

- User value gate comes first.
- Professional gate checks engineering quality.
- Contract gate checks required rules and evidence.
- Reviewer PASS is evidence only.
- Validator success is evidence only.
- Tests are evidence only.
- Subagent conclusions are evidence only.
- User approval remains an explicit gate decision.

## Review Layers

### Layer 1: Value Gate

Checks whether the user-visible outcome matches approved intent and acceptance
criteria.

Evidence:

- product intent
- PRD or acceptance criteria
- scenario walkthrough
- user-facing verification notes

### Layer 2: Professional Gate

Checks whether the solution is technically sound.

Minimum dimensions:

- product and domain fit
- architecture and dependency direction
- API and data consistency when applicable
- UX states and accessibility when applicable
- security and privacy
- tests and regression risk
- observability and operations when applicable
- maintainability and handoff

### Layer 3: Contract Gate

Checks whether required project rules, gates, artifacts, and evidence are
present.

Contract gate must run last. It cannot repair missing value or engineering
quality by itself.

## Review Report Fields

```yaml
review_id:
reviewed_artifacts:
review_scope:
baseline:
findings:
  - id:
    severity: P0 | P1 | P2 | P3
    evidence:
    affected_ids:
    required_repair:
    gate_impact:
unchecked_items:
passed_checks:
residual_risks:
recommendation:
user_gate_needed:
```

## Severity Rules

- P0: unsafe, unauthorized, destructive, or fundamentally wrong; stop.
- P1: blocks baseline, implementation, or release until repaired.
- P2: important repair or explicit deferral required before promotion.
- P3: improvement note; can be logged for later.

## Zero-Finding Rule

If a review has no findings, it must still state:

- which artifacts were checked
- which failure hypotheses were considered
- which gates were in scope
- which items were not checked
- why no finding was recorded

## Repair Loop

When findings exist:

1. Create `FIND-*`.
2. Map each finding to affected artifact IDs.
3. Record repair plan.
4. Repair only within approved scope.
5. Rerun review.
6. Record residual risks or deferrals.

## Boundary

Review results cannot approve gates, expand scope, enter real projects, install
rules, enable tools, deploy, roll back, or touch high-risk resources.
