# Commands - T-0024

## Startup Validation

Read startup and governance files:

```powershell
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\skills\project-governor\SKILL.md'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\state.yaml'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\HANDOFF.md'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\tasks\T-0023.md'
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
[project-governor] current_task_id: T-0023
[ok] state is usable
```

Git status/log check:

```text
fatal: not a git repository (or any of the parent directories): .git
```

## Registration Actions

- Created `.ai/evidence/T-0024/`.
- Created `.ai/tasks/T-0024.md`.
- Created `.ai/evidence/T-0024/startup-validation.v0.1.md`.
- Created `.ai/evidence/T-0024/gate-request.G-T-0024-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-DESIGN.v0.1.md`.
- Created `.ai/evidence/T-0024/user-decision-packet.real-project-test-review-quality-assurance-governance-design.v0.1.md`.
- Recorded
  `G-T-0024-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-DESIGN`
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
[project-governor] current_task_id: T-0024
[error] Pending gate(s) require user decision before continuing: G-T-0024-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-DESIGN
```

Observed exit code: 1.

This is the expected blocker for the pending T-0024 design gate.

## User Approval

Approval record created:

```text
.ai/evidence/T-0024/real-project-test-review-quality-assurance-governance-design.approval.record.v0.1.md
```

Updated gate:

```text
G-T-0024-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-DESIGN -> approved
```

Post-approval validation result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0024
[ok] state is usable
```

## Contracts Consulted During Approved Design

- `C:\Users\Administrator\.claude\contracts\testing-standards.md`
- `C:\Users\Administrator\.claude\contracts\test-plan-design.md`
- `C:\Users\Administrator\.claude\contracts\test-execution.md`
- `C:\Users\Administrator\.claude\contracts\test-report-output-spec.md`
- `C:\Users\Administrator\.claude\contracts\review-gates.md`
- `C:\Users\Administrator\.claude\contracts\review-process.md`
- `C:\Users\Administrator\.claude\contracts\review-consistency-checklist.md`
- `C:\Users\Administrator\.claude\contracts\agent-review-report-spec.md`
- `C:\Users\Administrator\.claude\contracts\falsification-qa.md`
- `C:\Users\Administrator\.claude\contracts\verification-checker.md`
- `C:\Users\Administrator\.claude\contracts\scenario-traceability.md`
- `C:\Users\Administrator\.claude\contracts\security-governance.md`
- `C:\Users\Administrator\.claude\contracts\deployment-governance.md`
- `C:\Users\Administrator\.claude\contracts\data-protection.md`

## Design Evidence Created

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

## Final Validation

Validation command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Observed validation result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0024
[ok] state is usable
```

Evidence file count under `.ai/evidence/T-0024/`: 15.

## Boundary

T-0024 design evidence was created only after explicit user approval. No
implementation, installation, runtime/tool enablement, `AGENTS.md`
modification, real-project entry, business code, build, deployment, release,
rollback, database, permission, secret, payment, production-data, or migration
action occurred.
