# T-0036 Repair Gate Decision Packet v0.1

Gate: `G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

Status: `pending`. This packet requests a user decision only. It does not authorize or perform repair.

## Outcome And Hard Boundary

The proposed execution repairs all nine T-0036 findings only inside the isolated candidate, updates additive T-0036 execution evidence and the minimum current governance projection, then stops. It does not install, activate, enable, or expose the candidate.

The isolated CLI has no trustworthy Codex host user-message or turn-identity source. Therefore the repair must make every authority-bearing CLI transition fail closed with `USER_DECISION_REQUIRED` unless a future, separately gated host adapter supplies a verifiable authority event. This Gate does not authorize such an adapter, host integration, controller runtime, agent orchestration, or a fabricated identity mechanism.

## Exact Candidate Paths Allowed After Approval And A Later Exact Execution Request

Existing paths allowed to change:

- `candidates/T-0030-project-governor-repair/BOUNDARY.md`
- `candidates/T-0030-project-governor-repair/PROVENANCE.yaml`
- `candidates/T-0030-project-governor-repair/scripts/governor_lib.py`
- `candidates/T-0030-project-governor-repair/scripts/governance_action.py`
- `candidates/T-0030-project-governor-repair/scripts/close_session.py`
- `candidates/T-0030-project-governor-repair/scripts/validate_state.py`
- `candidates/T-0030-project-governor-repair/scripts/audit_handoff.py`
- `candidates/T-0030-project-governor-repair/tests/test_project_governor_consistency.py`

New candidate paths allowed:

- `candidates/T-0030-project-governor-repair/scripts/authority_records.py`
- `candidates/T-0030-project-governor-repair/scripts/validation_runner.py`
- `candidates/T-0030-project-governor-repair/scripts/continuity_producer.py`
- `candidates/T-0030-project-governor-repair/scripts/continuity_auditor.py`
- `candidates/T-0030-project-governor-repair/scripts/evidence_manifest.py`
- `candidates/T-0030-project-governor-repair/scripts/transaction_registry.py`

No other candidate path is allowed. In particular, `NOT_INSTALLED` and `NOT_ACTIVATED` are protected and must remain byte-for-byte identical to the registration baseline.

## Exact Governance And Evidence Paths Allowed During Future Repair Execution

Governance projections allowed to change:

- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/task_graph.yaml`
- `.ai/tasks/T-0036.md`
- `.ai/HANDOFF.md`

Additive evidence allowed to be created only under these exact paths/prefixes:

- `.ai/evidence/T-0036/t0036-repair-execution-request.v0.1.md`
- `.ai/evidence/T-0036/t0036-repair-preflight.v0.1.md`
- `.ai/evidence/T-0036/t0036-repair-red-results.v0.1.md`
- `.ai/evidence/T-0036/t0036-repair-implementation-report.v0.1.md`
- `.ai/evidence/T-0036/t0036-repair-commands.v0.1.md`
- `.ai/evidence/T-0036/t0036-repair-test-results.v0.1.md`
- `.ai/evidence/T-0036/t0036-repair-final-validation-manifest.v0.1.yaml`
- `.ai/evidence/T-0036/t0036-repair-final-validation.stdout.txt`
- `.ai/evidence/T-0036/t0036-repair-final-validation.stderr.txt`
- `.ai/evidence/T-0036/t0036-repair-protected-boundary-postcheck.v0.1.md`
- `.ai/evidence/T-0036/t0036-repair-changed-path-manifest.v0.1.md`
- `.ai/evidence/T-0036/t0036-repair-failure-record.v0.1.md` only on failure
- `.ai/evidence/T-0036/repair-preimages/` for exact pre-write recovery copies of the eight existing candidate files above

No old T-0035 or T-0036 evidence may be rewritten or deleted.

## Finding-to-Repair Matrix

### T0036-F001: authority evidence is not content/hash/identity bound

Root cause: `load_inline_json_record()` accepts caller JSON independently of the cited evidence file; existence is treated as provenance.

Repair behavior:

- Remove `--action-record-json`, `--action-evidence`, `--command-evidence-json`, and `--command-evidence-ref` from authority and validation paths.
- Load one immutable on-disk `AuthorityEvent/v2` envelope; bind canonical content SHA-256, evidence file SHA-256, event ID, actor ID, host message ID, host turn ID, exact user text, predecessor event ID, timestamp, task ID, Gate ID, and requested transition.
- Require a trusted authority adapter attestation. The isolated candidate ships no such adapter; its CLI returns `USER_DECISION_REQUIRED` before any canonical write.
- Never treat request ID, inline JSON, filename, exact phrase alone, or caller assertions as identity.

Candidate files: `governance_action.py`, `authority_records.py`, `governor_lib.py`, tests.

Acceptance: mismatched content/hash/event fields, copied evidence, changed cited bytes, inline JSON, unknown adapter, and absent host identity all produce no write and a closed failure; the production CLI cannot claim authority success in isolation.

### T0036-F002: create -> approve -> execute can cross one user turn through processes

Root cause: argparse mutual exclusion is process-local and request IDs are caller-selected.

Repair behavior:

- Authority events require a trusted monotonic host turn/message identity and predecessor chain.
- Transition persistence uses an atomic compare-and-swap against Gate lifecycle revision and last consumed authority event.
- Create, approval/rejection, and execution must reference strictly later distinct trusted host events; same event, same turn, replay, forked predecessor, stale revision, or concurrent loser is rejected.
- Because no host identity adapter exists in the isolated candidate, all production authority transitions return `USER_DECISION_REQUIRED`; synthetic events are permitted only inside explicitly labelled unit fixtures and are not evidence of host trust.

Candidate files: `authority_records.py`, `transaction_registry.py`, `governance_action.py`, `governor_lib.py`, tests.

Acceptance: three subprocesses with distinct caller request IDs cannot advance the lifecycle; replay, same-turn, concurrent approval, concurrent execute, stale predecessor, and CAS-race tests all leave one truthful state or no write.

### T0036-F003: final validation trusts self-reported command success

Root cause: the binder accepts caller-provided argv, timestamps, exit code, and test count without executing the command.

Repair behavior:

- Replace snapshot-plus-self-report binding with one controlled `run-final-validation` path.
- Read the exact argv, working directory, allowed environment, subject manifest, output paths, and result path from the approved Gate record, not CLI JSON.
- Execute the command with `shell=False`, an explicit minimal environment, timeout, bounded stdout/stderr capture, and no inherited `PYTHONPATH`.
- Bind actual argv; executable and test-subject fingerprints; sanitized environment key/value hashes; stdout/stderr SHA-256 and byte counts; actual exit code; strict unittest test identity/count; start/end timestamps; and pre/post target/protected fingerprints.
- A timeout, non-zero exit, malformed test identity, truncated output, subject drift, or result-path conflict cannot produce `status: bound`.

Candidate files: `validation_runner.py`, `governance_action.py`, `governor_lib.py`, tests.

Acceptance: a caller cannot inject exit code or test count; a fake success record is ignored/rejected; an intentionally failing test produces actual failure evidence and no bound success manifest.

### T0036-F004: HANDOFF omits canonical direction and authority semantics

Root cause: `close_session.py` renders prose directly from partial files and the auditor checks headings rather than normalized protected semantics.

Repair behavior:

- Define required `ProjectContinuity/v1` structured state containing project direction, north star, user authorities, Codex responsibility, evidence-only boundary, lifecycle, and source fingerprints.
- `continuity_producer.py` consumes only the normalized structure plus canonical structured task/Gate/state records.
- Missing normalized state causes `RECOVERY_REQUIRED` and no apparently valid HANDOFF.
- HANDOFF embeds a closed-world structured continuity block and hashes its source records.
- `continuity_auditor.py` independently parses the source records and compares protected semantics without calling the producer builder.

Candidate files: `continuity_producer.py`, `continuity_auditor.py`, `close_session.py`, `audit_handoff.py`, `validate_state.py`, `governor_lib.py`, tests.

Acceptance: omitted or changed project direction, user authority, Codex delivery responsibility, or evidence-only boundary is rejected. Prose with the same words cannot substitute for the structured block.

### T0036-F005: `state.current_gate_id` contradicts HANDOFF Gate projection

Root cause: the producer selects the latest approved Gate after canonical state clears `current_gate_id`.

Repair behavior:

- Keep `state.current_gate_id` meaning strictly `pending decision Gate or null`.
- Structured HANDOFF copies that field exactly.
- Add separate `approved_execution_gate_id` and lifecycle revision fields derived from structured Gate state when applicable.
- The independent auditor reads state and gates directly and rejects cross-field contradictions.

Candidate files: `continuity_producer.py`, `continuity_auditor.py`, `governor_lib.py`, `close_session.py`, `audit_handoff.py`, tests.

Acceptance: null current Gate plus an approved Gate is represented as null plus the separate approved execution field; any producer mutation is caught by the auditor.

### T0036-F006: Unverified relies on `TBD` text scanning

Root cause: lifecycle uncertainty is inferred from five prose files and may collapse to `none`.

Repair behavior:

- Derive `verified`, `unverified`, `not_performed`, and `not_authorized` from normalized lifecycle flags, Gate state, review verdict, acceptance state, install/activate markers, required evidence presence, and manifest verification.
- Remove `TBD` scanning from authority-bearing completion semantics.
- Permit `unverified: []` only when every required lifecycle field is explicit, consistent, and supported by verified evidence; otherwise list stable machine codes.

Candidate files: `continuity_producer.py`, `continuity_auditor.py`, `close_session.py`, `audit_handoff.py`, tests.

Acceptance: review not rerun, user acceptance absent, installation/activation not performed, missing evidence, or unknown lifecycle fields can never render as prose `none`.

### T0036-F007: Stable Checkpoint is emitted without stability proof

Root cause: active transactions are hard-coded empty; in-flight actors and deltas do not block; the continuity hash covers only four fields.

Repair behavior:

- Read a canonical `TransactionRegistry/v1` with generation, active transactions, in-flight actors, unconsumed deltas, partial-write markers, fence, and consumer acknowledgment.
- Missing/unverifiable registry or any non-empty blocking set yields `checkpoint_status: NOT_ESTABLISHED`; the document must not be titled or labelled Stable Checkpoint.
- Stable status requires zero active/in-flight/delta/partial-write entries, a matching generation fence, durable revision/hash bindings, and explicit consumer acknowledgment.
- Bind the complete protected continuity, task scope, authority, transaction registry, and approved evidence-manifest hashes.

Candidate files: `transaction_registry.py`, `continuity_producer.py`, `continuity_auditor.py`, `close_session.py`, `audit_handoff.py`, tests.

Acceptance: absent registry, active transaction, in-flight actor, unconsumed delta, partial write, stale generation, missing fence, or missing acknowledgment never produces a Stable Checkpoint.

### T0036-F008: unrelated trust boundaries share `governor_lib.py`

Root cause: one module owns transaction writes, authority, evidence hashing, HANDOFF production/audit expectations, parsing, paths, and validation binding; producer and auditor share expected-state construction.

Repair behavior:

- Move authority, validation runner, producer, auditor, evidence manifest, and transaction registry responsibilities to the six named modules.
- Retain only narrow serialization, path, YAML, and atomic-write primitives in `governor_lib.py`.
- Producer and auditor may share primitive schema constants only; they must have separate source traversal and expected-state construction paths.
- Add a correlated-failure test that monkey-patches or corrupts producer output and proves the auditor still rejects it.

Candidate files: all six new modules, `governor_lib.py`, entry scripts, tests.

Acceptance: import/dependency inspection shows no producer call into auditor or auditor call into producer, and no shared expected-state builder; old public entry scripts still have explicit narrow wiring.

### T0036-F009: evidence hashing is unbounded and can cross reparse boundaries

Root cause: recursive `rglob('*')` plus whole-file `read_bytes()` has no approved subject set or resource bounds.

Repair behavior:

- Require `EvidenceManifest/v1` with exact project-relative paths, expected SHA-256 and size, file count, per-file limit, total-byte limit, and manifest authority/reference.
- Defaults for this candidate: at most 256 files, 16 MiB per file, and 256 MiB total; the manifest may set lower limits but never higher without another approved change.
- Reject absolute paths, traversal, alternate streams, duplicates/case collisions, directories, symlinks, junctions, and any reparse point on every ancestor and target.
- Resolve containment, open each regular file, compare pre/open/post identity and size, and stream SHA-256 in bounded 1 MiB chunks.
- Bind file count, total bytes, manifest hash, and ordered entry hashes into checkpoint/final evidence.

Candidate files: `evidence_manifest.py`, `continuity_producer.py`, `continuity_auditor.py`, `validation_runner.py`, `governor_lib.py`, tests.

Acceptance: oversized count/file/total, undeclared file, mutation during read, duplicate/case collision, reparse ancestor/target, and external escape are rejected without Stable Checkpoint or bound validation.

## BOUNDARY, PROVENANCE, And Isolation Markers

- `BOUNDARY.md`: append the approved repair Gate ID, exact post-repair inventory, module ownership map, fail-closed host-identity limitation, and unchanged installation/activation exclusions. Do not erase T-0033/T-0035 history.
- `PROVENANCE.yaml`: append a `t0036_repair` lineage record with pre/post fingerprints, Gate/execution evidence, module inventory, test result, and non-claims. Do not rewrite prior lineage.
- `NOT_INSTALLED`: protected, no write, final SHA-256 must remain `CA19715176E4FD328515F5ECD36D1EB7B91AF7C70BC767C3F61EF9A52B2AB7E5`.
- `NOT_ACTIVATED`: protected, no write, final SHA-256 must remain `9BBB093D9C5E6129B1CE440575E9D289366FCDC7223C944532376D0C2E033EAE`.

## RED -> GREEN Verification Plan

The detailed scenario list is in `t0036-repair-test-plan.v0.1.md`.

RED phase, after adding tests but before implementation, must demonstrate failures for all nine findings. Existing tests may be updated only where they assert the vulnerable behavior; no historical finding test may be deleted, skipped, weakened, or have severity lowered.

GREEN requires:

- all behavior, negative, adversarial, concurrency, failure-recovery, boundary, and regression tests pass;
- controlled runner actually runs the exact Gate-bound command;
- candidate and global validators/audits are classified as mechanical evidence only;
- final candidate inventory contains exactly the approved existing and new paths, no cache/compiled artifact, and no reparse point;
- all protected source fingerprints, `AGENTS.md`, markers, PATH/PYTHONPATH discovery, and global Project Governor files remain unchanged.

## Exact Controlled Final-validation Plan

- argv: `C:\Python312\python.exe -B C:\Users\Administrator\.codex\loop-engine-lab\candidates\T-0030-project-governor-repair\tests\test_project_governor_consistency.py -v`
- cwd: `C:\Users\Administrator\.codex\loop-engine-lab\candidates\T-0030-project-governor-repair`
- timeout: 180 seconds
- environment: process-local `PYTHONDONTWRITEBYTECODE=1`, `PYTHONHASHSEED=0`, `PYTHONIOENCODING=utf-8`; inherited `PYTHONPATH` removed; any required `SystemRoot`, `TEMP`, `TMP`, and executable search values are recorded by canonical SHA-256 rather than exposed as secrets
- stdout/stderr: bounded capture, immutable evidence files, SHA-256 and byte counts in the final manifest
- test identity: exact Python executable fingerprint, exact test-file fingerprint, exact argv, strict unittest `Ran N tests` parse, and actual exit code
- subjects: every approved candidate file plus the protected manifest subjects, each with pre/post SHA-256, size, and `mtime_ns`

## Preflight, Stop Conditions, And Failure Recovery

Before the first candidate write, future execution must:

1. rerun global `validate_state.py` and confirm this is the only pending/approved repair Gate as appropriate;
2. recompute every registration baseline subject and stop on any SHA-256/size/mtime/inventory/reparse mismatch;
3. confirm a distinct later exact execution request exists after Gate approval;
4. create exact recovery preimages under `.ai/evidence/T-0036/repair-preimages/` and hash them;
5. confirm no installation, activation, runtime discovery, or real-project effect is in scope.

Immediate stop results:

- `BLOCKED`: baseline drift, unexpected path, duplicate/contradictory Gate, protected-path change, partial write, test infrastructure failure, uncontrolled command, evidence conflict, or validation ambiguity.
- `USER_DECISION_REQUIRED`: host identity/turn verification is needed, normalized continuity/transaction state would require live controller enablement, or any P1 cannot be repaired without host platform, agent orchestration, skill/MCP/plugin/hook/protocol, or scope expansion.

On failure, preserve truthful partial state and additive failure evidence. Do not delete new files or restore preimages automatically. Any rollback/recovery write requires a separate explicit user Gate; the preimages and baseline make that later recovery deterministic.

## Independent Rereview And Final Stop

After a future approved and separately requested repair execution:

- produce the implementation report, final fingerprints, controlled-runner manifest, and per-finding verification result;
- stop before independent rereview;
- a fresh independent reviewer in a later session must re-freeze the repaired candidate and review all F001-F009 from source and adversarial tests, not only changed lines;
- the reviewer must treat repair evidence, validator success, and tests as evidence only.

A repair PASS does not authorize installation, activation, T-0037, runtime/tool enablement, real-project entry, deployment, migration, user acceptance, project PASS, or product acceptance.

## Decision And Later Execution Phrases

Approval: `批准 G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

Rejection: `拒绝 G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

Approval records a decision only. A later independent message must request exactly:

`执行已批准的 G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`
