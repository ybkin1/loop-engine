# T-0036 Repair RED Results v0.1

Gate: `G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

Command:

`C:\Python312\python.exe -B C:\Users\Administrator\.codex\loop-engine-lab\candidates\T-0030-project-governor-repair\tests\test_project_governor_consistency.py -v`

Working directory:

`C:\Users\Administrator\.codex\loop-engine-lab\candidates\T-0030-project-governor-repair`

## Result

- Exit code: `1` (expected RED).
- Ran: `37` tests in `14.207s`.
- Existing regression tests: `28/28` passed.
- New repair contract tests: `0/9` passed, `8` failures and `1` missing-module error.
- Combined stdout/stderr UTF-8 bytes: `18312`.
- Combined stdout/stderr SHA-256: `D69892F94F8EDD81C21932223AF7C0DF4DB2AA9D596FEAAFA2EC2E693BA24184`.

## Reproduced RED Scenarios

- `AUTH-001`, `AUTH-005`: inline authority options remain and secure-isolation capability is absent.
- `RUN-001`: controlled runner entrypoint is absent; caller self-report binder remains.
- `PC-002`: missing ProjectContinuity does not fail closed and HANDOFF is overwritten.
- `TR-001`: missing TransactionRegistry still emits `## Stable Checkpoint`.
- `GATE-001`, `LIFE-001`: structured producer and lifecycle projection are absent.
- `ARCH-001`: six responsibility modules and independent auditor are absent.
- `EM-002`: bounded evidence-manifest verifier is absent.
- `E2E-CURRENT-001`: positive structured-current-project entrypoint is absent.

This is behavioral RED evidence only. It does not authorize installation, activation, independent rereview, T-0037, or any scope expansion.
