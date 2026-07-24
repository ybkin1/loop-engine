# Commands

## Startup Read

- Read `.ai/state.yaml`.
- Read `.ai/HANDOFF.md`.
- Read `.ai/tasks/T-0017.md`.
- Read `.ai/gates.yaml`.
- Read `.ai/task_graph.yaml`.
- Read `.ai/PROGRESS.md`.

## Pre-Gate Validation

Command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Output:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0017
[ok] state is usable
```

## Pending Gate Check Before Creation

Command:

```powershell
Select-String -Path '.ai\gates.yaml' -Pattern 'status:\s*pending'
```

Output:

```text
<no matches>
```

## Gate Creation

Created/presented pending review-only gate:

```text
G-T-0018-REAL-PROJECT-DELIVERY-ARCHITECTURE-GOVERNANCE-REVIEW
```

Review work has not started.

## Post-Gate Validation

Command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Exit code:

```text
1
```

Output:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0018
[error] Pending gate(s) require user decision before continuing: G-T-0018-REAL-PROJECT-DELIVERY-ARCHITECTURE-GOVERNANCE-REVIEW
```

## User Approval

The user explicitly approved the pending gate:

```text
批准 G-T-0018-REAL-PROJECT-DELIVERY-ARCHITECTURE-GOVERNANCE-REVIEW
```

Approval was recorded as user approval, not AI approval.

## Post-Approval Validation

Command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Output:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0018
[ok] state is usable
```

## Review Evidence Created

- `.ai/evidence/T-0018/review-scope.v0.1.md`
- `.ai/evidence/T-0018/package-coverage-review.v0.1.md`
- `.ai/evidence/T-0018/lifecycle-and-gate-review.v0.1.md`
- `.ai/evidence/T-0018/real-project-boundary-review.v0.1.md`
- `.ai/evidence/T-0018/architecture-and-design-depth-review.v0.1.md`
- `.ai/evidence/T-0018/enforcement-gap-review.v0.1.md`
- `.ai/evidence/T-0018/role-review-findings.v0.1.md`
- `.ai/evidence/T-0018/residual-risk-register.v0.1.md`
- `.ai/evidence/T-0018/review-summary.v0.1.md`
- `.ai/evidence/T-0018/next-gate-recommendation.v0.1.md`

## Review Result

Verdict:

```text
repair required
```

Finding counts:

```text
P0=0
P1=1
P2=2
P3=1
```

Recommended next gate:

```text
G-T-0019-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-DESIGN
```

## Closeout

Ran `close_session.py`:

```text
[ok] wrote C:\Users\Administrator\.codex\loop-engine-lab\.ai\HANDOFF.md
```

Ran `validate_state.py` after closeout:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0018
[ok] state is usable
```

Ran `audit_handoff.py` after closeout:

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0018
```

The generated closeout handoff and task graph then required correction because
the generated text compressed away T-0018-specific review findings and recorded
the current task graph status as `in_progress`. Corrected closeout facts:

```text
T-0018 status: completed
verdict: repair required
recommended next gate: G-T-0019-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-DESIGN
```
