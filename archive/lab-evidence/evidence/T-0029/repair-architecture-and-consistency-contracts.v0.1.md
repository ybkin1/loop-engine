# Repair Architecture And Consistency Contracts - T-0029

## Architectural Principle

Separate authoritative facts, projections, validation, and transitions. A rendering command must never invent or perform a lifecycle transition.

## Source-Of-Truth Contract

- Task file `## Status`: authoritative task lifecycle state until a future structured task metadata format is explicitly approved.
- `gates.yaml`: authoritative gate decision and authorization state.
- `state.yaml`: authoritative current phase/current task/current gate pointers, not task lifecycle truth.
- `task_graph.yaml`: indexed projection of task identity, lifecycle state, dependency edges, timestamps, and summary note; it must mirror the authoritative task status.
- Evidence: immutable factual records supporting transitions and conclusions.
- HANDOFF: derived session projection only; it must never become an authorization or lifecycle source.

## Required Invariants

1. Current task file exists and has exactly one recognized status.
2. Current task appears exactly once in task graph.
3. Task file status equals task graph status after normalization.
4. `current_gate_id` is null unless it identifies a gate for the current task.
5. A pending gate must match `current_gate_id`; an approved/rejected gate must not remain the current blocker.
6. `approved_not_started` requires explicit approval evidence and an approved gate.
7. `in_progress` requires an execution-start record tied to an approved scope.
8. `completed` requires completion evidence and no pending gate for the task.
9. HANDOFF current task, status, gate state, scope, blockers, and next action must match authoritative records.
10. HANDOFF generation must preserve task lifecycle status.

## Close Session Architecture

Refactor closeout into explicit phases:

1. Load an immutable governance snapshot.
2. Validate preconditions and invariants.
3. Render HANDOFF entirely in memory from the snapshot.
4. Audit the rendered document semantically before writing.
5. Stage HANDOFF and `last_handoff_at` updates in temporary files.
6. Atomically replace destination files.
7. Write closeout evidence containing snapshot hash, outputs, and result.

`close_session.py` must not call task lifecycle mutation helpers. Any lifecycle transition must use a separate explicit transition function/command with its own validation and evidence.

## Shared Domain Layer

Add shared functions in `governor_lib.py` or a dedicated domain module:

- parse task metadata/status deterministically.
- build a normalized governance snapshot.
- validate cross-artifact invariants.
- normalize recognized lifecycle states.
- validate a proposed task transition.
- render a HANDOFF model from authoritative facts.
- write text/YAML atomically with recovery metadata.

## Handoff Content Contract

HANDOFF must contain:

- exact phase, task id/title/status, and active action mode.
- approved and forbidden scope from the current task/gate.
- verified/unverified facts with evidence paths.
- known inconsistencies or blockers without silently repairing them.
- exact pending decision phrases when a gate is pending.
- a next action derived from state, not a generic suggestion.
- a startup prompt that cannot broaden scope.

## Next-Action Derivation

- pending gate: request exact approval/rejection only.
- approved_not_started: require explicit `execute_approved_gate` request.
- in_progress: resume only the approved task body.
- completed: ask user whether to create a separate next gate/task or change direction; never name an unapproved next task as current work.
- inconsistent/partial state: enter recovery-only behavior and prohibit normal continuation.

