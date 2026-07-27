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

## 3. Evidence Fan-In Contract

Rules:

- `FAN-I01`: Every admitted packet yields exactly one terminal result or explicit timeout/crash result.
- `FAN-I02`: Blocking and high findings propagate without summarization loss.
- `FAN-I03`: Missing, stale, conflicting, or unconsumed results block PASS.
- `FAN-I04`: Aggregation may preserve or lower confidence; it cannot upgrade a child verdict layer.
- `FAN-I05`: Duplicate result IDs with different hashes produce `CONFLICTED`.
- `FAN-I06`: Only the transaction owner may propose commit; validators/auditors never commit.

## 4. Boundary

This specification defines contracts only. It creates no controller runtime, lease service, dispatcher, transaction engine, agent, review, installation, activation, or closeout.
