# Operating Rules Design Candidate v0.1

Status: candidate design evidence only
Task: T-0013
Gate: G-T-0013-METHOD-OPERATING-RULES-DESIGN

## Purpose

Design how the baseline-approved Loop engineering method could later become explicit operating rules without confusing reference approval with installation or runtime behavior.

The practical goal is not better governance for its own sake. The goal is to help a user without programming or project-management background work with Codex to produce real software products that are usable, deployable, acceptable, and sustainably iterable.

## Current Lifecycle Position

| Artifact | Current State | Meaning | What It Does Not Mean |
| --- | --- | --- | --- |
| `loop-engineering-method.repaired-candidate` | `baseline_approved` as reference only | The user approved it as a baseline reference under T-0012. | Not installed, not enabled, not active operating rules, not applied to a real project. |
| `operating-rules-design.candidate.v0.1` | `candidate` | This T-0013 package proposes how future operating rules could be installed. | Not an installed rule and not a change to `AGENTS.md`. |

## Required Separations

| Term | Meaning In This Project | Required Gate Before Change |
| --- | --- | --- |
| `reference` | A baseline-approved method may be cited in `.ai` evidence. | Already covered by T-0012 as reference only. |
| `activation` | A method may guide project-local governance work within a stated scope. | Separate activation/reference gate. |
| `installation` | Text or behavior is written into `AGENTS.md`, a startup file, plugin, automation, skill, MCP, agent, protocol, or runtime surface. | Separate installation/rule-change gate with changed-path audit. |
| `runtime behavior` | Codex behavior changes because an installed rule, tool, automation, or protocol is now in effect. | Separate explicit runtime-behavior gate. |
| `real-project application` | The method is used inside a named real business project root. | Separate real-project-entry/application gate. |

## Candidate Operating Rule Layers

### 1. Startup Routing Rules

Future installed rules should require Codex to:

- read the latest user request before selecting a workflow
- confirm the project root for governed work
- use `$project-governor` for implementation, review, debugging, design, handoff, task-state, or governance work
- read `.ai/state.yaml`, `.ai/HANDOFF.md`, current task file, `.ai/gates.yaml`, and `.ai/task_graph.yaml`
- run `validate_state.py`
- stop on any pending gate unless the latest user message explicitly approves or rejects that gate

These rules should not apply to simple Q&A, single-file explanation, or temporary read-only commands unless the user requests governance.

### 2. Session Lifecycle Rules

Future installed rules should make sessions follow:

| Stage | Codex Responsibility | User Responsibility |
| --- | --- | --- |
| Start | Load governance state, validate, identify pending gates, and confirm scope. | Provide goal, project root, and explicit gate decisions. |
| Plan | Convert user goal into tasks, artifacts, gates, and verification path. | Correct business truth and choose tradeoffs. |
| Do | Produce artifacts or code inside approved scope. | Stay available for material business decisions. |
| Check | Run validation, tests, reviews, and boundary audits appropriate to scope. | Accept risk only through explicit gates. |
| Handoff | Record evidence, open risks, next step, and startup prompt. | Decide whether to continue, pause, approve, reject, or repair. |

### 3. Gate Rules

Future installed rules should state:

- gates are user decisions, not AI conclusions
- `pending` means stop and ask
- `approved` requires explicit user approval text
- reviewer PASS, validator success, tests, and AI recommendation are evidence only
- every gate must state allowed actions, forbidden actions, allowed paths, evidence, validation, and exit criteria
- high-risk gates require explicit flags for deployment, rollback, database, permission, secret, payment, production data, migration, and runtime behavior
- installation gates must include changed-path baseline, exact target paths, exact candidate diff, validation, rollback or recovery plan, and residual risks

### 4. Subagent Dispatch Rules

Future installed rules should let Codex use subagents as review and analysis support only within the active task scope.

Recommended dispatch pattern:

| Moment | Main Thread | Subagents |
| --- | --- | --- |
| Before deterministic startup validation | Run startup validation locally. | No subagent dependency. |
| After candidate artifacts exist | Continue integrating and recording evidence. | Perform read-only role reviews against files and current diff. |
| Before user decision packet | Summarize material issues and decision points. | Check boundary, installation, real-project, security, QA, or handoff risks. |
| After subagent results | Record conclusions as evidence only and repair wording if needed. | No approval authority. |

Subagents must not:

- approve gates
- modify files when assigned read-only review
- install or enable tools, skills, MCPs, agents, automations, or protocols
- enter real projects without a separate approved gate
- change runtime behavior

### 5. Verification Rules

Future installed rules should require verification proportional to risk:

- run `validate_state.py` before and after material `.ai` changes
- record command evidence under `.ai/evidence/<task-id>/commands.md`
- record known unverified items explicitly
- for design packages, run role reviews and traceability checks
- for implementation work, run relevant tests, type checks, linting, or manual verification
- for browser/frontend work, verify with a real browser when applicable
- for installation/rule-change work, verify target file paths, exact diff, and startup behavior
- validator success never substitutes for user approval

### 6. Handoff Rules

Future installed rules should keep `.ai/HANDOFF.md` operational and short:

- current phase and current task
- task status
- allowed scope
- forbidden scope
- recent changes
- verified and unverified items
- evidence location
- integration impact
- quarantined test cases and stale-context warnings
- pending gates and blockers
- next session first step
- copyable startup prompt

Stable decisions belong in `.ai/DECISIONS.md`, `.ai/CONTRACTS.md`, `.ai/ACCEPTANCE.md`, and `.ai/KNOWN_ISSUES.md` when the active gate permits updates.

### 7. Real-Project Application Rules

Future installed rules should require a separate real-project-entry gate before entering or modifying a business project.

The gate must name:

- target project root
- entry mode: read-only audit, discovery-evidence-only, design-only, or implementation
- allowed paths
- forbidden paths
- no-write directories
- changed-path baseline
- path audit
- validation plan
- exit criteria

Method approval, activation, or installation must not imply real-project application.

## Future Installation Gate Preconditions

Before any later installation/rule-change task may modify `AGENTS.md` or other operating surfaces, it should provide:

- exact target file list
- changed-path baseline
- exact unified diff
- rollback or recovery plan
- validation plan
- risk review
- user decision packet
- explicit user approval for the installation/rule-change gate
- pre-installation validation evidence
- post-installation validation evidence
- startup behavior verification
- failure recovery steps with evidence paths

## Candidate AGENTS.md Change Draft

The following block is evidence only. It has not been written to `AGENTS.md`.

```markdown
# DRAFT ONLY / NOT ACTIVE

## Candidate Loop Engineering Operating Rules Draft - Not Installed

These rules apply only after this AGENTS.md change is installed by an explicit user-approved installation/rule-change gate.

### Mission

Help a non-technical user turn goals into usable, deployable, acceptable, and sustainably iterable software products. Governance exists to reduce delivery risk and user burden; it is not the product.

### Startup

1. Read the latest user request first.
2. For implementation, review, debugging, design, handoff, task-state, or governance work, use `$project-governor`.
3. Confirm the project root.
4. Read `.ai/state.yaml`, `.ai/HANDOFF.md`, the current task file, `.ai/gates.yaml`, and `.ai/task_graph.yaml`.
5. Run `validate_state.py`.
6. If any gate is `pending`, stop and ask the user to approve, reject, or request repair.
7. Continue only inside the approved task and gate scope.

### Lifecycle

Use Plan -> Do -> Check -> Handoff.

Codex owns technical execution inside approved boundaries. The user owns goals, business truth, key tradeoffs, and explicit gate decisions.

### Gates

Reviewer PASS, validator success, tests, and AI recommendations are evidence only. They do not approve gates.

Separate explicit gates are required before:

- installation or operating-rule change
- `AGENTS.md` modification
- skill, MCP, agent, automation, protocol, or tool enablement
- real-project entry or application
- implementation, build, release, deployment, or rollback
- database, permission, secret, payment, production-data, or migration action

### Subagents

Use subagents for bounded sidecar analysis and review after deterministic startup checks. Subagent conclusions are evidence only. Subagents do not approve gates or expand scope.

### Evidence And Handoff

Store evidence under `.ai/evidence/<task-id>/`. Keep `.ai/HANDOFF.md` focused on current phase, current task, scope, forbidden scope, evidence, pending gates, blockers, and next startup prompt.
```

## Candidate Validation For Later Installation

A later installation/rule-change gate should verify:

| Check | Required Result |
| --- | --- |
| Changed-path baseline captured | PASS before writes |
| Exact unified diff reviewed | PASS before approval |
| Forbidden scope preserved | PASS |
| No skill/MCP/agent/automation/protocol enabled | PASS |
| No real project entered | PASS |
| Pre-installation `validate_state.py` result recorded | PASS or expected pending-gate blocker |
| Post-installation `validate_state.py` result recorded | PASS or expected pending-gate blocker |
| Startup behavior verification recorded | PASS |
| Rollback or recovery steps recorded | PASS |
| Handoff warns that installation scope is exact | PASS |

## Open Risks Before Installation

- No full dry run has tested these operating rules in a real business project.
- Candidate `AGENTS.md` wording should receive another installation-specific review before any write.
- Worked examples may still be needed so future sessions interpret artifact schemas consistently.

## Explicit Boundary

This file is a candidate design artifact only. It does not install, enable, activate, or apply the baseline method, and it does not modify `AGENTS.md`.
