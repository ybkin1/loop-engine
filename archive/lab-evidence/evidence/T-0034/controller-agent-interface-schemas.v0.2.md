# Versioned Controller And Agent Interface Schemas v0.2

Contract ID: `CAIS-2026-07-16-R1`. Satisfies `OUT-04` and contributes to `WS-03`, `WS-04`, and `WS-06`.

## 1. Compatibility Policy

- Schema identifiers use `name/vMAJOR.MINOR`; packets include the exact schema ID.
- Minor versions may add optional fields only. Major versions require impact assessment, migration plan, and explicit authority before use.
- Unknown fields are rejected unless the receiver advertises the exact minor-version extension.
- Required field removal, semantic reinterpretation, enum narrowing, default changes, and ordering dependence are breaking changes.
- Every packet is validated at the controller/actor boundary. Persisted bytes are immutable.

## 2. Common Envelope

```yaml
Envelope:
  schema: string
  envelope_id: string
  packet_type: string
  created_at: timestamp
  producer_id: string
  producer_role: string
  controller_generation: integer
  project_id: string
  task_id: string
  transaction_id: string|null
  requirements_revision: string
  project_continuity_hash: sha256
  parent_scope_hash: sha256
  authority_hash: sha256
  evidence_manifest_hash: sha256|null
  idempotency_key: string
  source_sha256: sha256
  semantic_sha256: sha256
  freshness:
    execution_bound_revision: string
    latest_known_revision: string
    verdict: current|stale_rebase_required|conflicted|unknown
  payload: object
```

Envelope validation fails closed for missing authority, stale/conflicted freshness, unknown schema, malformed hash, generation mismatch, duplicate ID with different bytes, or scope hash mismatch.

## 3. `TaskCharter/v1.0`

```yaml
payload:
  user_outcome: string
  observable_success: [string]
  approved_scope: [string]
  forbidden_scope: [string]
  allowed_paths: [string]
  allowed_effects: [string]
  required_outputs: [ArtifactRequirement]
  acceptance_criteria: [Criterion]
  verification_plan_ref: string
  review_boundary: string
  budgets: BudgetSet
  stop_conditions: [string]
```

## 4. `TaskPacket/v1.0`

```yaml
payload:
  packet_id: string
  parent_charter_id: string
  assigned_role: executor|verifier|auditor|repair_planner
  objective: string
  scope_subset_proof: ScopeSubsetProof
  exact_inputs: [EvidenceRef]
  exact_outputs: [ArtifactRequirement]
  exact_allowed_paths: [string]
  exact_forbidden_effects: [string]
  preconditions: [CheckRef]
  completion_contract: [Criterion]
  failure_contract: [FailureAction]
```

## 5. `ExecutionResult/v1.0`

```yaml
payload:
  packet_id: string
  terminal_status: completed|partial|blocked|failed|timed_out|crashed|scope_violation
  artifacts: [ArtifactRef]
  changed_paths: [ChangedPath]
  commands: [CommandResult]
  checks: [CheckResult]
  findings: [FindingRef]
  residual_risks: [Risk]
  unverified_items: [string]
  next_safe_action: string
  authority_claims: [string]
```

`authority_claims` must be empty unless it merely echoes an existing authority reference. Results cannot claim approval, acceptance, installation, activation, or closeout.

## 6. `VerificationPlan/v1.0`

```yaml
payload:
  plan_id: string
  assurance_profile_id: string
  requirement_coverage: [{requirement_id: string, checks: [string]}]
  deterministic_checks: [CheckSpec]
  adversarial_vectors: [VectorRef]
  protected_baselines: [BaselineRef]
  allowed_error_set: [ExpectedError]
  pass_rule: string
  blocking_rule: string
  evidence_requirements: [string]
```

## 7. `AuditPacket/v1.0` And `AuditResult/v1.0`

```yaml
AuditPacket.payload:
  audit_id: string
  subject_artifacts: [ArtifactRef]
  canonical_requirements: [RequirementRef]
  assurance_profile: AssuranceProfile
  role_overlays: [string]
  independence_constraints: [string]
  prohibited_actions: [string]
  verdict_schema: verdict/v1.0

AuditResult.payload:
  audit_id: string
  findings: [Finding]
  coverage: [CoverageResult]
  verdict: Verdict
  uncertainty: [string]
  residual_risk: [Risk]
  next_safe_action: string
```

## 8. `RepairPacket/v1.0` And `RepairResult/v1.0`

```yaml
RepairPacket.payload:
  repair_id: string
  source_findings: [FindingRef]
  authorized_findings: [string]
  exact_allowed_paths: [string]
  immutable_paths: [BaselineRef]
  required_artifacts: [ArtifactRequirement]
  validation_plan: VerificationPlan
  stop_before_review: boolean

RepairResult.payload:
  repair_id: string
  finding_dispositions: [{finding_id: string, status: resolved|partial|blocked, evidence: [EvidenceRef]}]
  artifacts: [ArtifactRef]
  commands: [CommandResult]
  checks: [CheckResult]
  changed_paths: [ChangedPath]
  protected_hash_results: [CheckResult]
  next_safe_action: string
```

## 9. `Checkpoint/v1.0`, `Finding/v1.0`, And `Verdict/v1.0`

```yaml
Finding:
  finding_id: string
  severity: P0|P1|P2|P3
  category: string
  requirement_ids: [string]
  statement: string
  evidence_refs: [EvidenceRef]
  affected_scope: [string]
  blocked_effects: [string]
  reproducibility: deterministic|conditional|unknown
  owner_role: string
  status: open|accepted_for_repair|resolved_pending_review|verified|rejected|superseded

Verdict:
  verdict_id: string
  layer: local_slice|artifact|task|project|user_acceptance
  value: PASS|REPAIR_REQUIRED|BLOCKED|USER_DECISION_REQUIRED|SCOPE_VIOLATION
  requirement_coverage: [CoverageResult]
  blocking_findings: [string]
  evidence_refs: [EvidenceRef]
  residual_risk: [Risk]
  authority_ref: string|null
```

`Checkpoint/v1.0` uses the checkpoint fields from `PCC-2026-07-16-R1` and adds `consumer_acknowledgment`, `generation_fence`, and `semantic_equivalence_verdict`.

## 10. Error Contract

```yaml
InterfaceError:
  code: VALIDATION_ERROR|AUTHORITY_MISSING|SCOPE_VIOLATION|BASELINE_MISSING|STALE_RESULT|CONFLICT|GENERATION_FENCED|BUDGET_EXCEEDED|INTERNAL_ERROR
  message: string
  field_path: string|null
  retryable: boolean
  blocked_effects: [string]
  evidence_refs: [EvidenceRef]
  safe_next_action: string
```

Errors never expose secrets, hidden prompts, unapproved paths, or unverifiable internal claims.

## 11. Idempotency And Ordering

- Same `idempotency_key` plus same semantic hash returns the existing result.
- Same key plus different semantic hash returns `CONFLICT`.
- Consumers order by explicit revision/generation/sequence fields, never filesystem timestamp or arrival order.
- Persistence, validation, commit, notification, and acknowledgment are separate observable states.

## 12. Contract Checks

- `MC-SCHEMA-001`: required fields, enum and unknown-field rejection.
- `MC-COMPAT-001`: compatibility classification for schema changes.
- `MC-IDEMP-001`: duplicate key same/different semantic hash behavior.
- `MC-FRESH-001`: execution-bound/latest-known revision check.
- `MC-AUTH-001`: authority and scope hash validation.
- `ADV-SCHEMA-001`: candidate ID placed in committed revision field; reject.
- `ADV-SCHEMA-002`: result claims task PASS at local layer; reject.
- `ADV-SCHEMA-003`: packet hides forbidden effect in unknown field; reject.

Review roles require a later review Gate: API/protocol, architecture, security, correctness, compatibility, and evidence-integrity.

## 13. Boundary

These are design schemas, not generated code, JSON Schema files, runtime validators, agents, transports, or enabled protocols.
