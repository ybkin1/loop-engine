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
