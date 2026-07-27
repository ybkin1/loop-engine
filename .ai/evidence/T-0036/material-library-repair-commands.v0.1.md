# T-0036 F-001..F-006 Repair Commands v0.1

Gate: `G-T-0036-REPAIR-F001-F006-V0-1`
Execution request: `执行 G-T-0036-REPAIR-F001-F006-V0-1`
Execution mode: bounded repair only; stop before independent rereview.

## Preflight

- `validate_state.py`: PASS before repair; approved Gate was `approved_not_started`.
- Old freeze manifest: `58/58` path/size/SHA-256 matches; mismatches `0`.
- Gate allowlist and preimage baseline were read before modification.

## Repair actions

1. Added `materials/source-register-schema.yaml` with required per-record freshness fields and conditional status/local sentinels.
2. Added selection/version/scope/subset fields to generic profiles and simulation profiles; normalized simulation template paths.
3. Replaced the phase-profile template with an aggregate `phases` shape and added the concrete `PHASE-PROFILE-T0036-SIM-FULL-DESIGN-V0.1` simulation instance.
4. Added `ARCH-004` to the coverage matrix.
5. Ran one authoritative retrieval run for 44 HTTP(S) and 2 local sources. Generated `materials/source-register.yaml` and its Markdown projection, then updated catalog verification status/observation fields and DOC-001 authority.

Retrieval run: `T0036-REPAIR-F006-20260724T1325`

- started: `2026-07-24T13:31:48+08:00`
- completed: `2026-07-24T13:32:43+08:00`
- records: `46`; HTTP: `44`; local: `2`
- statuses: `content_read=37`, `url_verified_only=2`, `access_blocked=7`
- HTTP status counts: `200=38`, `403=2`, transport-null=`4`
- records with non-none failure reason: `9`

## Deterministic commands and results

- `python .ai/evidence/T-0036/material-library-repair-validator.v0.1.py C:\Users\Administrator\.codex\loop-engine-lab`: PASS; catalog 46; authority violations 0; register 46/46; status conflicts 0; Markdown IDs 46; coverage 46/46; freshness 46/46; phase ref 1/1; selection materials 8/17; templates 7/9.
- `python -m pytest tests/codex_loop -q`: PASS; `28 passed`.
- `python -m pytest -q`: FAIL; `40 passed, 6 failed`. All six failures are existing `candidates/T-0030-project-governor-repair` consistency tests stopped by missing authoritative `AGENTS.md:24`; this is outside the Gate allowlist and was not changed.
- `python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab`: PASS after repair evidence was prepared and before final execution projection update.
- `git diff --check`: PASS.
- UTF-8 YAML parse of all repaired YAML, profiles, simulation files, governance files: PASS; 12 files parsed.

## Final freeze checks

- Old v0.1 freeze after repair: `58` records; exactly `9` allowlisted repair subjects changed; protected unchanged subjects `49/49`.
- New post-repair v0.1 freeze: `65` records; `65/65` path/size/SHA-256 matches; mismatches `0`.
- Old independent-review report, review commands, review validation, old changed-path manifest, and old freeze manifest retained their baseline fingerprints.

## Scope and stop condition

- No old independent-review report, command, validation, changed-path manifest, or old freeze manifest was modified.
- No T-0037/T-0038 artifact, runtime behavior, Host Integration, baseline acceptance, version freeze, or rereview was started.
- Repair execution stops after validation and new freeze-manifest generation.
