# T-0036 Residual Path Repair Gate Registration Commands v0.1

Gate: `G-T-0036-REPAIR-F003-F005-PATH-CLOSURE-V0-1`

Project root: `C:\Users\Administrator\.codex\loop-engine-lab`

Registration mode: `create_pending_gate_only`

## Startup And Preflight

- Read `$project-governor`, `.ai/state.yaml`, `.ai/HANDOFF.md`, `.ai/tasks/T-0036.md`, `.ai/gates.yaml`, and `.ai/task_graph.yaml`.
- Read the fresh rereview report, validation, and changed-path manifest.
- Ran `python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab`.
- Result before registration: `PASS`; phase `S0-method-repair`; task `T-0036`; no pending Gate.
- Ran `git status --short`, `git status --porcelain=v1 -uall`, `git log -5 --oneline`, path existence checks, size/SHA-256 capture, and a strict parser of the 65-subject freeze manifest.
- Freeze result before registration: `65/65`; mismatches `0`.

## Registration Assertions

- Only four new registration evidence files and `.ai/gates.yaml`, `.ai/state.yaml`, `.ai/HANDOFF.md` may change.
- Both future YAML repair targets retain their recorded preimages throughout registration.
- Registration creates one pending Gate and records `repair_authorized: false`.
- Gate creation is not approval. Approval is not execution. A later exact execution request remains mandatory.
- No repair, rereview, baseline acceptance, version freeze, T-0037 review, Host Integration, or runtime/tool behavior change occurs.

## Required Post-Registration Commands

1. Parse `.ai/state.yaml`, `.ai/gates.yaml`, and `.ai/task_graph.yaml` as UTF-8 YAML and confirm exactly one pending Gate with the requested ID.
2. Recheck the 65-subject freeze and both future repair target hashes.
3. Run `python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab`.
4. Run `python C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py C:\Users\Administrator\.codex\loop-engine-lab`.
5. Run `git diff --check`.

The expected `validate_state.py` result after registration is a governance stop naming the pending Gate. That stop is the intended authorization boundary, not repair execution or repair failure.

## Post-Registration Results

- UTF-8 YAML parse: `PASS` for `.ai/state.yaml`, `.ai/gates.yaml`, and `.ai/task_graph.yaml`.
- Pending Gate count: `1`; ID: `G-T-0036-REPAIR-F003-F005-PATH-CLOSURE-V0-1`.
- State projection: `current_gate_id=G-T-0036-REPAIR-F003-F005-PATH-CLOSURE-V0-1`.
- Existing freeze recheck: `65/65`; mismatches `0`; manifest size/SHA-256 unchanged.
- Future repair target preimages: both sizes and SHA-256 values unchanged from the baseline.
- `validate_state.py`: expected governance stop, exit code `1`; `Pending gate(s) require user decision before continuing: G-T-0036-REPAIR-F003-F005-PATH-CLOSURE-V0-1`.
- `audit_handoff.py`: semantic and structural checks pass; expected exit code `1` only because `Pending gate(s) not resolved: G-T-0036-REPAIR-F003-F005-PATH-CLOSURE-V0-1`.
- `git diff --check`: `PASS`.

These pending-Gate stops are the intended `user_decision_required` state. No repair has started.
