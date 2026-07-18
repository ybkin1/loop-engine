# Repair Planning - T-0031

## Recommended Order

1. Resolve the activation boundary with an explicit user decision.
2. Repair action-mode enforcement at real entry points.
3. Replace HANDOFF next-action marker checks with a structured contract.
4. Bind final validation evidence to final code hashes and timestamps.
5. Keep historical blocker repair as a separate later decision.

## Activation Boundary Recovery Options

Option A: Explicitly ratify the current active global scripts.

- Requires a separate activation/runtime-behavior gate.
- Must name the exact four target paths and current SHA-256 values.
- Must acknowledge that current Project Governor behavior is already effective from global skill paths.
- Must rerun tests, validator, and HANDOFF audit after ratification.
- Risk: normalizes an implementation that became active before the activation decision.

Option B: Roll back the global scripts from the T-0030 implementation backup.

- Requires a separate rollback gate.
- Must name the four backup sources and four target paths.
- Must accept that the pre-T-0030 closeout and audit gaps return.
- Must preserve T-0030/T-0031 evidence and record rollback validation.
- Risk: restoring older behavior may mask historical blockers again.

Option C: Move the T-0030 implementation into an isolated candidate path.

- Requires a separate recovery gate.
- Restore or freeze active global scripts, keep the T-0030 implementation as a candidate copy, then validate in isolation.
- Later installation/activation would require another explicit gate.
- Risk: more steps, but cleanest boundary separation.

Option D: Temporarily hold current active scripts under an explicit quarantine decision.

- Requires a separate temporary-operating decision.
- Acknowledge current behavior is active, forbid further target-script changes, and proceed only with planning.
- Risk: leaves boundary ambiguity longer than options A-C.

Recommended boundary path:

Use Option C if the priority is governance correctness. Use Option A only if the user explicitly accepts retroactive ratification of already-active global behavior. Do not combine rollback, ratification, and implementation repair in one gate.

## Action-Mode Entry Integration Plan

Real entry points that need deterministic validation:

- pending-gate creation
- pending-gate approval/rejection recording
- approved-gate execution start
- close-session/handoff generation
- validation/audit of current state after any transition

Implementation shape:

- Add a structured action record for every transition: `mode`, `task_id`, `gate_id`, `latest_user_text`, `explicit_execution_request`, `allowed_paths`, `allowed_actions`, `forbidden_actions`, and `stop_condition`.
- Make transition helpers call `validate_action_mode()` before writing state, gates, task graph, HANDOFF, or evidence.
- Require `execute_approved_gate` to have both an approved gate and execution evidence naming the exact user request.
- Disallow implicit same-turn chaining by recording the completed mode and requiring a new user request for the next mode.
- Add negative tests for pending gate creation followed by same-turn approval, approval followed by same-turn execution, and execution without exact request evidence.

## Structured HANDOFF Next-Action Contract

Replace marker-only audit with a structured block containing:

- `current_task_id`
- `current_task_status`
- `current_gate_id`
- `current_action_mode`
- `result`
- `next_action_mode`
- `next_action_requires_explicit_user_request`
- `exact_next_user_phrase`
- `copyable_next_prompt`
- `allowed_scope`
- `forbidden_scope`
- `stop_condition`

Audit requirements:

- Parse the structure, not English prose.
- Verify task, gate, status, and next action against state, gates, and task file.
- Support Chinese copyable prompts without requiring English markers.
- Fail if required fields are missing, stale, contradictory, or semantically inconsistent with the current task status.

## Final Evidence Binding Plan

For every future implementation completion:

- Capture pre-change target hashes and timestamps.
- Capture post-change target hashes and timestamps.
- Run final tests after the last target-file change.
- Record validation start/end timestamps, command, exit code, test count, and target hashes in one manifest.
- Fail completion if any target file mtime or hash changes after final validation starts.
- Record completion only after the final manifest is written.
- Include the test file hash and test count in the final manifest to prevent stale `12/13` evidence from being treated as final.

## File-Level Repair Split

Phase 1: Boundary recovery.

- No code repair until the user chooses ratification, rollback, isolation, or quarantine.

Phase 2: Action-mode enforcement.

- Modify only the approved Project Governor helper/entry scripts under a separate implementation gate.
- Add tests covering mode selection, explicit request evidence, and no same-turn chaining.

Phase 3: HANDOFF contract.

- Update closeout rendering, HANDOFF audit, and tests for structured next-action fields.

Phase 4: Final evidence binding.

- Add validation manifest generation and stale-evidence detection.
- Add tests proving target changes after validation fail completion.

Phase 5: Historical repair decision.

- Separate gate only; do not merge with T-0030 boundary or evidence repair.

## Recommended Later Gate

Recommended gate only, not created:

`G-T-0032-PROJECT-GOVERNOR-T0030-ACTIVATION-BOUNDARY-EVIDENCE-REPAIR-IMPLEMENTATION`

Precondition:

- The user first chooses one activation-boundary recovery option or explicitly includes that decision in the gate packet.

Scope:

- Implement the selected activation-boundary recovery.
- Wire action-mode validation into real transition entry points.
- Replace HANDOFF next-action marker checks with a structured contract.
- Add final validation evidence binding.

Forbidden:

- Historical task/task-graph repair.
- Subagents or automatic loops.
- Real-project entry, deployment, database, permission, secret, payment, production-data, or migration actions.
