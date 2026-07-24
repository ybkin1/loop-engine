# T-0036 Task-level Closeout Gate Registration Commands

Gate: `G-T-0036-CLOSEOUT-DECISION-AND-EXECUTION-V0-1`

## Pre-registration

- `rg -n --hidden --glob '!.git/**' 'G-T-0036-CLOSEOUT-DECISION-AND-EXECUTION-V0-1' .` -> no exact match; exit `1`.
- Global `validate_state.py` -> exit `0`; state usable.
- Global `audit_handoff.py` -> exit `0`; handoff audit passed.
- Baseline captured with zero pending gates, T-0036 `active`, `current_gate_id: null`, and `blocking_findings: []`.

## Registration

- Added one `pending` task-level closeout Gate to `.ai/gates.yaml`.
- Set `.ai/state.yaml.current_gate_id` to this Gate and kept T-0036 `active`.
- Updated only the T-0036 governance projection and added registration evidence.
- Corrected current HANDOFF wording while preserving the superseded F003-open statement as explicitly historical.

## Post-registration

- Ran `validate_state.py` and `audit_handoff.py`; both stopped on the pending Gate as expected.
- No candidate implementation, test, runtime/tool, downstream task, or historical evidence was modified.
