# Action Mode Contract - T-0029

## Common Rules

- Exactly one action mode is active per request.
- The mode is selected from the latest explicit user request plus governance state.
- Modes cannot implicitly chain into another mode in the same turn.
- Every write must be allowed by the active mode and approved path/action scope.
- Mode completion stops; a new explicit request is required for the next mode.

## `read_only`

- Reads and reports only.
- No project, governance, evidence, task, gate, HANDOFF, or runtime writes.
- Cannot create prompts as durable artifacts unless separately requested under an allowed mode.

## `prompt_generation_only`

- Produces bounded prompt text only.
- Must not create a task, gate, evidence directory, plan execution record, or new governance system.
- Must not execute the generated prompt.
- Output must name scope, forbidden scope, required inputs, expected evidence, and stop condition.

## `create_pending_gate`

- May create the named task/gate-registration artifacts and update approved governance indexes only.
- Gate status must be `pending`; task status must be `blocked_pending_user_decision`.
- Must not approve, execute, analyze the gated body, or create downstream gates.
- Must stop after recording validation and exact decision phrases.

## `approve_pending_gate`

- Requires an exact user approval/rejection phrase matching the current pending gate.
- May record decision evidence and update task/gate/state/HANDOFF only.
- Approval transitions the task to `approved_not_started`, never directly to `in_progress`.
- Must not execute the gate body in the approval-recording turn.

## `execute_approved_gate`

- Requires an approved gate, matching current task, approved scope, and an explicit execution request.
- Creates an execution-start record, then transitions task to `in_progress`.
- May perform only the approved body and evidence writes.
- Must stop at completion; implementation or downstream gates remain separate decisions.

## Mutual-Exclusion Enforcement

Introduce a normalized action-mode decision object containing mode, task id, gate id, allowed paths, allowed action classes, forbidden actions, and stop condition. All Project Governor entry scripts validate this object before writes.

Reject ambiguous combinations such as:

- prompt generation plus task creation.
- gate approval plus execution.
- closeout plus lifecycle transition.
- read-only plus evidence mutation.
- planning plus implementation.

