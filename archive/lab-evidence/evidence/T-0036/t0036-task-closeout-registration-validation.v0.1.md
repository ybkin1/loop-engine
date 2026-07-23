# T-0036 Task-level Closeout Gate Registration Validation

Gate: `G-T-0036-CLOSEOUT-DECISION-AND-EXECUTION-V0-1`

## Pre-registration

- `validate_state.py`: exit `0`, state usable.
- `audit_handoff.py`: exit `0`, handoff audit passed.
- Exact Gate ID conflict search: no historical match; `rg` exit `1` means no match.

## Post-registration

- `validate_state.py`: exit `1`; expected blocker: `Pending gate(s) require user decision before continuing: G-T-0036-CLOSEOUT-DECISION-AND-EXECUTION-V0-1`.
- `audit_handoff.py`: exit `1`; expected blocker: `Pending gate(s) not resolved: G-T-0036-CLOSEOUT-DECISION-AND-EXECUTION-V0-1`.
- Gate status: `pending`; `.ai/state.yaml.current_gate_id` matches the Gate.
- T-0036 task and task graph status: `active`; `T0036-F003` remains administratively `CLOSED`.
- No approval, rejection, closeout execution, user acceptance, project PASS, installation, activation, runtime/tool enablement, T-0037, or real-project entry occurred.

The non-zero post-registration results are expected pending-Gate containment, not validation defects.
