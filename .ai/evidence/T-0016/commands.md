# Commands Evidence: T-0016

Task: T-0016
Gate: G-T-0016-STARTUP-RULES-ACCEPTANCE-SMOKE-TEST
Status: completed

## Startup Reads

Project root:

```text
C:\Users\Administrator\.codex\loop-engine-lab
```

Read before writing T-0016 records:

```text
C:\Users\Administrator\.codex\skills\project-governor\SKILL.md
AGENTS.md
.ai/state.yaml
.ai/HANDOFF.md
.ai/tasks/T-0015.md
.ai/gates.yaml
.ai/task_graph.yaml
.ai/PROGRESS.md
```

## Startup Validation

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

Pending gate scan:

```text
No status: pending entries found in .ai/gates.yaml.
```

## User Approval

User approval message:

```text
批准 G-T-0016-STARTUP-RULES-ACCEPTANCE-SMOKE-TEST
```

Recorded approval evidence:

```text
.ai/evidence/T-0016/gate-approval.G-T-0016-STARTUP-RULES-ACCEPTANCE-SMOKE-TEST.v0.1.md
```

## AGENTS.md Verification

Hash command:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md'
```

Observed SHA256:

```text
7D9B688C8364E4E2AA79D6878376B19D1E98FBC850A8116E297C50AB18F391BA
```

Installed sections verified in `AGENTS.md`:

```text
Loop Engineering Method Operating Rules
Startup Routing
Gates And Boundaries
Evidence And Handoff
```

## Final Validation And Closeout

Command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Observed result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0016
[ok] state is usable
```

Pending gate scan after T-0016 updates:

```text
No status: pending entries found in .ai/gates.yaml.
```

Post-update `AGENTS.md` SHA256:

```text
7D9B688C8364E4E2AA79D6878376B19D1E98FBC850A8116E297C50AB18F391BA
```

Matched `AGENTS.md` sections:

```text
AGENTS.md:20:## Loop Engineering Method Operating Rules
AGENTS.md:26:### Startup Routing
AGENTS.md:42:### Gates And Boundaries
AGENTS.md:53:### Evidence And Handoff
```

Closeout command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\close_session.py' 'C:\Users\Administrator\.codex\loop-engine-lab' --note 'T-0016 completed post-installation startup-rules acceptance smoke test. AGENTS.md content and SHA256 were verified. No AGENTS.md change, runtime/tool enablement, real-project entry, business code, or high-risk action occurred.'
```

Observed result:

```text
[ok] wrote C:\Users\Administrator\.codex\loop-engine-lab\.ai\HANDOFF.md
```

The generated handoff was then corrected to the T-0016-specific closeout facts,
and `.ai/task_graph.yaml` was restored to `status: completed` for T-0016.

Final validation command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Observed result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0016
[ok] state is usable
```

Handoff audit command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Observed result:

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0016
```
