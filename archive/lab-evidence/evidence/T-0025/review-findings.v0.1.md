# T-0025 Review Findings v0.1

## Finding Summary

| Severity | Count |
|---|---:|
| Critical | 0 |
| Major | 2 |
| Minor | 2 |
| Suggestion | 0 |

## FIND-T0025-MAJOR-001: Report schema does not structurally close skipped, deferred, and not-applicable outcomes

- **Severity**: major
- **Dimension**: test/review/audit/verdict schema
- **Location**:
  `.ai/evidence/T-0024/test-review-report-and-quality-verdict-schema.candidate.v0.1.md:23`
- **Description**: The test report schema counts `passed`, `failed`,
  `skipped`, and `not_run`, but it does not structurally capture `deferred` or
  `not_applicable` outcomes at execution summary level. The same artifact later
  says reports must separate failed, skipped, not-run, deferred, and
  not-applicable outcomes at line 101. This mismatch leaves a path where
  deferred or N/A scenarios are only represented indirectly in the
  traceability matrix, making the final delivery verdict easier to overclaim.
- **Evidence**:
  - T-0024 schema line 23 defines execution summary without `deferred` or
    `not_applicable`.
  - T-0024 report quality rule line 101 requires those states to be separated.
  - `test-execution.md:43` requires skipped/todo tests to have explicit reason
    and recovery plan.
  - `test-report-output-spec.md:52` requires uncovered scenarios with reason
    and risk assessment.
  - `quality-release-gate-and-defect-severity-rules.candidate.v0.1.md:48`
    treats pass claims with skipped or untested P0/P1 scenarios as a hard stop.
- **Impact**: A real project could claim `PASS_FOR_ACCEPTANCE` while a P0/P1
  scenario is deferred or treated as N/A without a first-class owner, reason,
  risk, expiry, and user decision.
- **Suggested Repair**: Add explicit schema fields for `deferred`,
  `not_applicable`, `skipped_items`, `deferred_items`, `reason`, `owner`,
  `recovery_plan`, `expires_or_revisit_at`, `impacted_scenarios`,
  `required_user_decision`, and verdict-blocking semantics.

## FIND-T0025-MAJOR-002: Severity taxonomies are not mapped across review reports and final quality verdicts

- **Severity**: major
- **Dimension**: defect severity and quality verdict aggregation
- **Location**:
  `.ai/evidence/T-0024/test-review-report-and-quality-verdict-schema.candidate.v0.1.md:48`
- **Description**: The review report schema uses
  `critical | major | minor | suggestion`, while the final quality verdict and
  release rules use `p0 | p1 | p2 | p3`. T-0024 does not define a lossless
  mapping between these two severity systems. That weakens aggregation from
  review findings into release-blocking quality verdicts.
- **Evidence**:
  - T-0024 review report schema line 48 defines
    `critical | major | minor | suggestion`.
  - T-0024 final quality verdict schema begins at line 73 and aggregates open
    findings as `p0`, `p1`, `p2`, and `p3`.
  - T-0024 quality release rules lines 13-16 define P0-P3 delivery effects.
  - `agent-review-report-spec.md:53` uses critical/major/minor/suggestion for
    review reports, while `test-report-output-spec.md:79` uses P0/P1/P2 style
    defect records.
- **Impact**: A critical review finding could fail to become an open P0/P1
  quality blocker, or a P1 delivery defect could be reported as a non-blocking
  review finding.
- **Suggested Repair**: Define a severity normalization rule, for example
  `critical -> P0/P1 by impact`, `major -> P1/P2 by scenario priority`,
  `minor -> P3/P2 by delivery impact`, and `suggestion -> P3/non-blocking`.
  Require every finding to carry both `review_severity` and
  `delivery_severity` or adopt a single canonical severity taxonomy.

## FIND-T0025-MINOR-001: Tier 0 and Tier 1 adaptation lack concrete minimum artifact profiles

- **Severity**: minor
- **Dimension**: real-project adaptation boundaries
- **Location**:
  `.ai/evidence/T-0024/real-project-adaptation-boundaries.candidate.v0.1.md:22`
- **Description**: T-0024 defines Tier 0 and Tier 1 lightweight paths, but it
  does not specify the minimum artifact set or exit criteria for those paths.
  The risk tiering is directionally sound, but the low-risk paths could drift
  into either over-governance or under-evidenced delivery.
- **Evidence**:
  - Tier 0 says lightweight self-check may be enough if project rules allow it.
  - Tier 1 requires scenario plan and focused tests.
  - No minimum artifact profile is specified for those lightweight tiers.
- **Impact**: Real-project use may be inconsistent for trivial or low-risk
  changes.
- **Suggested Repair**: Add a tier-to-artifact matrix, including required
  evidence, optional evidence, reviewer requirement, and promotion triggers
  from Tier 0/1 into Tier 2/3.

## FIND-T0025-MINOR-002: T-0024 next-gate recommendation uses a stale gate ID variant

- **Severity**: minor
- **Dimension**: later gate order and governance consistency
- **Location**:
  `.ai/evidence/T-0024/next-gate-recommendation.v0.1.md:16`
- **Description**: The T-0024 recommendation names
  `G-T-0025-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-DESIGN-REVIEW`,
  while the actual approved T-0025 gate is
  `G-T-0025-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REVIEW`.
- **Evidence**:
  - T-0024 next-gate recommendation line 16 contains the `DESIGN-REVIEW`
    variant.
  - T-0025 gate registry records the user-approved non-`DESIGN` variant.
- **Impact**: Low. The current `.ai/gates.yaml` entry is the governing truth,
  but the stale recommendation may confuse future handoff or repair work.
- **Suggested Repair**: In a later repair task, normalize the T-0024
  next-gate recommendation or add a note that the user-selected T-0025 gate ID
  supersedes the candidate recommendation.
