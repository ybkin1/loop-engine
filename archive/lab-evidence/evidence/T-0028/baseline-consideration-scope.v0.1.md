# T-0028 Baseline Consideration Scope v0.1

## Task

```text
T-0028: Real Project Test Review And Quality Assurance Governance Baseline Consideration
```

## Gate

```text
G-T-0028-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-BASELINE-CONSIDERATION
```

## Approval Boundary

The user explicitly approved the gate:

```text
批准 G-T-0028-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-BASELINE-CONSIDERATION
```

The same message required handoff/startup prompt to include:

```text
Next Action Contract: T-0027 hygiene cleanup + baseline consideration
```

## Approved Scope

Part 1: T-0027 evidence/handoff hygiene cleanup.

- Remove duplicate T-0027 `handoff-audit.v0.1.md` evidence references from
  `.ai/tasks/T-0027.md` and `.ai/HANDOFF.md`.
- Check obvious duplicate T-0027 evidence references.
- Check listed T-0027 evidence files exist.
- Check T-0027 task, state, task graph, and gate status consistency.
- Record cleanup evidence under `.ai/evidence/T-0028/`.

Part 2: baseline consideration.

- Read required T-0024, T-0025, T-0026, and T-0027 evidence.
- Decide whether repaired T-0024 design evidence can be recorded as a baseline
  reference/candidate for later implementation planning.
- Record whether the duplicate evidence/handoff issue reveals a later
  governance enhancement gap.

## Required Evidence Read

- `.ai/evidence/T-0024/test-review-quality-governance-scope.v0.1.md`
- `.ai/evidence/T-0024/business-quality-role-model.v0.1.md`
- `.ai/evidence/T-0024/test-review-plan-generation-protocol.candidate.v0.1.md`
- `.ai/evidence/T-0024/test-review-plan-audit-protocol.candidate.v0.1.md`
- `.ai/evidence/T-0024/independent-subagent-test-review-execution-protocol.candidate.v0.1.md`
- `.ai/evidence/T-0024/test-review-report-and-quality-verdict-schema.candidate.v0.1.md`
- `.ai/evidence/T-0024/quality-release-gate-and-defect-severity-rules.candidate.v0.1.md`
- `.ai/evidence/T-0024/traceability-and-evidence-chain.candidate.v0.1.md`
- `.ai/evidence/T-0024/real-project-adaptation-boundaries.candidate.v0.1.md`
- `.ai/evidence/T-0024/next-gate-recommendation.v0.1.md`
- `.ai/evidence/T-0025/review-findings.v0.1.md`
- `.ai/evidence/T-0025/review-verdict.v0.1.md`
- `.ai/evidence/T-0026/repair-summary.v0.1.md`
- `.ai/evidence/T-0027/review-rerun-findings.v0.1.md`
- `.ai/evidence/T-0027/review-rerun-verdict.v0.1.md`
- `.ai/evidence/T-0027/next-gate-recommendation.v0.1.md`

## Forbidden Scope

- No baseline approval.
- No implementation planning.
- No implementation, installation, runtime/tool enablement, or `AGENTS.md`
  modification.
- No real-project entry, business code, build, release, deployment, rollback,
  database, permission, secret, payment, production-data, or migration action.
- No checker, workflow, subagent protocol, runtime behavior, or tool behavior
  implementation.
- No changes to T-0025/T-0026/T-0027 conclusions or the T-0027 verdict.
