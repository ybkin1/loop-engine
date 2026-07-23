# T-0036 F003 Closure Decision Gate Registration Commands

Gate: `G-T-0036-F003-CLOSURE-DECISION-V0-1`

## Pre-registration checks

- `C:\Python312\python.exe C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py .` -> `0`
- `C:\Python312\python.exe C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py .` -> `0`
- `rg -n --fixed-strings 'G-T-0036-F003-CLOSURE-DECISION-V0-1' .ai` -> no match, exit `1`
- `git status --porcelain=v1` -> captured in the baseline; pre-existing worktree changes were preserved.

## Registration action

- Add one `pending` Gate to `.ai/gates.yaml`.
- Set `.ai/state.yaml.current_gate_id` to this Gate and retain `T0036-F003` as blocking.
- Update only the T-0036 governance projection and add registration evidence.

## Post-registration checks

- `C:\Python312\python.exe C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py .` -> expected pending-Gate blocker.
- `C:\Python312\python.exe C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py .` -> expected pending-Gate blocker or truthful pending-Gate audit result.

No repair, rereview, installation, activation, runtime/controller/agent/tool enablement, T-0037 creation, or real-project entry is part of this registration.
