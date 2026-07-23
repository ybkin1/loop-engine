# Commands Evidence: T-0014

Task: T-0014
Gate: G-T-0014-METHOD-OPERATING-RULES-INSTALLATION
Status: completed; stopped on pending user gate

## Startup Read And Validation

Project root:

```text
C:\Users\Administrator\.codex\loop-engine-lab
```

Files read before creating T-0014:

```text
AGENTS.md
.ai/state.yaml
.ai/HANDOFF.md
.ai/tasks/T-0013.md
.ai/gates.yaml
.ai/task_graph.yaml
.ai/evidence/T-0013/operating-rules-design.candidate.v0.1.md
.ai/evidence/T-0013/user-decision-packet.method-operating-rules-design.v0.1.md
.ai/PROGRESS.md
```

Initial command requested by user:

```powershell
python 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Observed result:

```text
Exit code: 1
No stdout.
```

Interpreter diagnosis:

```text
python resolved to C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\python.exe
```

Rerun with the local Python interpreter:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Observed result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0013
[ok] state is usable
```

## Git And Baseline Checks

Commands:

```powershell
git status --short
git log -1 --oneline
```

Observed result:

```text
fatal: not a git repository (or any of the parent directories): .git
fatal: not a git repository (or any of the parent directories): .git
```

Because this workspace is not a git repository, T-0014 uses file existence, length, last-write time, and SHA256 as the changed-path baseline.

## Contract Index Check

Checked:

```text
C:\Users\Administrator\.claude\contracts\_index.md
```

Observed result:

```text
Contract index exists.
Relevant high-risk categories identified from index: gate register, security, deployment, production merge, data management, data protection, storage location, review gates, task tracking, verification.
```

T-0014 does not perform high-risk operations. The package explicitly keeps database, permission, secret, payment, production-data, migration, deployment, rollback, and runtime changes outside T-0014.

## Expected Pending Gate Stop Point

Final validation is expected to report:

```text
Pending gate(s) require user decision before continuing: G-T-0014-METHOD-OPERATING-RULES-INSTALLATION
```

The actual final validation output is recorded below in `Final Pending Gate Validation`.

## Proposed Diff Check

Command:

```powershell
git apply --check --verbose '.ai\evidence\T-0014\agents-md.proposed-diff.v0.1.patch'
```

Initial observed result:

```text
error: corrupt patch at line 53
```

Repair performed:

```text
Updated the unified diff hunk header from +47 to +48 in the evidence patch file.
```

Rerun result:

```text
Checking patch AGENTS.md...
Exit code: 0
```

No patch was applied.

## AGENTS.md No-Change Check

Command:

```powershell
Get-FileHash -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md' -Algorithm SHA256
```

Result:

```text
DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87
```

This matches the T-0014 changed-path baseline. `AGENTS.md` was not modified.

## Final Pending Gate Validation

Command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Observed result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0014
[error] Pending gate(s) require user decision before continuing: G-T-0014-METHOD-OPERATING-RULES-INSTALLATION
```

Observed command status:

```text
non-zero exit as expected for pending gate blocker
```

This is the expected T-0014 stop point.

## Evidence Provenance After Read-Only Reviews

During read-only subagent review, the main thread made narrow evidence repairs:

```text
15:15:57 main thread corrected agents-md.proposed-diff.v0.1.patch hunk header from +47 to +48 after git apply --check reported a corrupt patch; no patch was applied.
15:19:08 main thread updated commands.md with final validation evidence and updated rollback-recovery-plan.v0.1.md with explicit future recovery authorization boundary.
After safety review, main thread updated the gate request and decision packet to clarify that future execution would change project-local AGENTS.md startup / operating-rule text only and would not enable external agent runtimes, skills, MCPs, automations, protocol services, or tools.
```

Subagents did not modify files, approve gates, or apply patches.

## Post-Review Final Mechanical Checks

After subagent-driven evidence wording repairs, the main thread reran mechanical checks.

Patch check:

```powershell
git apply --check --verbose '.ai\evidence\T-0014\agents-md.proposed-diff.v0.1.patch'
```

Result:

```text
Checking patch AGENTS.md...
Exit code: 0
```

AGENTS.md hash check:

```powershell
Get-FileHash -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md' -Algorithm SHA256
```

Result:

```text
DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87
```

Validator check:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0014
[error] Pending gate(s) require user decision before continuing: G-T-0014-METHOD-OPERATING-RULES-INSTALLATION
```

This remains the expected T-0014 final stop point.

## Approval Recording

User approval message:

```text
批准 G-T-0014-METHOD-OPERATING-RULES-INSTALLATION
```

Recorded approval evidence:

```text
.ai/evidence/T-0014/method-operating-rules-installation.approval.record.v0.1.md
```

Updated governance records:

```text
.ai/gates.yaml -> G-T-0014-METHOD-OPERATING-RULES-INSTALLATION status: approved, decision: approved
.ai/state.yaml -> current_gate_id: null
.ai/task_graph.yaml -> T-0014 status: completed
```

Boundary:

```text
Approval recording did not apply the proposed diff, modify AGENTS.md, install or enable the repaired method, or change runtime behavior.
```

AGENTS.md hash after approval recording:

```text
DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87
```

## Final Validation After Approval Recording

Command:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0014
[ok] state is usable
```

Final boundary check:

```text
AGENTS.md hash remains DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87.
The proposed diff remains evidence only and was not applied.
```
