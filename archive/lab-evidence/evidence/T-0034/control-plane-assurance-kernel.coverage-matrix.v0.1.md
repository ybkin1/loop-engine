# Control-Plane Assurance Kernel Coverage Matrix v0.1

Evidence class: `覆盖矩阵设计证据`.
Evidence class: coverage design. Baseline: `T-0034-REQ-2026-07-16-R1`.

Evidence codes: `A` = `control-plane-assurance-kernel.design-addendum.v0.1.md`; `P` = `control-plane-assurance-kernel.requirements-revision-protocol.v0.1.md`; `M` = this matrix. Status `DESIGNED` means specified but not implemented, installed, activated, piloted, independently accepted, or task-closed.

| requirement_id | requirement | design_section | status | evidence_path | residual_risk | downstream_dependency | user_decision_needed |
|---|---|---|---|---|---|---|---|
| `COV-SCOPE-001` | Original T-0034 continuity, hierarchy, neutral audit, assurance design scope. | A 1-15 | DESIGNED | A | Independent semantic review pending. | Separate review gate. | Yes: acceptance. |
| `COV-KERNEL-001` | Kernel mission, non-goals, authority. | A 1-2 | DESIGNED | A | Human authority misuse remains possible. | Schema/policy implementation. | Yes for effects. |
| `COV-ENV-001` | Common header, canonical hashes, provenance, authority refs. | A 3 | DESIGNED | A | Canonical serializer unbuilt. | Interface implementation gate. | No for design. |
| `COV-ENV-002` | Task and ExecutionResult Envelopes. | A 3 | DESIGNED | A | Runtime conformance untested. | T-0041 roadmap only. | Before implementation. |
| `COV-ENV-003` | Verification and Audit Envelopes. | A 3 | DESIGNED | A | Reviewer neutrality needs execution proof. | Review-system gate. | Before enablement. |
| `COV-ENV-004` | Finding and Repair Envelopes. | A 3 | DESIGNED | A | Severity calibration pending. | Repair-loop implementation. | Before repair effect. |
| `COV-ENV-005` | Closeout and Handoff Envelopes. | A 3,10 | DESIGNED | A,P | Legacy handoffs may lack fields. | Migration design/gate. | Before migration. |
| `COV-ENV-006` | SuccessorAttestation and UserDecision Envelopes. | A 3,5 | DESIGNED | A | Identity binding unimplemented. | Controller/interface implementation. | Yes for user effects. |
| `COV-ENV-007` | RequirementBaseline, Delta, RebaseDecision Envelopes. | P 2-3 | DESIGNED | P | Schema code absent. | Requirements-control implementation. | Before implementation. |
| `COV-ASSURE-001` | Structural assurance. | A 4 | DESIGNED | A | Checks not executable yet. | Validator implementation. | No. |
| `COV-ASSURE-002` | Factual assurance. | A 4 | DESIGNED | A | Environment reproducibility varies. | Verification tooling. | No. |
| `COV-ASSURE-003` | Semantic/professional assurance. | A 4 | DESIGNED | A | Judgment calibration required. | Independent review profiles. | Possibly on tradeoffs. |
| `COV-ASSURE-004` | User authorization assurance. | A 2,4 | DESIGNED | A | Exact identity/auth method undecided. | User decision interface. | Yes. |
| `COV-CTRL-001` | Single active lease and generation uniqueness. | A 5 | DESIGNED | A | Atomic store absent. | Controller runtime gate. | Before runtime. |
| `COV-CTRL-002` | Split-brain detection and stale-generation fencing. | A 5; P 7 | DESIGNED | A,P | Distributed failure model untested. | Runtime plus chaos tests. | Before activation. |
| `COV-LIFE-001` | Lifecycle, blockers, timeout, retry, cancel, recovery. | A 6 | DESIGNED | A | Policy thresholds unset. | Profile implementation. | On risk/cost thresholds. |
| `COV-LIFE-002` | Emergency recovery preserves authority/evidence. | A 6 | DESIGNED | A | Recovery drills absent. | Recovery implementation/review. | Yes before destructive action. |
| `COV-PROFILE-001` | Lite/Standard/High/Critical profiles and independence. | A 7 | DESIGNED | A | Profile selection calibration. | Profile schema and pilots. | On cost/risk tradeoff. |
| `COV-RESOURCE-001` | Cost/token/time/agent/storage/gate/retry ceilings. | A 8 | DESIGNED | A | Telemetry absent. | Runtime instrumentation. | For ceiling changes. |
| `COV-RESOURCE-002` | Closeout reserve, output reserve, anti-self-loop. | A 8; P 13,18 | DESIGNED | A,P | False-positive stops possible. | Admission/check implementation. | On scope/budget choices. |
| `COV-SEC-001` | Evidence security, privacy, minimization, redaction. | A 9 | DESIGNED | A | Scanner blind spots. | Security review/tooling. | For policy/risk acceptance. |
| `COV-RET-001` | Retention, immutability, additive correction. | A 9 | DESIGNED | A | Legal retention policy absent. | Policy and storage design. | Yes before deletion. |
| `COV-SCHEMA-001` | SemVer, compatibility, migration, fail-closed evolution. | A 9 | DESIGNED | A | Legacy consumer inventory absent. | Migration gate. | Before migration/activation. |
| `COV-HANDOFF-001` | Handoff-finalization specialization. | A 10 | DESIGNED | A,P | Existing phase-1 evidence needs review. | Independent disk review. | Acceptance pending. |
| `COV-BOUNDARY-001` | Separate implementation/review/install/activate/pilot gates. | A 15; P 18 | DESIGNED | A,P | Future scope creep. | Independent gates. | Yes at each boundary. |
| `COV-UTF8-001` | UTF-8 no BOM, LF-only, one final LF, high bytes, no replacement. | A 13; M validation | DESIGNED | A,P,M | Toolchain can recode later. | Deterministic byte checks. | No. |

| `COV-REQ-ID-001` | Four unambiguous committed/observed/execution/latest revision IDs. | P 2 | DESIGNED | P | Consumer errors until schema enforcement. | Schema/check implementation. | No. |
| `COV-REQ-CAND-001` | Candidate ID separated from committed ID. | P 2-3 | DESIGNED | P | Legacy aliases may persist. | Compatibility scanner. | No. |
| `COV-REQ-STATE-001` | Observation, persistence, assessment, authorization, commit, notify, reconcile states. | P 5 | DESIGNED | P | Atomic store unbuilt. | Registrar implementation. | Before runtime. |
| `COV-REQ-ROLE-001` | Observer/classifier separated. | P 4 | DESIGNED | P | Same-session misuse possible. | Capability enforcement. | No. |
| `COV-REQ-ROLE-002` | Impact assessor separated. | P 4 | DESIGNED | P | Professional judgment variance. | Review rubric. | On uncertain impact. |
| `COV-REQ-ROLE-003` | User authority separated. | P 4,10 | DESIGNED | P | User identity binding undecided. | Decision interface. | Yes. |
| `COV-REQ-ROLE-004` | Finalizer/registrar separated and atomic. | P 4-5 | DESIGNED | P | CAS/store absent. | Registrar implementation. | Before implementation. |
| `COV-REQ-ROLE-005` | Freshness reconciler separated. | P 4,9 | DESIGNED | P | Claims may be incompletely modeled. | Result schema/reconciler. | No. |
| `COV-REQ-HASH-001` | Source hash binding. | P 6 | DESIGNED | P | Framing policy variance. | Canonical byte policy. | No. |
| `COV-REQ-HASH-002` | Semantic hash, normalization policy, trace. | P 6 | DESIGNED | P | Semantic canonicalization defects. | Golden vectors/review. | On semantic conflict. |
| `COV-REQ-SAFE-001` | Durable safe-point acknowledgment. | P 7 | DESIGNED | P | Consumer may hang. | Timeout/recovery runtime. | On cancel/escalation. |
| `COV-REQ-FENCE-001` | Generation fence and successor admission CAS. | P 7 | DESIGNED | P | Distributed races untested. | Runtime/chaos testing. | Before activation. |
| `COV-REQ-IMPACT-001` | Eight impact verdicts and effects. | P 8 | DESIGNED | P | Misclassification remains. | Assessor rubric/checks. | For required verdicts. |
| `COV-REQ-NOIMPACT-001` | Auditable proof for NO_IMPACT_CONTINUE. | P 8 | DESIGNED | P | Proof completeness judgment. | Check implementation. | No. |
| `COV-REQ-FRESH-001` | Composite result freshness. | P 9 | DESIGNED | P | Requirement graph completeness. | Reconciler implementation. | No. |
| `COV-REQ-PASS-001` | LOCAL_SLICE_PASS distinct. | P 9 | DESIGNED | P | Human overstatement. | UI/report validation. | No. |
| `COV-REQ-PASS-002` | TASK_REQUIREMENTS_PASS distinct. | P 9,12 | DESIGNED | P | Coverage defects. | Trace/check implementation. | No. |
| `COV-REQ-PASS-003` | USER_ACCEPTED distinct. | P 9 | DESIGNED | P | Acceptance granularity. | User decision interface. | Yes. |
| `COV-REQ-PASS-004` | TASK_CLOSED distinct. | P 9 | DESIGNED | P | Governance-state integration. | Closeout implementation. | As gate requires. |
| `COV-REQ-BATCH-001` | Gate batching reduces burden without hiding decisions. | P 10 | DESIGNED | P | Batch window calibration. | Decision UX/pilot. | Yes for items. |
| `COV-REQ-CONFLICT-001` | Conflict contract and no automatic supersession. | P 11 | DESIGNED | P | Precedence may stay ambiguous. | User escalation path. | Yes when unresolved. |
| `COV-REQ-QUEUE-001` | Queued/unpersisted/unconsumed/conflict blocks PASS/closeout/eligibility. | P 12 | DESIGNED | P | Queue inventory may be incomplete. | Durable queue/check. | On disposition. |
| `COV-REQ-LIVE-001` | Batching, merge, fast path, rebase ceiling/no-progress/timeout/freeze. | P 13 | DESIGNED | P | Threshold tradeoffs. | Profile/runtime implementation. | On escalation options. |
| `COV-REQ-EXAMPLE-001` | Actual T-0034 old handoff slice vs new Kernel drift. | P 14 | DESIGNED | P | Independent review pending. | L0 disk review. | Acceptance pending. |

| `COV-CHECK-001` | Kernel schema/hash/trace/authority checks. | A 12 | DESIGNED | A | Executables absent. | Validator implementation. | Before enablement. |
| `COV-CHECK-002` | Lease/generation/liveness/profile/budget/security checks. | A 12 | DESIGNED | A | Runtime telemetry absent. | Controller/tooling implementation. | Before activation. |
| `COV-CHECK-003` | Handoff/no-auto-effect checks. | A 12 | DESIGNED | A | Integration missing. | Closeout implementation. | Before activation. |
| `COV-CHECK-004` | Field semantics and candidate identity checks. | P 15 | DESIGNED | P | Schema absent. | Requirements validator. | No. |
| `COV-CHECK-005` | Role/finalizer checks. | P 15 | DESIGNED | P | Capability enforcement absent. | Registrar implementation. | Before runtime. |
| `COV-CHECK-006` | Safe-point and generation fence checks. | P 15 | DESIGNED | P | Atomic store absent. | Runtime tests. | Before activation. |
| `COV-CHECK-007` | Dual hash and normalization trace checks. | P 15 | DESIGNED | P | Golden corpus absent. | Canonicalizer tests. | No. |
| `COV-CHECK-008` | Gate batch and output admission checks. | P 15 | DESIGNED | P | Budget prediction imperfect. | Decision/output tooling. | On cost/scope. |
| `COV-CHECK-009` | Conflict and queue-closeout-block checks. | P 15 | DESIGNED | P | Queue durability absent. | Queue/reconciler implementation. | On conflict disposition. |
| `COV-CHECK-010` | No-impact, freshness, PASS layering, rebase liveness checks. | P 15 | DESIGNED | P | Semantic proof needs review. | Reconciler implementation. | On uncertain impact. |
| `COV-ACCEPT-001` | Kernel acceptance criteria. | A 13 | DESIGNED | A | No independent acceptance yet. | Independent design review. | Yes: accept/reject. |
| `COV-ACCEPT-002` | Revision protocol acceptance criteria. | P 16 | DESIGNED | P | No executable proof yet. | Independent review/implementation. | Yes: accept/reject. |
| `COV-ADV-001` | Kernel adversarial catalog: split brain, stale PASS, authority inflation, audit mutation. | A 14 | DESIGNED | A | Tests not implemented. | Test implementation gate. | No. |
| `COV-ADV-002` | Kernel adversarial catalog: retry, budget, privacy, schema, handoff, self-loop, partial write, install trap. | A 14 | DESIGNED | A | Tests not implemented. | Test implementation gate. | No. |
| `COV-ADV-003` | Revision adversarial: field ambiguity, self-finalization, stale fence, candidate disguise. | P 17 | DESIGNED | P | Tests not implemented. | Requirements test suite. | No. |
| `COV-ADV-004` | Revision adversarial: normalization bug, gate explosion, truncation, false supersession. | P 17 | DESIGNED | P | Tests not implemented. | Requirements test suite. | On conflict only. |
| `COV-ADV-005` | Revision adversarial: queued closeout, persisted-not-committed, missing ack, hidden semantic drift, endless rebase, PASS inference. | P 17 | DESIGNED | P | Tests not implemented. | Requirements test suite. | On escalations. |
| `COV-IFACE-001` | Interface cleanup: four explicit revision identity fields. | P 2 | DESIGNED | P | Legacy consumer ambiguity. | Schema migration. | Before migration. |
| `COV-IFACE-002` | Interface cleanup: five separated roles. | P 4 | DESIGNED | P | Enforcement absent. | Capability model. | Before runtime. |
| `COV-IFACE-003` | Interface cleanup: safe-point acknowledgment and generation fence. | P 7 | DESIGNED | P | Race tests absent. | Runtime implementation. | Before activation. |
| `COV-IFACE-004` | Interface cleanup: candidate vs committed identity. | P 2-3 | DESIGNED | P | Legacy aliases. | Migration scanner. | No. |
| `COV-IFACE-005` | Interface cleanup: dual hash and normalization trace. | P 6 | DESIGNED | P | Canonicalizer risk. | Golden vectors. | No. |
| `COV-IFACE-006` | Interface cleanup: gate batching and user burden. | P 10 | DESIGNED | P | UX calibration. | Decision packet implementation. | Yes for batched items. |
| `COV-IFACE-007` | Interface cleanup: output budget fail-safe. | A 8; P 18 | DESIGNED | A,P | Estimation uncertainty. | Admission implementation. | On scope reduction. |
| `COV-IFACE-008` | Interface cleanup: conflict resolution contract. | P 11 | DESIGNED | P | Business ambiguity. | Escalation workflow. | Yes if unresolved. |
| `COV-IFACE-009` | Interface cleanup: queued rebase closeout block. | P 12 | DESIGNED | P | Queue completeness. | Durable queue/check. | On disposition. |

## Coverage summary

- Total stable requirements: 76.
- Status: 76 `DESIGNED`; 0 implemented; 0 installed; 0 activated; 0 independently accepted.
- Envelope coverage: 10 original Envelope types plus 3 requirements-control types.
- Assurance coverage: 4 layers, 4 profiles, lifecycle/liveness, controller uniqueness, resource/security/schema/handoff specializations.
- Revision coverage: identities, roles, persistence/commit, dual hash, safe point/fence, 8 impact verdicts, freshness, 4 PASS layers, batching, conflict, queue block, perpetual-rebase protection, and the actual T-0034 drift.
- Verification coverage: 29 machine-check groups/IDs represented by rows, 26 adversarial scenarios represented by rows, and separate Kernel/protocol acceptance rows.
- Residual risk is concentrated in absent implementation, independent review, runtime atomicity, canonicalization correctness, profile calibration, and future user decisions.

End of `control-plane-assurance-kernel.coverage-matrix.v0.1.md`.
