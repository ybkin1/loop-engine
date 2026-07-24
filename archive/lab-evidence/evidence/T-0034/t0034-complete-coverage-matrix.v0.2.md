# T-0034 Complete Coverage Matrix v0.2

Matrix ID: `TCM-2026-07-16-R1`. Requirements revision: `T-0034-REQ-2026-07-16-R1`.

Status `DESIGNED_PENDING_INDEPENDENT_REVIEW` means the repair artifact exists and has execution checks, but no independent review, artifact PASS, T-0034 PASS, closeout, or user acceptance is asserted.

## 1. Workstream Coverage

| ID | Artifact/section | Acceptance | Deterministic/adversarial tests | Required later review roles | Status |
|---|---|---|---|---|---|
| `WS-01` | `t0034-requirements-baseline.v0.2.md`; `project-continuity-contract.v0.2.md` | `AC-01`, `AC-07`, PCC invariants/evolution | `MC-BASE-001`, `MC-PCC-001..005`, `GV-010`, `GV-013` | product, continuity, architecture, governance | DESIGNED_PENDING_INDEPENDENT_REVIEW |
| `WS-02` | PCC §§5-7; existing `handoff-writing-standard.v0.1.md`; CDFT §§6-8 | `AC-04`, `AC-05`, complete checkpoint and successor attestation | `MC-FENCE-001`, `MC-DRIFT-001`, `GV-006`, `GV-014` | handoff, continuity, recovery, product | DESIGNED_PENDING_INDEPENDENT_REVIEW |
| `WS-03` | `controller-data-flow-transaction-contracts.v0.2.md` §§5-8 | Legal guarded transitions, leases, fences, safe rotation/recovery | `MC-TX-001`, `MC-FENCE-001`, `GV-006`, `GV-008`, `GV-016` | controller architecture, correctness, recovery, security | DESIGNED_PENDING_INDEPENDENT_REVIEW |
| `WS-04` | CDFT §§1-4; `controller-agent-interface-schemas.v0.2.md` | `AC-02`, `AC-03`; child subset and lossless fan-in | `MC-SCOPE-001`, `MC-FANIN-001`, `MC-SCHEMA-001`, `GV-003..005` | architecture, API/protocol, security, evidence integrity | DESIGNED_PENDING_INDEPENDENT_REVIEW |
| `WS-05` | `neutral-audit-charter-assurance-schemas.v0.2.md` | Neutral core, required overlays, independence and evidence-only authority | `MC-AUDIT-001`, `ADV-AUDIT-001..003` | product, architecture, API, QA, security, performance, delivery, handoff, continuity | DESIGNED_PENDING_INDEPENDENT_REVIEW |
| `WS-06` | NAC; `verification-acceptance-convergence-recovery-rules.v0.2.md` | `AC-08`, `AC-09`; deterministic verdict, findings, bounded repair | `MC-PASS-001`, `MC-CONV-001`, `MC-COVER-001`, `GV-005`, `GV-009`, `GV-012`, `GV-015` | QA, correctness, security, evidence integrity, governance | DESIGNED_PENDING_INDEPENDENT_REVIEW |
| `WS-07` | `continuity-drift-role-contracts-ledger.v0.2.md` | `AC-06`; three drift dimensions, four roles, append-only ledger, re-anchor | `MC-DRIFT-001`, `GV-010..013` | continuity, product, architecture, golden-reference, evidence integrity | DESIGNED_PENDING_INDEPENDENT_REVIEW |
| `WS-08` | VACR §§4,8-12; downstream plan; Gate boundaries | `AC-10..12`; executable acceptance and separated lifecycle effects | `MC-COVER-001`, `MC-PATH-001`, `MC-PROTECT-001`, `MC-UTF8-001`, `GV-016` | delivery, governance boundary, QA, product | DESIGNED_PENDING_INDEPENDENT_REVIEW |

## 2. Required Output Coverage

| ID | Artifact/section | Acceptance | Deterministic/adversarial tests | Required later review roles | Status |
|---|---|---|---|---|---|
| `OUT-01` | `project-continuity-contract.v0.2.md` | Required schema fields and `PCC-I01..08` | `MC-PCC-001..005`, `ADV-PCC-001..002` | continuity, architecture, product, security | DESIGNED_PENDING_INDEPENDENT_REVIEW |
| `OUT-02` | PCC §§5-7; existing HANDOFF standard; CDFT rotation/recovery | Bounded R0-R3 reading, complete checkpoint, successor equivalence | `MC-BASE-001`, `MC-FENCE-001`, `GV-006`, `GV-014` | handoff, continuity, recovery | DESIGNED_PENDING_INDEPENDENT_REVIEW |
| `OUT-03` | `controller-data-flow-transaction-contracts.v0.2.md` | Complete hierarchy, subset, fan-in and transaction guards | `MC-SCOPE-001`, `MC-FANIN-001`, `MC-TX-001`, `GV-003..006` | architecture, correctness, security, recovery | DESIGNED_PENDING_INDEPENDENT_REVIEW |
| `OUT-04` | `controller-agent-interface-schemas.v0.2.md` | Versioned envelopes, compatibility, idempotency, freshness, errors | `MC-SCHEMA-001`, `MC-COMPAT-001`, `MC-FRESH-001`, `GV-007..009` | API/protocol, architecture, security, compatibility | DESIGNED_PENDING_INDEPENDENT_REVIEW |
| `OUT-05` | `neutral-audit-charter-assurance-schemas.v0.2.md` | Charter, 12 overlays, AssuranceProfile, Finding and Verdict schemas | `MC-AUDIT-001`, `ADV-AUDIT-001..003` | all selected professional overlays | DESIGNED_PENDING_INDEPENDENT_REVIEW |
| `OUT-06` | `continuity-drift-role-contracts-ledger.v0.2.md` | Four role contracts, ledger fields/lifecycle and drift rules | `MC-DRIFT-001`, `GV-010..013` | continuity, product, architecture, evidence integrity | DESIGNED_PENDING_INDEPENDENT_REVIEW |
| `OUT-07` | `verification-acceptance-convergence-recovery-rules.v0.2.md` | PASS layers, acceptance, blocking, lifecycle, convergence, recovery, anti-loop | `MC-PASS-001`, `MC-CONV-001`, `GV-009`, `GV-012`, `GV-015` | QA, correctness, recovery, product/governance | DESIGNED_PENDING_INDEPENDENT_REVIEW |
| `OUT-08` | `machine-check-adversarial-golden-vectors.v0.2.md` | 16 checker contracts and 16 deterministic golden vectors | `GV-001..016` plus malformed-input exit-2 rule | QA automation, security, correctness, continuity | DESIGNED_PENDING_INDEPENDENT_REVIEW |
| `OUT-09` | downstream plan + corrected Gate + VACR boundary | Repair stops before review; every later effect separately gated | `MC-PASS-001`, `MC-PATH-001`, `GV-015`, `GV-016` | delivery, governance boundary, product | DESIGNED_PENDING_INDEPENDENT_REVIEW |

## 3. Acceptance Coverage

All `AC-01..12` are referenced above. `AC-01` is mechanically satisfied by exact set equality of eight WS rows and nine OUT rows; no blanket row substitutes for itemized coverage. `AC-12` is completed only by the executor, command, changed-path, protected-baseline, consistency, and final validation evidence.

## 4. Review Boundary

No review is performed by this matrix. A later separate pending review Gate must freeze artifact hashes, define the review evidence path, require fresh independent L0 context, and apply the roles listed above.
