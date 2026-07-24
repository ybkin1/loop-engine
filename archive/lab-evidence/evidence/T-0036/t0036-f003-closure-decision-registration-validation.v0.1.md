# T-0036 F003 Closure Decision Gate Registration Validation

Gate: `G-T-0036-F003-CLOSURE-DECISION-V0-1`

## Pre-registration

- `validate_state.py`: exit `0`, state usable.
- `audit_handoff.py`: exit `0`, handoff audit passed.
- Gate conflict search: no historical match; `rg` exit `1` means no match.

## Post-registration

- `validate_state.py`: exit `1`; correctly stopped with `Pending gate(s) require user decision before continuing: G-T-0036-F003-CLOSURE-DECISION-V0-1`.
- `audit_handoff.py`: exit `1`; correctly stopped with `Pending gate(s) not resolved: G-T-0036-F003-CLOSURE-DECISION-V0-1`.
- Gate status: `pending`; `.ai/state.yaml.current_gate_id` matches the Gate.
- Task status: `T-0036 active`; blocking finding remains `T0036-F003`.
- Latest rereview evidence remains evidence-only `PASS`; no closure, acceptance, project PASS, installation, activation, runtime/tool enablement, T-0037, or real-project entry occurred.

The non-zero post-registration results are expected pending-Gate containment, not a validation defect.
