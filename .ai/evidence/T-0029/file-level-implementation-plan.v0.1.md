# File-Level Implementation Plan - T-0029

This is a plan only. No listed target is modified by T-0029.

## Phase 1: Domain And Consistency Layer

### `project-governor/scripts/governor_lib.py`

- Add deterministic task-status parsing and recognized status enum.
- Add normalized governance snapshot construction.
- Add cross-artifact invariant validation.
- Replace misleading `append_task_graph_status` with explicit projection synchronization and separately named lifecycle transition operations.
- Add atomic text/YAML write helpers and staged-write recovery metadata.

### Optional new `project-governor/scripts/governance_model.py`

- Prefer this file if domain logic would make `governor_lib.py` too broad.
- Own status normalization, transition matrix, snapshot types, invariant findings, and action-mode decision model.

## Phase 2: Closeout And Handoff

### `project-governor/scripts/close_session.py`

- Remove implicit task graph lifecycle mutation.
- Load and validate one immutable snapshot.
- Render HANDOFF from authoritative facts.
- Derive next action from task/gate/action-mode state.
- Stage, audit, and atomically commit HANDOFF/state timestamp.
- Emit deterministic recovery instructions on failure.

### `project-governor/templates/ai/HANDOFF.md`

- Align headings and semantic fields with the new HANDOFF contract.
- Include current status, action mode, known inconsistencies, pending decision phrases, and evidence-based next action.

## Phase 3: Validators

### `project-governor/scripts/validate_state.py`

- Call shared invariant validation.
- Fail on task/task-graph mismatch, duplicate/missing graph task, invalid gate pointer, approval without evidence, impossible lifecycle/gate combinations, or partial-write recovery markers.
- Use stable finding IDs and structured optional JSON output.

### `project-governor/scripts/audit_handoff.py`

- Parse HANDOFF semantic fields.
- Compare phase/task/status/gate/action mode/scope/blockers/next action with the normalized snapshot.
- Detect stale next-task recommendations and scope expansion.
- Fail if HANDOFF claims authorization not present in gates/task evidence.

## Phase 4: Action Modes

### New `project-governor/scripts/action_mode.py` or shared domain module

- Define the five modes and mutual-exclusion rules.
- Produce an action decision object consumed by entry scripts.
- Require explicit execution transition from `approved_not_started` to `in_progress`.

### `project-governor/SKILL.md`

- Document mode selection, stop conditions, and the rule that approval never starts execution.
- This documentation update requires inclusion in the implementation gate scope.

## Phase 5: Tests

### New `project-governor/tests/`

- Unit tests for parsing, invariants, transition matrix, next-action derivation, and atomic writes.
- Integration tests for close_session/validate_state/audit_handoff.
- Failure injection tests for partial writes and recovery.

## Project-Local Follow-Up

After script implementation is independently approved and validated, a separate repair/migration step should reconcile existing project artifacts such as T-0028. The implementation gate must not silently change historical project state unless that repair is explicitly included and approved.

