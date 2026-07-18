# 2026-07-15 Unified Loop Engineering Design Synthesis

## Purpose

This is consolidated planning input for T-0034. It prevents reliance on chat memory and does not authorize implementation, installation, activation, orchestration, or real-project entry.

## Mission And User Position

- Serve a non-technical user who provides goals, business facts, key tradeoffs, and explicit gate decisions.
- Codex owns technical discovery, planning, implementation, verification, review, repair, delivery preparation, and handoff inside approved boundaries.
- Governance reduces risk and user burden; it is not the product and must not become a documentation self-loop.
- The desired experience is that the user starts a formal task, intervenes only for genuine business decisions or gates, and later receives a usable, deeply verified result with traceable residual risk.

## Reference And Target Workflow

The current manual flow is the behavioral reference:

```text
main controller creates a complete prompt
-> user opens an independent session
-> session reports
-> main controller validates disk facts
-> a complete repair prompt is issued when needed
-> an independent audit session reviews
-> repair and re-audit continue until convergence
```

The future system automates transport, not authority. It preserves separate creation, approval, execution, review, repair, installation, activation, and real-project gates.

## Controller Hierarchy And Data Flow

```text
User
-> L0 Project / Program Controller
-> L1 Task Controller
-> L2 Execution, Repair, Verification, Audit Agents
-> Deterministic Tools And Disk Facts
```

- L0 owns the project north star, roadmap, cross-task dependencies, task admission, gate requests, phase state, and task-closeout synthesis.
- L1 owns one task, its iterations, TaskPackets, deterministic validation, verifier/auditor dispatch, findings, repair convergence, and Task Closeout Envelope.
- L2 agents are fresh-context, single-purpose units. Execution, repair, verification, and audit contexts remain independent.
- L2 never reports directly to L0; L1 validates and fans in evidence first.
- Child scope must be a subset of parent scope and user authorization.
- Prompts, logs, diffs, and reports live on disk. Cross-layer messages carry versioned paths, hashes, statuses, blockers, and high-severity findings only.
- Every controller is a replaceable session generation; chat is never a fact source.

## Context, Admission, And Rotation

- Context compaction is not the continuity mechanism; canonical facts remain on disk.
- New controllers first read a small Bootstrap Capsule, not all history.
- Required Reading uses Tier 0 bootstrap, Tier 1 action-specific, and Tier 2 exception/audit material.
- Bootstrap and iteration admission have independent size, file-count, result-ingestion, validation, closeout-reserve, and safety budgets.
- An iteration starts only when the controller can complete it and preserve closeout reserve.
- Rotation occurs only at stable checkpoints: before execution, after a frozen/validated result, after audit, after repair, or after phase closeout.
- Normal rotation is forbidden during writes, tests, state transitions, partial evidence, installation, activation, migration, active transactions, or in-flight agents.
- Emergency handoff records untrusted partial writes and requires recovery rather than pretending successful continuity.
- HANDOFF remains short and operational; checkpoint records reference canonical facts by ID, version, path, and hash.

## Handoff Quality

- Success means equivalent control semantics, not copied chat memory.
- The predecessor emits ExpectedControllerState; a fresh successor probe emits RecoveredControllerState.
- Machine comparison covers user goal, phase/task/gate/iteration, authorization, allowed/forbidden scope, protected decisions, blockers, findings, active transaction, and the unique next safe action.
- Counterfactual traps test approval-vs-execution, PASS-vs-acceptance, candidate-vs-installed, local-vs-product completion, and stale-action errors.
- Producer and consumer attestations form a handoff double-signature. Failed semantic equivalence blocks normal closeout.

## Project And Engineering Continuity

- HANDOFF is short-term state and cannot replace the long-term Project Continuity Baseline.
- The versioned baseline covers user origin, product north star, identity, philosophy, protected decisions, non-goals, design language, architecture invariants, technology choices, interfaces/protocols, coding standards, implementation conventions, golden journeys/references, and delivery constraints.
- Every controller re-anchors to both checkpoint and approved baseline.
- Baselines evolve only through explicit change decisions/gates; original versions remain immutable.
- Every task declares continuity impact and references relevant invariant IDs/hashes.

## Drift Model And Roles

- Step drift compares current and previous stable states and detects sudden change.
- Anchor drift compares current state with the approved baseline and detects cumulative micro-drift.
- Goal drift compares delivered outcome with the user's business goal and detects locally coherent but irrelevant work.
- A drift ledger records baseline version, affected invariants, approved/unexplained changes, cumulative trend, and correction status.
- Phase, installation, activation, and release require full re-anchor audits, not only incremental review.
- Continuity Checker performs lightweight checks; Drift Auditor performs fresh-context deep review; Continuity Repair Planner proposes correction but cannot edit; Re-anchor Auditor reassesses the whole product.
- Drift output is multidimensional severity, trend, authorization, scope, evidence, and correction?not a false-precision percentage.

## Neutral Audit Charter

All controllers, reviewers, verifiers, auditors, repair planners, handoff editors, successor probes, and re-anchor auditors share a versioned neutral core:

- Fresh context and read-only review by default.
- Canonical user decisions, approved baselines, disk facts, task/gate scope, and reports have explicit precedence.
- Evidence outranks confidence, sunk cost, deadlines, author narrative, prior PASS, or controller recommendation.
- No sycophancy, self-approval, scope expansion, baseline invention, evidence rewriting, test weakening, or convenience-based severity reduction.
- Missing/conflicting required baselines return BASELINE_MISSING or BLOCKED.
- Findings cite requirement/invariant, canonical reference, observed evidence, comparison/reproduction, impact, authorization, correction, gate need, confidence, and limitations.
- Verdicts are PASS, PASS_WITH_RESIDUAL_RISK, REPAIR_REQUIRED, USER_DECISION_REQUIRED, BLOCKED, SCOPE_VIOLATION, or BASELINE_MISSING. All remain evidence only.

## Professional Assurance Dimensions

Risk-selected roles cover:

- Product outcome and continuity.
- Architecture boundaries, dependency direction, state/data authority, trust boundaries, deployment shape, and ADR compliance.
- Technology and dependency necessity, maintenance, security, licensing, versioning, compatibility, and operational burden.
- API/protocol types, optionality, errors, idempotency, ordering, retry, timeout, authentication, authorization, pagination, events, evolution, and backward compatibility.
- Coding standards/style, naming, structure, typing, errors, logs, configuration, secrets, complexity, duplication, coupling, and canonical patterns.
- Correctness across happy, error, edge, concurrency, precision, time, partial failure, retry, and resource cleanup.
- Test plans, implementations, assertions, fixtures, mocks, traceability, skips, flakiness, regression, contract, integration, end-to-end, security, and operational evidence.
- Security, privacy, performance, capacity, observability, reproducible build, installation, activation, deployment, rollback, recovery, runbooks, and support readiness.
- Scope, dependencies, milestones, blockers, repeated rework, no-progress loops, context budget, handoff readiness, and progress toward real software rather than governance output.

## Verification And Convergence

```text
executor self-check
-> controller deterministic verification
-> fresh verifier
-> risk-triggered adversarial auditor
-> L1 evidence fan-in
-> L0 project/phase synthesis
-> user gate where required
```

- Controllers directly verify schemas, paths, hashes, manifests, protected files, commands, exit codes, governance consistency, evidence presence, and unauthorized artifacts.
- Independent agents assess semantic correctness, architecture, tests, risk, continuity, and drift.
- Assurance profiles select roles by risk and prevent infinite reviewer chains.
- VerificationPlan is fixed before execution and maps requirements/invariants to checks, commands, roles, evidence, allowed findings, PASS, blockers, and rerun rules.
- Technical PASS requires complete acceptance evidence, mandatory checks, scope integrity, required independent review, no unresolved P0/P1, disclosed residual risk, consistent governance state, valid handoff, no active transaction, and no in-flight agent.
- Findings have stable IDs/lifecycle. Repair addresses only open findings. Repeated blockers, no progress, new gate needs, or missing business facts stop and escalate.

## Executable Anti-drift Controls

- Visual systems: design tokens, canonical components, golden screenshots, browser review, visual diff.
- Interfaces: schemas, compatibility rules, contract tests.
- Architecture: ADRs, dependency/module boundaries, forbidden dependencies, architecture tests.
- Code: formatter, linter, canonical examples, complexity limits.
- Requirements: business-goal -> scenario -> code -> test -> finding -> acceptance traceability.
- Local PASS never substitutes for whole-product continuity and golden-journey verification.

## Current Gaps And Non-negotiable Boundaries

- Project-specific `CONVENTIONS.md` and `ARCHITECTURE.md` remain incomplete; `CODING_STANDARDS.md` is generic. Audits must report missing baselines instead of inventing them.
- Useful designs are distributed across earlier candidate evidence; T-0034 must unify interfaces without creating competing authorities.
- Actual orchestration, automatic loops, installation, activation, and real-project use remain unauthorized.
- Tests, reviews, validators, auditors, subagents, and AI recommendations are evidence, not user authorization.
- Original evidence remains immutable; later correction uses addenda.
- Unclear authority stops rather than expands impact.
