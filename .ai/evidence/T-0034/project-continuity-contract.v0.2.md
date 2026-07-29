# Project Continuity Contract v0.2

Contract ID: `PCC-2026-07-16-R1`. Satisfies `OUT-01` and contributes to `OUT-02`, `WS-01`, `WS-02`, and `WS-07`.

## 1. Contract Envelope

```yaml
schema: project-continuity-contract/v1
contract_id: PCC-2026-07-16-R1
requirements_revision: T-0034-REQ-2026-07-16-R1
status: designed_not_implemented
authority_ref: G-T-0034-REPAIR-DESIGN-COVERAGE-AND-ASSURANCE-GAPS
canonical_encoding: UTF-8
unknown_field_policy: reject
```

Every persisted instance carries `schema`, `contract_id`, `requirements_revision`, `source_sha256`, `semantic_sha256`, `created_at`, `created_by`, and `authority_ref`.

## 2. Required Schema

```yaml
project_continuity:
  user_origin:
    audience: string
    capability_assumptions: [string]
    user_authorities: [goal, business_fact, tradeoff, risk_acceptance, gate, acceptance]
  product_identity:
    project_id: string
    one_sentence_outcome: string
    north_star: string
    success_signals: [string]
  protected_decisions:
    - decision_id: string
      statement: string
      rationale_ref: path-or-id
      authority_ref: gate-or-user-record
      change_policy: immutable|new_gate|user_decision
  non_goals: [string]
  design_language:
    terms: {canonical_term: definition}
    forbidden_equivalences: [string]
  engineering_invariants:
    architecture: [invariant]
    technology: [invariant]
    interfaces: [invariant]
    coding_standards: [invariant]
    quality: [invariant]
    security: [invariant]
  golden_references:
    - reference_id: string
      kind: visual|api|architecture|code|workflow|evidence
      path: string
      sha256: string
      comparison_policy: exact|semantic|threshold
  authorization_boundaries:
    allowed_effects: [string]
    forbidden_effects: [string]
    current_gate_id: string|null
  lifecycle:
    phase: string
    task_id: string
    task_status: string
    active_transaction_ids: [string]
    in_flight_actor_ids: [string]
  evidence_index:
    canonical: [EvidenceRef]
    additive: [EvidenceRef]
    superseded_not_deleted: [EvidenceRef]
  revision_lineage:
    parent_revision: string|null
    change_set_id: string
    impact_assessment_ref: string
    approval_ref: string
```

## 3. Invariants

- `PCC-I01`: `user_origin`, `product_identity`, protected decisions, and authority boundaries cannot be summarized away.
- `PCC-I02`: A child packet may reference a subset but may not redefine canonical values.
- `PCC-I03`: Missing architecture, interface, coding, visual, or product baseline is represented explicitly as `BASELINE_MISSING`.
- `PCC-I04`: Golden references require path plus full SHA-256; labels without bytes are non-canonical.
- `PCC-I05`: `allowed_effects` is closed-world. An unlisted effect is forbidden.
- `PCC-I06`: Evidence correction appends a new reference and never changes historical bytes.
- `PCC-I07`: `source_sha256` detects byte drift; `semantic_sha256` detects normalized semantic drift; normalization policy is versioned.
- `PCC-I08`: User acceptance, technical PASS, task PASS, project PASS, and closeout are distinct fields with no implicit transition.

## 4. Controlled Evolution

Change proposal states:

```text
DRAFT -> IMPACT_ASSESSED -> USER_DECISION_REQUIRED -> APPROVED
APPROVED -> COMMITTED -> NOTIFIED -> ACKNOWLEDGED
any state -> REJECTED | CONFLICTED | BLOCKED
```

Required proposal fields are `change_set_id`, old/new revision IDs, source diff, affected invariants, affected packets/transactions, compatibility verdict, required user decisions, rollback plan, and evidence. A revision cannot become canonical before explicit authority and durable commit. Notification is not acknowledgment; acknowledgment is not semantic-equivalence PASS.

## 5. Bootstrap And Reading Tiers

| Tier | Required content | Budget rule |
|---|---|---|
| `R0` | state, current task/gate, HANDOFF next action, protected authority, blockers | Must always fit the bootstrap reserve. |
| `R1` | PCC fields relevant to current task, current transactions, required evidence index | Load by deterministic manifest. |
| `R2` | Detailed source artifacts, historical evidence, professional standards | Load by risk/scope trigger. |
| `R3` | Archive and non-current history | Load only through explicit reference. |

Admission fails with `BOOTSTRAP_OVERSIZE` if complete `R0` plus validation and closeout reserve cannot fit. Truncating a protected field is forbidden.

## 6. Checkpoint Contract

A stable checkpoint requires:

```yaml
checkpoint:
  checkpoint_id: string
  controller_generation: integer
  requirements_revision: string
  project_continuity_hash: string
  task_scope_hash: string
  authority_hash: string
  active_transactions: [TransactionRef]
  in_flight_actors: [ActorRef]
  blocking_findings: [FindingRef]
  evidence_manifest_hash: string
  unconsumed_deltas: [DeltaRef]
  next_safe_action: string
  producer_attestation: signed|unsigned
  created_at: timestamp
```

Safe rotation requires zero unrecorded canonical writes, durable transaction state, a generation fence, and consumer acknowledgment of the checkpoint.

## 7. Successor Probe And Attestation

The successor independently reconstructs `RecoveredControllerState` from `R0/R1`, answers authorization and counterfactual traps, and compares protected fields with the expected state. Verdicts:

- `SEMANTIC_EQUIVALENCE_PASS`: all protected semantics match; evidence refs may differ only by additive updates.
- `REPAIR_REQUIRED`: recoverable omissions or drift exist; no canonical effect allowed until repaired.
- `BLOCKED`: source conflict, missing authority, missing baseline, or unverifiable checkpoint.

Producer and successor attestations are separate. Producer signature cannot satisfy successor attestation.

## 8. Acceptance Checks

- `MC-PCC-001`: reject missing protected fields.
- `MC-PCC-002`: reject child value differing from canonical parent without approved revision.
- `MC-PCC-003`: reject golden reference without full SHA-256.
- `MC-PCC-004`: reject unlisted effect.
- `MC-PCC-005`: detect source/semantic hash divergence.
- `ADV-PCC-001`: malicious summary omits user authority; expected `REPAIR_REQUIRED`.
- `ADV-PCC-002`: latest message is treated as automatic supersession; expected `USER_DECISION_REQUIRED`.

Review roles after a separately approved review Gate: continuity, architecture, product, security, and governance-boundary reviewers.

## 9. Boundary

This contract is a design specification. It does not create runtime storage, dispatch, validation code, review authority, installation, activation, task closeout, or user acceptance.
