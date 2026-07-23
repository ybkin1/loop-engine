# Known Findings For Independent Reverification - T-0031

These items are existing review findings and evidence leads. They are not predetermined T-0031 conclusions.

## A. Global Skill Modification And Activation Boundary

- T-0030 excluded installation and activation but modified the four globally used Project Governor scripts in place.
- Current project validation already exhibits the modified fail-closed behavior.
- T-0031 must independently determine whether this constitutes activation, installation, runtime/tool behavior change, scope overrun, or another lifecycle state.

## B. Action-Mode Validator Entry Integration

- `validate_action_mode()` is reported as implemented and unit-tested.
- Existing evidence suggests it may not be called by real `create_pending_gate`, `approve_pending_gate`, or `execute_approved_gate` entry paths.
- T-0031 must independently verify actual call paths and enforcement claims.

## C. HANDOFF Next-Action Audit Strength

- Existing audit logic appears to rely partly on English substring checks.
- T-0031 must independently assess semantic agreement with task/gate state, multilingual behavior, exact user prompts, allowed/forbidden scope, and stop conditions.

## D. Final Validation Evidence Consistency

- T-0030 completion records say regression and failure-injection tests passed 13/13.
- `.ai/evidence/T-0030/final-validation-output.txt` records `Ran 12 tests`.
- T-0031 must independently bind file hashes, timestamps, completion time, and final test evidence to determine whether evidence became stale.

## Preserved Historical Blockers

T-0002, T-0004, T-0005, T-0007, T-0009, and T-0028 are context only. T-0031 may analyze their impact but must not repair or reconcile them.
