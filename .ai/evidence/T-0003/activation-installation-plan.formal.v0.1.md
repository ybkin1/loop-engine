# Activation / Installation Plan Formal v0.1

Status: formal evidence
Task: T-0003
Recorded at: 2026-07-07T09:09:28+08:00
Approved basis: `unified-governance-architecture.v0.2.1`
Current artifact state: `approved: true`, `active: true`, `installed: false`

## 0. Boundary Notice

This document is a formal design artifact. It is not an installation, deployment, rollback, placeholder cleanup, or real-project application approval.

The current approved action is limited to writing this formal Activation / Installation Plan body into T-0003 evidence and updating `PROGRESS.md` and `HANDOFF.md`.

This document does not authorize:

- installing or modifying `AGENTS.md`
- enabling skill, MCP, agent, automation, or protocol behavior
- entering any real business project
- deploying or rolling back
- touching database, permissions, secrets, payment, production data, or migrations
- performing placeholder cleanup

## 1. `active` Definition, Scope, And Non-Goals

`active` means an approved artifact has been explicitly selected by the user as a governance/process reference for future work inside this governance project.

For `unified-governance-architecture.v0.2.1`, `active` is already approved and recorded as governance-reference-only.

Scope:

- limited to `C:\Users\Administrator\.codex\loop-engine-lab`
- limited to this project's `.ai` governance records
- may guide task design, review criteria, handoff rules, gate design, evidence structure, and future governance documents

Non-goals:

- does not modify runtime entrypoints
- does not install or modify `AGENTS.md`
- does not install or enable skill, MCP, agent, automation, or protocol behavior
- does not change Codex global behavior
- does not enter or affect real business projects
- does not authorize deployment, rollback, database, permission, secret, payment, production data, or migration actions

`approved` does not imply `active`. In this project, `active` exists only because a separate activation-only user gate was already approved.

## 2. `installed` Definition, Scope, And Non-Goals

`installed` means an artifact has been written into an effective loaded location or configuration surface and has passed installation verification.

Possible installation surfaces include:

- `AGENTS.md`
- Codex global or project startup rules
- skill files
- MCP configuration
- agent configuration
- automation configuration
- protocol definitions
- any other executable, loaded, or behavior-changing surface

Non-goals:

- review PASS does not imply `installed`
- `approved` does not imply `installed`
- `active` does not imply `installed`
- installation targets must not be inferred
- installation must not be bundled with activation-only work

The current artifact remains:

```yaml
approved: true
active: true
installed: false
```

## 3. Activation-Only Plan

Activation-only is the lower-risk path. It marks an artifact as a governance reference while preserving `installed: false`.

For `unified-governance-architecture.v0.2.1`, this step has already been completed under `G-T-0003-ACTIVATE-V0.2.1`.

Recorded activation-only result:

```yaml
approved: true
active: true
installed: false
```

Activation-only may affect governance records such as:

- artifact registry
- `.ai/gates.yaml`
- `.ai/PROGRESS.md`
- `.ai/DECISIONS.md`
- `.ai/HANDOFF.md`
- evidence under `.ai/evidence/T-0003/`, unless a future task state explicitly changes

Activation-only must not modify runtime/startup/tooling surfaces.

## 4. Installation Plan

Installation is a separate higher-risk path. This document does not provide installation gate wording and does not authorize installation.

Before any installation gate can be considered, a separate installation candidate must define:

- exact target paths
- expected diffs
- behavior that becomes loaded or enforced
- validation method
- rollback method
- residual risks
- forbidden actions
- user gate wording

An installation gate must be created only after those details exist. This prevents the user from accidentally approving installation before the exact paths, diffs, validation, rollback, and residual risks are inspectable.

## 5. `AGENTS.md` As A Possible Installation Target

`AGENTS.md` may be a future installation target because it can affect startup behavior and agent instructions.

If `AGENTS.md` is ever considered, it requires a separate installation gate that names:

- exact `AGENTS.md` path
- exact content to add, replace, or remove
- expected diff
- validation method
- rollback method
- confirmation that no real business project is entered

No `AGENTS.md` file is created or modified by this formal plan.

## 6. Files Future Gates May Modify

Future installation or follow-up gates may modify only the exact files named in those gates.

Activation-only has already modified governance records. Any future governance-only follow-up should normally keep evidence under:

- `.ai/evidence/T-0003/`

unless the project state later moves to a different current task.

Possible future installation candidate work may create new evidence under a future authorized task. It must not modify installation targets until an installation gate exists.

## 7. Files This Plan Does Not Modify

This plan does not modify:

- any `AGENTS.md`
- skill files
- MCP configuration
- agent configuration
- automation configuration
- protocol configuration
- Codex global bootstrap rules
- real business project files
- source code outside authorized governance evidence scope
- database resources
- permission settings
- secrets, passwords, tokens, or API keys
- payment systems
- production data
- migration files
- deployment or rollback targets

## 8. Placeholder Cleanup Strategy

Placeholder cleanup is useful but remains separate from this plan.

Known placeholder-level files include:

- `.ai/CONTRACTS.md`
- `.ai/ACCEPTANCE.md`
- `.ai/KNOWN_ISSUES.md`

Strategy:

- do not bundle placeholder cleanup with activation-only
- do not bundle placeholder cleanup with installation
- require a separate cleanup gate
- if installation is considered before cleanup, record the placeholder state as residual risk in the installation candidate

## 9. Risk Table

| Risk | Impact | Control |
| --- | --- | --- |
| `approved` mistaken for `active` | Future work treats a basis as current governing policy without gate | Keep `approved`, `active`, and `installed` separate in registry, gates, and handoff |
| `active` mistaken for `installed` | Runtime behavior changes without installation approval | Define `active` as governance-reference-only |
| `AGENTS.md` modified accidentally | Startup behavior changes | Require separate installation gate with exact path and diff |
| skill/MCP/agent/automation/protocol enabled accidentally | Tool or protocol behavior changes | Keep those surfaces forbidden unless explicitly gated |
| real business project entered accidentally | Governance experiment affects business work | Require separate real-project-application gate |
| placeholder cleanup bundled silently | Scope expands without user approval | Require separate cleanup gate |
| installation rollback underspecified | Behavior change may be hard to undo | Require exact rollback plan before installation gate |

## 10. Rollback Plan

Activation rollback, if later approved:

- set the relevant registry `active` field back to `false`
- keep `approved: true`
- keep `installed: false`
- record rollback evidence
- update gates, progress, decisions, and handoff
- preserve historical candidate, review, approval, activation, plan, and rollback evidence

Installation rollback is not defined here because installation is not authorized here. A future installation candidate must define exact rollback steps before any installation gate can be approved.

Evidence should normally be superseded rather than deleted. Deletion requires a separate explicit destructive-action gate.

## 11. Validation Plan

Validation before this formal evidence write-down:

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0003
[ok] state is usable
```

Future activation validation, if activation state is rechecked or rolled back, must confirm:

- explicit gate exists for the state change
- registry status matches the gate
- `installed: false` remains true unless an installation gate exists
- no `AGENTS.md` modification occurred
- no skill/MCP/agent/automation/protocol enablement occurred
- no real business project was entered

Future installation validation must confirm:

- explicit installation gate exists
- actual modified paths match the gate exactly
- actual diffs match expected diffs
- installed behavior is loaded only as approved
- rollback path is defined and inspectably verifiable
- no forbidden high-risk action occurred

## 12. User Gate Conditions

Separate explicit user gates are required before:

- marking any artifact as `installed`
- modifying or installing `AGENTS.md`
- enabling skill, MCP, agent, automation, or protocol behavior
- entering a real business project
- deploying
- rolling back
- changing databases, permissions, secrets, payment, production data, or migrations
- performing placeholder cleanup
- deleting or destructively rewriting evidence

## 13. Real Business Project Boundary

No activation or installation planning step may automatically enter real business projects.

Forbidden by default:

- automatic scanning for business project roots
- automatic task creation in real projects
- automatic writing outside the approved governance project root
- using real business project files as installation validation targets
- deployment, migration, database, permission, secret, payment, or production-data actions

Any real-project application requires a separate real-project-application gate naming the project root, allowed files, forbidden files, validation method, rollback plan, and production boundary.

## 14. PASS / FAIL Conditions

PASS if:

- `approved`, `active`, and `installed` remain separate
- activation-only and installation paths remain separate
- `AGENTS.md` requires a separate installation gate
- placeholder cleanup remains separate
- risk, rollback, validation, and real-project boundaries are explicit
- current artifact state remains `approved: true`, `active: true`, `installed: false`

FAIL if:

- this plan is treated as installation authorization
- any installation target is inferred instead of explicitly approved
- `installed` changes without a user gate
- `AGENTS.md` changes without an installation gate
- skill/MCP/agent/automation/protocol behavior is enabled without a gate
- a real business project is entered
- deployment, rollback, database, permission, secret, payment, production data, migration, or placeholder cleanup occurs without a separate gate

## 15. Next Step Recommendation

The default next step is not installation.

Recommended next step is to keep using `unified-governance-architecture.v0.2.1` as an active governance/process reference for this project's `.ai` records only, then decide whether a separate installation candidate is actually needed.

If installation is considered later, first create an installation candidate that lists exact target paths, expected diffs, validation method, rollback method, residual risks, and gate wording. Only after that candidate is reviewed should the user consider an installation gate.

Until then, preserve:

```yaml
approved: true
active: true
installed: false
```
