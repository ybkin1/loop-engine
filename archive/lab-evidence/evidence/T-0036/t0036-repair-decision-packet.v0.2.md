# T-0036 Repair Gate Decision Packet v0.2

Gate: `G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

Status: `pending`. Revision only; no approval or repair execution.

## Effective Packet And Precedence

This v0.2 document normatively revises and incorporates the unchanged portions of:

- `.ai/evidence/T-0036/t0036-repair-decision-packet.v0.1.md`
- SHA-256 `A5129998A359C3981080EA9532F99DEC5324244067FFF45F39266BB56D7B6EA8`

Where v0.1 and v0.2 differ, v0.2 controls. Exact candidate paths, nine-finding repair mappings, BOUNDARY/PROVENANCE treatment, non-weakening rules, controlled runner requirements, rollback policy, fresh independent rereview, decision phrases, and all forbidden effects remain in force unless explicitly revised below.

## F001/F002 Outcome And Installation Eligibility

The current bounded target for F001/F002 is:

`SECURELY_ISOLATED_AUTHORITY_LIFECYCLE_UNAVAILABLE`

This means:

- the exploitable paths that accept caller inline JSON, request IDs, filenames, or exact phrases as authority are removed or fail closed;
- the isolated production CLI cannot create, approve/reject, or start execution through a trustworthy user authority lifecycle;
- returning `USER_DECISION_REQUIRED` is a security boundary, not restored functional availability;
- synthetic test authority events prove parsing/CAS behavior only and never prove a trustworthy Codex host identity.

Installation effect:

- `installation_eligibility_after_repair: BLOCKED`.
- A repair PASS may qualify the artifact only for fresh isolated rereview; it must not return `PASS_FOR_INSTALLATION_CONSIDERATION` while production authority lifecycle is unavailable.
- Installation eligibility can be reconsidered only after separate user Gates authorize and validate a trustworthy Codex host message/turn adapter, live structured-state provisioning/migration, controller writer/acknowledgment responsibilities where required, fresh independent rereview of all nine findings plus the new integration surfaces, and then a separate installation Gate with exact diff and rollback.
- Fail-closed safety must not be described as a complete Project Governor replacement or operational authority implementation.

## Normative Structured State Contracts

The exact schemas are defined in:

`.ai/evidence/T-0036/t0036-repair-structured-state-contracts.v0.2.md`

### ProjectContinuity/v1

- Normative sources: `PCC-2026-07-16-R1`, `.ai/PROJECT.md`, `.ai/CONTRACTS.md`, and the CDFT L0/L1/L2 ownership rules.
- Persistence: `.ai/project_continuity.yaml`.
- Writer: separately authorized L0 continuity registrar only; candidate producer/auditor/validator are readers.
- Missing: `RECOVERY_REQUIRED`; leave existing HANDOFF unchanged; no prose fallback.
- Binding: ordered source-manifest hash, semantic payload hash, and exact persisted file hash are all required in HANDOFF/checkpoint.

### TransactionRegistry/v1

- Normative sources: `CDFT-2026-07-16-R1` sections 5-8 and PCC checkpoint/successor sections 6-7.
- Persistence: `.ai/transaction_registry.yaml`.
- Writer: separately authorized L0 transaction owner/controller runtime; successor acknowledgment writer is separate. Repair candidate components are readers only.
- Missing: recovery HANDOFF may state `checkpoint_status: NOT_ESTABLISHED`; Stable wording and final completion binding are forbidden.
- Binding: source contract hash, complete registry semantic hash, and exact persisted file hash. Stable additionally requires quiescence, generation fence, deterministic checkpoint ID, and matching successor acknowledgment.

### EvidenceManifest/v1

- Normative sources: PCC evidence/checkpoint requirements, CDFT fan-in and transaction guards, T0036-F009, and this Gate's hard resource bounds.
- Persistence template: `.ai/evidence/<task-id>/evidence-manifest.v1.yaml`; exact repair execution path `.ai/evidence/T-0036/t0036-repair-evidence-manifest.v1.yaml`.
- Writer: authorized L1 evidence aggregator or L0 repair executor, create-only and atomic. Runner/producer/auditor are readers.
- Missing: `EVIDENCE_MANIFEST_REQUIRED`; diagnostic command execution may occur only if Gate-bound, but no `status: bound`, Stable checkpoint, or completion claim is permitted.
- Binding: exact persisted manifest hash, canonical ordered-entry hash, manifest semantic hash, file count, total bytes, and every streamed subject hash/size/mtime.

This Gate does not authorize creating the live `.ai/project_continuity.yaml` or `.ai/transaction_registry.yaml`. Temporary fixtures may exercise the schemas; live provisioning is a separate future Gate.

## Protected Source Revision

The effective protected baseline is the immutable v0.1 baseline plus:

- `.ai/PROJECT.md`
- `.ai/CONTRACTS.md`
- `.ai/evidence/T-0034/project-continuity-contract.v0.2.md`
- `.ai/evidence/T-0034/controller-data-flow-transaction-contracts.v0.2.md`

Exact SHA-256, size, and `mtime_ns` values are in `.ai/evidence/T-0036/t0036-repair-candidate-and-protected-baseline.v0.2.yaml`. All four paths are read-only and forbidden repair targets.

## Current-project-shaped Positive End-to-end Acceptance

Scenario ID: `E2E-CURRENT-001`.

Purpose: prove that the repaired candidate has a real positive path for continuity projection, lifecycle reading, checkpoint progression, audit, and controlled validation, rather than only returning safe rejection.

Exact flow:

1. Create a temporary project mirror; do not write the live project.
2. Copy the current project's protected `.ai/PROJECT.md`, `.ai/CONTRACTS.md`, T-0036 task/state/Gate/task-graph shapes, and the two T-0034 normative contracts into the mirror using explicit paths and verified hashes.
3. Add fixture-only `ProjectContinuity/v1`, `TransactionRegistry/v1`, and `EvidenceManifest/v1` instances that satisfy the exact schemas and bind those copied anchors. The registry is explicitly `fixture_only: true`; it cannot establish production authority or installation eligibility.
4. Begin from an already durable approved-execution lifecycle snapshot. Do not invoke create/approve/execute authority transitions and do not inject a trusted-host adapter.
5. Run repaired `validate_state.py`; require structural success for the mirror.
6. Run repaired `close_session.py`; require a HANDOFF that exactly carries product direction, user authority, Codex delivery responsibility, evidence-only boundary, canonical Gate projection, lifecycle classifications, and all structured hashes.
7. Run independent repaired `audit_handoff.py`; require success without calling the producer's expected-state builder.
8. Produce a deterministic checkpoint candidate. Before acknowledgment it must be `PENDING_SUCCESSOR_ACK`, not Stable. Add a separate fixture successor acknowledgment for the same ID/generation/recovered-state hash, rerun without protected-state drift, and require `STABLE_FIXTURE_ONLY`; production `STABLE` remains unavailable.
9. Execute a Gate-bound controlled validation subprocess against the mirror's repaired validator. Bind actual argv, environment hashes, stdout/stderr hashes, exit code, executable/test identity, timestamps, evidence manifest, and pre/post subject fingerprints.
10. Assert no live project path, candidate marker, global Project Governor path, PATH/PYTHONPATH, installation, activation, or runtime discovery state changed.

Positive acceptance does not contradict F001/F002: it proves read/projection/audit/checkpoint/validation usability from a pre-existing durable lifecycle snapshot; it does not claim that the isolated candidate can acquire trustworthy user authority.

## T-0036 Historical Boundary Clarification

The T-0036 task's old prohibition on creating a repair Gate belonged only to the 2026-07-18 review-registration stage. It prevented the review-registration action from chaining into repair. That stage completed before the user's later explicit authorization to register the current repair Gate. The task text must preserve this history while stating that it does not prohibit the current pending Gate revision.

## Additional Future Execution Evidence

The exact future execution evidence allowlist is extended by:

- `.ai/evidence/T-0036/t0036-repair-evidence-manifest.v1.yaml`
- `.ai/evidence/T-0036/t0036-repair-current-project-e2e.v0.2.md`
- `.ai/evidence/T-0036/t0036-repair-structured-state-contract-results.v0.2.md`

No live structured-state instance, host adapter, controller runtime, installation, activation, T-0037, or real-project action is added to scope.

## Decision Boundary

Approval remains exactly:

`批准 G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

Rejection remains exactly:

`拒绝 G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

Approval is not execution. A later distinct message must still request:

`执行已批准的 G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`
