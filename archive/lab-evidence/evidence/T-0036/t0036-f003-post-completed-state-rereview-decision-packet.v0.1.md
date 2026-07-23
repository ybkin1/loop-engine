# T-0036 F003 Post-Repair Fresh Independent Rereview Decision Packet v0.1

Gate: `G-T-0036-FRESH-INDEPENDENT-REREVIEW-F003-POST-COMPLETED-STATE-REPAIR-V0-1`

## Authoritative Goal

The project goal is the exact authoritative text at `.ai/PROJECT.md:5`: help users without coding ability or project-management background move from rough requirements to real, usable, deployable, acceptable, and continuously iterable software delivery with Codex.

## Registration-Time Facts

- Task: `T-0036`; phase: `S0-method-repair`; status: `active`.
- `current_gate_id` was `null` before this registration and no pending Gate existed.
- Blocking finding: `T0036-F003`.
- Latest F003 repair result: `PASS_PENDING_FRESH_INDEPENDENT_REREVIEW`.
- HANDOFF semantic anchoring repair is complete; its evidence and current target fingerprints are inputs only.
- No post-HANDOFF-repair F003 independent rereview has been performed.

## Review Scope

The future reviewer may only perform a fresh, read-only reassessment of the latest F003 repair and the current HANDOFF semantic projection. It must re-freeze the candidate and the 33 protected subjects, verify structured result binding, run focused protocol checks and the complete structured regression, verify live completed-state `AUTHORITY_MISSING`, verify fixture-only `64/64`, and independently inspect separated HANDOFF semantic fields.

## Independence And Verdict

The reviewer must use a fresh independent context and may not inherit a prior implementation or rereview conclusion. Prior evidence is evidence to reproduce or rebut, not a predetermined disposition. The only allowed evidence-only verdicts are `PASS`, `REPAIR_REQUIRED`, `BLOCKED`, and `USER_DECISION_REQUIRED`.

## Security Invariants

- `validation_runner.py` remains fail-closed; stable completed state must not be treated as production authority.
- A fixture-only `in_progress` mirror must never be treated as a real Gate or runtime authority.
- `UnittestResultEnvelope/v1` nonce, adapter/test fingerprints, discovered IDs, count, and result hashes remain bound.
- stdout/stderr are diagnostic only and cannot establish test identity, count, or success.
- No live Gate mutation, F003 closure, user acceptance, project PASS, installation, activation, runtime/tool enablement, T-0037, or real-project entry is permitted.

## Execution Evidence

Future execution may write only additive evidence under `.ai/evidence/T-0036/`. Candidate, tests, global tools, project semantic sources, AGENTS.md, and historical evidence are read-only.
