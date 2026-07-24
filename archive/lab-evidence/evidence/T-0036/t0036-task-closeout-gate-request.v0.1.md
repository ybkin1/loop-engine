# T-0036 Task-level Closeout Gate Request

Gate: `G-T-0036-CLOSEOUT-DECISION-AND-EXECUTION-V0-1`

## Requested decision

Ask the user whether T-0036 should be marked `completed` after verifying that T0036-F003 is administratively closed and all T-0036 evidence remains accounted for.

## Execution boundary

Registration is complete only when this Gate is recorded as `pending`. Approval alone does not close T-0036. A later exact request is required: `执行已批准的 G-T-0036-CLOSEOUT-DECISION-AND-EXECUTION-V0-1`.

Future approved execution may update only the T-0036 task status, task graph, state, and HANDOFF, preserve all historical evidence, and correct stale HANDOFF wording so F003 is identified as historical or currently closed.

This Gate is not user acceptance, project PASS, installation, activation, runtime/controller/agent/tool enablement, T-0037 creation, or real-project entry. Candidate implementations and tests are outside scope.
