# Commands Evidence: T-0015

Task: T-0015
Gate: G-T-0015-METHOD-OPERATING-RULES-EXECUTION
Status: blocked on pending user decision

## Startup Reads

Project root:

```text
C:\Users\Administrator\.codex\loop-engine-lab
```

Read before any write to `AGENTS.md`:

```text
AGENTS.md
.ai/state.yaml
.ai/HANDOFF.md
.ai/tasks/T-0014.md
.ai/gates.yaml
.ai/task_graph.yaml
.ai/PROGRESS.md
.ai/evidence/T-0014/agents-md.proposed-diff.v0.1.patch
.ai/evidence/T-0014/changed-path-baseline.v0.1.md
.ai/evidence/T-0014/validation-plan.v0.1.md
.ai/evidence/T-0014/rollback-recovery-plan.v0.1.md
.ai/evidence/T-0014/failure-recovery-steps.v0.1.md
.ai/evidence/T-0014/method-operating-rules-installation.approval.record.v0.1.md
```

## Startup Validation

Command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Observed result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0014
[ok] state is usable
```

## Baseline And Dry-Run Checks

`AGENTS.md` SHA256:

```text
DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87
```

This matches the T-0014 baseline.

Dry-run command:

```powershell
git apply --check --verbose -- 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0014\agents-md.proposed-diff.v0.1.patch'
```

Observed result:

```text
Checking patch AGENTS.md...
Exit code: 0
```

No patch was applied.

Git status/log result:

```text
fatal: not a git repository (or any of the parent directories): .git
```

## Gate Decision

T-0015 cannot proceed directly to modifying `AGENTS.md` under T-0014 approval.
A new T-0015 execution gate is required and is recorded as pending.

## Pending Gate Validation

Command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Observed result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0015
[error] Pending gate(s) require user decision before continuing: G-T-0015-METHOD-OPERATING-RULES-EXECUTION
```

Observed command status:

```text
non-zero exit as expected for pending gate blocker
```

`AGENTS.md` hash after recording the pending gate:

```text
DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87
```

## Approval Recording

User approval message:

```text
批准 G-T-0015-METHOD-OPERATING-RULES-EXECUTION
```

Recorded approval evidence:

```text
.ai/evidence/T-0015/method-operating-rules-execution.approval.record.v0.1.md
```

Updated gate:

```text
G-T-0015-METHOD-OPERATING-RULES-EXECUTION -> status: approved, decision: approved
```

Validator after approval recording:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0015
[ok] state is usable
```

Pre-execution recheck:

```text
AGENTS.md SHA256=DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87
git apply --check: passed
```

## Patch Execution

Command:

```powershell
git apply --verbose -- 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0014\agents-md.proposed-diff.v0.1.patch'
```

Observed result:

```text
Checking patch AGENTS.md...
Applied patch AGENTS.md cleanly.
```

Post-execution hash:

```text
7D9B688C8364E4E2AA79D6878376B19D1E98FBC850A8116E297C50AB18F391BA
```

Reverse patch check:

```text
git apply --reverse --check --verbose: passed
```

Inserted sections verified in `AGENTS.md`:

```text
Loop Engineering Method Operating Rules
Startup Routing
Gates And Boundaries
Evidence And Handoff
```

## Final Validation

Command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Observed result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0015
[ok] state is usable
```

Post-execution `AGENTS.md` hash:

```text
7D9B688C8364E4E2AA79D6878376B19D1E98FBC850A8116E297C50AB18F391BA
```

Reverse patch check remained valid:

```text
Checking patch AGENTS.md...
Exit code: 0
```

Pending gate scan:

```text
No pending gate entries found.
```

## Session Closeout

Command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\close_session.py' 'C:\Users\Administrator\.codex\loop-engine-lab' --note 'T-0015 applied the exact approved T-0014 AGENTS.md operating-rules patch under explicit user approval G-T-0015-METHOD-OPERATING-RULES-EXECUTION. Validation passed and no pending gates remain.'
```

Observed result:

```text
[ok] wrote C:\Users\Administrator\.codex\loop-engine-lab\.ai\HANDOFF.md
```

The generated handoff was then corrected to the T-0015-specific closeout facts,
and `.ai/task_graph.yaml` was restored to `status: completed` for T-0015.

## Handoff Audit

Command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Observed result:

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0015
```

Final verification snapshot:

```text
validate_state.py: [ok] state is usable
AGENTS.md SHA256: 7D9B688C8364E4E2AA79D6878376B19D1E98FBC850A8116E297C50AB18F391BA
pending gates: none
T-0015 task_graph status: completed
```
