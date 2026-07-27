# T-0036 F-001..F-006 Independent Repair Gate Request v0.1

Gate ID: `G-T-0036-REPAIR-F001-F006-V0-1`

Status: `pending / user_decision_required`

## Decision requested

Approve or reject this independent repair Gate. Gate creation is not approval and does not execute repair. Approval authorizes only the later, separately requested bounded repair execution; it does not authorize rereview, candidate-baseline acceptance, version freeze, T-0037 review, or Codex Host Integration.

Exact decision phrases:

- `批准 G-T-0036-REPAIR-F001-F006-V0-1`
- `拒绝 G-T-0036-REPAIR-F001-F006-V0-1`

After approval, a separate exact execution phrase is still required:

- `执行 G-T-0036-REPAIR-F001-F006-V0-1`

## Preconditions

- T-0036 remains `active` in `S0-method-repair`.
- The fresh independent review returned evidence-only `REPAIR_REQUIRED` for F-001..F-006.
- The old 58-input freeze has been rechecked before this registration: `58/58` path, size, and SHA-256 matches; drift `0`.
- No pending Gate existed before registration; `validate_state.py` returned `[ok] state is usable`.
- Existing user modifications are preserved. This Gate does not claim authorship of any pre-existing worktree change.

## Repair scope and exact mapping

| finding | root cause | target and proposed fields | acceptance |
| --- | --- | --- | --- |
| F-001 | DOC-001 uses a value from `source_type` semantics in the `authority` field. | `materials/catalog.yaml`: DOC-001 `authority: industry_practice` -> `community_method`; keep `source_type: methodology`; keep `materials/material-schema.yaml` enum unchanged. | 46/46 authorities are in the Schema enum; violations `0`. |
| F-002 | The hand-maintained Markdown register has 38 IDs for a 46-item catalog and DOC-002 disagrees across files. | `materials/source-register.yaml` (new canonical records), `materials/source-register-schema.yaml` (new constraints), `materials/source-register.md` (46-row projection), `materials/catalog.yaml` DOC-002 status/observation. Add the eight missing IDs and synchronize status by ID. | catalog/register/Markdown IDs are exactly equal, `46/46`; missing, extra, duplicate, and status-conflict counts are `0`. |
| F-003 | The project profile references an ID with no concrete instance; a generic template is not an instance. | `.ai/evidence/T-0036/simulation/phase-profile.v0.1.yaml` (new aggregate instance), simulation project profile reference, and phase-selection reference. | Exactly one resolvable instance for the referenced ID; project -> phase -> selection -> project closure `100%`; candidate/design-only markers remain explicit. |
| F-004 | Coverage matrix stops at ARCH-003 although catalog contains ARCH-004. | `materials/coverage-matrix.md`: architecture row `ARCH-001..003` -> `ARCH-001..004`. | Expanded coverage IDs equal catalog IDs; missing/extra `0`; ARCH-004 is covered, with no exclusion record. |
| F-005 | Project selection is an inline 17-item list while phase selection has 8 items without explicit version/scope/subset semantics. | Simulation profiles plus `materials/profiles/project-profile.yaml`, `materials/profiles/material-selection-record.yaml`: add stable selection ID/version/scope, `parent_selection_id`, `subset_relation: strict_subset`, `phase_profile_id`, and normalized `materials/templates/...` paths. | IDs, versions, scopes and references are non-empty and unique; phase materials `8` are a strict subset of project materials `17`; phase templates `7` are a strict subset of project templates `9`; all references resolve. |
| F-006 | The catalog has only a top-level retrieval date; per-item HTTP, final URL, title and failure data are not structurally closed. | Canonical source register/schema: each of 46 records has `retrieved_at` (RFC3339 with offset), `http_status`, `final_url`, `page_title`, `failure_reason`, access method, status and observation. Update README to identify YAML as canonical and Markdown as projection. | 46/46 records have all fields; 44 HTTP(S) and 2 local records use explicit types/sentinels; status/field invariants pass; actual retrieval failures remain failures and are never upgraded. |

F-002 and F-006 are one coordinated source-register/catalog change. No unrelated refactor is allowed.

## Exact paths allowed during Gate registration

Only these paths may be created or modified in this registration:

- `.ai/evidence/T-0036/material-library-repair-gate-request.v0.1.md`
- `.ai/evidence/T-0036/material-library-repair-changed-path-baseline.v0.1.md`
- `.ai/evidence/T-0036/material-library-repair-registration-commands.v0.1.md`
- `.ai/evidence/T-0036/material-library-repair-sidecar-audit.v0.1.md`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`

## Exact paths allowed only after approval and a separate execution request

Repair objects and additive execution evidence are restricted to this explicit list:

- `materials/README.md`
- `materials/catalog.yaml`
- `materials/source-register.md`
- `materials/source-register.yaml`
- `materials/source-register-schema.yaml`
- `materials/coverage-matrix.md`
- `materials/profiles/project-profile.yaml`
- `materials/profiles/material-selection-record.yaml`
- `materials/templates/phase-profile.yaml`
- `.ai/evidence/T-0036/simulation/project-profile.v0.1.yaml`
- `.ai/evidence/T-0036/simulation/material-selection.v0.1.yaml`
- `.ai/evidence/T-0036/simulation/phase-profile.v0.1.yaml`
- `.ai/evidence/T-0036/material-library-repair-validator.v0.1.py`
- `.ai/evidence/T-0036/material-library-repair-commands.v0.1.md`
- `.ai/evidence/T-0036/material-library-repair-validation.v0.1.md`
- `.ai/evidence/T-0036/material-library-repair-changed-path-manifest.v0.1.md`
- `.ai/evidence/T-0036/material-library-repair-freeze-manifest.v0.1.md`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`

The validator and all repair evidence are additive. Existing `.ai/tasks/T-0036.md`, `.ai/task_graph.yaml`, `.ai/DECISIONS.md`, and `materials/material-schema.yaml` are not repair targets in this Gate.

## Explicitly forbidden paths and effects

- All 58 paths in the old freeze manifest remain read-only throughout Gate preparation. After execution starts, the old freeze manifest and every frozen path not explicitly listed above remain immutable.
- Do not modify, append, normalize, replace, rename, delete, or overwrite the prior independent review report, review commands, review validation, review changed-path manifest, old freeze manifest, approval record, Gate request, or registration commands.
- Do not modify `.ai/evidence/T-0035/**`, `.ai/evidence/T-0037/**`, `.ai/evidence/T-0038/**`, `codex_loop/**`, `tests/codex_loop/**`, `docs/codex-loop/**`, `AGENTS.md`, global `C:\Users\Administrator\.codex\skills\**`, or system configuration.
- Do not perform repair during Gate preparation; do not run fresh HTTP retrieval during Gate preparation.
- Do not perform rereview, baseline acceptance, version freeze, T-0037 review, Host Integration, installation, activation, deployment, migration, database, permissions, secrets, payment, production data, or external business-project actions.

## Changed-path and freeze proof

- The pre-registration baseline is `.ai/evidence/T-0036/material-library-repair-changed-path-baseline.v0.1.md`.
- Before and after Gate registration, parse the old freeze manifest and verify all 58 exact relative paths, byte sizes, and SHA-256 values. Any mismatch stops the operation and records `BLOCKED`.
- Future repair execution must compare every changed path against the baseline, prove the changed set is an exact subset of this Gate list, record before/after fingerprints, and list absent-to-present files. The old 58-input set must remain unchanged except for explicitly approved repair objects; no historical evidence is overwritten.

## Candidate diff / mechanical change list

- `catalog.yaml`: one authority value, one status/observation reconciliation, plus no unrelated ordering changes.
- `source-register.yaml`: add one canonical record per catalog ID with the required retrieval fields; `source-register-schema.yaml`: define required keys and conditional status invariants; `source-register.md`: regenerate the 46-row human projection without changing meaning.
- `coverage-matrix.md`: one range expansion from `ARCH-001..003` to `ARCH-001..004`.
- Profile templates and simulation selections: additive ID/version/scope/parent/subset/phase fields and normalized repository-relative template paths; no material re-selection.
- `phase-profile.v0.1.yaml`: one aggregate candidate instance with the existing referenced ID, project back-reference, material-selection reference, all phase entries, and explicit design-only/planned-not-executed markers.
- `README.md`: identify `source-register.yaml` as canonical and Markdown as projection.
- No unrelated formatting, renaming, reordering, or refactoring is permitted.

## Verification plan

After the later exact execution request, run and record:

1. Strict UTF-8 decode; YAML parse for every YAML/schema file; Markdown structural checks; validator script syntax and deterministic output.
2. `authority` enum violations `0` against `materials/material-schema.yaml`.
3. catalog count `46`; canonical register count `46`; IDs unique and exactly closed; Markdown projection count/IDs equal; status conflicts `0`.
4. Phase-profile reference resolution `1/1` and full closure `100%`; no unresolved internal path or ID.
5. Coverage expansion covers all catalog IDs; `missing=0`, `extra=0`, or an explicit machine-readable exclusion (none is planned).
6. Project/phase selection IDs, versions, scopes, parent relation and strict-subset checks; materials `8 < 17`, templates `7 < 9`, both subsets true.
7. Freshness closure `46/46`: per-item `retrieved_at`, HTTP status, final URL, page title, failure reason; 44 HTTP(S) and 2 local access methods; timestamps inside the recorded retrieval window; content/status conditional invariants.
8. Run related deterministic tests/checks, the new validator, `python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab`, and `git diff --check`.
9. Generate `material-library-repair-freeze-manifest.v0.1.md` after repair without modifying the old freeze manifest. Stop immediately after repair validation and freeze generation.

The later fresh independent rereview must be a separate Gate, a fresh context, a separate approval, and a separate exact execution request. Repair validation is evidence only and cannot become rereview PASS.

## Risks and recovery

- Schema compatibility: freshness constraints must be introduced atomically with all 46 records; do not leave a half-upgraded consumer or silently widen an enum.
- Source status fabrication: HTTP 200 is not `content_read`; final URL/title must be observed; blocked/timeout/local cases require explicit truthful sentinel and failure data.
- Dual-register drift: canonical YAML, catalog status, and Markdown projection must be cross-checked by ID and status.
- Path drift and historical evidence pollution: all worktree objects are fingerprinted; old evidence and old freeze remain immutable.
- Scope expansion: no T-0037, Host Integration, runtime behavior, global tool behavior, or unrelated cleanup.
- On mismatch, path breach, parse failure, test failure, network recording failure, or incomplete evidence, stop and preserve truthful partial evidence with `BLOCKED` or `repair_incomplete`. Do not fabricate completion.
- No deletion or destructive rollback is included. Any destructive recovery requires a separate Gate.

## Authorization boundary

- Gate creation is not user approval.
- User approval is not repair execution authorization.
- Repair execution requires both the exact approval phrase and a later exact execution request.
- Repair completion must stop immediately. No independent rereview occurs in this Gate.
- Rereview, candidate-baseline acceptance, version freeze, T-0037 review, and Codex Host Integration each require later independent Gates.

Current conclusion: `pending / user_decision_required / repair_not_started / baseline_not_accepted`.
