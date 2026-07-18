# Commands v0.1

Status: evidence
Task: T-0012

## Startup

Project root:

```text
C:\Users\Administrator\.codex\loop-engine-lab
```

User request:

```text
Open T-0012 baseline approval decision task. First generate the gate request / user decision package for G-T-0012-METHOD-BASELINE-APPROVAL. Do not directly approve. Do not make the approval decision for the user.
```

## Startup Reads

```powershell
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\state.yaml'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\HANDOFF.md'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\tasks\T-0011.md'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\gates.yaml'
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\task_graph.yaml'
```

## Startup Validation

Command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Output:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0011
[ok] state is usable
```

## Evidence Read

Read T-0011 evidence:

- `.ai/evidence/T-0011/next-gate-recommendation.v0.1.md`
- `.ai/evidence/T-0011/baseline-readiness-review.v0.1.md`
- `.ai/evidence/T-0011/lifecycle-transition-recommendation.v0.1.md`
- `.ai/evidence/T-0011/residual-risk-register.v0.1.md`

Read T-0010 templates:

- `.ai/evidence/T-0010/gate-request-template.v0.1.md`
- `.ai/evidence/T-0010/user-decision-packet-template.v0.1.md`

## Task Creation

Command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\new_task.py' 'C:\Users\Administrator\.codex\loop-engine-lab' --title 'Method Baseline Approval Decision' --allow-parallel
```

Output:

```text
[ok] created T-0012: Method Baseline Approval Decision
[next] edit .ai/tasks/T-0012.md and record evidence under .ai/evidence/T-0012/
```

## File Writes

Created:

- `.ai/tasks/T-0012.md`
- `.ai/evidence/T-0012/commands.md`
- `.ai/evidence/T-0012/gate-request.G-T-0012-METHOD-BASELINE-APPROVAL.v0.1.md`
- `.ai/evidence/T-0012/user-decision-packet.baseline-approval.v0.1.md`

Updated:

- `.ai/state.yaml`
- `.ai/task_graph.yaml`
- `.ai/gates.yaml`
- `.ai/PROGRESS.md`
- `.ai/HANDOFF.md`

## Expected Final Validation

Because the generated gate is intentionally pending, final validation blocks until the user explicitly approves, rejects, or redirects.

Command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Output:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0012
[error] Pending gate(s) require user decision before continuing: G-T-0012-METHOD-BASELINE-APPROVAL
```

## Explicit User Approval

Explicit user approval received:

```text
批准 G-T-0012-METHOD-BASELINE-APPROVAL
```

## Approval Recording

Created:

- `.ai/evidence/T-0012/baseline-approval.record.v0.1.md`

Updated:

- `.ai/state.yaml`
- `.ai/tasks/T-0012.md`
- `.ai/task_graph.yaml`
- `.ai/gates.yaml`
- `.ai/PROGRESS.md`
- `.ai/DECISIONS.md`
- `.ai/HANDOFF.md`

Boundary:

```text
Baseline approval is reference-only. It does not install or enable the method, modify AGENTS.md, change runtime behavior, enter a real project, or authorize implementation/build/deploy/release/high-risk action.
```

## Final Validation After Approval

Command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Output:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0012
[ok] state is usable
```

## Wording Clarification

Recorded at: 2026-07-08T13:42:00+08:00

Clarification:

```text
Approval should be understood as explicit user approval, not Codex or AI approval.
```

Updated:

- `.ai/gates.yaml`
- `.ai/evidence/T-0012/baseline-approval.record.v0.1.md`
- `.ai/evidence/T-0012/commands.md`

Boundary unchanged:

```text
This remains baseline reference approval only, not installation, enablement, AGENTS.md modification, runtime behavior change, or real-project application.
```

Validation after wording clarification:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0012
[ok] state is usable
```

Ambiguous wording search:

```text
No matches for 我的批准, 你的批准, my approval, or your approval.
```
