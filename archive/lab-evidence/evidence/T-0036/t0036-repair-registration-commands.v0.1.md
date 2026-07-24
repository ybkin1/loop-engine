# T-0036 Repair Gate Registration Commands v0.1

All commands were run from `C:\Users\Administrator\.codex\loop-engine-lab`. File writes used `apply_patch` only.

## Read-only startup and inspection

```powershell
Get-Content -Raw -LiteralPath 'C:\Users\Administrator\.codex\skills\project-governor\SKILL.md'
Get-Content -Raw -LiteralPath 'AGENTS.md'
Get-Content -Raw -LiteralPath '.ai\PROJECT.md'
Get-Content -Raw -LiteralPath '.ai\CONTRACTS.md'
Get-Content -Raw -LiteralPath '.ai\state.yaml'
Get-Content -Raw -LiteralPath '.ai\gates.yaml'
Get-Content -Raw -LiteralPath '.ai\task_graph.yaml'
Get-Content -Raw -LiteralPath '.ai\tasks\T-0035.md'
Get-Content -Raw -LiteralPath '.ai\tasks\T-0036.md'
Get-Content -Raw -LiteralPath '.ai\HANDOFF.md'
```

The exact user-listed T-0034/T-0035/T-0036 evidence was read. T-0036 old controller handoff, trust-baseline, closeout, and topic-explanation supplements were not adopted as repair authority.

Candidate inspection used `rg -n -C` on the six candidate scripts and the single candidate test file for authority records, request IDs, lifecycle transitions, final validation, HANDOFF, Gate projection, Unverified, checkpoint, evidence hashing, reparse handling, and relevant tests.

## Mechanical validation

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
C:\Python312\python.exe -B C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
C:\Python312\python.exe -B C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py C:\Users\Administrator\.codex\loop-engine-lab
```

Before registration, validator exit was `0`. After registration, validator and audit exit `2` only because the newly registered Gate is pending; exact outputs are recorded in `t0036-repair-registration-validation.v0.1.md`.

## Boundary and baseline checks

PowerShell `Get-FileHash -Algorithm SHA256`, `Get-Item`, and `Get-ChildItem -Force -Recurse` were used to record and recheck SHA-256, size, `mtime_ns`, file/directory counts, cache/compiled artifacts, and reparse points.

`mtime_ns` was computed as:

```powershell
([long]$item.LastWriteTimeUtc.Ticks - [long]621355968000000000) * [long]100
```

The first attempted `DateTime.UnixEpoch` expression did not evaluate correctly in this PowerShell host and produced overflow diagnostics. Those values were discarded and never used as evidence. The fixed-constant calculation exactly matched the T-0035 final manifest for all 10 candidate files.

## Writes

`apply_patch` created only the additive repair Gate evidence and updated only:

- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/task_graph.yaml`
- `.ai/tasks/T-0036.md`
- `.ai/HANDOFF.md`

No candidate, test, global Project Governor, `AGENTS.md`, marker, installation, activation, or runtime path was written.
