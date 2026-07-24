# Commands For T-0019

## Startup

```powershell
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\state.yaml'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\HANDOFF.md'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\tasks\T-0018.md'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\gates.yaml'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\task_graph.yaml'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\PROGRESS.md'
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0018
[ok] state is usable
```

## Gate Creation

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\new_task.py' 'C:\Users\Administrator\.codex\loop-engine-lab' --title 'Real Project Governance Enforcement Architecture Design' --allow-parallel
```

Result:

```text
[ok] created T-0019: Real Project Governance Enforcement Architecture Design
[next] edit .ai/tasks/T-0019.md and record evidence under .ai/evidence/T-0019/
```

## Notes

- This evidence records gate creation only.
- No T-0019 enforcement architecture design work was performed.
- No `AGENTS.md` change, runtime/tool enablement, real-project entry,
  implementation, build, deployment, rollback, database, permission, secret,
  payment, production-data, or migration action occurred.

## Post-Gate Validation

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0019
[error] Pending gate(s) require user decision before continuing: G-T-0019-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-DESIGN
```

This is the expected blocker for the pending T-0019 gate.

## Gate Approval

User approval text:

```text
批准 G-T-0019-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-DESIGN
```

Recorded approval evidence:

```text
.ai/evidence/T-0019/real-project-governance-enforcement-architecture-design.approval.record.v0.1.md
```

## Design Evidence Created

```text
.ai/evidence/T-0019/contract-consultation.v0.1.md
.ai/evidence/T-0019/enforcement-architecture.candidate.v0.1.md
.ai/evidence/T-0019/machine-readable-gate-register-schema.candidate.v0.1.md
.ai/evidence/T-0019/checker-catalog-and-blocking-semantics.candidate.v0.1.md
.ai/evidence/T-0019/policy-guard-and-wrapper-design.candidate.v0.1.md
.ai/evidence/T-0019/tool-entry-restriction-model.candidate.v0.1.md
.ai/evidence/T-0019/evidence-and-audit-enforcement-design.candidate.v0.1.md
.ai/evidence/T-0019/failure-mode-and-recovery-design.candidate.v0.1.md
.ai/evidence/T-0019/t0017-repair-coverage-map.v0.1.md
.ai/evidence/T-0019/next-gate-recommendation.v0.1.md
.ai/evidence/T-0019/self-review.v0.1.md
```

Validation during design:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0019
[ok] state is usable
```

## Closeout

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\close_session.py' 'C:\Users\Administrator\.codex\loop-engine-lab' --note 'T-0019 completed as design-only enforcement architecture candidate. User approved G-T-0019. Candidate evidence created for gate register schema, checker catalog, policy guard/wrapper, tool-entry restrictions, evidence/audit, failure recovery, and repair coverage. No implementation, AGENTS.md change, runtime/tool enablement, or real-project entry occurred. Recommended next gate: G-T-0020-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-REVIEW.'
```

Result:

```text
[ok] wrote C:\Users\Administrator\.codex\loop-engine-lab\.ai\HANDOFF.md
```

Manual correction after closeout:

- Restored T-0019-specific `HANDOFF.md` facts.
- Restored `.ai/task_graph.yaml` T-0019 status to `completed` after the
  generic closeout generator marked it `in_progress`.

Final validation:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0019
[ok] state is usable
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0019
```
