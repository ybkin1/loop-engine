# T-0036 Full-Suite Failure Repair Validation v0.1

Gate: `G-T-0036-FULL-SUITE-FAILURE-REPAIR-V0-1`
Result: `repair_completed`

## Acceptance

| check | result |
| --- | --- |
| RED reproduction | 12 passed, 6 failed; all six missing `AGENTS.md:24` |
| focused candidate module | 13 passed, 5 subtests passed |
| full pytest suite | 41 passed, 5 subtests passed |
| focused current candidate suite | 28 passed |
| validate_state.py | PASS |
| git diff --check | PASS |
| candidate test changed paths | exactly 1 |
| repository-level candidate AGENTS.md | absent |
| global Project Governor scripts | unchanged |

## Root cause resolution

The test fixture now creates the authoritative `AGENTS.md` only inside each `TemporaryDirectory` root, with a non-empty line 24, and asserts the exact line count. The fixture state also supplies the required `current_direction` field. The production anchor contract remains enforced and unchanged.

## Scope proof

- No candidate file other than `tests/test_project_governor_consistency.py` changed.
- No global skill, production script, T-0036 material, freeze manifest, prior review evidence, T-0037/T-0038 artifact, or repository-level `AGENTS.md` changed.
- Temporary fixture files are removed by `TemporaryDirectory` cleanup.

## Boundary

This is execution evidence only. It does not authorize independent rereview, candidate-baseline acceptance, version freeze, T-0037 review, or Host Integration.
