# Verified And Unverified - T-0029

## Verified

- T-0029 gate was approved and execution was explicitly requested.
- Startup `validate_state.py` returned exit code `0`.
- `close_session.py` defaults task graph status to `in_progress` and overwrites the current task graph node.
- An isolated completed-task fixture was changed to task graph `in_progress` while its task file remained `completed`.
- Fixture `close_session.py` returned exit code `0` despite creating the contradiction.
- Fixture `validate_state.py` returned exit code `0` and `[ok] state is usable` with the contradiction present.
- Fixture `audit_handoff.py` returned exit code `0` and `[ok] handoff audit passed` with the contradiction present.
- Current Project Governor action-mode boundaries are not implemented as a shared executable contract.
- No target script, template, schema, `AGENTS.md`, runtime behavior, tool behavior, or agent orchestration was modified or enabled by T-0029.

## Not Yet Verified

- Compatibility of the proposed strict status parser across every historical task file.
- Final module split between `governor_lib.py` and a new domain module.
- Atomic replace behavior and file-lock edge cases on all supported operating systems.
- Performance impact on very large gate registers and task graphs.
- Exact backward-compatible CLI/JSON output format for new findings.
- Whether activation should initially be report-only before fail-closed enforcement.
- Implementation correctness; no implementation has occurred.
- Historical T-0028 repair; the contradiction remains intentionally unchanged.

