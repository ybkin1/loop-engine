# T-0036 Repair Gate Registration Commands v0.1

Gate: `G-T-0036-REPAIR-F001-F006-V0-1`
Project root: `C:\Users\Administrator\.codex\loop-engine-lab`
Registration mode: `create_pending_gate_only`

## Deterministic startup evidence

Command:

`python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab`

Before registration result: `PASS`

Observed: `phase=S0-method-repair`; `current_task_id=T-0036`; `state is usable`; no pending Gate.

Commands:

- `git status --porcelain -uall`
- `git status --short --branch`
- `git log -5 --oneline --decorate`
- strict parser of `.ai/evidence/T-0036/material-library-independent-review-freeze-manifest.v0.1.md` with `Get-FileHash -Algorithm SHA256`

Results:

- Git baseline: 145 porcelain lines; staged `0`; tracked worktree modifications `6`; untracked `139`.
- Branch: `checkpoint-through-T-0034`; HEAD `eb07a30`.
- Frozen subjects: `58`; path/size/SHA-256 matches `58/58`; mismatches `0`.
- Old freeze manifest SHA-256: `5F475585FA007FECE4E352CA6F43F5BF8940A05DBE52C94D48C9B60E929BBA78`.

## Registration assertions

- Only the four new Gate evidence files and the three governance projections are registration paths.
- No materials source, catalog, schema, register, matrix, profile, template, simulation object, old review evidence, old freeze manifest, T-0037 artifact, or T-0038 artifact was modified by registration.
- The three re-run subagents were read-only and returned evidence only.
- No repair, fresh HTTP retrieval, rereview, baseline acceptance, version freeze, T-0037 review, Host Integration, installation, activation, deployment, migration, database, permission, secret, payment, production-data, or external business-project action occurred.

## Post-registration checks to execute

1. Re-run the old freeze-manifest parser and record `58/58` matches and `0` mismatches.
2. Parse `.ai/state.yaml`, `.ai/gates.yaml`, and `.ai/task_graph.yaml` as UTF-8 YAML; confirm exactly one new `pending` Gate with the requested ID and no other pending Gate.
3. Run `git diff --check` and record success.
4. Run `validate_state.py`. Its expected result after a pending Gate is a governance stop naming `G-T-0036-REPAIR-F001-F006-V0-1`; this is the intended user-decision blocker, not repair execution.
5. Do not run `audit_handoff.py` as a closeout operation in this Gate-preparation turn; no handoff closeout was requested.

## Actual post-registration results

- Old freeze-manifest recheck: `records=58; matches=58; mismatches=0`.
- UTF-8 YAML parse of `.ai/state.yaml`, `.ai/gates.yaml`, and `.ai/task_graph.yaml`: `PASS`.
- Pending Gate IDs after registration: `G-T-0036-REPAIR-F001-F006-V0-1`; target present: `True`.
- `git diff --check`: `PASS`.
- `validate_state.py`: expected governance stop, exit code `1`, output `Pending gate(s) require user decision before continuing: G-T-0036-REPAIR-F001-F006-V0-1`.

The validator stop is the intended authorization boundary. It does not indicate that repair has started or failed.

## Approval record

- approval_text: `批准 G-T-0036-REPAIR-F001-F006-V0-1`
- approval_actor: `user`
- approval_source: `explicit_user_message`
- approved_at: `2026-07-24T13:20:14+08:00`
- resulting_state: `approved_not_started`
- repair_execution_started: `false`
- exact execution request still required: `执行 G-T-0036-REPAIR-F001-F006-V0-1`

## Authority boundary

Gate creation is not approval. The next state transition is exactly one user decision: `批准 G-T-0036-REPAIR-F001-F006-V0-1` or `拒绝 G-T-0036-REPAIR-F001-F006-V0-1`. Even approval requires a later exact `执行 ...` request before any repair path can change.
