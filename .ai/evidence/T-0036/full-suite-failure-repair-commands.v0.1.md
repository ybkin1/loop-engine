# T-0036 Full-Suite Failure Repair Commands v0.1

Gate: `G-T-0036-FULL-SUITE-FAILURE-REPAIR-V0-1`
Execution request: `执行 G-T-0036-FULL-SUITE-FAILURE-REPAIR-V0-1`

## Preflight and RED

- `validate_state.py`: PASS before execution.
- Candidate test preimage: 13152 bytes; SHA-256 `ED22E7DCBFF310EB91AFB9713A2076E7C7140C77C37CEA418794E87717C77385`.
- `python -m pytest candidates/T-0030-project-governor-repair/tests/test_project_governor_consistency.py -q`: `12 passed, 6 failed`; all failures reported missing `AGENTS.md:24`.

## Bounded repair

- Modified only `candidates/T-0030-project-governor-repair/tests/test_project_governor_consistency.py`.
- Added a temporary-root `AGENTS.md` with an explicit non-empty line 24 and a line-count assertion.
- Added `current_direction: fixture continuation` to the temporary `.ai/state.yaml` fixture after the first GREEN run exposed the second missing fixture contract.
- No repository-level `AGENTS.md` was created; no production or global Project Governor file changed.

## GREEN and final checks

- Focused candidate module: `13 passed, 5 subtests passed`.
- Full suite `python -m pytest -q`: `41 passed, 5 subtests passed`.
- Focused current candidate suite `python -m pytest tests/codex_loop -q`: `28 passed`.
- `validate_state.py`: PASS.
- `git diff --check`: PASS.
- Candidate postimage: 13572 bytes; SHA-256 `DEC3C8FD572AC69E311681AAC8FC6C027622C5EDE0483360F0785C43CF56959B`.
- Repository-level candidate `AGENTS.md`: absent.
- Global `C:\Users\Administrator\.codex\skills\project-governor\scripts\close_session.py`: present and unchanged.

## Stop condition

All six failures are repaired and the full suite is green. Execution stops here; no rereview, baseline acceptance, version freeze, T-0037 review, or Host Integration starts in this Gate.
