# Commands For T-0020

## Startup

```powershell
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\state.yaml'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\HANDOFF.md'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\tasks\T-0019.md'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\gates.yaml'
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\task_graph.yaml'
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0019
[ok] state is usable
```

## Task Creation

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\new_task.py' 'C:\Users\Administrator\.codex\loop-engine-lab' --title 'Real Project Governance Enforcement Architecture Review' --allow-parallel
```

Result:

```text
[ok] created T-0020: Real Project Governance Enforcement Architecture Review
[next] edit .ai/tasks/T-0020.md and record evidence under .ai/evidence/T-0020/
```

## Gate Registration

- Created `.ai/tasks/T-0020.md`.
- Created T-0020 startup validation evidence.
- Created the pending gate request.
- Created the user decision packet.
- Recorded the pending gate in `.ai/gates.yaml`.
- Updated `.ai/state.yaml`, `.ai/task_graph.yaml`, `.ai/PROGRESS.md`, and
  `.ai/HANDOFF.md` for the pending review-only gate.

## Post-Gate Validation

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Expected blocker after this gate is recorded:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0020
[error] Pending gate(s) require user decision before continuing: G-T-0020-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-REVIEW
```

## Boundary Notes

- No T-0020 review body was started.
- No checker was implemented.
- No MCP, skill, policy guard, wrapper, automation, protocol, runtime, or tool
  behavior was installed or enabled.
- No `AGENTS.md` change, real-project entry, business code, build,
  deployment, release, rollback, database, permission, secret, payment,
  production-data, or migration action occurred.

## Gate Approval

User approval text:

```text
批准 G-T-0020-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-REVIEW
```

Recorded approval evidence:

```text
.ai/evidence/T-0020/real-project-governance-enforcement-architecture-review.approval.record.v0.1.md
```

## Post-Approval Validation

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0020
[ok] state is usable
```

## Review Evidence Created

```text
.ai/evidence/T-0020/review-scope.v0.1.md
.ai/evidence/T-0020/t0019-package-coverage-review.v0.1.md
.ai/evidence/T-0020/enforcement-architecture-review.v0.1.md
.ai/evidence/T-0020/gate-register-schema-review.v0.1.md
.ai/evidence/T-0020/checker-and-blocking-semantics-review.v0.1.md
.ai/evidence/T-0020/policy-guard-and-wrapper-review.v0.1.md
.ai/evidence/T-0020/tool-entry-restriction-review.v0.1.md
.ai/evidence/T-0020/evidence-and-audit-enforcement-review.v0.1.md
.ai/evidence/T-0020/failure-mode-and-recovery-review.v0.1.md
.ai/evidence/T-0020/t0018-repair-coverage-verdict.v0.1.md
.ai/evidence/T-0020/residual-risk-register.v0.1.md
.ai/evidence/T-0020/review-summary.v0.1.md
.ai/evidence/T-0020/next-gate-recommendation.v0.1.md
```

## Closeout

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\close_session.py' 'C:\Users\Administrator\.codex\loop-engine-lab' --note 'T-0020 completed as review-only. User explicitly approved G-T-0020. Review verdict PASS_FOR_BASELINE_CONSIDERATION with P0=0, P1=0, P2=2, P3=1. T-0019 repaired the T-0018 P1 enforcement architecture gap at design level and may enter a later baseline consideration gate. No implementation, installation, AGENTS.md change, runtime/tool enablement, real-project entry, build, deploy, rollback, DB, permission, secret, payment, production data, or migration action occurred. Recommended next gate: G-T-0021-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-BASELINE-CONSIDERATION.'
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0020
[ok] state is usable
[ok] wrote C:\Users\Administrator\.codex\loop-engine-lab\.ai\HANDOFF.md
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0020
[ok] state is usable
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0020
```

Manual correction after closeout:

- Restored T-0020-specific `HANDOFF.md` facts.
- Restored `.ai/task_graph.yaml` T-0020 status to `completed` after the
  generic closeout generator marked it `in_progress`.
