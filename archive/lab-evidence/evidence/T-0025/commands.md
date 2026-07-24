# Commands - T-0025

## Startup Validation

Read startup and governance files:

```powershell
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\skills\project-governor\SKILL.md'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\state.yaml'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\HANDOFF.md'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\tasks\T-0024.md'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\gates.yaml'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\task_graph.yaml'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\PROGRESS.md'
```

Startup validation command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Startup validation result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0024
[ok] state is usable
```

## Evidence And Contracts Read

Read the required T-0024 evidence files and the requested testing, review,
audit, traceability, security, data-protection, and delivery contracts for
gate-boundary setup only. No T-0025 review finding or verdict was produced.

## Registration Actions

- Created `.ai/evidence/T-0025/`.
- Created `.ai/tasks/T-0025.md`.
- Created `.ai/evidence/T-0025/startup-validation.v0.1.md`.
- Created `.ai/evidence/T-0025/gate-request.G-T-0025-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REVIEW.v0.1.md`.
- Created `.ai/evidence/T-0025/user-decision-packet.real-project-test-review-quality-assurance-governance-review.v0.1.md`.
- Recorded
  `G-T-0025-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REVIEW`
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
[project-governor] current_task_id: T-0025
[error] Pending gate(s) require user decision before continuing: G-T-0025-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REVIEW
```

Observed exit code: 1.

This is the expected blocker for the pending T-0025 review-only gate.

## User Approval

Approval record created:

```text
.ai/evidence/T-0025/real-project-test-review-quality-assurance-governance-review.approval.record.v0.1.md
```

Updated gate:

```text
G-T-0025-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REVIEW -> approved
```

Post-approval validation result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0025
[ok] state is usable
```

## Review Evidence Created

- `.ai/evidence/T-0025/review-scope-and-method.v0.1.md`
- `.ai/evidence/T-0025/review-findings.v0.1.md`
- `.ai/evidence/T-0025/quality-governance-review-report.v0.1.md`
- `.ai/evidence/T-0025/review-verdict.v0.1.md`
- `.ai/evidence/T-0025/next-gate-recommendation.v0.1.md`

## Review Result

```text
REPAIR_REQUIRED
```

Finding counts:

```text
critical: 0
major: 2
minor: 2
suggestion: 0
```

## Final Validation

Validation command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Observed validation result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0025
[ok] state is usable
```

## Handoff Audit

Audit command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Observed audit result:

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0025
```

## Boundary

No T-0025 review body, baseline approval, implementation, installation,
runtime/tool enablement, `AGENTS.md` modification, real-project entry,
business code, build, deployment, release, rollback, database, permission,
secret, payment, production-data, or migration action occurred during gate
registration.
