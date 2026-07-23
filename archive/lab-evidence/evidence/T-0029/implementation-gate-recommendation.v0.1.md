# Independent Implementation Gate Recommendation - T-0029

## Recommended Gate

`G-T-0030-PROJECT-GOVERNOR-CLOSE-SESSION-HANDOFF-CONSISTENCY-REPAIR-IMPLEMENTATION`

This is a recommendation only. T-0029 does not create or approve this gate.

## Proposed Scope

- Implement the shared governance snapshot, status parser, invariant checker, transition matrix, and atomic write/recovery helpers.
- Repair `close_session.py` so HANDOFF generation cannot mutate lifecycle state.
- Repair `validate_state.py` and `audit_handoff.py` to enforce semantic consistency.
- Implement action-mode contracts for the five approved planning modes.
- Update Project Governor HANDOFF template and SKILL documentation as explicitly listed targets.
- Add unit, integration, regression, failure-injection, and compatibility tests.

## Explicit Exclusions

- No installation or enablement beyond editing/testing the Project Governor implementation in the approved target paths.
- No subagent orchestration or automatic loop implementation.
- No MCP, plugin, hook, automation, protocol, or external tool behavior enablement.
- No automatic repair of T-0028 or other historical project artifacts.
- No real-project entry, build/release/deployment/rollback, or high-risk action.

## Gate Packet Requirements

- exact target paths and changed-path baseline.
- exact proposed diff or bounded implementation plan.
- test and compatibility matrix.
- activation versus implementation distinction.
- backup, rollback, and partial-write recovery plan.
- explicit decision on whether historical T-0028 repair is excluded or handled by a separate gate.

