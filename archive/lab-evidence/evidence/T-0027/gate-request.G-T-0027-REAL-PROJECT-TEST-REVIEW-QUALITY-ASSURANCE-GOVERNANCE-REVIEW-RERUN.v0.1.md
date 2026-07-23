# Gate Request: G-T-0027-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REVIEW-RERUN

## Gate ID

```text
G-T-0027-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REVIEW-RERUN
```

## Gate Type

```text
real-project-test-review-quality-assurance-governance-review-rerun
```

## Status

```text
pending
```

## Purpose

Allow the user to decide whether Codex may perform an independent review-rerun
of the T-0026 repairs against the T-0025 findings and repaired T-0024 design
evidence package.

This gate exists only to decide whether the repaired T-0024 evidence can
become a candidate for later baseline consideration. It is not baseline
consideration and not baseline approval.

## Allowed Before Explicit User Decision

- Create `.ai/tasks/T-0027.md`.
- Create `.ai/evidence/T-0027/`.
- Create T-0027 startup validation evidence.
- Create this T-0027 gate request evidence.
- Create T-0027 user decision packet.
- Record this gate as `pending`.
- Update `.ai/state.yaml`, `.ai/task_graph.yaml`, `.ai/gates.yaml`,
  `.ai/PROGRESS.md`, and `.ai/HANDOFF.md`.
- Run `validate_state.py` after gate registration and expect a pending gate
  blocker for T-0027.
- Stop and ask the user to approve, reject, or request repair.

## Review-Rerun Scope After Explicit Approval Only

### FIND-T0025-MAJOR-001

Review whether the repair sufficiently closes skipped, not-run, deferred, and
not-applicable outcomes across the test report, audit report, and final quality
verdict.

Required checks:

- `skipped`, `not_run`, `deferred`, and `not_applicable` are first-class
  structured fields.
- `skipped_items`, `not_run_items`, `deferred_items`, and
  `not_applicable_items` include `reason`, `owner`, `risk_level`,
  `impacted_scenarios`, `recovery_plan`, `expires_or_revisit_at`,
  `required_user_decision`, and `verdict_blocking_effect`.
- P0/P1 skipped, not-run, deferred, or N/A scenarios block
  `PASS_FOR_ACCEPTANCE` by default.
- N/A has explicit allowed boundaries, evidence requirements, and user
  confirmation or approval boundary.
- Deferred is explicitly not pass.

### FIND-T0025-MAJOR-002

Review whether severity semantics are repaired sufficiently for delivery-grade
quality verdicts.

Required checks:

- `review_severity` and `delivery_severity` are required finding fields.
- `critical | major | minor | suggestion` can map without loss to
  `P0 | P1 | P2 | P3 | non_blocking`.
- Final verdict aggregation uses `delivery_severity`, scenario priority,
  business impact, and `blocking_effect`.
- Open P0/P1 findings block by default.
- Accepted risk requires a user decision or separate gate and cannot be
  accepted by AI.

### FIND-T0025-MINOR-001

Review whether real-project adaptation boundaries now include concrete
artifact profiles.

Required checks:

- Tier 0 / Tier 1 / Tier 2 / Tier 3 artifact profile matrix exists.
- Each tier defines applicability, required evidence, optional evidence,
  independent review requirement, subagent review requirement, minimum tests,
  minimum traceability, exit criteria, and promotion triggers.
- Tier 0/1 cannot bypass high-risk gates.
- Security, permission, database, payment, production data, migration,
  deployment, rollback, secret, regulated, or irreversible-risk content must
  promote or require a separate explicit gate.

### FIND-T0025-MINOR-002

Review whether the stale T-0024 candidate gate ID was corrected or annotated.

Required checks:

- The old candidate gate ID is marked as historical candidate:
  `G-T-0025-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-DESIGN-REVIEW`.
- The actual completed T-0025 gate ID is clear:
  `G-T-0025-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REVIEW`.
- Later handoff, review rerun, and baseline-consideration references use the
  actual executed gate ID.

### Additional Consistency Review

- Check whether T-0026 introduced conflicts, over-governance, unenforceable
  clauses, or gate-boundary confusion.
- Check whether repaired T-0024 remains design evidence, not implementation,
  runtime/tool enablement, or real-project approval.
- Check whether the evidence still separates review pass, baseline
  consideration, baseline approval, implementation, installation,
  runtime/tool enablement, real-project entry, delivery/release, and high-risk
  actions.

## Required Inputs After Approval

T-0026 repair evidence:

- `.ai/evidence/T-0026/repair-summary.v0.1.md`
- `.ai/evidence/T-0026/final-validation.v0.1.md`
- `.ai/evidence/T-0026/handoff-audit.v0.1.md`

T-0025 review evidence:

- `.ai/evidence/T-0025/review-findings.v0.1.md`
- `.ai/evidence/T-0025/review-verdict.v0.1.md`
- `.ai/evidence/T-0025/quality-governance-review-report.v0.1.md`
- `.ai/evidence/T-0025/next-gate-recommendation.v0.1.md`

T-0024 repaired design evidence:

- `.ai/evidence/T-0024/test-review-report-and-quality-verdict-schema.candidate.v0.1.md`
- `.ai/evidence/T-0024/quality-release-gate-and-defect-severity-rules.candidate.v0.1.md`
- `.ai/evidence/T-0024/real-project-adaptation-boundaries.candidate.v0.1.md`
- `.ai/evidence/T-0024/next-gate-recommendation.v0.1.md`

If needed during the approved review-rerun, additional T-0024 design evidence
may be read only. This must not expand into implementation, installation,
real-project entry, or baseline decision.

## Possible Verdicts After Approval

- `PASS_FOR_BASELINE_CONSIDERATION`
- `REPAIR_REQUIRED`
- `BLOCKED`

## Risks

- The review-rerun could be mistaken for baseline consideration unless the
  boundary is explicit.
- A successful review-rerun verdict could be mistaken for baseline approval.
- Reading repaired T-0024 evidence could accidentally drift into design repair
  or implementation unless the body remains review-only.
- Accepted risk, N/A boundaries, or P0/P1 exceptions could be treated as AI
  decisions unless the gate preserves user authority.

## Forbidden Scope

- Do not treat this prompt as approval.
- Do not start the T-0027 review-rerun body while this gate is pending.
- Do not approve this gate without explicit user approval.
- Do not treat T-0026 repair completion, T-0025 review, T-0024 design
  evidence, validator success, AI recommendation, handoff, or prompt text as
  user approval.
- Do not perform baseline consideration or baseline approval.
- Do not implement checker, workflow, subagent protocol, runtime behavior, or
  tool behavior.
- Do not install or enable MCP, skill, policy guard, wrapper, automation,
  protocol, hook, plugin, or tool-entry behavior.
- Do not modify `AGENTS.md`.
- Do not enter, create, or modify a real business project.
- Do not write business code.
- Do not build, deploy, release, or roll back.
- Do not change databases, permissions, secrets, payment systems, production
  data, or migrations.

## Required User Decision

The user must explicitly approve, reject, or request repair.

Exact approval phrase:

```text
批准 G-T-0027-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REVIEW-RERUN
```
