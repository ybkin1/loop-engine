# Quality Release Gate And Defect Severity Rules Candidate v0.1

## Purpose

Define delivery quality pass/fail rules and defect severity semantics. These
rules support later acceptance or release decisions but do not approve release,
deployment, or rollback.

## Severity Levels

| Severity | Meaning | Default gate effect |
|---|---|---|
| P0 | Safety, security, data loss, payment, production-data, auth bypass, or core business flow unusable | Block acceptance and release |
| P1 | Major user flow broken, severe regression, critical scenario untested, or required evidence missing | Block acceptance unless user explicitly accepts residual risk |
| P2 | Non-critical defect, incomplete edge case, degraded experience, or test gap with known workaround | May pass with repair plan if business accepts risk |
| P3 | Minor polish, wording, non-blocking documentation, or low-risk improvement | Does not block by default |

## Review Severity To Delivery Severity Mapping

Review findings may use `critical`, `major`, `minor`, and `suggestion`, but
final quality verdicts must use delivery severity and scenario priority. Every
finding must carry both taxonomies:

```yaml
finding:
  review_severity: critical | major | minor | suggestion
  delivery_severity: p0 | p1 | p2 | p3 | non_blocking
  business_impact: <impact-or-na>
  affected_scenarios: []
  blocking_effect: block_acceptance | block_release | accepted_risk_required | non_blocking
  rationale: <why-this-mapping-is-correct>
```

Minimum mapping rules:

| Review severity | Delivery severity | Mapping condition |
|---|---|---|
| critical | P0 | Core business flow unusable, data loss, security/auth/payment/permission/production-data risk, irreversible harm, or unsafe delivery |
| critical | P1 | Severe defect or evidence gap that blocks acceptance but is not P0 |
| major | P1 | Blocks key scenario, required acceptance, integration, release readiness, or required evidence |
| major | P2 | Material issue with workaround that does not block key acceptance or release readiness |
| minor | P2 | Affects usability, consistency, maintainability, or local experience enough to require planned repair |
| minor | P3 | Low-impact local issue that does not affect acceptance or release readiness |
| suggestion | P3 | Useful improvement with low delivery impact |
| suggestion | non_blocking | Advisory only; rationale must explain why it does not block |

Rules:

- Review severity alone cannot release or block a delivery verdict.
- Final verdicts must aggregate by `delivery_severity`, affected scenario
  priority, business impact, and blocking effect.
- A delivery P0 or open security/privacy/data/payment/permission/production
  P1 blocks acceptance and release by default.
- Any open P1 blocks `PASS_FOR_ACCEPTANCE` unless the user explicitly accepts
  residual risk through a recorded decision or a separate explicit gate.
- Accepted risk cannot be decided by AI. It must cite the user decision, owner,
  expiration or revisit condition, impacted scenarios, and mitigation.

## Quality Verdicts

- `PASS_FOR_ACCEPTANCE`: no open P0/P1, required scenarios covered, evidence is
  complete, no P0/P1 scenario is skipped, not-run, deferred, or N/A without an
  approved boundary, and residual risk is low.
- `PASS_WITH_ACCEPTED_RISK`: no open P0, P1/P2 residual risks are explicitly
  documented and require user acceptance before delivery use.
- `REPAIR_REQUIRED`: open P0/P1, missing scenario coverage, weak test evidence,
  failed audit, or inconsistent reports.
- `BLOCKED`: missing business context, missing environment, unsafe data
  condition, forbidden scope request, or repeated unresolved gate blocker.

## Release Readiness Conditions

Before a later delivery/release gate can be recommended, the evidence package
must show:

- all P0 scenarios tested or explicitly out of scope
- all P1 critical or required acceptance scenarios tested or covered by
  equivalent evidence
- no open P0 defects
- no open security/privacy P1 defects
- no P0/P1 skipped, not-run, deferred, or not-applicable item without explicit
  evidence and user approval or confirmation boundary
- no unapproved production data, secret, database, permission, payment, or
  migration risk
- test report, review report, audit report, and traceability matrix complete
- rollback, deployment, and release actions still behind separate explicit
  gates

## Hard Stop Conditions

- P0 security, data loss, auth bypass, payment, migration, secret, permission,
  or production-data issue.
- Tests cannot run and no equivalent manual evidence exists.
- The report claims pass while skipped or untested P0/P1 scenarios exist.
- Deferred P0/P1 scenarios are treated as pass or omitted from residual risk.
- N/A is used for P0/P1 scenarios without evidence and approval or confirmation
  boundary.
- Real production data is used without explicit gate and data-protection
  controls.
- Reviewer PASS is treated as user approval.

## Residual Risk Handling

Residual risk must include owner, severity, impacted scenario, mitigation,
expiration date or revisit condition, and required user decision. Risk cannot
be accepted by the agent alone.

Deferred, skipped, not-run, and not-applicable items enter residual-risk
handling unless they are blockers. They must not be silently excluded from the
quality verdict. If the item affects a P0/P1 scenario, the default outcome is
`REPAIR_REQUIRED` or `BLOCKED` until a user decision or separate gate records
the accepted boundary.

## Gate Boundary

Quality evidence may recommend a later acceptance or release gate. It never
executes release, deployment, rollback, production data access, database
changes, permission changes, secret handling, payment actions, or migrations.
