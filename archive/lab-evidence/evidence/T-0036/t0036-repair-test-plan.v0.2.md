# T-0036 Repair RED -> GREEN Test Plan v0.2

Gate: `G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

Status: pending Gate revision only. No candidate or test file is changed by this plan.

## Effective Plan

This plan incorporates the unchanged v0.1 scenarios at:

- `.ai/evidence/T-0036/t0036-repair-test-plan.v0.1.md`
- SHA-256 `6D0EA9F3C4FA0BBE0579BF352CACF98CDC4881CEAEEBC0165642972C8800F769`

The scenarios below are mandatory additions. Where wording differs, v0.2 controls.

## Authority Availability And Installation Scenarios

| ID | Finding | Scenario | GREEN acceptance |
|---|---|---|---|
| AUTH-005 | F001/F002 | Query isolated CLI production capability after fail-closed repair | Reports `SECURELY_ISOLATED_AUTHORITY_LIFECYCLE_UNAVAILABLE`; never reports authority lifecycle available |
| AUTH-006 | F001/F002 | Synthetic unit adapter passes parser/CAS tests | Evidence is labelled fixture-only and cannot set production capability or installation eligibility |
| INST-001 | Boundary | All repair tests and fresh finding checks pass while no trusted host adapter exists | Installation eligibility remains `BLOCKED`; verdict cannot be `PASS_FOR_INSTALLATION_CONSIDERATION` |
| INST-002 | Boundary | Attempt to infer installability from safe rejection or controlled validation PASS | Rejected as lifecycle/authority overclaim |

## Structured State Contract Scenarios

Normative schema: `.ai/evidence/T-0036/t0036-repair-structured-state-contracts.v0.2.md`.

| ID | Contract | Scenario | GREEN acceptance |
|---|---|---|---|
| PC-001 | ProjectContinuity/v1 | Exact schema, four required protected decisions, and protected source manifest are valid | Producer and independent auditor agree on semantic/source/file hashes through separate construction paths |
| PC-002 | ProjectContinuity/v1 | `.ai/project_continuity.yaml` missing | `RECOVERY_REQUIRED`; existing HANDOFF bytes unchanged; no prose fallback |
| PC-003 | ProjectContinuity/v1 | PROJECT/CONTRACTS/PCC/CDFT source hash drifts | Validation/audit fail before HANDOFF replacement |
| PC-004 | ProjectContinuity/v1 | Semantic payload changes without semantic hash update | `PROJECT_CONTINUITY_HASH_MISMATCH` |
| PC-005 | ProjectContinuity/v1 | Unknown field or missing required protected decision ID | Closed-schema rejection |
| TR-001 | TransactionRegistry/v1 | Registry missing | Recovery HANDOFF only; `NOT_ESTABLISHED`; no Stable wording or final completion bind |
| TR-002 | TransactionRegistry/v1 | Exact quiescent registry and deterministic checkpoint without acknowledgment | `PENDING_SUCCESSOR_ACK`, not Stable |
| TR-003 | TransactionRegistry/v1 | Matching separate fixture acknowledgment added without protected-state drift | Same deterministic checkpoint ID may become `STABLE_FIXTURE_ONLY`, never production `STABLE` |
| TR-004 | TransactionRegistry/v1 | Active/in-flight/delta/partial-write/fence/generation/hash conflict | Stable rejected and blocker retained |
| TR-005 | TransactionRegistry/v1 | `fixture_only: true` registry used to claim production Stable/installability | Claim rejected |
| EM-001 | EvidenceManifest/v1 | Exact bounded manifest and streamed files | Count/total/ordered-entry/semantic/file hashes all bind |
| EM-002 | EvidenceManifest/v1 | Manifest missing | `EVIDENCE_MANIFEST_REQUIRED`; no bound success, Stable, or completion claim |
| EM-003 | EvidenceManifest/v1 | Persisted manifest bytes drift with same semantic payload | Exact file hash mismatch rejects |
| EM-004 | EvidenceManifest/v1 | Entry hash/size/mtime/count/total differs | Verification fails closed |
| EM-005 | EvidenceManifest/v1 | Writer attempts edit after create-only persistence | Immutable conflict; old bytes preserved |

## Current-project-shaped Positive End-to-end Scenario

Scenario: `E2E-CURRENT-001`.

The test must execute real candidate subprocesses, not mocks:

1. Build a temporary mirror from the current project's exact protected `.ai/PROJECT.md`, `.ai/CONTRACTS.md`, T-0036 structural records, and T-0034 PCC/CDFT sources.
2. Verify all copied source hashes against the effective v0.2 protected baseline.
3. Add exact fixture-only ProjectContinuity/TransactionRegistry/EvidenceManifest instances.
4. Start from a durable already-approved execution snapshot; do not call isolated authority transitions.
5. Run repaired candidate validator, close producer, and independent auditor successfully.
6. Verify HANDOFF direction, authority, Codex responsibility, evidence-only boundary, lifecycle, Gate projection, and hashes.
7. Verify checkpoint progresses `PENDING_SUCCESSOR_ACK -> STABLE_FIXTURE_ONLY` only after a separate matching fixture acknowledgment and with the same deterministic checkpoint ID; production Stable remains unavailable.
8. Run a Gate-bound controlled validation subprocess against the mirror's repaired validator; require actual output/exit/environment/test identity/fingerprint binding.
9. Recompute the live project and candidate protected baseline; require zero drift and zero installation/activation/runtime effects.

Required positive assertions:

- `HANDOFF_GENERATED_FROM_STRUCTURED_STATE`
- `LIFECYCLE_PROJECTED_WITHOUT_PROSE_SCAN`
- `CHECKPOINT_PENDING_ACK_BEFORE_STABLE`
- `CHECKPOINT_STABLE_FIXTURE_ONLY_AFTER_MATCHING_ACK`
- `CONTROLLED_VALIDATION_COMMAND_ACTUALLY_EXECUTED`
- `AUTHORITY_TRANSITIONS_NOT_CLAIMED_AVAILABLE`
- `INSTALLATION_ELIGIBILITY_BLOCKED`
- `LIVE_PROJECT_UNCHANGED`

## RED Requirement

Before implementation, at least PC-002, TR-001/TR-002, EM-002, AUTH-005, INST-001, and `E2E-CURRENT-001` must fail against the current candidate for the documented reason. A test that passes only because it accepts safe rejection does not satisfy the positive E2E scenario.

## GREEN And Fresh Rereview Requirement

GREEN requires every v0.1 and v0.2 scenario to pass without skipped/xfail/weakened assertions. The repair report must distinguish:

- security containment PASS;
- production authority availability BLOCKED;
- structured read/projection/checkpoint/validation usability PASS or FAIL;
- installation eligibility BLOCKED.

Fresh independent rereview must reassess F001-F009 and explicitly verify that the positive path is real while authority/installability claims remain bounded.
