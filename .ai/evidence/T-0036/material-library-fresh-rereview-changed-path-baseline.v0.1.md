# T-0036 Fresh Independent Rereview Changed-Path Baseline v0.1

Recorded at: `2026-07-24T15:56:12+08:00`

Gate: `G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-REPAIR-V0-1`

This byte-level baseline was captured before Gate registration. `absent` means the path did not exist. Existing dirty-worktree changes belong to earlier work and must be preserved.

| path | size | SHA-256 |
| --- | ---: | --- |
| `.ai/evidence/T-0036/material-library-fresh-rereview-gate-request.v0.1.md` | absent | absent |
| `.ai/evidence/T-0036/material-library-fresh-rereview-changed-path-baseline.v0.1.md` | absent | absent |
| `.ai/evidence/T-0036/material-library-fresh-rereview-control-manifest.v0.1.md` | absent | absent |
| `.ai/evidence/T-0036/material-library-fresh-rereview-registration-commands.v0.1.md` | absent | absent |
| `.ai/evidence/T-0036/material-library-fresh-rereview-approval-record.v0.1.md` | absent | absent |
| `.ai/evidence/T-0036/material-library-fresh-rereview.v0.1.md` | absent | absent |
| `.ai/evidence/T-0036/material-library-fresh-rereview-commands.v0.1.md` | absent | absent |
| `.ai/evidence/T-0036/material-library-fresh-rereview-validation.v0.1.md` | absent | absent |
| `.ai/evidence/T-0036/material-library-fresh-rereview-changed-path-manifest.v0.1.md` | absent | absent |
| `.ai/gates.yaml` | 323812 | `B35D10E81B7CFFE213257078B33BBDF78F61BD87D19CFEFB137315D85496B917` |
| `.ai/state.yaml` | 12332 | `02D609C4489DD3EE55D86866F63500C63730D8432DA4F3A507AA7005EBBF3865` |
| `.ai/HANDOFF.md` | 18428 | `7D91FA88B800479BB5E939918F591CD0F853388A759BFAB255424A8CCBDC9B6C` |

## Startup Worktree

`git status --porcelain -uall` was non-clean before registration. Modified paths included governance records, `README.md`, and the candidate consistency test; numerous T-0035..T-0038 evidence, Loop candidate, material, documentation, and test paths were already untracked.

`git diff --check` returned exit code `0` with no output. This Gate claims authorship only for its seven-path registration allowlist and must preserve every unrelated change.

## Drift Rule

Future approval recording and execution must recheck the applicable preimages. Any unexplained drift returns `BLOCKED`; any path outside the exact allowlist returns `SCOPE_VIOLATION`. No automatic deletion, reset, checkout, or destructive rollback is authorized.
