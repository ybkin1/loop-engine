# AGENTS.md -- Codex Loop Engineering Governance

## Loop Governance

When a user request involves implementation, review, debugging, design,
handoff, task state changes, or governance work, the Loop Engineering system
takes over. For simple Q and A, single-file explanation, or temporary read-only
commands, governance is skipped.

Project root:

`C:\Users\Administrator\.codex\loop-engine-lab`

### Startup Checklist (every governed session)

1. Read the latest user request first.
2. Confirm project root (must contain `.ai/state.yaml`).
3. Read `.ai/state.yaml`, `.ai/HANDOFF.md`, `.ai/tasks/<current_task_id>.md`,
   `.ai/gates.yaml`, and `.ai/task_graph.yaml`.
4. Run `python codex_loop/governance/validate_state.py`.
5. If a pending **user gate** exists (S1 project direction or S6 delivery acceptance): stop, present the gate to the user,
   and wait for an explicit decision (approve, reject, or request repair).
6. Continue only inside the approved task and gate scope.
7. For internal phases (S2-S5, S7-S11): proceed automatically once role verdicts and evidence satisfy phase constraints. User intervention is only required at S1 and S6 gates.

### Intent Recognition (Auto-Routing)

Before starting any new project or significant task, run intent analysis
via `codex_loop/planning/intent_router.py`. Rules:
- HIGH risk (database, auth, payments, production data, security) -> FULL mode
- MEDIUM risk (API, multi-module, deployment, iteration) -> at least STANDARD
- LOW risk (single-file, simple tool, one-off) -> LIGHTWEIGHT
- When uncertain, escalate rather than misjudge.

### Core Principles (Non-Negotiable)

1. Gates are user decisions, not AI conclusions.
2. Approval is not execution. A separate exact execution request is required.
3. Partial completion is not product completion.
4. Governance is a means, not the product.

### Lifecycle

Plan -> Do -> Check -> Handoff. Codex owns technical execution inside
approved boundaries. The user owns goals, business truth, key tradeoffs,
and explicit gate decisions.

### Enforcement Layer

The enforcement_hub (`codex_loop/core/enforcement_hub.py`) provides
fail-closed governance decisions. Hard constraints are checked by
`codex_loop/core/hard_constraints.py` (C1-C11). The state machine
(`codex_loop/core/state_machine.py`) enforces phase transitions, gate
logic, and role isolation.

### Boundaries

- Do not install or enable skill, MCP, agent, automation, or protocol
  behavior without a separate explicit user gate.
- Do not enter real business projects without a separate explicit user gate.
- Do not deploy, roll back, change databases, change permissions, handle
  secrets, perform payment actions, touch production data, or run migrations
  without a separate explicit user gate.
- Treat reviewer PASS, validator success, tests, and AI recommendations
  as evidence only, not user approval.

### Evidence And Handoff

Store evidence under `.ai/evidence/<task-id>/`. Keep `.ai/HANDOFF.md`
focused on current phase, current task, scope, forbidden scope, evidence,
pending gates, blockers, and next startup prompt.

### Active Status

- approved: true
- active: true
- installed: true
- engine: codex_loop v3.12.8 (native Codex)
- supersedes: zcode loop-engine v3.0.0

### Auto-Role Dispatch (v3.12.8)

When a phase requires role agents, the system auto-generates a SubagentManifest:
1. manifest_generator.generate_manifest(phase, task_id, title, paths)
2. DispatchRunner.prepare(manifest) -> ExecutionPlan
3. DispatchRunner.get_spawn_specs(manifest) -> spawn_agent params
4. For each spec: spawn_agent(agent_type, message, fork_turns)
5. Collect results -> DispatchRunner.finalize() -> gate presentation
6. fork_turns policy: dev/test/qa get all context, reviewer gets none