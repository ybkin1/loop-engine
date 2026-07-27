# T-0036 Full-Suite Failure Repair Gate Changed-Path Baseline v0.1

Gate: `G-T-0036-FULL-SUITE-FAILURE-REPAIR-V0-1`
Captured: `2026-07-24`

## Current Git baseline

Command: `git status --porcelain -uall`

- status lines: `157`
- staged: `0`
- tracked worktree modifications: `6`
- untracked: `151`
- UTF-8 joined-output SHA-256: `560B39A9D9E27D6D22D399BD578C2E0BC8ADA4ED16E87B3047EC0621C1CFA400`
- Existing changes are preserved and are not attributed to this Gate.

## Failure reproduction baseline

- command: `python -m pytest -q`
- observed result: `40 passed, 6 failed`
- all six failures are `ProjectGovernorConsistencyTests` cases that call `close_session.py` and receive `Missing authoritative anchor AGENTS.md:24`.
- focused suite: `python -m pytest tests/codex_loop -q` -> `28 passed`.

## Allowed repair object before Gate execution

| path | status | size | SHA-256 | lines |
| --- | --- | ---: | --- | ---: |
| `candidates/T-0030-project-governor-repair/tests/test_project_governor_consistency.py` | clean tracked | 13152 | `ED22E7DCBFF310EB91AFB9713A2076E7C7140C77C37CEA418794E87717C77385` | 248 |

The candidate root does not contain `AGENTS.md`; the repair must create the anchor only inside each temporary test root at runtime, not add or modify a repository-level `AGENTS.md`.

## Registration paths

| path | before |
| --- | --- |
| `.ai/evidence/T-0036/full-suite-failure-repair-gate-request.v0.1.md` | absent |
| `.ai/evidence/T-0036/full-suite-failure-repair-changed-path-baseline.v0.1.md` | absent |
| `.ai/evidence/T-0036/full-suite-failure-repair-registration-commands.v0.1.md` | absent |
| `.ai/gates.yaml` | modified user worktree path; preserve existing content |
| `.ai/state.yaml` | modified user worktree path; preserve existing content |
| `.ai/HANDOFF.md` | modified user worktree path; preserve existing content |

## Forbidden pre-existing paths

All T-0036 materials, the 65-subject post-repair freeze, prior independent-review evidence, global Project Governor files, and every candidate path other than the exact test file above are read-only during Gate preparation and execution.
