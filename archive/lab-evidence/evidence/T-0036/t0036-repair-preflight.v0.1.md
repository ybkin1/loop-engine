# T-0036 Repair Preflight v0.1

Gate: `G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

Completed at: `2026-07-20T13:45:45.0935674+08:00`

## Mechanical Results

- Global Project Governor `validate_state.py`: exit `0`, state usable.
- Pending Gate count: `0`.
- Approved Gate: exactly one matching Gate, status `approved`, execution status `approved_not_started`.
- Exact execution request: present at `t0036-repair-execution-request.v0.1.md` and matches the approved phrase.
- Effective baseline: 39 inherited subjects plus 4 protected additions; SHA-256, size, and `mtime_ns` mismatches: `0`.
- Candidate inventory: `10` files, `2` directories, `0` reparse points, `0` cache/compiled artifacts.
- Candidate `PATH` matches: `0`; candidate `PYTHONPATH` matches: `0`.
- Live `.ai/project_continuity.yaml`: absent.
- Live `.ai/transaction_registry.yaml`: absent.
- T-0037 task: absent.
- `NOT_INSTALLED` and `NOT_ACTIVATED`: unchanged from approved baseline.

## Recovery

Exact preimages of the eight existing candidate files were copied under `.ai/evidence/T-0036/repair-preimages/` before candidate writes. Preimage hashes and sizes are recorded in `t0036-repair-commands.v0.1.md`.

## Scope Decision

Preflight passed. Repair may proceed only inside the approved candidate paths and additive T-0036 evidence paths. Any baseline drift, host-identity requirement, live controller requirement, or scope expansion is a stop condition.
