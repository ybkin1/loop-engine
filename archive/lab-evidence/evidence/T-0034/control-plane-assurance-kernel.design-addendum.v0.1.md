# Control-Plane Assurance Kernel Design Addendum v0.1

## 1. Status

- Evidence class: `设计证据`.
- Task: `T-0034`; baseline: `T-0034-REQ-2026-07-16-R1`.
- Approved design gate: `G-T-0034-DESIGN-PROJECT-CONTINUITY-CONTROLLER-HIERARCHY-LOOP-ASSURANCE`.
- Requirement drift is normative in `control-plane-assurance-kernel.requirements-revision-protocol.v0.1.md`; coverage is in `control-plane-assurance-kernel.coverage-matrix.v0.1.md`.
- This is additive design evidence only. It does not implement, install, activate, enable automation, enter a real project, close `T-0034`, or record user acceptance.

## 2. Mission and authority

The Kernel keeps intent, authority, execution, evidence, assurance, recovery, and handoff consistent across controller generations. It exposes stale work, blocks false task PASS, and preserves revision-bound evidence.

Non-goals: it is not a runtime, autonomous project manager, deployment system, or substitute for business judgment. It cannot approve gates, infer supersession from recency, create tasks, start agents, implement, install, activate, pilot, release, migrate, or touch production.

- The user owns goals, business truth, scope, acceptance, risk acceptance, cost ceilings, cancel/supersede, and effect gates.
- L0 coordinates only within approved scope. Executors create revision-bound artifacts. Verifiers and auditors create evidence, never user authority.
- Validator PASS proves only its declared checks; it is not semantic correctness, authorization, acceptance, or closure.

## 3. Common Envelope architecture

All Envelopes carry `schema_id`, `schema_version`, `envelope_type`, `envelope_id`, `task_id`, `controller_generation`, `producer_role`, `created_at`, `parent_envelope_ids`, `execution_bound_requirements_revision_id` when applicable, `input_contract_hash`, `content_hash`, `authority_refs`, `evidence_refs`, `sensitivity`, and `retention_class`. Unknown mandatory fields fail closed; unknown optional fields are preserved.

| Envelope | Purpose | Effect boundary |
|---|---|---|
| `TaskEnvelope` | Objective, scope, exclusions, acceptance revision, resources, dependencies, gates. | Admits work after gate checks. |
| `ExecutionResultEnvelope` | Outputs, claims, paths, checkpoint, limits, revision. | Evidence until reconciled. |
| `VerificationEnvelope` | Checks, environment, commands, outputs, coverage. | Cannot grant approval. |
| `AuditEnvelope` | Neutral review against criteria and baselines. | Cannot mutate artifact or approve gate. |
| `FindingEnvelope` | Severity, evidence, claims, owner, remedy, disposition. | Blocks effects by policy. |
| `RepairEnvelope` | Bounded repair, authority, recovery, results. | Cannot expand scope. |
| `CloseoutEnvelope` | Freshness, findings, resources, paths, eligibility. | Requires all blockers cleared. |
| `HandoffEnvelope` | State, scope, exclusions, evidence, blockers, next action. | Continuity, not authority. |
| `SuccessorAttestationEnvelope` | Semantic equivalence, generation, baselines, risks. | Supports valid transfer. |
| `UserDecisionEnvelope` | Exact choice, scope, alternatives, risks, effects. | Sole user-authority carrier. |

The companion protocol defines the three requirements-control Envelopes.

## 4. Four-layer Assurance

| Layer | Required proof | Failure effect |
|---|---|---|
| Structural | Parse, schema, manifest, links, canonical bytes, hashes. | Reject admission. |
| Factual | Independent read-back of paths, outputs, versions, hashes, state. | Block affected claims and closeout. |
| Semantic/professional | Traceable product, architecture, API, code, QA, security, performance, delivery review. | Repair, rebase, or escalation. |
| User authorization | Exact `UserDecisionEnvelope` or gate covering the effect. | Effect forbidden. |

No layer implies another. Authorization does not prove quality; quality does not create authority.

## 5. Controller uniqueness and generation safety

- At most one canonical L0 lease exists per task: `(task_id, controller_generation, lease_id, lease_epoch, holder, acquired_at, expires_at)`.
- Acquisition compare-and-sets the committed epoch; renewal is bounded and durable. Transfer requires handoff, successor attestation, and atomic generation increment.
- Split-brain means overlapping leases, conflicting generations, or competing canonical writers. Detection fences both uncertain writers and enters recovery; timestamps do not select a winner.
- A stale generation may emit isolated evidence bound to its old generation and revision. It cannot mutate canonical state, issue `TASK_REQUIREMENTS_PASS`, finalize handoff, or claim eligibility.
- Every canonical write checks lease, generation, committed revision, and input contract hash. Safe-point fencing is normative in the companion protocol.

## 6. Lifecycle and liveness

`proposed -> admitted -> active -> waiting | blocked | retry_pending -> verifying -> auditing -> repair_pending -> closeout_pending -> closed`

Terminal alternatives are `cancelled`, `superseded`, and `failed_recoverable`; `emergency_recovery` is controlled mode, not success.

- Blockers record ID, owner, affected effects, evidence, first-seen time, deadline, and next safe action. Every wait and lease has heartbeat and timeout.
- Retry requires a transient cause, idempotency key, bounded count, backoff, and unchanged authority. Timeout/no-progress never loops silently.
- Cancel preserves evidence and needs proportional authority. Supersede additionally records replacement and precedence evidence.
- Recovery inventories partial writes and resumes from a verified checkpoint; destructive cleanup needs separate authority.
- Emergency recovery may freeze writers, revoke leases, snapshot state, and restore verified state, but cannot bypass gates or invent PASS.
- Liveness alarms cover expired leases, no-progress, repeated findings, unresolved decisions, exhaustion, and perpetual rebase.

## 7. AssuranceProfile

| Profile | Typical use | Minimum controls |
|---|---|---|
| `Lite` | Read-only/low-risk reversible evidence. | Structural/factual checks; same-session capability separation allowed. |
| `Standard` | Normal local design/code. | Applicable four layers, independent review capability, freshness, closeout reserve. |
| `High` | Security, permissions, external API, migration planning, broad architecture. | Fresh session when configured, dual control, stronger retention/tests. |
| `Critical` | Production data, secrets, payments, deployment, irreversible effects. | Fresh independent sessions, fail-closed admission, recovery proof, strongest protection. |

Profiles may rise with risk but never silently fall. Lite/Standard independence separates capability, input, verdict, and effect authority, not mechanically sessions; High/Critical session rules are explicit profile fields.

## 8. Resource, closeout reserve, and anti-self-loop

`TaskEnvelope` declares cost, token, wall-time, agent, storage, gate, retry, and evidence ceilings. It reserves verification, audit, repair, closeout, and handoff resources before admission.

- Feature work cannot consume `closeout_reserve` without a user-approved budget change.
- Gate batching groups related decision items while retaining each item and affected effect.
- Agent fan-out is bounded; no agent authorizes another or expands scope.
- Detect repeated unchanged plans/findings, governance displacing product work, no-progress rebases, and rising cost without acceptance coverage.
- Threshold breach stops nonessential work, preserves evidence, reports budgets, and selects repair, scope reduction, user decision, or controlled closeout.
- Output admission fails closed when a complete artifact, its validation, and reporting reserve cannot fit.

## 9. Evidence security, privacy, retention, schema evolution

- Apply least privilege, purpose limitation, and minimization. Prohibit or redact secrets, credentials, personal data, production payloads, and unnecessary raw logs at source.
- Redaction is additive and records policy, reason, operator, and hash linkage; it cannot invisibly alter claims.
- Sensitivity controls access/transmission. Retention classes specify periods and holds but do not authorize irreversible deletion.
- Cited evidence is immutable; correction creates a linked additive artifact.
- Schema evolution uses SemVer, canonical serialization, compatibility tests, golden vectors, migration evidence, and consumer capabilities. Breaking change needs a new major version and separate migration/activation gate.
- Unknown required fields, unsupported major versions, hash mismatch, or ambiguous interpretation fail closed.

## 10. Handoff-finalization specialization

Finalization requires one active generation, no active transaction, no in-flight agent, verified changed paths, current committed revision, reconciled old results, no blocking queued/unconsumed delta, no conflict, no blocking finding, bounded bootstrap, successor semantic-equivalence attestation, and eligibility separated from action.

A well-written handoff may receive `LOCAL_SLICE_PASS` while task freshness fails. The companion protocol blocks `TASK_REQUIREMENTS_PASS` and `CloseoutEnvelope` until drift is consumed. This preserves useful phase-1 evidence without overstating T-0034.

## 11. Risk register

| Risk ID | Risk | Required response | Residual risk |
|---|---|---|---|
| `K-RISK-001` | Split-brain writers. | Fence uncertain generations; recovery audit. | Storage/clock faults need review. |
| `K-RISK-002` | False PASS from stale requirements. | Keep local evidence; rebase claims. | Impact can require judgment. |
| `K-RISK-003` | Validator authority inflation. | Reject unauthorized effect. | Readers may over-trust checks. |
| `K-RISK-004` | Governance consumes delivery budget. | Anti-loop stop, scope reduction, or decision. | High risk remains costly. |
| `K-RISK-005` | Sensitive evidence leakage. | Quarantine and additive redaction; separately authorize secret rotation. | Scanners miss context. |
| `K-RISK-006` | Schema consumers diverge. | Compatibility fail-closed; gated migration. | Legacy retirement remains. |
| `K-RISK-007` | Endless rebase. | Batch, local-slice freeze, or user decision. | Genuine rapid change delays closure. |
| `K-RISK-008` | Handoff hides active work. | Block finalization and identify owners. | Untracked external work. |

## 12. Kernel-wide machine checks

| Check ID | Assertion |
|---|---|
| `K-ENV-SCHEMA-001` | Every admitted Envelope validates against supported canonical schema. |
| `K-ENV-HASH-001` | Content and input hashes recompute. |
| `K-TRACE-001` | Claims trace requirement -> artifact -> verification -> finding disposition -> acceptance revision. |
| `K-AUTH-001` | Every gated effect has exact, scope-containing authority. |
| `K-CTRL-LEASE-001` | At most one active canonical lease exists per task. |
| `K-CTRL-GENERATION-001` | Canonical writes match generation and lease epoch. |
| `K-LIVENESS-001` | Waits, blockers, retries, leases have valid deadlines or escalation. |
| `K-PROFILE-001` | Executed controls meet declared profile. |
| `K-BUDGET-001` | Required verification and closeout reserves remain. |
| `K-EVIDENCE-SEC-001` | Sensitivity, retention, redaction, secret scan are present. |
| `K-SCHEMA-COMPAT-001` | Producer/consumer compatibility and golden vectors pass. |
| `K-HANDOFF-FINAL-001` | All handoff prerequisites and revision queue blocks pass. |
| `K-NO-AUTO-EFFECT-001` | No result auto-implements, installs, activates, creates tasks, or enters a real project. |

Companion `K-REQ-*` and `K-OUTPUT-ADMISSION-001` checks are mandatory inputs to handoff finalization.

## 13. Acceptance criteria

1. Thirteen Envelope families have identity, provenance, hash, purpose, and authority boundaries.
2. Four assurance layers remain non-substitutable; user authority is never inferred.
3. Lease uniqueness, fencing, split-brain, stale generation, lifecycle, retry, cancel, recovery, and timeout are deterministic.
4. Profiles proportionally bind independence, resources, security, liveness, and adversarial testing.
5. Evidence privacy, retention, immutability, and schema evolution fail closed.
6. Handoff finalization consumes the revision protocol and cannot pass with blocking drift.
7. Checks/tests map to coverage rows with residual risks and downstream dependencies.
8. Three documents are complete UTF-8 without BOM, LF-only, cross-linked, and hashed.
9. Protected baselines remain unchanged and no runtime/effect is enabled.

## 14. Adversarial test catalog

| Test ID | Attack | Expected result |
|---|---|---|
| `K-ADV-001` | Overlapping controller leases. | Fence both uncertain writers; no timestamp winner. |
| `K-ADV-002` | Stale generation submits task PASS. | Retain local evidence; reject canonical effect. |
| `K-ADV-003` | Validator PASS presented as approval. | Authorization fails. |
| `K-ADV-004` | Auditor edits audited artifact. | Role-separation failure. |
| `K-ADV-005` | Permanent error retries forever. | Retry/no-progress ceiling stops. |
| `K-ADV-006` | Feature work consumes closeout reserve. | Budget admission blocks. |
| `K-ADV-007` | Evidence includes secret/personal data. | Quarantine until safe additive repair. |
| `K-ADV-008` | Consumer accepts incompatible major schema. | Compatibility fails closed. |
| `K-ADV-009` | Handoff hides unconsumed delta. | Task PASS/finalization blocked. |
| `K-ADV-010` | Governance loops without product progress. | Anti-loop stop or scope decision. |
| `K-ADV-011` | Partial evidence is deleted to appear clean. | Preserve evidence; require recovery authority. |
| `K-ADV-012` | Review recommendation treated as install approval. | Eligibility/action remain separate and blocked. |

## 15. Downstream boundaries

This is implementation-neutral design. Schema/validator implementation, controller runtime, independent execution review, candidate modification, installation, activation, pilot, release, deployment, migration, permissions, or real-project entry each requires a separate explicit user gate. Review PASS is evidence only; eligibility is not action. `T-0035` through `T-0050` remain roadmap references and are not created or authorized.

End of `control-plane-assurance-kernel.design-addendum.v0.1.md`.
