# T-0036 Repair Structured State Contracts v0.2

Gate: `G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

Status: proposed contract for a pending repair Gate. It is not implemented, installed, activated, or provisioned in the live project.

Unknown fields are rejected in all three schemas. Canonical JSON means UTF-8, sorted keys, no insignificant whitespace, and normalized slash-form project-relative paths.

## ProjectContinuity/v1

Normative sources:

- `.ai/evidence/T-0034/project-continuity-contract.v0.2.md`, contract `PCC-2026-07-16-R1`, especially sections 1-3 and 5-7.
- `.ai/PROJECT.md` for the project outcome, north star, and success signals.
- `.ai/CONTRACTS.md` for user authority, Codex responsibility, evidence-only boundaries, lifecycle separation, and forbidden effects.
- `.ai/evidence/T-0034/controller-data-flow-transaction-contracts.v0.2.md`, contract `CDFT-2026-07-16-R1`, for L0/L1/L2 ownership and non-substitution.

Persistence path: `.ai/project_continuity.yaml`.

Writer: only the L0 continuity registrar during a separately approved project initialization, continuity revision, or migration Gate. The isolated repair candidate, `close_session.py`, validators, auditors, and controlled runner are readers only and must never synthesize this file from prose.

Readers: `continuity_producer.py`, `continuity_auditor.py`, `validate_state.py`, `close_session.py`, and `audit_handoff.py`.

Required schema:

```yaml
schema: ProjectContinuity/v1
contract_id: PCC-2026-07-16-R1
requirements_revision: T-0034-REQ-2026-07-16-R1
project_id: string
source_manifest:
  - path: project-relative-path
    sha256: 64-uppercase-hex
    size: integer
source_sha256: 64-uppercase-hex
semantic_sha256: 64-uppercase-hex
created_at: ISO-8601
created_by: string
authority_ref: user-message-or-approved-gate-ref
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
    terms: object
    forbidden_equivalences: [string]
  engineering_invariants:
    architecture: [string]
    technology: [string]
    interfaces: [string]
    coding_standards: [string]
    quality: [string]
    security: [string]
  golden_references:
    - reference_id: string
      kind: visual|api|architecture|code|workflow|evidence
      path: project-relative-path
      sha256: 64-uppercase-hex
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
    impact_assessment_ref: path-or-id
    approval_ref: path-or-id
```

Required protected decision IDs are `USER_AUTHORITY`, `CODEX_DELIVERY_RESPONSIBILITY`, `EVIDENCE_ONLY_BOUNDARY`, and `MEANS_END_BOUNDARY`. Their statements must be structured values sourced from the protected anchors, not extracted by keyword or `TBD` scanning.

Missing behavior: `close_session.py` exits with `RECOVERY_REQUIRED`, leaves the existing HANDOFF bytes unchanged, and produces no valid continuity block or checkpoint. Validator/auditor report `PROJECT_CONTINUITY_MISSING`. No prose fallback is permitted.

Hash binding:

- `source_manifest` is the exact ordered list of protected source path/SHA-256/size records.
- `source_sha256 = SHA256(canonical_json(source_manifest))`.
- `semantic_sha256 = SHA256(canonical_json(project_continuity))`.
- Each consumer also computes the exact persisted `.ai/project_continuity.yaml` file SHA-256 and binds all three hashes into HANDOFF and checkpoint records.
- Any source, semantic, or file hash mismatch is `RECOVERY_REQUIRED`.

## TransactionRegistry/v1

Normative sources:

- `.ai/evidence/T-0034/controller-data-flow-transaction-contracts.v0.2.md`, contract `CDFT-2026-07-16-R1`, sections 5-8.
- `.ai/evidence/T-0034/project-continuity-contract.v0.2.md`, checkpoint and successor-attestation sections 6-7.

Persistence path: `.ai/transaction_registry.yaml`.

Writer: only the L0 transaction owner/controller runtime under a separately approved runtime or recovery Gate. A successor controller may append an acknowledgment only through its separately authorized acknowledgment path. This repair candidate, close producer, validators, auditors, and controlled runner are readers only. Unit/E2E fixtures may create synthetic registries in temporary directories but must label them `fixture_only: true` and cannot establish live authority.

Readers: `transaction_registry.py`, `continuity_producer.py`, `continuity_auditor.py`, `validate_state.py`, `close_session.py`, and `audit_handoff.py`.

Required schema:

```yaml
schema: TransactionRegistry/v1
contract_id: CDFT-2026-07-16-R1
requirements_revision: T-0034-REQ-2026-07-16-R1
project_id: string
controller_generation: integer
registry_revision: integer
state_revision_sha256: 64-uppercase-hex
active_transactions:
  - transaction_id: string
    owner_actor_id: string
    state: string
    generation: integer
    lease_id: string
    safe_point: string
    result_ref: path-or-id|null
in_flight_actors:
  - actor_id: string
    packet_id: string
    generation: integer
    status: string
unconsumed_deltas:
  - delta_id: string
    producer_id: string
    generation: integer
    sha256: 64-uppercase-hex
    status: queued|blocked|conflicted
partial_writes:
  - transaction_id: string
    marker_path: project-relative-path
    status: RECOVERY_REQUIRED
generation_fence:
  fence_id: string
  fenced_generation: integer
  successor_generation: integer
  issued_at: ISO-8601
  authority_ref: path-or-id
checkpoint_acknowledgments:
  - checkpoint_id: string
    controller_generation: integer
    recovered_state_sha256: 64-uppercase-hex
    acknowledged_at: ISO-8601
    acknowledged_by: string
    authority_ref: path-or-id
source_sha256: 64-uppercase-hex
semantic_sha256: 64-uppercase-hex
updated_at: ISO-8601
updated_by: string
authority_ref: path-or-id
fixture_only: boolean
```

Missing behavior: HANDOFF may be generated only as a recovery HANDOFF with `checkpoint_status: NOT_ESTABLISHED` and blocker `TRANSACTION_REGISTRY_MISSING`; it must not contain a section or claim named Stable Checkpoint. Final completion binding is blocked. Validator/auditor fail the stable-checkpoint contract.

Stable checkpoint behavior:

- The deterministic checkpoint ID is derived from protected semantic hashes and excludes timestamps and acknowledgment fields.
- First production emits `PENDING_SUCCESSOR_ACK`, never Stable.
- Only a matching production acknowledgment for the same checkpoint ID, generation, and recovered-state hash can promote the unchanged deterministic checkpoint to `STABLE`.
- A matching temporary fixture acknowledgment may produce `STABLE_FIXTURE_ONLY`; it proves the algorithmic path but cannot be projected as production Stable or installation evidence.
- Any active transaction, in-flight actor, unconsumed delta, partial write, generation/fence mismatch, missing acknowledgment, or `fixture_only: true` prevents a production Stable claim.

Hash binding:

- `source_sha256` binds the ordered PCC/CDFT source path/SHA-256/size records.
- `semantic_sha256` binds every registry field except `semantic_sha256`, `updated_at`, and formatting.
- HANDOFF/checkpoint bind source hash, semantic hash, and exact persisted file SHA-256.
- Pre-read/open/post-read file identity and size must match.

## EvidenceManifest/v1

Normative sources:

- `PCC-2026-07-16-R1` evidence index and checkpoint `evidence_manifest_hash` requirements.
- `CDFT-2026-07-16-R1` evidence fan-in rules `FAN-I01` through `FAN-I06` and transaction guards `TX-G03`/`TX-G04`.
- T0036-F009 and this repair Gate's approved bounded hashing limits.

Persistence path template: `.ai/evidence/<task-id>/evidence-manifest.v1.yaml`. For this repair the exact future path is `.ai/evidence/T-0036/t0036-repair-evidence-manifest.v1.yaml`.

Writer: the owning L1 evidence aggregator or L0 repair executor after an approved Gate and later exact execution request, using atomic create-only persistence. The controlled runner, checkpoint producer, validator, and auditor are readers; the runner writes separate stdout/stderr/result evidence but never edits the approved manifest.

Readers: `evidence_manifest.py`, `validation_runner.py`, `continuity_producer.py`, `continuity_auditor.py`, `validate_state.py`, and `audit_handoff.py`.

Required schema:

```yaml
schema: EvidenceManifest/v1
manifest_id: string
task_id: T-NNNN
gate_id: G-...
authority_ref: path-or-id
evidence_root: .ai/evidence/<task-id>
limits:
  max_file_count: integer
  max_per_file_bytes: integer
  max_total_bytes: integer
  stream_chunk_bytes: integer
files:
  - path: project-relative-path
    role: source|test|command|stdout|stderr|result|protected
    required: boolean
    sha256: 64-uppercase-hex
    size: integer
    mtime_ns: integer
file_count: integer
total_bytes: integer
ordered_entries_sha256: 64-uppercase-hex
semantic_sha256: 64-uppercase-hex
created_at: ISO-8601
created_by: string
```

Hard limits are `file_count <= 256`, `per-file <= 16777216`, `total_bytes <= 268435456`, and `stream_chunk_bytes = 1048576`. A manifest may lower but not raise them.

Missing behavior: evidence verification returns `EVIDENCE_MANIFEST_REQUIRED`; controlled validation may execute only if its Gate-bound plan allows diagnostic execution, but it cannot emit `status: bound`; Stable checkpoint and completion claims are blocked.

Hash binding:

- Paths are unique after case-insensitive normalized slash canonicalization and must be beneath the project root and declared evidence root where applicable.
- `ordered_entries_sha256 = SHA256(canonical_json(files sorted by normalized path))`.
- `semantic_sha256` binds the entire manifest payload except `semantic_sha256`, timestamps, and formatting.
- Consumers compute and bind the exact persisted manifest file SHA-256.
- Every file is streamed in 1 MiB chunks with count/size/total enforcement, ancestor/target reparse rejection, and pre/open/post identity and size checks.
- Any undeclared, missing, stale, oversized, reparse, case-colliding, external, or concurrently changed subject fails closed.

## Live-project Boundary

This repair Gate does not authorize creation or modification of `.ai/project_continuity.yaml`, `.ai/transaction_registry.yaml`, or a live task evidence manifest before repair execution. It defines reader contracts and temporary-fixture tests only. Provisioning live canonical instances, adding a trusted authority adapter, or enabling a controller writer requires separate explicit Gates and fresh review before installation eligibility can be reconsidered.
