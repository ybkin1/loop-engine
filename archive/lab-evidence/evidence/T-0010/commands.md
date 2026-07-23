# Commands v0.1

Status: evidence
Task: T-0010

## Startup

Project root:

```text
C:\Users\Administrator\.codex\loop-engine-lab
```

User approval recorded in the request:

```text
批准 G-T-0010-METHOD-CANDIDATE-REPAIR
```

## Read Commands

```powershell
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\skills\project-governor\SKILL.md'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\state.yaml'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\HANDOFF.md'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\tasks\T-0009.md'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\gates.yaml'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\task_graph.yaml'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\PROGRESS.md'
```

## Startup Validation

Command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Output:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0009
[ok] state is usable
```

## Pending Gate Check

Command:

```powershell
Select-String -Path 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\gates.yaml' -Pattern 'status:\s*pending'
```

Output:

```text
<no matches>
```

## Evidence Directory

Command:

```powershell
New-Item -ItemType Directory -Force -Path 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0010'
```

Output:

```text
C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0010
```

## Source Evidence Read

T-0008 candidate evidence read:

- `ai-role-review-loop.v0.1.md`
- `design-document-generation-loop.v0.1.md`
- `gate-and-handoff-protocol.v0.1.md`
- `lifecycle-stage-map.v0.1.md`
- `loop-engine-method-diagnosis.v0.1.md`
- `stage-artifact-matrix.v0.1.md`

T-0009 review evidence read:

- `artifact-coverage-gap-review.v0.1.md`
- `governance-safety-review.v0.1.md`
- `harness-depth-comparison.v0.1.md`
- `next-gate-recommendation.v0.1.md`
- `repair-recommendations.v0.1.md`
- `role-review-findings.v0.1.md`

## File Writes

Written with `apply_patch` only.

Created:

- `.ai/tasks/T-0010.md`
- `.ai/evidence/T-0010/commands.md`
- `.ai/evidence/T-0010/repair-scope.v0.1.md`
- `.ai/evidence/T-0010/method-lifecycle-state-model.v0.1.md`
- `.ai/evidence/T-0010/gate-request-template.v0.1.md`
- `.ai/evidence/T-0010/real-project-entry-gate-template.v0.1.md`
- `.ai/evidence/T-0010/artifact-schema-catalog.v0.1.md`
- `.ai/evidence/T-0010/traceability-id-system.v0.1.md`
- `.ai/evidence/T-0010/user-decision-packet-template.v0.1.md`
- `.ai/evidence/T-0010/repair-loop-protocol.v0.1.md`
- `.ai/evidence/T-0010/handoff-context-hygiene-checklist.v0.1.md`
- `.ai/evidence/T-0010/design-baseline-readiness-checklist.v0.1.md`
- `.ai/evidence/T-0010/repair-summary.v0.1.md`
- `.ai/evidence/T-0010/next-gate-recommendation.v0.1.md`

Updated:

- `.ai/state.yaml`
- `.ai/task_graph.yaml`
- `.ai/gates.yaml`
- `.ai/PROGRESS.md`
- `.ai/HANDOFF.md`

## Final Validation

Command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Output:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0010
[ok] state is usable
```
