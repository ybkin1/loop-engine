# Progress

## Current Status

S0-method-repair. Current task is T-0020: Real Project Governance Enforcement
Architecture Review.

T-0020 is blocked on a pending review-only gate:

```text
G-T-0020-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-REVIEW
```

This gate has not been approved. The current user prompt requested gate
creation and presentation only; it is not approval.

Allowed before approval:

- startup validation
- T-0020 task registration
- gate request evidence
- user decision packet
- pending gate record

No T-0020 review body has started. No checker was implemented. No MCP, skill,
policy guard, wrapper, automation, protocol, runtime, or tool behavior was
installed or enabled. No `AGENTS.md` change, real-project entry, business code,
build, deployment, release, rollback, database, permission, secret, payment,
production-data, migration, or baseline promotion occurred.

Exact approval phrase required:

```text
批准 G-T-0020-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-REVIEW
```

Previous task was T-0019: Real Project Governance Enforcement Architecture
Design.

T-0019 is completed as a design-only / repair-candidate task.

The user explicitly approved:

```text
G-T-0019-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-DESIGN
```

T-0019 produced candidate design evidence for making T-0017 Markdown governance
rules enforceable, auditable, and hard to skip in future real-project work.

Primary outputs:

- machine-readable gate register schema
- checker catalog and blocking semantics
- policy guard / wrapper design
- tool-entry restriction model
- evidence and audit enforcement design
- failure mode and recovery design
- T-0017 repair coverage map

Self-review result:

```text
PASS_FOR_DESIGN_CANDIDATE
```

T-0019 remains design-only. It did not implement, install, or enable any
checker, policy guard, wrapper, MCP, skill, runtime, automation, protocol, or
tool behavior. It did not modify `AGENTS.md`, enter a real project, deploy,
roll back, change databases, change permissions, handle secrets, perform
payment actions, touch production data, or run migrations.

Recommended next gate:

```text
G-T-0020-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-REVIEW
```

Previous task was T-0018: Real Project Delivery And Architecture Governance
Review.

T-0018 is completed as a review-only task. The user explicitly approved the
review-only gate:

```text
G-T-0018-REAL-PROJECT-DELIVERY-ARCHITECTURE-GOVERNANCE-REVIEW
```

Review verdict:

```text
repair required
```

Finding counts:

```text
P0=0
P1=1
P2=2
P3=1
```

Primary blocker:

```text
FIND-T0018-P1-001
```

T-0017 is not ready for baseline consideration because its controls remain
Markdown-only and lack a concrete enforcement architecture.

Recommended next gate:

```text
G-T-0019-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-DESIGN
```

T-0018 did not authorize real-project entry, implementation, repair,
`AGENTS.md` change, runtime/tool enablement, deployment, rollback, database,
permission, secret, payment, production-data, or migration action.

Previous task was T-0017: Real Project Delivery And Architecture Governance
Design.

T-0017 is completed as a design-only / candidate-only task.

The user explicitly approved:

```text
G-T-0017-REAL-PROJECT-DELIVERY-ARCHITECTURE-GOVERNANCE-DESIGN
```

T-0017 produced a candidate governance package for how Codex should conduct
real software projects from rough idea through discovery, domain model, PRD,
architecture baseline, detailed design, implementation readiness, review,
handoff, and iteration.

Primary T-0017 package entry point:

```text
.ai/evidence/T-0017/package-index.real-project-delivery-architecture-governance.candidate.v0.1.md
```

T-0017 did not enter, create, or modify a real business project. It did not
write business code, build, deploy, release, roll back, modify `AGENTS.md`,
enable runtime/tool behavior, or touch database, permission, secret, payment,
production-data, or migration resources.

Recommended next step is a separate review-only gate, not real-project entry or
implementation:

```text
G-T-0018-REAL-PROJECT-DELIVERY-ARCHITECTURE-GOVERNANCE-REVIEW
```

Previous task was T-0016: Startup Rules Acceptance Smoke Test.

T-0016 verified the newly installed project-local `AGENTS.md` startup and
operating rules. Verified `AGENTS.md` SHA256:

```text
7D9B688C8364E4E2AA79D6878376B19D1E98FBC850A8116E297C50AB18F391BA
```

Previous task was T-0015: Method Operating Rules Installation Execution.

T-0015 is completed.

The user explicitly approved:

```text
G-T-0015-METHOD-OPERATING-RULES-EXECUTION
```

The exact approved T-0014 patch was applied to `AGENTS.md`.

Pre-execution SHA256:

```text
DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87
```

Post-execution SHA256:

```text
7D9B688C8364E4E2AA79D6878376B19D1E98FBC850A8116E297C50AB18F391BA
```

No external runtime, skill, MCP, automation, protocol, tool behavior, real
business project, build, deployment, rollback, database, permission, secret,
payment, production-data, or migration action occurred.

Previous task was T-0013: Method Operating Rules / Installation Design.

T-0013 created a candidate operating-rules / installation design package and the user explicitly approved the design gate:

```text
G-T-0013-METHOD-OPERATING-RULES-DESIGN
```

This approval accepts the T-0013 design package as candidate evidence only.

T-0013 is design-only. It does not install or enable the repaired method, modify `AGENTS.md`, change runtime behavior, or apply the method to a real project.

The user explicitly approved `G-T-0012-METHOD-BASELINE-APPROVAL`.
The approval is recorded as explicit user approval, not AI approval.

T-0008 changed the main line from the concrete T-0007 product sample to the method problem exposed by that sample. T-0007 remains a quarantined discovery-method stress test and must not be treated as the active product project unless the user explicitly reopens it.

T-0009 reviewed the T-0008 candidate and found no P0 issue. It found P1 repair requirements before baseline or installation:

- formal lifecycle/status transition model
- repeatable repair loop
- real-project entry isolation
- operational artifact schemas deep enough to generate Harness-like design packages

T-0010 completed repair-only / candidate-update-only work. It added lifecycle state, gate request, real-project entry, artifact schema, traceability ID, user decision packet, repair loop, handoff hygiene, design baseline readiness, repair summary, and next-gate recommendation artifacts. T-0010 remains candidate-only.

T-0011 completed the review-rerun. Result:

```text
PASS_RECOMMENDED_FOR_BASELINE_CANDIDATE
```

T-0011 found:

- no P0
- all T-0009 P1 repairs pass review-rerun
- major T-0009 P2 repairs are accepted
- expanded worked examples and a dry-run test plan are deferred as non-blocking enhancements before installation or real-project application
- the repaired candidate is recommended to move from `repaired` to `baseline_candidate`

This is not baseline approval. It is not installation. It is not active operating rules. It is not reflected in `AGENTS.md`. It is not applied to a real business project.

The baseline approval gate has now been approved:

```text
G-T-0012-METHOD-BASELINE-APPROVAL
```

The repaired Loop engineering method candidate is baseline-approved as a reference only:

```text
baseline_candidate -> baseline_approved
```

This is not installation. It is not active operating rules. It is not reflected in `AGENTS.md`. It is not applied to a real business project.

Do not recommend installation, `AGENTS.md` modification, or real-project application without a later separate explicit gate.

No real product project was created. No real business project root was entered. No business project files were modified. No `AGENTS.md` change, skill/MCP/agent/automation/protocol enablement, build, implementation, deployment, rollback, database, permission, secret, payment, production-data, migration, or runtime behavior change occurred.

## Recently Completed

- Initialized project governance for the loop-engine-lab governance project.
- Created task T-0001.
- Captured the project charter summary as a candidate evidence artifact.
- Created `unified-design-brief.candidate.v0.1.md` as the main T-0001 design brief.
- Created `generic-handoff-spec.candidate.v0.1.md` as a temporary handoff format for near-term use.
- Created task T-0002.
- Saved `unified-governance-architecture.candidate.v0.2.1.md` as T-0002 candidate evidence after addressing P2 review notes.
- Saved `unified-governance-architecture.review-report.v0.2.1.md` with `PASS_RECOMMENDED`, no P0/P1/P2/P3 findings, and no blocking residual risk.
- Recorded the explicit user gate approving T-0002 Candidate v0.2.1 as `approved` evidence only.
- Recorded artifact registry status for `unified-governance-architecture.v0.2.1`: `approved: true`, `active: false`, `installed: false`.
- Saved `activation-installation-plan.candidate.v0.1.md` as T-0002 evidence.
- Recorded a PASS_RECOMMENDED review summary for the activation / installation plan as T-0003 background evidence.
- Created T-0003 and synchronized governance state to make T-0003 the current task.
- Recorded the user's activation-only gate for `unified-governance-architecture.v0.2.1`: `approved: true`, `active: true`, `installed: false`.
- Saved `activation-installation-plan.formal.v0.1.md` as T-0003 formal evidence.
- Created T-0004 for placeholder cleanup under the user's explicit cleanup gate.
- Replaced placeholder-only content in `.ai/CONTRACTS.md`, `.ai/ACCEPTANCE.md`, and `.ai/KNOWN_ISSUES.md`.
- Closed out T-0004 handoff and audit.
- Created T-0005 for installation candidate design under the user's explicit design gate.
- Saved `installation-candidate.v0.1.md` as T-0005 candidate evidence.
- Repaired T-0005 installation candidate and stale memory after `PASS_WITH_REPAIRS`.
- Installed `unified-governance-architecture.v0.2.1` to project-local `AGENTS.md` under explicit installation gate `G-T-0005-INSTALL-AGENTS-MD`.
- Repaired the artifact registry `forbidden_actions` wording so the installed project-local `AGENTS.md` state no longer conflicts with a stale `install AGENTS.md` prohibition.
- Executed T-0005 closeout/review under explicit gate `G-T-0005-CLOSEOUT-REVIEW`; recorded `FAIL_BLOCKED_BY_STALE_MEMORY`.
- Repaired stale installation-state wording in `.ai/CONTRACTS.md` and `.ai/KNOWN_ISSUES.md`.
- Reran T-0005 closeout/review under explicit gate `G-T-0005-CLOSEOUT-REVIEW-RERUN`; recorded `PASS` and marked T-0005 completed.
- Created T-0006 under explicit design gate `G-T-0006-DESIGN-REAL-PRODUCT-ENTRY`.
- Saved `real-product-delivery-entry-design.v0.1.md` as T-0006 candidate design evidence.
- Repaired T-0006 candidate Required Artifacts and stale memory under explicit gate `G-T-0006-REPAIR-CANDIDATE-AND-MEMORY`.
- Created T-0007 under explicit discovery gate `G-T-0007-REAL-PRODUCT-DISCOVERY`.
- Saved T-0007 discovery artifacts under `.ai/evidence/T-0007/`.
- Recorded that the linear Q&A discovery method did not scale and recommended model-first business-domain synthesis.
- Created T-0008 under explicit method-repair design gate `G-T-0008-METHOD-REPAIR-DESIGN`.
- Used the Harness artifacts directory read-only as a target design-depth benchmark.
- Saved T-0008 candidate method repair artifacts under `.ai/evidence/T-0008/`.
- Created T-0009 under explicit review-only gate `G-T-0009-METHOD-CANDIDATE-REVIEW`.
- Saved T-0009 review and repair recommendation artifacts under `.ai/evidence/T-0009/`.
- Created T-0010 under explicit repair-only gate `G-T-0010-METHOD-CANDIDATE-REPAIR`.
- Saved T-0010 repaired candidate evidence under `.ai/evidence/T-0010/`.
- Created T-0011 under explicit review-rerun gate `G-T-0011-METHOD-REPAIR-REVIEW-RERUN`.
- Saved T-0011 review-rerun evidence under `.ai/evidence/T-0011/`.
- Created T-0012 as a baseline approval decision task.
- Created `.ai/evidence/T-0012/gate-request.G-T-0012-METHOD-BASELINE-APPROVAL.v0.1.md`.
- Created `.ai/evidence/T-0012/user-decision-packet.baseline-approval.v0.1.md`.
- Recorded `G-T-0012-METHOD-BASELINE-APPROVAL` as `pending` in `.ai/gates.yaml`.
- User explicitly approved `G-T-0012-METHOD-BASELINE-APPROVAL`.
- Clarified that the approval actor is the user and the source is an explicit user message.
- Created `.ai/evidence/T-0012/baseline-approval.record.v0.1.md`.
- Updated `G-T-0012-METHOD-BASELINE-APPROVAL` to `approved` in `.ai/gates.yaml`.
- Marked T-0012 completed as baseline approval reference-only.
- Created T-0013 as a Method Operating Rules / Installation Design task.
- Created `.ai/evidence/T-0013/gate-request.G-T-0013-METHOD-OPERATING-RULES-DESIGN.v0.1.md`.
- Created `.ai/evidence/T-0013/user-decision-packet.method-operating-rules-design.v0.1.md`.
- Created `.ai/evidence/T-0013/operating-rules-design.candidate.v0.1.md`.
- Created `.ai/evidence/T-0013/lifecycle-boundary-review.v0.1.md`.
- Created `.ai/evidence/T-0013/risk-and-forbidden-scope-review.v0.1.md`.
- Recorded read-only subagent review conclusions as evidence only.
- Recorded `G-T-0013-METHOD-OPERATING-RULES-DESIGN` as `pending`.
- Updated `.ai/state.yaml` to `current_task_id: T-0013` and `current_gate_id: G-T-0013-METHOD-OPERATING-RULES-DESIGN`.
- Added T-0013 to `.ai/task_graph.yaml` as `blocked_pending_user_decision`.
- User explicitly approved `G-T-0013-METHOD-OPERATING-RULES-DESIGN`.
- Created `.ai/evidence/T-0013/operating-rules-design.approval.record.v0.1.md`.
- Updated `G-T-0013-METHOD-OPERATING-RULES-DESIGN` to `approved` in `.ai/gates.yaml`.
- Updated `.ai/state.yaml` to `current_gate_id: null`.
- Marked T-0013 completed as design-candidate acceptance only.
- Created T-0014 as Method Operating Rules Installation Gate Preparation.
- Created `.ai/evidence/T-0014/commands.md`.
- Created `.ai/evidence/T-0014/gate-request.G-T-0014-METHOD-OPERATING-RULES-INSTALLATION.v0.1.md`.
- Created `.ai/evidence/T-0014/user-decision-packet.method-operating-rules-installation.v0.1.md`.
- Created `.ai/evidence/T-0014/agents-md.proposed-diff.v0.1.patch` as evidence only.
- Created `.ai/evidence/T-0014/changed-path-baseline.v0.1.md`.
- Created `.ai/evidence/T-0014/rollback-recovery-plan.v0.1.md`.
- Created `.ai/evidence/T-0014/validation-plan.v0.1.md`.
- Created `.ai/evidence/T-0014/installation-risk-review.v0.1.md`.
- Created `.ai/evidence/T-0014/lifecycle-boundary-review.v0.1.md`.
- Created `.ai/evidence/T-0014/startup-behavior-verification-plan.v0.1.md`.
- Created `.ai/evidence/T-0014/failure-recovery-steps.v0.1.md`.
- Created `.ai/evidence/T-0014/subagent-review-summary.v0.1.md`.
- Recorded read-only subagent review conclusions as evidence only.
- Repaired T-0014 evidence wording after subagent review: closed final validation evidence, clarified future recovery authorization boundary, and clarified that future execution would only change project-local `AGENTS.md` startup / operating-rule text rather than enabling external agent/runtime/tool behavior.
- Recorded `G-T-0014-METHOD-OPERATING-RULES-INSTALLATION` as `pending`.
- Updated `.ai/state.yaml` to `current_task_id: T-0014` and `current_gate_id: G-T-0014-METHOD-OPERATING-RULES-INSTALLATION`.
- Added T-0014 to `.ai/task_graph.yaml` as `blocked_pending_user_decision`.
- Confirmed T-0014 does not modify `AGENTS.md` and does not install or enable the repaired method.
- User explicitly approved `G-T-0014-METHOD-OPERATING-RULES-INSTALLATION`.
- Created `.ai/evidence/T-0014/method-operating-rules-installation.approval.record.v0.1.md`.
- Updated `G-T-0014-METHOD-OPERATING-RULES-INSTALLATION` to `approved` in `.ai/gates.yaml`.
- Updated `.ai/state.yaml` to `current_gate_id: null`.
- Marked T-0014 completed in `.ai/task_graph.yaml`.
- Confirmed the approval did not apply the proposed diff, modify `AGENTS.md`, install or enable the repaired method, or change runtime behavior.
- Created T-0015 as the separate execution task.
- Recorded T-0015 startup validation, `AGENTS.md` baseline verification, and approved patch dry-run evidence.
- Created `.ai/evidence/T-0015/changed-path-baseline.v0.1.md`.
- Created `.ai/evidence/T-0015/gate-request.G-T-0015-METHOD-OPERATING-RULES-EXECUTION.v0.1.md`.
- Created `.ai/evidence/T-0015/rollback-boundary.v0.1.md`.
- Recorded `G-T-0015-METHOD-OPERATING-RULES-EXECUTION` as `pending`.
- Updated `.ai/state.yaml` to `current_task_id: T-0015` and `current_gate_id: G-T-0015-METHOD-OPERATING-RULES-EXECUTION`.
- Marked T-0015 as blocked on pending user decision in `.ai/task_graph.yaml`.
- Confirmed `AGENTS.md` remains unchanged.
- User explicitly approved `G-T-0015-METHOD-OPERATING-RULES-EXECUTION`.
- Created `.ai/evidence/T-0015/method-operating-rules-execution.approval.record.v0.1.md`.
- Applied the exact approved T-0014 patch to `AGENTS.md`.
- Created `.ai/evidence/T-0015/execution-result.v0.1.md`.
- Created `.ai/evidence/T-0015/startup-rule-verification.v0.1.md`.
- Updated `.ai/state.yaml` to `current_gate_id: null`.
- Marked T-0015 completed in `.ai/task_graph.yaml`.

## Next

- Do not make further `AGENTS.md` changes without a new explicit gate.
- Do not enter or apply the method to a real business project.
- Require separate explicit user gates before enabling any skill/MCP/agent/automation/protocol, applying this governance to a real business project, building, implementing, deploying, rolling back, or touching database/permission/secret/payment/production data/migration resources.

## T-0021 ~ T-0030 (2026-07-21 ~ 2026-07-22)

### T-0021: Loop Governance Runtime Installation (07-21)
- Installed loop-governance skill package + 3 governance hooks
- 15 hook tests passed; validate_state.py ok

### T-0022: Requirements Specification (07-22)
- Wrote docs/01-requirements.md (8 chapters)

### T-0023: Architecture Design (07-22)
- Wrote docs/02-architecture.md (11 chapters, 4-layer architecture)

### T-0024: Interface Contract Design (07-22)
- Wrote docs/03-interface-contract.md (9 chapters, 20+ JSON schemas)

### T-0025: Code Implementation (07-22)
- Fixed 7 issues: MCP tools (6), install.py, tests (3 files)
- Created src/loop_engine/ core library
- Created cost_tracker.py, evidence_chain.py scripts

### T-0026: Quality Gates (07-22)
- Lint: 0 errors (ruff); Tests: 113/114 pass; Security: PyYAML 6.0.3 clean

### T-0027: Delivery Preparation (07-22)
- Updated README.md; created docs/06-delivery.md

### T-0028: Requirements Repair (07-22)
- Independent reviewer found 3 P0 gaps → fixed in docs/01-requirements.md
- Added: 11 roles, 12 phases, role certification

### T-0029: Execution Layer Hardening (07-22)
- Rewrote main-thread SKILL.md (Agent isolation + veto chain + input freezing)
- Enhanced validate_state.py (self-review detection)
- Updated independent-reviewer SKILL.md (structured verdict JSON)
- Created task_contract.py (role assignment validator)

### T-0030: Loop Core Protocol Extraction (07-22)
- Created loop_core/ with 6 JSON schemas, state_machine, router, enforcement, contracts
- HostAdapter abstract interface

### T-0031: ZCode Adapter Implementation (07-22)
- Implemented ZCodeAdapter (concrete HostAdapter for ZCode)
- Honestly declares MEDIUM enforcement level

### T-0032: Full Backlog Completion (07-22)
- 3 parallel sub-agents + main-thread self-processing
- Router integration + 49 loop_core tests
- Role certification system (11 challenges, 31 tests)
- 7 templates/examples (Human Review Packet, task card, gate request, etc.)
- ProjectContinuity, mutation tester, cost tracker, degradation paths
- Total: 193 tests passing

## Current Status
Phase: S6-delivery. All P0-P2 items completed.
Independent audit by external AI found P0 issues with stale memory files (now fixed).
