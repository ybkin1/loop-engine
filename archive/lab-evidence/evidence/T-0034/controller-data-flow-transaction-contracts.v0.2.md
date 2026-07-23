# Controller Data Flow And Transaction Contracts v0.2

Contract ID: `CDFT-2026-07-16-R1`. Satisfies `OUT-03` and contributes to `OUT-02`, `WS-02`, `WS-03`, and `WS-04`.

## 1. Hierarchy And Non-Substitution

| Layer | Owns | Must not do |
|---|---|---|
| `L0` project/program controller | North star, roadmap admission, cross-task dependencies, gate transport, project continuity, risk synthesis, next safe action | Create user authority, self-approve gates, silently redefine baselines, claim user acceptance. |
| `L1` task controller | Approved task scope, work decomposition, actor admission, task transaction, evidence aggregation, bounded repair | Expand L0 scope/authority, hide blocking findings, upgrade evidence to task PASS. |
| `L2` executor/verifier/auditor/repair actor | One explicit subset packet and one declared role | Modify parent scope, approve own work, commit outside declared paths/effects, suppress contrary evidence. |

Every child contract includes `parent_scope_hash`, `child_scope`, `parent_authority_hash`, `child_authority`, and proofs that both child sets are subsets.

## 2. Scope-Subset Contract

```yaml
scope_subset_proof:
  parent_packet_id: string
  parent_scope_sha256: string
  child_scope_sha256: string
  allowed_paths_subset: [string]
  allowed_effects_subset: [string]
  inherited_forbidden_effects: [string]
  exclusions: [string]
  proof_result: PASS|FAIL
  failure_items: [string]
```

Algorithm `MC-SCOPE-001`:

1. Canonicalize paths to project-relative slash form and reject traversal, symlink escape, alternate streams, case ambiguity, and environment-dependent expansion.
2. Verify every child path is contained by an exact parent path or an explicitly declared directory prefix.
3. Verify each child effect is explicitly listed by the parent.
4. Copy all parent forbidden effects into the child; forbiddance cannot be subtracted.
5. Return `FAIL` before dispatch when any item is unresolved.

## 3. L0/L1/L2 Data Flow

```text
User authority record + PCC + current state
  -> L0 TaskCharter admission
  -> L1 TaskPacket with scope/authority subset proof
  -> L2 role packets with disjoint responsibility and transaction lease
  -> L2 immutable result/evidence envelopes
  -> L1 deterministic validation and evidence fan-in
  -> L1 task-level candidate verdict (never user acceptance)
  -> L0 cross-task continuity, residual risk, and next-action synthesis
  -> user decision when required
```

No lower layer writes a higher-layer verdict field. Results are append-only inputs to the owning layer.

## 4. Evidence Fan-In Contract

```yaml
evidence_fan_in:
  aggregation_id: string
  expected_packet_ids: [string]
  received_results: [ResultRef]
  missing_results: [string]
  blocking_findings: [FindingRef]
  high_findings: [FindingRef]
  unresolved_conflicts: [ConflictRef]
  stale_results: [ResultRef]
  path_manifest_union_sha256: string
  candidate_verdict: PASS|REPAIR_REQUIRED|BLOCKED|USER_DECISION_REQUIRED
```

Rules:

- `FAN-I01`: Every admitted packet yields exactly one terminal result or explicit timeout/crash result.
- `FAN-I02`: Blocking and high findings propagate without summarization loss.
- `FAN-I03`: Missing, stale, conflicting, or unconsumed results block PASS.
- `FAN-I04`: Aggregation may preserve or lower confidence; it cannot upgrade a child verdict layer.
- `FAN-I05`: Duplicate result IDs with different hashes produce `CONFLICTED`.
- `FAN-I06`: Only the transaction owner may propose commit; validators/auditors never commit.

## 5. Task Transaction State Machine

```text
PROPOSED
  -> ADMITTED
  -> LEASED
  -> EXECUTING
  -> RESULT_PERSISTED
  -> VALIDATING
  -> COMMIT_READY
  -> COMMITTED
  -> NOTIFIED
  -> ACKNOWLEDGED
  -> CLOSED
```

Exceptional states: `REJECTED`, `BLOCKED`, `CONFLICTED`, `TIMED_OUT`, `CRASHED`, `FENCED`, `RECOVERY_REQUIRED`, `USER_DECISION_REQUIRED`, `ABORTED`.

Transition guards:

- `TX-G01`: `ADMITTED` requires valid scope/authority proofs and baseline freshness.
- `TX-G02`: `LEASED` requires unique owner, lease expiry, generation, and idempotency key.
- `TX-G03`: `RESULT_PERSISTED` requires immutable bytes, hash, changed-path manifest, and terminal actor status.
- `TX-G04`: `COMMIT_READY` requires all expected results, deterministic validation, no blocking finding/conflict/stale result, and current generation.
- `TX-G05`: `COMMITTED` requires compare-and-swap against parent revision and authority hash.
- `TX-G06`: `CLOSED` requires consumer acknowledgment, no blocking queued delta, and explicit owning-layer closeout authority.

## 6. Active Transactions And Leases

```yaml
transaction_lease:
  transaction_id: string
  owner_actor_id: string
  controller_generation: integer
  idempotency_key: string
  allowed_paths: [string]
  allowed_effects: [string]
  acquired_at: timestamp
  expires_at: timestamp
  heartbeat_at: timestamp
  safe_point: string
  generation_fence: string
```

Expired leases do not transfer commit authority. Recovery creates a new generation/lease and records the old lease as fenced.

## 7. Controller Rotation Protocol

1. Stop admitting new writes.
2. Persist every active transaction and unconsumed delta.
3. Create a checkpoint with hashes and next safe action.
4. Issue a generation fence preventing old-generation canonical writes.
5. Successor reconstructs state and returns semantic-equivalence verdict.
6. Consumer durably acknowledges checkpoint and fence.
7. Resume only PASS-safe transactions; all others enter recovery or user decision.

Old-generation results remain evidence but cannot write canonical state after the fence.

## 8. Emergency Recovery

| Condition | Required action |
|---|---|
| Writer crash before persistence | Mark `CRASHED`; no effect assumed; inspect changed paths. |
| Partial additive write | Preserve bytes; mark `PARTIAL_ADDITIVE_EVIDENCE_WRITE`; block commit. |
| Baseline/hash mismatch | Stop before write or enter `CONFLICTED`; require rebase/decision. |
| Lease timeout | Fence generation; preserve result; prohibit late commit. |
| Missing checkpoint field | `RECOVERY_REQUIRED`; no successor admission. |
| Repeated no-progress recovery | Freeze slice and return `USER_DECISION_REQUIRED`. |

## 9. Acceptance And Golden Scenarios

- `MC-SCOPE-001`: child path/effect subset validation.
- `MC-FANIN-001`: all expected terminal results and blocking propagation.
- `MC-TX-001`: legal transition and guard validation.
- `MC-FENCE-001`: reject old-generation canonical write.
- `MC-LEASE-001`: reject expired/non-owner commit.
- `ADV-TX-001`: executor returns PASS while verifier finding is blocking; expected `REPAIR_REQUIRED`.
- `ADV-TX-002`: old generation returns after successor fence; expected evidence retained, commit rejected.
- `ADV-TX-003`: queued blocking delta exists at closeout; expected closeout rejected.

Review roles after a separate review Gate: controller architecture, transaction correctness, security/authority, recovery/liveness, and evidence-integrity reviewers.

## 10. Boundary

This specification defines contracts only. It creates no controller runtime, lease service, dispatcher, transaction engine, agent, review, installation, activation, or closeout.
