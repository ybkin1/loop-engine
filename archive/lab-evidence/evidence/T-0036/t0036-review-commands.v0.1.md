# T-0036 Review Commands v0.1

All Python commands use `-B`. Candidate checks/tests use process-local `PYTHONDONTWRITEBYTECODE=1`, remove inherited `PYTHONPATH`, and use explicit candidate paths.

## L0 Preflight

- Global `validate_state.py`: exit `0` before execution start.
- Global `audit_handoff.py`: exit `0` before execution start.
- Frozen subject comparison: `60/60`, mismatches `0`.
- Candidate inventory/environment check: `10` files, `2` directories, `0` cache/compiled artifacts, `0` reparse points, `0` PATH/PYTHONPATH entries.

## Reviewer

- A fresh independent read-only reviewer is launched with `fork_turns="none"` after deterministic preflight.
- Reviewer: `/root/t0036_fresh_independent_review`; no parent conclusions and no project writes.
- T-0035 final manifest: 37/37 fingerprints match.
- T-0036 freeze manifest: 60/60 subjects match.
- Candidate tests: exit `0`, `Ran 28 tests in 17.477s`, `OK`.
- Candidate/global validators and audits: all exit `0`.
- Temporary-fixture reproductions covered inline evidence binding, cross-process transition chaining, self-reported validation, HANDOFF orientation, Gate projection, Unverified projection, and checkpoint stability.
- Verdict: `REPAIR_REQUIRED`; 7 P1, 2 P2, no P0/P3.

## Boundary

No repair, installation, activation, runtime/controller/orchestration enablement, downstream task creation, or real-project action is permitted.
