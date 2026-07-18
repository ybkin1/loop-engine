# Project Instructions

## Project Governor

For implementation, review, debugging, design, handoff, task state changes, or governance work in this project, use `$project-governor` before proceeding.

Project root:

`C:\Users\Administrator\.codex\loop-engine-lab`

Required startup steps:

1. Read the latest user request first.
2. Confirm the project root.
3. Read `.ai/state.yaml`, `.ai/HANDOFF.md`, the current task file, `.ai/gates.yaml`, and `.ai/task_graph.yaml`.
4. Run `validate_state.py`.
5. If a pending gate exists, stop and ask the user to approve or reject it.
6. Continue only inside the approved task and gate scope.

## Loop Engineering Method Operating Rules

The following project-local rules apply only after this `AGENTS.md` change is written by an explicit user-approved installation/rule-change gate.

Mission: help a non-technical user turn goals into usable, deployable, acceptable, and sustainably iterable software products. Governance exists to reduce delivery risk and user burden; it is not the product.

### Startup Routing

- Read the latest user request before choosing a workflow.
- Use `$project-governor` for implementation, review, debugging, design, handoff, task-state, or governance work.
- Confirm the project root before governed work.
- Read `.ai/state.yaml`, `.ai/HANDOFF.md`, the current task file, `.ai/gates.yaml`, and `.ai/task_graph.yaml`.
- Run `validate_state.py`.
- Stop on any pending gate unless the latest user message explicitly approves, rejects, or requests repair of that gate.
- Continue only inside the approved task and gate scope.

Simple Q&A, single-file explanation, and temporary read-only commands do not require project memory unless the user asks for governance.

### Lifecycle

Use Plan -> Do -> Check -> Handoff. Codex owns technical execution inside approved boundaries. The user owns goals, business truth, key tradeoffs, and explicit gate decisions.

### Gates And Boundaries

- Gates are user decisions, not AI conclusions.
- Reviewer PASS, validator success, tests, and AI recommendations are evidence only.
- Separate explicit gates are required before `AGENTS.md` modification, installation/rule change, runtime behavior change, real-project entry, implementation, build, release, deployment, rollback, skill/MCP/agent/automation/protocol/tool enablement, database, permission, secret, payment, production-data, or migration action.
- Installation gates must include exact target paths, changed-path baseline, exact unified diff, validation plan, rollback/recovery plan, risk review, startup behavior verification plan, and failure recovery steps.

### Subagents

Subagents may support bounded sidecar analysis and read-only review after deterministic startup checks. Subagent conclusions are evidence only; they do not approve gates or expand scope.

### Evidence And Handoff

Store evidence under `.ai/evidence/<task-id>/`. Keep `.ai/HANDOFF.md` focused on current phase, current task, scope, forbidden scope, evidence, pending gates, blockers, and next startup prompt.

## Active Governance Artifact

`unified-governance-architecture.v0.2.1` is active only as a governance/process reference for this project's `.ai` records.

Lifecycle status after a future approved installation gate:

- approved remains true
- active remains true
- installed becomes true only after this `AGENTS.md` file is created by a separate installation gate and installation validation has passed

## Boundaries

- Do not install or enable skill, MCP, agent, automation, or protocol behavior without a separate explicit user gate.
- Do not enter real business projects without a separate explicit user gate.
- Do not deploy, roll back, change databases, change permissions, handle secrets, perform payment actions, touch production data, or run migrations without a separate explicit user gate.
- Treat reviewer PASS, validator success, tests, and AI recommendations as evidence only, not user approval.
- Keep `approved`, `active`, and `installed` lifecycle states separate.
