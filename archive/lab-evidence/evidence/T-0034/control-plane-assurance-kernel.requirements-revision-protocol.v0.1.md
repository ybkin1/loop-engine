# Requirements Revision Protocol v0.1

## 1. Status and invariants

- Evidence class: `需求修订设计证据`.
- Evidence class: revision-control design; baseline `T-0034-REQ-2026-07-16-R1`.
- Companion files: `control-plane-assurance-kernel.design-addendum.v0.1.md` and `control-plane-assurance-kernel.coverage-matrix.v0.1.md`.
- Requirement input, observed delta, persisted evidence, impact verdict, revision commit, user authorization, execution admission, result freshness, PASS, and closeout are distinct facts.
- Latest message is not automatic supersession. No evidence or reviewer can create user authority, downstream tasks, implementation, installation, activation, or real-project effects.

## 2. Revision identities

Only these public revision identity fields are valid:

| Field | Meaning |
|---|---|
| `observed_requirements_revision_id` | Revision visible to the observer when input was captured. |
| `committed_requirements_revision_id` | Latest revision durably finalized by the registrar with valid authority. |
| `execution_bound_requirements_revision_id` | Immutable revision admitted for one execution generation. |
| `latest_known_requirements_revision_id` | Newest committed revision known at reconciliation time. |

`proposed_revision_candidate_id` identifies an uncommitted candidate and can never be used where a committed ID is required. Every consumer declares which field it consumes; ambiguous aliases fail `K-REQ-FIELD-SEMANTICS-001`.

## 3. Requirements-control Envelopes

All use the common Kernel header.

### RequirementBaselineEnvelope

Required payload: `committed_requirements_revision_id`, parent revision, canonical requirement IDs/text, source refs, authorization refs, `source_content_hash`, `semantic_model_hash`, `normalization_policy_id`, `normalization_trace_ref`, acceptance revision, registrar identity, commit time, and consumer notification state.

### RequirementDeltaEnvelope

Required payload: `observed_requirements_revision_id`, `proposed_revision_candidate_id`, source ref/time, atomic additions/changes/removals/clarifications, affected requirement IDs, source and semantic hashes, normalization fields, persistence state, observer identity, and suspected effects. It carries no commit or user authority.

### ExecutionRebaseDecisionEnvelope

Required payload: candidate ID, current committed and execution-bound IDs, assessor identity, impact verdict, evidence, affected claims/effects, safe local work, user-decision need, queue owner/deadline, safe-point state, generation/fence IDs, and next safe action.

## 4. Role and authority separation

| Role | Inputs | Verdict/output | Forbidden effect |
|---|---|---|---|
| Requirement Observer / Classifier | User input and current baseline. | Delta classification and evidence. | Commit, self-authorize, assess own final verdict. |
| Impact Assessor | Baseline, delta, execution/result claims. | Impact verdict and blocked effects. | User decision or revision commit. |
| User Decision Authority | Decision packet and business context. | Explicit scoped choice. | Technical PASS by authority alone. |
| Requirement Revision Finalizer / Registrar | Authorized decision, hashes, conflict disposition. | Atomic committed baseline and notification event. | Invent or broaden user intent. |
| Result Freshness Reconciler | Results, committed baseline, deltas, acceptance/input hashes. | Freshness verdict and PASS eligibility. | Modify requirements or approve effects. |

Independence means separated capability, admitted inputs, verdict identity, and effect authority. Lite/Standard can separate roles within one session if provenance is auditable. High/Critical require fresh sessions only when their `AssuranceProfile` says so. L0 cannot classify, commit, and validate its own revision as one undifferentiated act.

## 5. Persistence and commit state machine

`delta_observed -> delta_persisted_as_evidence -> impact_assessed -> revision_authorization_pending -> revision_committed -> consumers_notified -> old_results_reconciled`

- Persistence records what was observed; it does not commit a revision.
- Commit is atomic compare-and-set on parent committed ID and requires resolved conflict, valid hashes, registrar role, and exact authority where needed.
- Failed commit leaves the candidate uncommitted and evidence intact. Consumers keep the prior committed revision until notification is durably acknowledged.
- New input not yet persisted is `UNPERSISTED_REQUIREMENT_DELTA` and blocks affected canonical claims.

## 6. Dual hash and normalization

- `source_content_hash`: SHA-256 of exact UTF-8 source bytes after only transport framing removal declared by policy.
- `semantic_model_hash`: SHA-256 of canonical requirement graph: stable IDs, normalized clauses, relationships, priority evidence, acceptance links, and exclusions.
- `normalization_policy_id`: versioned deterministic policy; no hidden synonym, priority, scope, or negation changes.
- `normalization_trace_ref`: durable source-span-to-node transform trace including discarded framing and warnings.

Hash equality is required at its own layer. Source difference plus semantic equality may support semantic-equivalent merge; semantic difference always requires impact assessment. Normalization failure or missing trace fails closed.

## 7. Safe-point acknowledgment and generation fencing

State sequence:

`rebase_requested -> consumer_acknowledged -> safe_point_pending -> safe_point_reached -> execution_generation_fenced -> rebase_checkpoint_committed -> successor_execution_admitted`

- `rebase_requested` records candidate, requester, affected execution, and deadline.
- `consumer_acknowledged` records durable `ack_id`, consumer, current generation, last completed atomic unit, partial-write inventory, and estimated safe point. Silence is not acknowledgment.
- At `safe_point_reached`, the consumer has completed or abandoned the atomic unit, flushed evidence, stopped canonical mutation, and reported checkpoint hash.
- Fence commit records `fence_id`, old/new generation, lease epoch, execution-bound old revision, target committed revision, checkpoint hash, and fenced effects.
- After fencing, old generation output remains old-revision evidence only. It cannot mutate canonical task state or submit task PASS/closeout/eligibility.
- Successor admission compare-and-sets active generation, fence, committed revision, lease, checkpoint, and input contract hash. Late old-generation writes are rejected deterministically.

## 8. Impact verdicts

Valid verdicts:

- `NO_IMPACT_CONTINUE`: only with requirement-by-requirement proof that scope, authority, risk, acceptance, input contract, execution plan, outputs, and result claims are unchanged; hashes and covered IDs are recorded.
- `INTERRUPT_AND_REBASE`: current work would create unsafe or materially stale output; use safe-point sequence now.
- `QUEUE_AND_REBASE`: current atomic unit may finish, but blocking delta has owner, deadline, checkpoint, affected effects, and mandatory consumption before task PASS.
- `CONTINUE_OLD_REVISION_LOCAL_SLICE_ONLY`: useful old-revision evidence may finish, explicitly ineligible for task-level claims.
- `ACCEPT_AS_SEPARATE_FOLLOW_UP`: requires explicit user boundary when scope/acceptance/business effect changes; does not create a task.
- `CANCEL_AND_SUPERSEDE`: requires valid cancel/supersede authority and precedence evidence.
- `IMPACT_UNCERTAIN`: evidence insufficient; block affected effects and investigate.
- `USER_DECISION_REQUIRED`: technical evidence cannot resolve business, authority, cost, risk, scope, acceptance, conflict, or supersession choice.

## 9. Result freshness and PASS layers

Freshness is a composite predicate over execution-bound and latest-known revision identities; source/semantic hashes; covered requirement IDs; authorization and acceptance revisions; input contract hash; execution checkpoint/generation; every unconsumed delta; and each delta's impact on result claims.

Freshness verdicts are `FRESH`, `STALE_REBASE_REQUIRED`, `STALE_LOCAL_EVIDENCE_ONLY`, `CONFLICT_BLOCKED`, and `UNKNOWN_BLOCKED`. A result is `FRESH` only when all material dimensions match or have auditable `NO_IMPACT_CONTINUE` proof.

PASS layers never imply one another:

| Verdict | Meaning |
|---|---|
| `LOCAL_SLICE_PASS` | Bounded output passes its execution-bound revision and declared checks. |
| `TASK_REQUIREMENTS_PASS` | All committed task requirements and acceptance criteria are freshly covered; all blocking queues/conflicts clear. |
| `USER_ACCEPTED` | User explicitly accepts the scoped result; technical PASS is separately recorded. |
| `TASK_CLOSED` | Governance closeout completes with required authority and evidence. |

## 10. Gate batching and user burden

Not every delta receives a gate. Observers batch semantically related pending decisions within a bounded window and present one packet with separate decision items, alternatives, risk/cost, recommendation, defaults that create no authority, and effect mapping.

Explicit user decision remains mandatory for scope, acceptance, authority, risk acceptance, business tradeoff, cost ceiling, cancel, supersede, follow-up boundary, implementation, installation, activation, and real-project effect. Batching cannot merge incompatible choices, hide consequences, or treat silence as approval. Urgent safety blocks bypass the batching delay but not authority.

## 11. Requirement conflict contract

A conflict output contains `conflicting_requirement_ids`, `conflicting_revision_ids`, `precedence_evidence`, `simultaneous_satisfaction_possible`, `supersession_proven`, `latest_explicit_user_instruction_ref`, `user_decision_needed`, `blocked_effects`, `safe_local_work_allowed`, and `next_safe_action`.

Recency alone is not precedence or supersession. If simultaneous satisfaction, precedence, or supersession cannot be proven, enter `USER_DECISION_REQUIRED`; block affected effects while allowing only explicitly safe local work. Resolution is committed additively with the authority reference and losing clauses retained as history.

## 12. Queued rebase closeout block

Any blocking `queued_for_rebase`, blocking unconsumed delta, `UNPERSISTED_REQUIREMENT_DELTA`, or `REQUIREMENT_CONFLICT` blocks:

- `TASK_REQUIREMENTS_PASS` and `CloseoutEnvelope`;
- installation and activation eligibility;
- handoff-finalization and real-project eligibility.

Old work may retain `LOCAL_SLICE_PASS` bound to its old revision. The queue record must name owner, consumption deadline, rebase checkpoint, blocked effects, and next safe action. Block clears only after formal consumption, proven no-impact, explicit separate follow-up, or lawful cancel/supersede.

## 13. Perpetual rebase protection

- A bounded batching window combines related deltas; semantic-equivalent merge reuses one assessment when dual-hash evidence proves equivalence.
- Clarification fast path applies only when scope, acceptance, authority, risk, cost, and claims are unchanged with proof.
- Profile sets maximum rebase count and total rebase time. Repeated equivalent state triggers no-progress detection.
- At threshold, freeze a safe local slice, stop new admissions, preserve queues, and enter `USER_DECISION_REQUIRED` with finish-current, narrow-scope, defer, cancel, or supersede options.
- Timeout cannot silently discard deltas or promote old results.

## 14. Worked T-0034 drift example

1. The old executor was bound to the handoff-finalization local requirements and produced phase-1 handoff documents.
2. The user later added Loop-wide Control-Plane Assurance Kernel requirements.
3. L0 did not interrupt or fence the old execution, so the new delta was not consumed before the old result.
4. The phase-1 documents may retain `LOCAL_SLICE_PASS` against their old execution-bound revision.
5. Relative to `T-0034-REQ-2026-07-16-R1`, freshness is `STALE_REBASE_REQUIRED`; the old result cannot become `TASK_REQUIREMENTS_PASS`.
6. The current three additive design artifacts consume the widened baseline as design evidence only. They do not close T-0034 or imply acceptance/effects.

## 15. Machine checks

| Check ID | Deterministic assertion |
|---|---|
| `K-REQ-FIELD-SEMANTICS-001` | Every revision identity field has one declared meaning and consumer; no ambiguous public alias. |
| `K-REQ-ROLE-SEPARATION-001` | Observer, assessor, user authority, registrar, reconciler capabilities/verdict/effects are separated. |
| `K-REQ-REVISION-FINALIZER-001` | Only registrar commits after valid parent CAS, authority, hashes, and conflict disposition. |
| `K-REQ-SAFEPOINT-ACK-001` | Fence requires durable consumer acknowledgment and safe-point checkpoint. |
| `K-REQ-GENERATION-FENCE-001` | Fenced generation cannot write canonical task effects. |
| `K-REQ-CANDIDATE-ID-001` | Candidate identity never appears in a committed-revision slot. |
| `K-REQ-DUAL-HASH-001` | Source and semantic hashes recompute against declared policy and trace. |
| `K-REQ-NORMALIZATION-TRACE-001` | Every semantic node maps to source spans/transforms; warnings are closed. |
| `K-REQ-GATE-BATCH-001` | Batched packet retains distinct mandatory user decisions and effects. |
| `K-OUTPUT-ADMISSION-001` | Complete artifact, validation, consistency, and closeout reserve fit before output starts. |
| `K-REQ-CONFLICT-001` | Conflict contract is complete; unresolved conflict blocks listed effects. |
| `K-REQ-QUEUE-CLOSEOUT-BLOCK-001` | Blocking queued/unpersisted/unconsumed/conflicting delta rejects task PASS and closeout. |
| `K-REQ-NO-IMPACT-001` | `NO_IMPACT_CONTINUE` has complete dimension-by-dimension proof. |
| `K-REQ-FRESHNESS-001` | Composite freshness inputs are present and match before task PASS. |
| `K-REQ-PASS-LAYER-001` | No automatic transition exists among the four PASS layers. |
| `K-REQ-REBASE-LIVENESS-001` | Count/time/no-progress thresholds and escalation are enforced. |

## 16. Acceptance criteria

1. The four revision identity fields and candidate identity cannot be confused by any consumer.
2. Three requirements-control Envelopes validate against common headers and type payloads.
3. Persistence, impact, authorization, commit, notification, and reconciliation are durable separate states.
4. Role separation prevents L0 or any one capability from observing, self-authorizing, committing, and validating its own revision without independent effect boundaries.
5. Dual hash, normalization policy, and trace detect both byte and semantic drift.
6. Safe-point acknowledgment and generation fence reject every late old-generation canonical write.
7. Impact, freshness, PASS, gate batching, conflict, queue block, and rebase liveness rules are deterministic and fail closed.
8. The worked example yields local-slice evidence plus rebase-required task freshness, never task PASS.
9. All machine checks and adversarial tests have coverage rows; no downstream effect is authorized.

## 17. Adversarial tests

| Test ID | Attack | Expected result |
|---|---|---|
| `K-REQ-ADV-001` | Two consumers interpret an ambiguous revision field differently. | Schema/check rejects field before admission. |
| `K-REQ-ADV-002` | L0 classifies, commits, and validates its own revision. | Role-separation check blocks commit/task effect. |
| `K-REQ-ADV-003` | Old generation submits task PASS after fence. | Canonical write rejected; old evidence retained. |
| `K-REQ-ADV-004` | Candidate ID is disguised as committed ID. | Candidate/registrar checks reject. |
| `K-REQ-ADV-005` | Normalization removes a negation or scope qualifier. | Semantic hash/trace check fails closed. |
| `K-REQ-ADV-006` | Every clarification triggers an independent gate. | Batching/fast-path policy consolidates safe items without swallowing decisions. |
| `K-REQ-ADV-007` | Three artifacts would be truncated at output end. | Output admission refuses to begin incomplete artifact. |
| `K-REQ-ADV-008` | Latest message is treated as automatic supersession. | Conflict enters `USER_DECISION_REQUIRED`. |
| `K-REQ-ADV-009` | Blocking queued rebase remains but closeout reports PASS. | Queue-closeout check rejects both. |
| `K-REQ-ADV-010` | Delta is persisted and consumer treats it as committed. | State/identity check keeps prior committed revision. |
| `K-REQ-ADV-011` | Consumer never acknowledges rebase request. | Timeout blocks fence/admission and escalates. |
| `K-REQ-ADV-012` | Source bytes differ while normalization hides material semantic change. | Dual-hash trace demands impact assessment. |
| `K-REQ-ADV-013` | Rebase repeats with no semantic progress. | Threshold freezes local slice and requests user decision. |
| `K-REQ-ADV-014` | User accepts output and system infers technical PASS/closure. | PASS-layer check rejects inference. |

## 18. Output, continuity, and downstream boundary

Every produced result/handoff carries execution-bound revision, latest-known revision, freshness verdict, unconsumed delta inventory, blocked effects, and next safe action. Output is admitted only when complete deterministic bytes, validation, hashes, cross-file checks, and reporting reserve can be produced. Partial evidence is preserved and reported; deletion/rewrite needs separate authority.

This protocol is design only. Implementing schemas/checks, executing independent review, modifying a candidate, installing, activating, piloting, creating downstream tasks, or entering real projects requires separate explicit gates.

End of `control-plane-assurance-kernel.requirements-revision-protocol.v0.1.md`.
