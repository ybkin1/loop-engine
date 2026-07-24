# Test Review Report And Quality Verdict Schema Candidate v0.1

## Purpose

Define the minimum report formats needed to support code quality, project
consistency, and delivery quality decisions.

## Test Report Minimum Schema

```yaml
test_report:
  task_id: <task-id>
  generated_at: <ISO8601>
  scope:
    requirements: []
    scenarios: []
    code_surfaces: []
  environment:
    os: <value>
    runtime_versions: []
    database: <value-or-na>
    external_dependencies: []
  execution_summary:
    passed: 0
    failed: 0
    skipped: 0
    not_run: 0
    deferred: 0
    not_applicable: 0
  skipped_items: []
  not_run_items: []
  deferred_items: []
  not_applicable_items: []
  coverage:
    line: null
    branch: null
    function: null
    statement: null
  defects: []
  uncovered_scenarios: []
  raw_evidence_refs: []
```

## Review Report Minimum Schema

```yaml
review_report:
  review_id: <id>
  reviewer_role: scenario | code | security | data | delivery
  artifact_refs: []
  dimensions_checked: []
  findings:
    - finding_id: F-001
      review_severity: critical | major | minor | suggestion
      delivery_severity: p0 | p1 | p2 | p3 | non_blocking
      dimension: <dimension>
      location: <path-or-na>
      description: <issue>
      evidence_ref: <path>
      business_impact: <impact-or-na>
      affected_scenarios: []
      blocking_effect: block_acceptance | block_release | accepted_risk_required | non_blocking
      rationale: <why-this-severity-and-effect>
      suggested_fix: <repair>
  verdict: passed | request_changes | blocked | contract_not_closed
  zero_finding_checks_ruled_out: []
```

## Audit Report Minimum Schema

```yaml
audit_report:
  audit_id: <id>
  mode: plan_audit | execution_audit | falsification | final_quality
  audited_refs: []
  outcome_summary:
    passed: 0
    failed: 0
    skipped: 0
    not_run: 0
    deferred: 0
    not_applicable: 0
  skipped_items: []
  not_run_items: []
  deferred_items: []
  not_applicable_items: []
  checklist:
    - item: <check>
      result: pass | fail | na
      evidence_ref: <path>
  gaps: []
  verdict: audited | mechanical_gap | insufficient_evidence | failed
```

## Final Quality Verdict Schema

```yaml
quality_verdict:
  task_id: <task-id>
  business_goal_ref: <ref>
  requirements_total: 0
  scenarios_total: 0
  scenarios_passed: 0
  scenario_outcomes:
    passed: 0
    failed: 0
    skipped: 0
    not_run: 0
    deferred: 0
    not_applicable: 0
  non_pass_items:
    skipped_items: []
    not_run_items: []
    deferred_items: []
    not_applicable_items: []
  open_findings:
    p0: 0
    p1: 0
    p2: 0
    p3: 0
    non_blocking: 0
  blocking_summary:
    p0_or_p1_non_pass_items: 0
    accepted_risk_items_requiring_user_decision: 0
    pass_for_acceptance_blocked: false
  evidence_refs:
    test_report: <path>
    review_report: <path>
    audit_report: <path>
    traceability_matrix: <path>
  verdict: PASS_FOR_ACCEPTANCE | PASS_WITH_ACCEPTED_RISK | REPAIR_REQUIRED | BLOCKED
  release_recommendation: not_requested | later_gate_required | do_not_release
  residual_risks: []
  user_decisions_required: []
```

## Non-Pass Outcome Item Schema

`skipped_items`, `not_run_items`, `deferred_items`, and
`not_applicable_items` must use the same structured item shape in test reports,
audit reports, and final quality verdicts:

```yaml
non_pass_outcome_item:
  id: <stable-id>
  related_requirement_id: <requirement-id-or-na>
  related_scenario_id: <scenario-id-or-na>
  outcome_type: skipped | not_run | deferred | not_applicable
  reason: <why-this-is-not-passed>
  owner: <person-role-or-team>
  risk_level: p0 | p1 | p2 | p3 | non_blocking
  impacted_scenarios: []
  recovery_plan: <repair-or-validation-plan>
  expires_or_revisit_at: <date-or-condition>
  required_user_decision: none | accept_residual_risk | approve_scope_exclusion | approve_later_gate
  verdict_blocking_effect: blocks_pass_for_acceptance | blocks_release | residual_risk_review_required | non_blocking
  evidence_refs: []
```

Rules:

- A P0 or P1 scenario that is `skipped`, `not_run`, `deferred`, or
  `not_applicable` blocks `PASS_FOR_ACCEPTANCE` by default.
- `not_applicable` is allowed only when the scenario is outside the approved
  scope, impossible in the current product context, superseded by an approved
  requirement change, or covered by equivalent evidence. The item must cite
  evidence and the approval or confirmation boundary.
- `deferred` is not a pass. It must be classified as residual risk or blocker,
  and it must name an owner, revisit condition, and required user decision.
- `skipped` and `not_run` must explain the gap, impacted scenarios, and
  recovery plan before any delivery-quality verdict can claim completeness.

## Severity Normalization Fields

Review reports must not rely on review severity alone for delivery decisions.
Each finding must carry both `review_severity` and `delivery_severity`.

Minimum mapping rules:

- `critical` maps to `p0` or `p1`, depending on whether it causes core
  business unavailability, data/security/payment/permission/production risk,
  inability to deliver, or irreversible harm.
- `major` maps to `p1` or `p2`, depending on whether it blocks a key scenario,
  acceptance, integration, or release.
- `minor` maps to `p2` or `p3`, depending on whether it affects usability,
  consistency, maintainability, or local experience.
- `suggestion` maps to `p3` or `non_blocking`, but the finding must explain
  why it does not block acceptance or release.

Final quality verdicts must aggregate by `delivery_severity`, affected
scenario priority, and blocking effect. Open P0 or P1 findings block
`PASS_FOR_ACCEPTANCE` unless the user explicitly accepts residual risk through
an approved decision or a later explicit gate.

## Report Quality Rules

- Reports must cite evidence, not just say tests passed.
- Reports must separate failed, skipped, not-run, deferred, and not-applicable.
- Reports must list uncovered scenarios and explain risk.
- Reports must preserve user gate authority: report verdicts are evidence only.
- Reports must not treat deferred or not-applicable outcomes as passed
  scenarios.
- Reports must show whether every P0/P1 skipped, not-run, deferred, or
  not-applicable item blocks `PASS_FOR_ACCEPTANCE`.
- Reports must preserve the lossless mapping from review severity to delivery
  severity before making any quality verdict.
