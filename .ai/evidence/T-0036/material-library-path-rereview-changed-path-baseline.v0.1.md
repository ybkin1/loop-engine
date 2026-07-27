# T-0036 Path-Closure Fresh Rereview Changed-Path Baseline v0.1

Recorded at: `2026-07-24T17:48:00+08:00`

Gate: `G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-PATH-CLOSURE-REPAIR-V0-1`

This byte-level baseline was captured before Gate registration. `absent` means the path did not exist. Existing dirty-worktree changes belong to prior work and must be preserved.

| path | size | SHA-256 |
| --- | ---: | --- |
| `.ai/evidence/T-0036/material-library-path-rereview-gate-request.v0.1.md` | absent | absent |
| `.ai/evidence/T-0036/material-library-path-rereview-changed-path-baseline.v0.1.md` | absent | absent |
| `.ai/evidence/T-0036/material-library-path-rereview-control-manifest.v0.1.md` | absent | absent |
| `.ai/evidence/T-0036/material-library-path-rereview-registration-commands.v0.1.md` | absent | absent |
| `.ai/evidence/T-0036/material-library-path-rereview.v0.1.md` | absent | absent |
| `.ai/evidence/T-0036/material-library-path-rereview-commands.v0.1.md` | absent | absent |
| `.ai/evidence/T-0036/material-library-path-rereview-validation.v0.1.md` | absent | absent |
| `.ai/evidence/T-0036/material-library-path-rereview-changed-path-manifest.v0.1.md` | absent | absent |
| `.ai/gates.yaml` | 338986 | `8CF100214F6AA1CF74381A1D4170F47B801F3BF8B0F189A779049DE9A65EE38F8` |
| `.ai/state.yaml` | 14040 | `9E8B8633487D9E49A0D59760F9E782ADA4E9795472BCE571FAE65B7999C03E6B` |
| `.ai/HANDOFF.md` | 19874 | `964BB49F9BC68E0B9C052CFB3AFECF75BB5DACCD94AA29039C4897905B7B83BF` |

## Startup State

- Startup Gate state: `current_gate_id=null`, pending Gate count `0`.
- `validate_state.py`: exit `0`, state usable.
- `audit_handoff.py`: exit `0`, audit passed.
- `git diff --check`: exit `0`, no output.
- Startup worktree was already non-clean; this registration claims authorship only for its seven-path allowlist.

## Drift Rule

Future approval recording and execution must recheck the applicable preimages. Any unexplained drift returns `BLOCKED`; any path or effect outside the exact allowlist returns `SCOPE_VIOLATION`. No automatic deletion, reset, checkout, destructive rollback, or silent rebaseline is authorized.
