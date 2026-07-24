# T-0036 HANDOFF Semantic Anchoring Execution Implementation Report v0.1

## Repair

`close_session.py` now reads exact authoritative lines from `.ai/PROJECT.md:5`, `.ai/PROJECT.md:9`, `.ai/PROJECT.md:22`, and `AGENTS.md:24`, and emits them under a dedicated `## Project Anchors` section. Current topic, problem, state, and execution constraints are separate sections.

`audit_handoff.py` independently reloads those source lines and fails closed on missing sections, missing or duplicate fields, unexpected fields, value mismatch, source drift, and anchor fields placed under current-state sections.

## RED/GREEN

- RED against the preimage: the new semantic suite failed because the old closeout emitted no Project Anchors and the old audit accepted mutated output.
- GREEN after repair: focused semantic suite `10/10`.
- Repeated closeout semantic anchor payload: stable.
- Pending-gate closeout/audit blocking: preserved.

## Protected Behavior

- Live `close_session.py`: exit `0`.
- Live `audit_handoff.py`: exit `0`.
- Live `validate_state.py`: exit `0`.
- Candidate regression subsets: transaction `4/4`, close `3/3`, audit `7/7`, validator `3/3`, action-mode `1/1`.
- F003 remains open; no fresh independent rereview was performed.
