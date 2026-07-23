# T-0036 F003 Repair Gate Decision Packet v0.1

Gate: `G-T-0036-REPAIR-F003-CONTROLLED-TEST-RESULT-PROTOCOL-V0-1`

Status: `pending`. This packet requests a user decision only. It does not approve or execute repair.

## Outcome

Repair only `T0036-F003`: controlled validation must stop treating unittest-like stdout as proof that tests were discovered and executed.

The repair target is a Gate-bound structured test-result protocol. The controlled runner may bind success only when the approved trusted test adapter reports actual discovery and execution through the structured channel and all adapter/test fingerprints match. Stdout and stderr remain evidence, but never determine test identity, count, or PASS.

## Exact Candidate Scope

Existing candidate paths allowed to change after approval and a later exact execution request:

- `candidates/T-0030-project-governor-repair/scripts/validation_runner.py`
- `candidates/T-0030-project-governor-repair/tests/test_project_governor_consistency.py`
- `candidates/T-0030-project-governor-repair/BOUNDARY.md`
- `candidates/T-0030-project-governor-repair/PROVENANCE.yaml`

One new candidate path is allowed:

- `candidates/T-0030-project-governor-repair/scripts/unittest_result_adapter.py`

No other candidate path is allowed.

## Required Repair Behavior

1. Remove regex-derived `test_count` and `OK` from success authority.
2. Require the Gate record to declare `test_result_protocol: UnittestResultEnvelope/v1` and the exact adapter path/fingerprint.
3. Require exact adapter invocation shape; an arbitrary Python script or unsupported command returns `UNSUPPORTED_TEST_PROTOCOL` before a success bind.
4. The adapter uses `unittest` discovery/runner APIs and writes one create-only structured envelope containing protocol version, run nonce, adapter fingerprint, discovered test IDs, `testsRun`, failures, errors, skips, unexpected successes, successful flag, start/end time, and result hash.
5. The parent runner generates the run nonce and verifies the envelope schema, nonce, adapter/test fingerprints, exact discovered IDs, `testsRun > 0`, and zero failure/error/unexpected-success counts.
6. Stdout/stderr hashes are retained as diagnostic evidence only.
7. Missing, duplicate, stale, malformed, wrong-nonce, wrong-adapter, zero-test, mismatched-count, or contradictory envelopes cannot produce `status: bound`.
8. Existing subject/protected fingerprint, timeout, output-limit, evidence-manifest, create-only, and fail-closed behavior remains intact.

Threat boundary: the adapter and test files are exact Gate-bound fingerprinted subjects. This repair prevents arbitrary zero-test command/stdout spoofing. It does not claim hostile test code running in the same interpreter is a cryptographic trust boundary.

## Acceptance

- The original zero-test stdout spoof is reproduced RED and rejected GREEN.
- A command printing `Ran N tests` and `OK` without the exact adapter/protocol is rejected.
- A valid adapter run reports the exact discovered IDs and executed count without parsing stdout.
- Zero discovered tests, wrong nonce, forged/malformed envelope, adapter drift, test drift, count mismatch, failure, error, skip-policy violation, timeout, or output limit cannot bind success.
- Existing regressions plus new F003 adversarial tests pass through the controlled runner.
- A later fresh independent rereview must reproduce the original attack and independently assess F003 closure.

## Governance And Boundary

Allowed governance projection paths during future execution:

- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/task_graph.yaml`
- `.ai/tasks/T-0036.md`
- `.ai/HANDOFF.md`
- exact additive T-0036 F003 execution evidence named in the Gate record

Explicitly forbidden:

- modify global Project Governor, including `C:/Users/Administrator/.codex/skills/project-governor/scripts/close_session.py` and `audit_handoff.py`
- combine HANDOFF generator/auditor repair with this candidate F003 repair
- modify `AGENTS.md`, `.ai/PROJECT.md`, `.ai/CONTRACTS.md`, T-0034 contracts, old evidence, `NOT_INSTALLED`, or `NOT_ACTIVATED`
- install, activate, provision live structured state, enable host identity/controller/agent/tool behavior, create T-0037, or enter a real project
- infer installation eligibility, user acceptance, project PASS, or production readiness

## Stop And Recovery

- Stop before candidate writes on any baseline drift, scope ambiguity, or unsupported protocol requirement.
- Approval records the decision only. Repair execution requires a later distinct exact request.
- Preserve truthful failure evidence; do not weaken tests or delete historical findings.
- Stop after repair evidence. Fresh independent rereview requires another separate Gate.
- Installation remains `BLOCKED` regardless of F003 repair because production authority and live structured-state gaps remain.

## Decision Phrases

Approval:

`批准 G-T-0036-REPAIR-F003-CONTROLLED-TEST-RESULT-PROTOCOL-V0-1`

Rejection:

`拒绝 G-T-0036-REPAIR-F003-CONTROLLED-TEST-RESULT-PROTOCOL-V0-1`

Approval is not execution. Later exact execution phrase:

`执行已批准的 G-T-0036-REPAIR-F003-CONTROLLED-TEST-RESULT-PROTOCOL-V0-1`
