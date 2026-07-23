# T-0034 Design Repair Registration Commands v0.1

Read-only startup commands:

```powershell
python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
python C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py C:\Users\Administrator\.codex\loop-engine-lab
```

Both exited `2` and reported exactly six preserved historical mismatches: `T-0002`, `T-0004`, `T-0005`, `T-0007`, `T-0009`, and `T-0028`. No other startup error or pending gate existed.

The hash baseline was captured with PowerShell `Get-FileHash -Algorithm SHA256` before registration. The project root returned `fatal: not a git repository`; no Git operation or repository mutation occurred.

Registration writes are limited to this file, the gate request, disk review, changed-path baseline, `.ai/gates.yaml`, `.ai/state.yaml`, and `.ai/HANDOFF.md`. No repair artifact was produced or modified.
