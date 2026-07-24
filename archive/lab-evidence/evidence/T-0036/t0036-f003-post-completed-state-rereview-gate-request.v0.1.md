# T-0036 F003 Post-Repair Fresh Independent Rereview Gate Request v0.1

Gate: `G-T-0036-FRESH-INDEPENDENT-REREVIEW-F003-POST-COMPLETED-STATE-REPAIR-V0-1`

This is a registration-only request. It does not approve or execute rereview.

## Required Future Checks

- Re-freeze the 17-file/2-directory candidate inventory and all 33 protected subjects from the current protected-subject set.
- Run focused F003 protocol checks and the complete structured adapter regression.
- Verify real completed state remains `AUTHORITY_MISSING`.
- Verify fixture-only structured regression is `64/64` and does not mutate live Gate state.
- Verify stdout/stderr remain diagnostic only and structured envelope binding remains intact.
- Verify HANDOFF Project Anchors, current topic, current problem/state, and execution constraints are distinct and exact.
- Run `validate_state.py`, `audit_handoff.py`, and necessary read-only candidate regression checks.
- Produce only an evidence-only verdict: `PASS`, `REPAIR_REQUIRED`, `BLOCKED`, or `USER_DECISION_REQUIRED`.

## Decision Phrases

Approval: `批准 G-T-0036-FRESH-INDEPENDENT-REREVIEW-F003-POST-COMPLETED-STATE-REPAIR-V0-1`

Rejection: `拒绝 G-T-0036-FRESH-INDEPENDENT-REREVIEW-F003-POST-COMPLETED-STATE-REPAIR-V0-1`

Later exact execution request: `执行已批准的 G-T-0036-FRESH-INDEPENDENT-REREVIEW-F003-POST-COMPLETED-STATE-REPAIR-V0-1`

Approval is not execution. No prior F003 rereview verdict is reused as the future verdict.
