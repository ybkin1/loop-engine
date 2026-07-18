# T-0034 Closeout Commands v0.1

Working directory: `C:\Users\Administrator\.codex\loop-engine-lab`

## Preflight Reads

```powershell
Get-Content -Raw .ai\state.yaml
Get-Content -Raw .ai\HANDOFF.md
Get-Content -Raw .ai\tasks\T-0034.md
Get-Content -Raw .ai\gates.yaml
Get-Content -Raw .ai\task_graph.yaml
python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
```

Observed result: only the six preserved historical task-status mismatches were reported: `T-0002`, `T-0004`, `T-0005`, `T-0007`, `T-0009`, and `T-0028`.

## Baseline Verification

```powershell
Get-FileHash -Algorithm SHA256 <each closeout freeze-baseline path>
```

Observed result: `BASELINE_OK 14/14`.

## Closeout Writes

```text
apply_patch
```

Applied only the Gate-approved closeout execution paths.

## Final Validation

```powershell
python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
python C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py C:\Users\Administrator\.codex\loop-engine-lab
```

Final command outputs are recorded in `.ai/evidence/T-0034/t0034-closeout-validation.v0.1.md`.
