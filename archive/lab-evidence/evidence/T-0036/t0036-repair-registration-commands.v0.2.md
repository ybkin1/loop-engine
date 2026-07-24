# T-0036 Repair Gate Revision Commands v0.2

All commands ran from `C:\Users\Administrator\.codex\loop-engine-lab`. Writes used `apply_patch` only.

## Startup

```powershell
Get-Content -Raw C:\Users\Administrator\.codex\skills\project-governor\SKILL.md
Get-Content -Raw AGENTS.md
Get-Content -Raw .ai\PROJECT.md
Get-Content -Raw .ai\CONTRACTS.md
Get-Content -Raw .ai\state.yaml
Get-Content -Raw .ai\HANDOFF.md
Get-Content -Raw .ai\tasks\T-0036.md
```

`gates.yaml` and `task_graph.yaml` were parsed with `yaml.safe_load`; exactly the current T-0036 records and pending count were projected for inspection.

Global startup validator:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
C:\Python312\python.exe -B C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
```

Expected result remained exit `2` for the one pending Gate.

## Protected Baseline

`Get-FileHash -Algorithm SHA256` plus exact file length and Windows `mtime_ns` were captured for:

- `.ai/PROJECT.md`
- `.ai/CONTRACTS.md`
- `.ai/evidence/T-0034/project-continuity-contract.v0.2.md`
- `.ai/evidence/T-0034/controller-data-flow-transaction-contracts.v0.2.md`

The effective baseline checker composed the immutable 39 v0.1 subjects with the four v0.2 protected additions and recomputed all 43 subjects.

## Writes

Additive v0.2 evidence was created for the Gate request, decision packet, test plan, structured-state contracts, protected-baseline revision, commands, validation, and changed-path manifest.

Only these governance projections were modified:

- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/task_graph.yaml`
- `.ai/tasks/T-0036.md`
- `.ai/HANDOFF.md`

No candidate, test, live ProjectContinuity/TransactionRegistry instance, protected project source, global Project Governor source, `AGENTS.md`, marker, PATH/PYTHONPATH, installation, activation, or runtime file was written.
