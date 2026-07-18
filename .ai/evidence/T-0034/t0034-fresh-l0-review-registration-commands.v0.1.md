# T-0034 Fresh Independent L0 Review Gate Registration Commands v0.1

## Pre-Registration Read-Only Checks

Project root: `C:\Users\Administrator\.codex\loop-engine-lab`

```powershell
python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
python C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py C:\Users\Administrator\.codex\loop-engine-lab
```

- `validate_state.py` exit code: `2`
- `audit_handoff.py` exit code: `2`
- Both reported only preserved historical mismatches `T-0002`, `T-0004`, `T-0005`, `T-0007`, `T-0009`, and `T-0028`.
- No pending Gate existed before registration.
- `T-0034` remained `active`; repair execution status was `repair_completed_awaiting_separate_review_gate`; independent review and task closeout were unauthorized.

## Governance Write Baseline

Captured at `2026-07-16T15:43:47.5485000+08:00`:

| Path | Size (bytes) | SHA-256 |
|---|---:|---|
| `.ai/gates.yaml` | 203803 | `8C6C7E0B9086AB066D5FF19AE72399830004D0101FD1BF1A74AE7EB86699F27C` |
| `.ai/state.yaml` | 2497 | `E927D82488B0A0BBA408B6F68B877A2C4377075E06C941EF9BF2AD5CF3A0F01B` |
| `.ai/HANDOFF.md` | 14174 | `CDAC229C1AB39943E2BF9D0790FF8BC2038784D3CAF0C315B01BA30E870C8688` |
| `.ai/tasks/T-0034.md` | 3897 | `932053AC7325AF3BC4BC6212F5F91705423527C8FDD3922EF876C64B4125D905` |
| `.ai/task_graph.yaml` | 10191 | `4D5BA7A55F613D1E08A9EE81DC67FADDA0D149F589C079B6CB18347BF8CC2C14` |

## Registration Boundary

- Registration writes only this command record, the Gate request, the freeze manifest, `.ai/gates.yaml`, `.ai/state.yaml`, and `.ai/HANDOFF.md`.
- `.ai/tasks/T-0034.md`, `.ai/task_graph.yaml`, frozen subjects, repair artifacts, and existing evidence remain read-only.
- No post-registration review command is permitted in this Gate-creation session.
- After the pending Gate is written, execution stops immediately for an explicit user approve-or-reject decision.
