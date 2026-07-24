# Commands - T-0022

## Startup Validation

Read startup and governance files:

```powershell
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\skills\project-governor\SKILL.md'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\state.yaml'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\HANDOFF.md'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\tasks\T-0021.md'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\gates.yaml'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\task_graph.yaml'
```

Startup validation command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Startup validation result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0021
[ok] state is usable
```

## Registration Actions

- Created `.ai/tasks/T-0022.md`.
- Created `.ai/evidence/T-0022/`.
- Created `.ai/evidence/T-0022/startup-validation.v0.1.md`.
- Created `.ai/evidence/T-0022/gate-request.G-T-0022-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-IMPLEMENTATION-PLANNING.v0.1.md`.
- Created `.ai/evidence/T-0022/user-decision-packet.real-project-governance-enforcement-architecture-implementation-planning.v0.1.md`.
- Recorded
  `G-T-0022-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-IMPLEMENTATION-PLANNING`
  as `pending`.
- Updated `.ai/state.yaml`, `.ai/task_graph.yaml`, `.ai/gates.yaml`,
  `.ai/PROGRESS.md`, and `.ai/HANDOFF.md`.

## Post-Registration Validation

Validation command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Validation result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0022
[error] Pending gate(s) require user decision before continuing: G-T-0022-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-IMPLEMENTATION-PLANNING
```

Observed exit code: 1.

This is the expected blocker for the pending T-0022 gate.

## User Approval

User approval text:

```text
批准 G-T-0022-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-IMPLEMENTATION-PLANNING
```

Approval record created:

```text
.ai/evidence/T-0022/real-project-governance-enforcement-architecture-implementation-planning.approval.record.v0.1.md
```

Updated gate:

```text
G-T-0022-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-IMPLEMENTATION-PLANNING -> approved
```

## Planning Evidence

Created planning evidence:

- `.ai/evidence/T-0022/implementation-planning-scope.v0.1.md`
- `.ai/evidence/T-0022/implementation-targets-and-boundaries.v0.1.md`
- `.ai/evidence/T-0022/checker-implementation-plan.candidate.v0.1.md`
- `.ai/evidence/T-0022/policy-guard-wrapper-implementation-plan.candidate.v0.1.md`
- `.ai/evidence/T-0022/validation-and-test-plan.candidate.v0.1.md`
- `.ai/evidence/T-0022/rollout-and-recovery-plan.candidate.v0.1.md`
- `.ai/evidence/T-0022/next-gate-recommendation.v0.1.md`

## Final Validation

Validation command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Validation result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0022
[ok] state is usable
```

Handoff audit command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Handoff audit result:

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0022
```

## Boundary

No implementation, installation, runtime/tool enablement, `AGENTS.md`
modification, real-project entry, build, deployment, release, rollback,
database, permission, secret, payment, production-data, or migration action
occurred.
