# T-0035 Implementation Decision Packet v0.1

## Decision Boundary

This packet proposes a candidate-only implementation. It creates no implementation, installation, activation, runtime enablement, controller/orchestration behavior, downstream task, or real-project authority.

Gate creation is not approval. Approval is not execution. A later exact execution request is required after approval.

## Source Of Truth

| Source | Role | SHA-256 |
|---|---|---|
| `.ai/evidence/T-0031/review-findings.v0.1.md` | Reviewed defects and boundary finding | `F6341CB7D1E9B171F5A5A3E7EB5EC67407EB75E98392F5151DD3296A8C996F98` |
| `.ai/evidence/T-0031/repair-planning.v0.1.md` | Repair order, action record, HANDOFF contract, final evidence binding | `E7C2946835A099232CDF24F73F05E2D69C9E060AE931DBB58F0ECCF01D49DB95` |
| `.ai/evidence/T-0030/implementation-scope.v0.1.md` | Original implementation scope | `E14E9B3AA9F212160CAD22001EB84676CD9ADADB400C4A233932280DF03E7489` |
| `.ai/evidence/T-0030/test-and-acceptance-plan.v0.1.md` | Original regression obligations | `BE050F7635EB20E4186BF26FC494F4560C33DCD11537E8F485CA980285A403A3` |
| `.ai/evidence/T-0033/isolated-candidate-activation-boundary-recovery.decision-packet.v0.1.md` | Candidate-only boundary | `EBC5208B8AF4C6852CCE0AA5D78B58E2FD562EC3BBB1F6EA95BB15B195CE5BAB` |
| `candidates/T-0030-project-governor-repair/PROVENANCE.yaml` | Copy lineage and recovery record | `648550FB2D02B121C5740AA611C7ADC74769D243451C5D5D955E72AB6918011C` |
| `candidates/T-0030-project-governor-repair/BOUNDARY.md` | Not-installed/not-activated boundary | `C5F24330B13E6A2BF0C2CAE8C8792AA58584433675BFEA4721858E683D1C56EB` |
| `.ai/evidence/T-0034/downstream-program-plan.v0.1.md` | T-0035/T-0040 separation | `1949EED355B3F87C8322B150811EABD959FE0837A35C1E6FA1CCB1FF89C71146` |
| `.ai/evidence/T-0034/t0034-requirements-baseline.v0.2.md` | Canonical requirements `T-0034-REQ-2026-07-16-R1` | `41931EE234718792F6CE386EBBD1F300FBA386EAF8ACE7F62EC542054FB6F1B7` |
| `.ai/evidence/T-0034/t0034-requirements-baseline.v0.3.md` | Additive exact-byte hash framing | `E99F7FA67FC56A2F4734E5E73F8D9A20B3CEC9AF330E8828E4BDD423FE0F4540` |
| `.ai/evidence/T-0034/project-continuity-contract.v0.2.md` | Canonical continuity/checkpoint owner `PCC-2026-07-16-R1` | `EDCE58BBE0D74744AFB5803FD2CFDCBC361CA084F78DE9C83E77CAF961832766` |
| `.ai/evidence/T-0034/handoff-writing-standard.v0.1.md` | HANDOFF structure and successor semantics | `5DF3B70ACA44B3593111F002AD3C132BA0374B447587E1E6D86A8BF3D64B416C` |
| `.ai/evidence/T-0034/controller-agent-interface-schemas.v0.2.md` plus v0.3/v0.4 additive chain | `Checkpoint/v1.0` reference and additive compatibility constraints | v0.2 `3F3D8C6905E476E35300DC189BA9A69F3722FBADDDC6659AA481716CA196508D`; v0.3 `616BC96184332318FD0CF87BD1143D5BAC212BE74F2D35647D9D8910B5A2D2BE`; v0.4 `3D60C80C48C503ED42BF2F6E75347C3EA6D96C27D6EB0F9C0E13B8E64E544C4F` |
| `.ai/evidence/T-0034/t0034-l0r3-v0-4-fresh-independent-rereview.v0.1.md` | Final evidence-only PASS for frozen v0.4 slice | `745EB5A419498011377627B6BB1927A170E7F1ABB416E2D862A2F79FE5EA1BC8` |
| `.ai/evidence/T-0034/t0034-closeout-freeze-baseline.v0.1.md` and closeout evidence | Frozen closeout chain; no user acceptance/project PASS | freeze `0920B08C5BF97B29195F01B8FFE599684B5D8BA64A3F379297E671941D7D83A6` |

## Selected Minimal Interface Shape

One new public candidate CLI is proposed:

`candidates/T-0030-project-governor-repair/scripts/governance_action.py`

It has mutually exclusive subcommands and exits after exactly one action:

- `create-pending-gate`: validate a structured action record and pending Gate packet before atomic writes.
- `decide-pending-gate --decision approved|rejected`: require a pending Gate and a distinct explicit user decision record; approval and rejection are variants of the existing pending-Gate decision action class.
- `start-approved-execution`: require an approved Gate, approval evidence, and a later distinct exact execution-request record before atomic execution-start writes.
- `snapshot-final-validation`: record target/test path, SHA-256, size, and `mtime_ns` immediately before final validation.
- `bind-final-validation`: require successful command evidence and test count; recompute every fingerprint; fail if any target/test fingerprint changed after the snapshot; atomically finalize one immutable manifest.

Shared parsing, closed-world field validation, action-chain checks, path containment, exact-byte hashing, transactional writes, structured HANDOFF/checkpoint rendering, and manifest verification remain in `scripts/governor_lib.py`.

## Why This Option Was Selected

| Option | Decision | Reason |
|---|---|---|
| One `governance_action.py` with mutually exclusive subcommands | selected | Smallest public surface; one validation boundary; one action per process prevents same-call chaining; reuses transactional helpers. |
| Separate transition and validation-manifest CLIs | rejected | Cleaner physical separation but adds another public entrypoint and duplicates argument/error/atomic-write behavior. |
| Add write subcommands to `validate_state.py` or `close_session.py` | rejected | Violates read-only/renderer responsibilities and makes familiar validation/closeout commands unsafe to invoke. |
| Copy/extend global `new_task.py` | rejected | `new_task.py` creates tasks, not Gate decisions; it performs sequential non-atomic writes and would import unrelated template behavior. |
| Library helpers only | rejected | Repeats T-0031's defect: direct unit tests without a real production entrypoint. |

Risk accepted for proposal: one CLI contains two related concerns, lifecycle transitions and evidence binding. The mitigation is mutually exclusive subcommands, shared closed-world schemas, one action per process, and tests that prove no transition chaining.

## Exact Future Candidate Paths

| Path | Responsibility |
|---|---|
| `scripts/governor_lib.py` | Shared `GovernanceAction/v1`, structured next-action/checkpoint, transition guards, exact path/hash/mtime fingerprints, atomic write and manifest binding. |
| `scripts/governance_action.py` (new) | Only Gate lifecycle and final-validation action boundary for Gate create/decision/execution-start and two-stage final-validation binding. |
| `scripts/close_session.py` | Existing HANDOFF/state writer; render structured next-action and stable checkpoint, and validate current action mode before writing. |
| `scripts/validate_state.py` | Read-only validation of action evidence chain, gate/task/state projections, checkpoint/manifest consistency. |
| `scripts/audit_handoff.py` | Parse and compare the structured contract; remove English-marker dependence. |
| `tests/test_project_governor_consistency.py` | Explicit-candidate-path unit/integration/failure tests; no global script import or implicit discovery. |
| `PROVENANCE.yaml` | Append T-0035 implementation lineage, new-file origin, final fingerprints, and explicit no-install/no-activate result. |
| `BOUNDARY.md` | Additive update from 9 to 10 approved files and retain all isolation prohibitions. |

`NOT_INSTALLED` and `NOT_ACTIVATED` remain immutable.

## Requirement-To-Target-To-Test Mapping

| Requirement | Candidate targets | Required deterministic tests and acceptance |
|---|---|---|
| `T0031-P0-ACTIVATION-BOUNDARY` | all eight exact paths; lineage/boundary updates | Explicit candidate imports/commands only; ten files, no reparse/cache/compiled artifacts; markers unchanged; all protected global hashes unchanged; PATH/PYTHONPATH/discovery unchanged. |
| `T0031-P1-ACTION-ENTRY` | `governor_lib.py`, `governance_action.py`, `validate_state.py`, test | Positive tests for create, approve, reject, execute-start; negative tests for wrong Gate state, missing user record, missing exact execution request, same-request reuse, same-process chaining, path escape, and partial-write rollback. No write occurs before guard PASS. |
| `T0031-P1-HANDOFF-CONTRACT` | `governor_lib.py`, `close_session.py`, `validate_state.py`, `audit_handoff.py`, test | Parse required structured fields; compare task/gate/status/mode/result/scope/stop condition; accept Chinese exact prompts; reject missing, unknown, stale, contradictory fields and marker-only prose. |
| `T0031-P1-FINAL-EVIDENCE` | `governor_lib.py`, `governance_action.py`, test | Snapshot then bind command/exit/test-count/target/test fingerprints; mutation of hash or `mtime_ns` after snapshot returns stale-evidence failure; manifest absent means completion is rejected. |
| `T0031-P2-HISTORICAL-SEPARATION` | no candidate repair target; validation exclusion boundary only | Existing history is not rewritten; fixtures prove unrelated historical states are reported, not modified. |
| `T0031-P2-STATUS-VOCABULARY` | `governor_lib.py`, `validate_state.py`, test | Only supported task statuses; pending Gate uses task `active`; approve uses `approved_not_started`; execution uses `in_progress`; rejection uses `rejected`. |
| `T0034-OUT02-HANDOFF-CHECKPOINT` / `PCC-2026-07-16-R1` | `governor_lib.py`, `close_session.py`, `audit_handoff.py`, test | Structured checkpoint carries IDs/revision/hashes/active transactions/in-flight actors/findings/evidence hash/next action/attestation/time; missing protected field fails; stable checkpoint requires no unrecorded write. |
| `T0034-AUTH-LIFECYCLE` | `governor_lib.py`, `governance_action.py`, validators, test | Closed-world allowed effects; no inferred approval; design/implementation/install/activate/accept/close remain separate; evidence never upgrades authority. |
| `T0034-v0.3/v0.4-ADDITIVE-INTEGRITY` | preflight and final evidence logic only | Canonical source files are verified by exact bytes/SHA-256 with no trimming/normalization; v0.4 Finding/Verdict runtime and controller packets are explicitly not implemented. |

## Approved Continuity Slice Versus Deferred Controller Slice

Included in T-0035 proposal:

- deterministic structured next-action contract;
- stable checkpoint representation and validation;
- exact scope/authority/evidence hashes;
- explicit successor-facing fields and Chinese copyable prompt;
- fail-closed missing/conflicting fields.

Deferred to T-0040 and later:

- L0/L1/L2 dispatch, agent execution, fan-out/fan-in runtime;
- leases, generation fencing services, controller rotation runtime;
- TaskPacket/AuditPacket/RepairPacket transports;
- Finding/Verdict runtime, neutral audit loop, automatic repair loop;
- subagent, automation, plugin, hook, skill, MCP or protocol enablement.

## Validation Plan For Later Implementation

1. Verify every registration baseline and source-chain hash before writes; any mismatch is `BLOCKED`.
2. Verify only the eight exact candidate paths are touched; the new CLI is absent before execution.
3. Run source compilation through in-memory `compile()` only, not `py_compile`.
4. Run tests with `PYTHONDONTWRITEBYTECODE=1`, `python -B`, and explicit candidate test/script paths; child processes inherit suppression.
5. Run the explicit candidate `validate_state.py` and `audit_handoff.py`; never invoke implicitly discovered global commands for candidate verification.
6. Execute negative transition, stale-evidence, path escape, partial-write, Chinese HANDOFF, checkpoint, and boundary tests.
7. Bind final test evidence after the last candidate source change to final SHA-256, size, `mtime_ns`, exact command, exit code, and test count.
8. Recompute candidate inventory, boundary markers, global protected hashes, PATH/PYTHONPATH/discovery, reparse points, and forbidden cache/compiled artifacts.
9. Run the global `validate_state.py` and `audit_handoff.py` only for project governance projection evidence; global files remain unchanged.
10. Stop before independent review, installation, activation, T-0036 creation, or any runtime enablement.

## Rollback, Recovery, And Failure Stops

- Baseline/source mismatch: stop before candidate write with `BLOCKED`.
- Any attempted path outside the exact lists: stop with `SCOPE_VIOLATION`.
- Guard or contract test failure: preserve truthful evidence and stop; do not mark implementation complete.
- Partial atomic transaction with successful rollback: record failure and verify original fingerprints; no silent retry.
- Unresolved recovery marker, rollback failure, boundary/global drift, cache pollution, or reparse point: stop with `RECOVERY_REQUIRED`; destructive cleanup requires a separate user Gate.
- Target/test fingerprint change after final validation snapshot: return `STALE_FINAL_VALIDATION`; rerun final validation only after a later in-scope repair request or recovery decision.
- Never roll back, replace, or modify global Project Governor files.

## Authorization Flags

- `implementation_authorized: false`
- `installation_authorized: false`
- `activation_authorized: false`
- `runtime_tool_enablement_authorized: false`
- `downstream_task_creation_authorized: false`
- `real_project_entry_authorized: false`
