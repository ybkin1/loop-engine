# Gate Request: G-T-0026-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REPAIR

## Gate ID

```text
G-T-0026-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REPAIR
```

## Gate Type

```text
real-project-test-review-quality-assurance-governance-repair
```

## Status

```text
pending
```

## Purpose

Allow the user to decide whether Codex may perform a repair-only update to the
T-0024 design evidence package for the four findings from T-0025.

This gate exists only to close the T-0025 review findings so T-0024 can later
be reviewed again or considered by a separate baseline-consideration gate.

## Allowed Before Explicit User Decision

- Create `.ai/tasks/T-0026.md`.
- Create `.ai/evidence/T-0026/`.
- Create T-0026 startup validation evidence.
- Create this T-0026 gate request evidence.
- Create T-0026 user decision packet.
- Record this gate as `pending`.
- Update `.ai/state.yaml`, `.ai/task_graph.yaml`, `.ai/gates.yaml`,
  `.ai/PROGRESS.md`, and `.ai/HANDOFF.md`.
- Run `validate_state.py` after gate registration and expect a pending gate
  blocker for T-0026.
- Stop and ask the user to approve, reject, or request repair.

## Repair Scope After Explicit Approval Only

### FIND-T0025-MAJOR-001

Repair the report, audit, and final quality verdict schemas so skipped,
not-run, deferred, and not-applicable outcomes are first-class and cannot hide
P0/P1 risk.

Required structure for non-pass items must include:

- `id`
- `related_requirement_id`
- `related_scenario_id`
- `outcome_type`
- `reason`
- `owner`
- `risk_level`
- `impacted_scenarios`
- `recovery_plan`
- `expires_or_revisit_at`
- `required_user_decision`
- `verdict_blocking_effect`

The repair must clarify P0/P1 blocking effects, valid N/A evidence and
approval boundaries, and the rule that deferred is not pass.

### FIND-T0025-MAJOR-002

Repair severity semantics by defining lossless mapping from review severity to
delivery severity. Each finding must carry:

- `review_severity`
- `delivery_severity`
- `business_impact`
- `affected_scenarios`
- `blocking_effect`
- `rationale`

The repair must preserve open P0/P1 default blocking behavior and require user
decision or a clear gate for accepted risk.

### FIND-T0025-MINOR-001

Repair real-project adaptation boundaries by adding Tier 0, Tier 1, Tier 2,
and Tier 3 artifact profiles. Each tier must define applicability, required
evidence, optional evidence, independent review requirement, subagent review
requirement, minimum testing, minimum traceability, exit criteria, and
promotion triggers.

Tier 0 and Tier 1 must not bypass high-risk gates. Security, permission,
database, payment, production-data, migration, deployment, rollback, secret,
or similar high-risk content must upgrade or require a separate explicit gate.

### FIND-T0025-MINOR-002

Repair the stale gate ID in T-0024 next-gate recommendation by correcting or
annotating:

```text
G-T-0025-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-DESIGN-REVIEW
```

The repair must state that the actual approved and completed T-0025 gate was:

```text
G-T-0025-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REVIEW
```

The stale gate ID must be treated as a historical candidate recommendation,
not the executed gate.

## Required Inputs After Approval

- `.ai/evidence/T-0025/review-findings.v0.1.md`
- `.ai/evidence/T-0025/review-verdict.v0.1.md`
- `.ai/evidence/T-0025/quality-governance-review-report.v0.1.md`
- `.ai/evidence/T-0025/next-gate-recommendation.v0.1.md`
- `.ai/evidence/T-0024/test-review-report-and-quality-verdict-schema.candidate.v0.1.md`
- `.ai/evidence/T-0024/quality-release-gate-and-defect-severity-rules.candidate.v0.1.md`
- `.ai/evidence/T-0024/real-project-adaptation-boundaries.candidate.v0.1.md`
- `.ai/evidence/T-0024/next-gate-recommendation.v0.1.md`

## Candidate Repair Targets After Approval

- `.ai/evidence/T-0024/test-review-report-and-quality-verdict-schema.candidate.v0.1.md`
- `.ai/evidence/T-0024/quality-release-gate-and-defect-severity-rules.candidate.v0.1.md`
- `.ai/evidence/T-0024/real-project-adaptation-boundaries.candidate.v0.1.md`
- `.ai/evidence/T-0024/next-gate-recommendation.v0.1.md`
- `.ai/evidence/T-0026/repair-summary.v0.1.md`

## Risks

- The repair could accidentally expand into baseline consideration if the gate
  boundary is not enforced.
- The repair could accidentally become implementation or runtime/tool behavior
  if schema wording is treated as executable enablement.
- The repair could overcorrect beyond the four T-0025 findings, which would
  require a separate gate.

## Forbidden Scope

- Do not treat this prompt as approval.
- Do not start the T-0026 repair body while this gate is pending.
- Do not approve this gate without explicit user approval.
- Do not treat T-0025 review verdict, T-0024 design evidence, validator
  success, AI recommendation, handoff, or prompt text as user approval.
- Do not expand repair scope beyond the four T-0025 findings.
- Do not perform baseline consideration.
- Do not modify `AGENTS.md`.
- Do not implement any checker, workflow, subagent protocol, runtime behavior,
  tool behavior, hook, plugin, automation, MCP, skill, policy guard, wrapper,
  protocol, or tool-entry behavior.
- Do not install or enable any MCP, skill, policy guard, wrapper, automation,
  protocol, hook, plugin, or tool-entry behavior.
- Do not enter, create, or modify a real business project.
- Do not write business code.
- Do not build, deploy, release, or roll back.
- Do not change databases, permissions, secrets, payment systems, production
  data, or migrations.

## Required User Decision

The user must explicitly approve, reject, or request repair.

Exact approval phrase:

```text
批准 G-T-0026-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REPAIR
```
