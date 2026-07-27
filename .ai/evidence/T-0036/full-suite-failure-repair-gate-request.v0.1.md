# T-0036 Full-Suite Failure Repair Gate Request v0.1

Gate ID: `G-T-0036-FULL-SUITE-FAILURE-REPAIR-V0-1`

Status: `pending / user_decision_required`

## Request

This is a separate Gate for six existing full-suite test failures discovered during T-0036 validation. It is not part of the completed F-001..F-006 material-library repair Gate.

Decision phrases:

- `批准 G-T-0036-FULL-SUITE-FAILURE-REPAIR-V0-1`
- `拒绝 G-T-0036-FULL-SUITE-FAILURE-REPAIR-V0-1`

Approval alone does not execute the test repair. A later exact request is required:

- `执行 G-T-0036-FULL-SUITE-FAILURE-REPAIR-V0-1`

## Root cause and minimum repair

- `close_session.py` requires four authoritative anchors, including `AGENTS.md:24`.
- `candidates/T-0030-project-governor-repair/tests/test_project_governor_consistency.py` copies `.ai` templates into a temporary root but never creates the required root-level `AGENTS.md` fixture.
- The minimum repair is test-only: in `setUp`, create a temporary-root `AGENTS.md` with exactly 24 lines and a non-empty line 24 before invoking `close_session.py`.
- Do not modify `close_session.py`, `handoff_semantic_schema.py`, global skill files, the candidate repository root, or any production behavior.

## Exact scope

### Registration-only paths

- `.ai/evidence/T-0036/full-suite-failure-repair-gate-request.v0.1.md`
- `.ai/evidence/T-0036/full-suite-failure-repair-changed-path-baseline.v0.1.md`
- `.ai/evidence/T-0036/full-suite-failure-repair-registration-commands.v0.1.md`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`

### Paths allowed only after approval and a separate execution request

- `candidates/T-0030-project-governor-repair/tests/test_project_governor_consistency.py`
- `.ai/evidence/T-0036/full-suite-failure-repair-commands.v0.1.md`
- `.ai/evidence/T-0036/full-suite-failure-repair-validation.v0.1.md`
- `.ai/evidence/T-0036/full-suite-failure-repair-changed-path-manifest.v0.1.md`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`

No repository-level `AGENTS.md` is added. The fixture is created only under each test's temporary root and is deleted by `TemporaryDirectory` cleanup.

## Expected diff

One test-fixture helper or equivalent `setUp` block that writes:

- line 1: fixture heading
- lines 2-23: deterministic padding
- line 24: non-empty governance mission anchor

No production script changes, no assertion weakening, no skipped tests, no test deletion, and no changes to unrelated candidate files.

## Verification plan

- RED reproduction: confirm the current six failures and exact `AGENTS.md:24` error.
- GREEN: run the focused failing test module and confirm its six previously failing cases pass.
- Run `python -m pytest -q` and require zero failures.
- Run `python -m pytest tests/codex_loop -q` to detect regressions in current candidate tests.
- Run `git diff --check`, `validate_state.py`, and a changed-path check proving only the exact test file plus additive evidence changed.
- Confirm no repository-level or global `AGENTS.md` was created or modified.

## Risks and recovery

- Fixture drift: use a helper with an explicit 24-line assertion so the test cannot silently regress.
- Contract masking: preserve the production anchor contract; do not weaken `close_session.py` validation.
- Scope expansion: any production or global skill change is a scope violation.
- On failure, stop with truthful `repair_incomplete` evidence. Do not delete or reverse existing user changes. Destructive rollback requires another Gate.

## Forbidden scope

- No modification of Project Governor global skill files or scripts.
- No modification of `.ai` T-0036 material-library inputs, freeze manifests, prior review evidence, T-0037/T-0038 artifacts, `codex_loop/`, or unrelated candidate files.
- No deployment, runtime enablement, database, permissions, secrets, production data, migration, Host Integration, baseline acceptance, version freeze, or independent rereview.

Current conclusion: `pending / user_decision_required / repair_not_started`.
