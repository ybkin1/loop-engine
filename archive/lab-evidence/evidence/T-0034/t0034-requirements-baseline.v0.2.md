# T-0034 Canonical Requirements Baseline v0.2

```yaml
baseline_id: T-0034-REQ-2026-07-16-R1
schema_version: 1
artifact_version: 0.2
status: canonical_design_repair_baseline
payload_sha256: A262B227ABA88E1CF3F235BF7CA9F9FB3023985F5EFDF017FAE05F8FF169582F
hash_scope: UTF-8 LF bytes strictly between CANONICAL-PAYLOAD markers, excluding the marker lines
authority_source: user-approved G-T-0034-REPAIR-DESIGN-COVERAGE-AND-ASSURANCE-GAPS
implementation_authorized: false
independent_review_authorized: false
task_closeout_authorized: false
```

<!-- CANONICAL-PAYLOAD-BEGIN -->
## Mission

Help a non-technical user turn rough intent into usable, verifiable, deployable, acceptable, maintainable, and sustainably iterable software. Codex owns end-to-end technical delivery inside approved boundaries. Governance reduces delivery risk and user burden and never replaces product delivery.

## Authority And Lifecycle Invariants

- `AUTH-01`: Only the user may approve gates, accept residual risk, approve baselines, authorize effects, or accept delivery.
- `AUTH-02`: Design, implementation, review, installation, activation, deployment, migration, real-project entry, acceptance, and closeout are separate effects.
- `AUTH-03`: Controllers, agents, validators, tests, reviewers, and auditors produce evidence only and cannot create or expand authority.
- `AUTH-04`: Missing or conflicting canonical baselines produce `BASELINE_MISSING` or `USER_DECISION_REQUIRED`; invention is forbidden.
- `AUTH-05`: Existing evidence is immutable; correction is additive and versioned.
- `AUTH-06`: Local or stale PASS cannot satisfy current-task, whole-product, user-acceptance, or closeout requirements.
- `AUTH-07`: Safety includes liveness, bounded cost, recovery, convergence, and anti-self-loop controls.

## Required Workstreams

| ID | Workstream | Required result |
|---|---|---|
| `WS-01` | Project Continuity Baseline and controlled evolution | Canonical continuity fields, protected invariants, golden references, change authority, conflict handling, and revision lineage. |
| `WS-02` | HANDOFF, bootstrap, checkpoint, reading tiers, and indexes | Bounded recovery packet, evidence/archive indexes, successor probe, semantic equivalence, and context budgets. |
| `WS-03` | Controller generations and safe continuity | Context admission, checkpoints, active transactions, leases, fences, emergency recovery, and safe rotation. |
| `WS-04` | L0/L1/L2 control flow | Scope-subset proof, envelope contracts, authority containment, evidence fan-in, and deterministic transaction state machines. |
| `WS-05` | Neutral professional assurance | Neutral Audit Charter plus product, architecture, technology, API/protocol, coding, QA, security, performance, delivery, project, handoff, and continuity overlays. |
| `WS-06` | Verification and bounded repair | VerificationPlan, AssuranceProfile, deterministic checks, findings, verdicts, blocking thresholds, convergence, and user escalation. |
| `WS-07` | Continuity and drift governance | Step, anchor, and goal drift, acknowledgements, Drift Ledger, golden references, correction, and controlled re-baseline. |
| `WS-08` | Executable acceptance and downstream boundaries | Machine-verifiable acceptance plus separate implementation, review, installation, activation, pilot, real-project, acceptance, and closeout boundaries. |

## Required Output Classes

| ID | Output class | Canonical requirement |
|---|---|---|
| `OUT-01` | Project Continuity Contract/schema | Versioned schema covering user origin, product identity, protected decisions, non-goals, design language, architecture/technology/interface/coding invariants, golden references, and evolution. |
| `OUT-02` | Bootstrap/checkpoint/HANDOFF/successor contract | Reading tiers, budgets, checkpoint completeness, active transactions, evidence indexes, successor state, traps, and attestation. |
| `OUT-03` | Controller data flow and transaction state machines | Complete L0/L1/L2 scope, admission, fan-out/fan-in, commit, conflict, fence, rotation, recovery, and closeout-block states. |
| `OUT-04` | Versioned controller/agent interface schemas | Common headers and typed packets/results/errors with compatibility, idempotency, freshness, authority, and provenance semantics. |
| `OUT-05` | Neutral Audit Charter and assurance schemas | Neutral core, professional overlays, AssuranceProfile, Finding, Verdict, evidence and independence requirements. |
| `OUT-06` | Continuity/drift roles and ledger | Contracts for Continuity Checker, Drift Auditor, Continuity Repair Planner, Re-anchor Auditor, and a versioned Drift Ledger. |
| `OUT-07` | Verification/acceptance/blocking/convergence/recovery rules | PASS layers, blocking rules, repair lifecycle, bounded retries, no-progress escalation, recovery, and anti-self-loop acceptance. |
| `OUT-08` | Machine-check catalog and adversarial golden vectors | Deterministic checker inputs, outputs, algorithms, fixtures, expected verdicts, and coverage for required threat scenarios. |
| `OUT-09` | Reviewed downstream boundaries | Design repair stops before independent review; later implementation, review, installation, activation, pilot, real-project entry, acceptance, and closeout each require separate gates. |

## Global Acceptance Criteria

- `AC-01`: Every `WS-*` and `OUT-*` maps to artifacts, explicit acceptance criteria, deterministic checks, and review roles.
- `AC-02`: Child scope and authority are provable subsets of parent scope and authority.
- `AC-03`: Evidence fan-in preserves every blocking/high-severity finding and cannot upgrade verdict layers.
- `AC-04`: Controller rotation cannot lose, duplicate, or commit in-flight effects from a fenced generation.
- `AC-05`: Successor recovery reproduces protected control semantics without full chat history.
- `AC-06`: Step, anchor, and goal drift are independently evaluated with evidence and trend.
- `AC-07`: Missing/conflicting baselines fail closed without inventing requirements.
- `AC-08`: Machine checks have deterministic inputs, expected outputs, and golden vectors.
- `AC-09`: Repair terminates on PASS, BLOCKED, USER_DECISION_REQUIRED, budget exhaustion, or no-progress threshold.
- `AC-10`: Governance effort is bounded and cannot substitute for real product progress.
- `AC-11`: No design artifact, validator, audit, or AI conclusion implies user approval or task/project PASS.
- `AC-12`: Repair execution produces complete UTF-8/hash/command/changed-path/protected-baseline/cross-file evidence and then stops before review.

## Source Chain And Revision Record

| Source | Role |
|---|---|
| `.ai/PROJECT.md` | User outcome and product north star. |
| `.ai/tasks/T-0034.md` | Approved task scope and forbidden effects. |
| `.ai/evidence/T-0034/project-continuity-controller-assurance.decision-packet.v0.1.md` | Eight workstreams, nine outputs, risks, acceptance. |
| `.ai/evidence/T-0034/session-design-synthesis.v0.1.md` | Consolidated hierarchy, continuity, neutral audit, drift, liveness, budgets. |
| `.ai/evidence/T-0034/handoff-writing-standard.v0.1.md` | Existing HANDOFF/checkpoint contract evidence. |
| `.ai/evidence/T-0034/current-main-controller-handoff.v0.1.md` | Current continuity state and known gaps. |
| Three Control-Plane Assurance Kernel v0.1 artifacts | Local design evidence retained unchanged. |
| `G-T-0034-REPAIR-DESIGN-COVERAGE-AND-ASSURANCE-GAPS` | User-approved authority for additive v0.2 repair only. |

Revision `R1` consolidates source requirements without superseding immutable source evidence. Any future change requires a new revision ID, source diff, impact assessment, explicit authority, new payload hash, and additive lineage entry.
<!-- CANONICAL-PAYLOAD-END -->

## Boundary

This baseline is design evidence only. It does not implement, install, activate, review, accept, close, deploy, migrate, create downstream tasks, or enter a real project.
