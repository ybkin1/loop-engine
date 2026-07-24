# T-0036 F003 Completed-State Regression Reproducibility Decision Packet v0.1

Gate: `G-T-0036-REPAIR-F003-COMPLETED-STATE-REGRESSION-REPRODUCIBILITY-V0-1`

Status: `pending`. Registration only; no approval or repair execution.

## Root Cause

The repaired `validation_runner.py` correctly requires a Gate-bound `in_progress` execution for controlled validation. The current stable disk is a completed-state projection with no such execution, so `E2E-CURRENT-001` cannot pass from the live project state and the full structured adapter regression is `63/64` with `AUTHORITY_MISSING`.

This is a test/fixture and authority-lifecycle coupling problem. It is not evidence that the original zero-test stdout spoof remains usable. Focused F003 protocol tests pass `8/8`; the zero-test spoof is rejected; stdout/stderr are diagnostic hashes only. Stable completed-state authority closure is the expected safe state.

## Minimum Modification Scope

1. Reproduce the RED failure from stable completed-state disk without changing live `.ai` Gate state.
2. Add the smallest isolated temporary fixture or test arrangement that explicitly creates a closed, non-production, Gate-bound `in_progress` execution for the positive controlled-validation path.
3. Keep production candidate authority logic unchanged unless evidence proves the fixture/test repair is insufficient.
4. Re-run focused protocol tests and the complete structured adapter regression from stable disk.

## Exact Allowed Paths For A Later Execution

Registration and governance projection paths:

- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/task_graph.yaml`
- `.ai/tasks/T-0036.md`
- `.ai/HANDOFF.md`
- `.ai/evidence/T-0036/` registration evidence for this Gate only

Future implementation paths are not pre-approved by registration. A later execution must name exact candidate/test paths after preflight and must not expand scope without a new user decision. Temporary fixture paths must be under an isolated temporary directory and must be recorded with cleanup evidence.

For a later exact execution request, the intended minimum allowed path set is:

- `candidates/T-0030-project-governor-repair/tests/test_project_governor_consistency.py`
- `.ai/evidence/T-0036/t0036-f003-completed-state-regression-reproducibility-execution-*.md`
- one per-run isolated temporary fixture directory outside the project root, with the exact resolved path recorded before execution

The production candidate runner is not an allowed repair target under this registration. A need to modify `validation_runner.py` or any other production candidate path requires a separate Gate decision package.

## Pre-Change Baseline

Before this registration, the disk facts were:

- `current_phase: S0-method-repair`
- `current_task_id: T-0036`
- `current_gate_id: null`
- `pending_gate_count: 0`
- `blocking_findings: [T0036-F003]`
- `repair_authorized: false`
- `implementation_authorized: false`
- `independent_rereview_authorized: false`
- candidate inventory: 17 files, 2 directories, 0 reparse points, 0 cache/compiled artifacts
- live `.ai/project_continuity.yaml`: absent
- live `.ai/transaction_registry.yaml`: absent
- T-0037: absent

Exact governance and protected-subject fingerprints are recorded in `t0036-f003-completed-state-regression-reproducibility-registration-baseline.v0.1.yaml`.

## RED / GREEN Test Plan

RED:

- From the unchanged completed-state disk, run the exact structured adapter regression.
- Capture `63/64`, exit `1`, failing `test_E2E_CURRENT_001_contract_entrypoint_exists`, and `AUTHORITY_MISSING`.
- Prove no live Gate mutation, candidate write, production authorization, or stdout/stderr authority is involved.

GREEN:

- In a temporary mirror, explicitly construct one closed, non-production, Gate-bound `in_progress` execution fixture.
- Ensure the fixture is isolated, deterministic, bounded, create-only where applicable, and cleaned after the run.
- Run controlled validation only through the exact `UnittestResultEnvelope/v1` path.
- Require the completed real state to continue returning `AUTHORITY_MISSING`.
- Require a wrong, duplicate, stale, or unbound execution to fail closed.
- Require the unique correctly bound fixture execution to permit controlled validation.
- Run focused F003 protocol checks (`8/8` expected), full structured adapter regression (`64/64` expected), protected-subject checks, and artifact/reparse checks.

## Validation Plan

- Run global `validate_state.py` before execution and after execution.
- Run the candidate's controlled runner tests with structured result binding.
- Verify `validation_runner.py` keeps `AUTHORITY_MISSING` for real completed state.
- Verify one and only one correctly bound `in_progress` execution is accepted.
- Verify zero-test stdout spoof remains rejected with `UNSUPPORTED_TEST_PROTOCOL`.
- Verify stdout/stderr do not determine test identity, count, or PASS.
- Verify `UnittestResultEnvelope/v1` nonce, adapter/test fingerprints, discovered IDs, `tests_run`, outcomes, and result hash remain bound.
- Verify 0 cache/compiled artifacts, 0 reparse points, and zero drift in protected subjects.
- Record all evidence under `.ai/evidence/T-0036/`.
- Stop before fresh independent rereview; register a separate future Gate for that rereview.

## Rollback And Recovery

- Record exact preimages, SHA-256, byte size, and `mtime_ns` for every later target before writing.
- Keep fixture state outside the project and delete only the verified temporary fixture root after evidence capture.
- On a failed execution, restore only approved-path changes from recorded preimages; never modify historical evidence.
- Preserve `T0036-F003: REPAIR_REQUIRED`, pending/approval boundaries, and `AUTHORITY_MISSING` behavior while recording failure evidence.
- Re-run validator, protected-boundary, cache, compiled-artifact, and reparse checks before stopping.

## Protected Subjects

- `validation_runner.py` authority and fail-closed checks
- `unittest_result_adapter.py` `UnittestResultEnvelope/v1` schema and binding
- existing F003 protocol tests and their discovered IDs
- `.ai/PROJECT.md`, `.ai/CONTRACTS.md`, `AGENTS.md`
- global Project Governor scripts and governance contracts
- prior T-0036 repair and rereview evidence
- live completed-state Gate projection and stable authority closure

## Security Invariants That Must Not Be Weakened

- `AUTHORITY_MISSING` remains the result for real completed-state controlled validation without a Gate-bound `in_progress` execution.
- Controlled validation requires exactly one correctly bound Gate-bound `in_progress` execution.
- A temporary fixture is not a real Gate, production authorization, or runtime authority.
- No production authorization may be fabricated to obtain PASS.
- stdout/stderr remain diagnostic evidence only.
- Zero-test stdout spoof remains rejected.
- Envelope nonce, adapter/test fingerprints, discovered IDs, `tests_run`, outcome fields, and canonical result hash remain verified.
- No installation, activation, runtime enablement, T-0037 creation, real-project entry, or production effect is implied.

## Later Independent Rereview

Repair execution evidence and test results are evidence only. After any approved repair execution, a fresh independent rereview must be separately registered and executed under a new explicit Gate before `T0036-F003` may be marked closed.
