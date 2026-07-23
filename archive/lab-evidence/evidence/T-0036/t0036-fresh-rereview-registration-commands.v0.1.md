# T-0036 Fresh Rereview Gate Registration Commands v0.1

Captured: `2026-07-20T15:57:27.8878569+08:00`

- `python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab` -> exit `0`
- `python C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py C:\Users\Administrator\.codex\loop-engine-lab` -> exit `0` before registration
- `C:\Python312\python.exe -B candidates\T-0030-project-governor-repair\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab` -> exit `2`, `PROJECT_CONTINUITY_MISSING` (expected fail closed)
- PowerShell `Get-ChildItem`, `Get-FileHash`, file metadata, and reparse-attribute checks -> 16 files, 2 directories, 0 reparse points, matching repair-final candidate fingerprints
- PowerShell `Test-Path` checks -> live `.ai/project_continuity.yaml`, live `.ai/transaction_registry.yaml`, and `.ai/tasks/T-0037.md` absent

Post-registration global validator, HANDOFF audit, pending-Gate uniqueness, YAML parsing, and changed-path checks are recorded in `t0036-fresh-rereview-registration-validation.v0.1.md`.
