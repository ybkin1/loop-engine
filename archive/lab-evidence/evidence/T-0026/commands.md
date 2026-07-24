# Commands - T-0026

## Startup Validation

Read latest user request and project-governor instructions from:

```text
C:\Users\Administrator\.codex\attachments\0a3295d9-5813-4c04-a23f-f749b76e399f\pasted-text.txt
C:\Users\Administrator\.codex\skills\project-governor\SKILL.md
```

Read startup and governance files:

```powershell
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\state.yaml'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\HANDOFF.md'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\tasks\T-0025.md'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\gates.yaml'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\task_graph.yaml'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\PROGRESS.md'
```

Repository state checks:

```powershell
git status --short
git log -1 --oneline
```

Observed result:

```text
fatal: not a git repository (or any of the parent directories): .git
fatal: not a git repository (or any of the parent directories): .git
```

Startup validation command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Startup validation result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0025
[ok] state is usable
```

## Evidence Read For Gate Registration Boundary

Read required T-0025 review evidence:

- `.ai/evidence/T-0025/review-findings.v0.1.md`
- `.ai/evidence/T-0025/review-verdict.v0.1.md`
- `.ai/evidence/T-0025/quality-governance-review-report.v0.1.md`
- `.ai/evidence/T-0025/next-gate-recommendation.v0.1.md`

Read required T-0024 design evidence:

- `.ai/evidence/T-0024/test-review-report-and-quality-verdict-schema.candidate.v0.1.md`
- `.ai/evidence/T-0024/quality-release-gate-and-defect-severity-rules.candidate.v0.1.md`
- `.ai/evidence/T-0024/real-project-adaptation-boundaries.candidate.v0.1.md`
- `.ai/evidence/T-0024/next-gate-recommendation.v0.1.md`

These reads were used only to define the T-0026 gate request. No T-0026 repair
body was performed.

## Registration Actions

- Created `.ai/evidence/T-0026/`.
- Created `.ai/tasks/T-0026.md`.
- Created `.ai/evidence/T-0026/startup-validation.v0.1.md`.
- Created `.ai/evidence/T-0026/gate-request.G-T-0026-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REPAIR.v0.1.md`.
- Created `.ai/evidence/T-0026/user-decision-packet.real-project-test-review-quality-assurance-governance-repair.v0.1.md`.
- Recorded
  `G-T-0026-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REPAIR`
  as `pending`.
- Updated `.ai/state.yaml`, `.ai/task_graph.yaml`, `.ai/gates.yaml`,
  `.ai/PROGRESS.md`, and `.ai/HANDOFF.md`.

## Post-Registration Validation

Validation command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Observed validation result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0026
[error] Pending gate(s) require user decision before continuing: G-T-0026-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REPAIR
```

Observed exit code: 1.

This is the expected blocker for the pending T-0026 repair-only gate.

## User Approval

Approval record created:

```text
.ai/evidence/T-0026/real-project-test-review-quality-assurance-governance-repair.approval.record.v0.1.md
```

Updated gate:

```text
G-T-0026-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REPAIR -> approved
```

Approval text:

```text
批准 G-T-0026-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REPAIR
```

Post-approval validation result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0026
[ok] state is usable
```

## Repair Actions

Repaired the four approved T-0025 findings in the approved T-0024 evidence
targets:

- `.ai/evidence/T-0024/test-review-report-and-quality-verdict-schema.candidate.v0.1.md`
- `.ai/evidence/T-0024/quality-release-gate-and-defect-severity-rules.candidate.v0.1.md`
- `.ai/evidence/T-0024/real-project-adaptation-boundaries.candidate.v0.1.md`
- `.ai/evidence/T-0024/next-gate-recommendation.v0.1.md`

Created repair evidence:

```text
.ai/evidence/T-0026/repair-summary.v0.1.md
```

Read-only verification commands:

```powershell
rg -n "deferred|not_applicable|skipped_items|not_run_items|deferred_items|not_applicable_items|review_severity|delivery_severity|PASS_FOR_ACCEPTANCE" .ai/evidence/T-0024/test-review-report-and-quality-verdict-schema.candidate.v0.1.md .ai/evidence/T-0024/quality-release-gate-and-defect-severity-rules.candidate.v0.1.md
rg -n "Artifact Profile Matrix|Tier 0|Tier 1|Tier 2|Tier 3|Promotion Triggers|high-risk|separate explicit gate" .ai/evidence/T-0024/real-project-adaptation-boundaries.candidate.v0.1.md
rg -n "Supersession Note|DESIGN-REVIEW|G-T-0025-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REVIEW|actual executed" .ai/evidence/T-0024/next-gate-recommendation.v0.1.md
```

## Final Validation

Validation command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Observed validation result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0026
[ok] state is usable
```

Observed exit code: 0.

## Handoff Audit

Audit command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Observed audit result:

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0026
```

Observed exit code: 0.

## Boundary

No T-0026 repair body, baseline consideration, implementation, installation,
runtime/tool enablement, `AGENTS.md` modification, real-project entry,
business code, build, deployment, release, rollback, database, permission,
secret, payment, production-data, or migration action occurred during gate
registration.
