# T-0036 Fresh Independent Rereview After Repair Gate Request v0.1

Gate ID: `G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-REPAIR-V0-1`

Status: `pending / user_decision_required / rereview_not_started`

## Decision Requested

Approve or reject a future fresh, independent, read-only rereview of the repaired T-0036 material-library candidate. Gate creation is not approval. Approval is not execution. After approval, the user must separately issue the exact execution request.

- Approve: `批准 G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-REPAIR-V0-1`
- Reject: `拒绝 G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-REPAIR-V0-1`
- After approval only, execute: `执行 G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-REPAIR-V0-1`

## Frozen Baseline Precondition

The only rereview baseline is `.ai/evidence/T-0036/material-library-repair-freeze-manifest.v0.1.md`.

- Declared, parsed, and unique subjects: `65 / 65 / 65`.
- Registration precheck: `65/65` path, byte size, and full SHA-256 match; mismatches `0`.
- Manifest size: `10029` bytes.
- Manifest SHA-256: `1CE2751794FBF643CD68976A70EFBD31FF6CACD3EECB0F70746BE45F0236783F`.
- Manifest ASCII `?` count: `0`.
- Any subject mismatch or manifest drift requires `BLOCKED`; no executable rereview Gate may proceed.

Historical review, repair, full-suite fixture repair, governance reconciliation, validators, tests, and AI conclusions are background evidence only. None is a rereview `PASS`.

## Independence Contract

- The reviewer must use a genuinely fresh context that did not participate in F-001..F-006 repair, full-suite fixture repair, continuity/legacy reconciliation, this Gate preparation, or candidate-baseline acceptance/version freeze.
- The report must disclose reviewer agent/session ID, whether parent-session history was inherited, visible inputs, read-only boundary, independence limitations, and unverified items.
- The reviewer must reconstruct acceptance from `.ai/tasks/T-0036.md` and the original review, rather than merely checking repair reports.
- If genuine independence cannot be established, return `BLOCKED` or `USER_DECISION_REQUIRED` before substantive review.

## Substantive Rereview Checklist

1. F-001 authority schema: 46 catalog records, zero enum violations, and semantically valid DOC-001 repair without widening the enum to hide an error.
2. F-002 register closure: catalog, canonical YAML, and Markdown projection are 46/46; missing, extra, duplicate, and status conflicts are zero; YAML is canonical and Markdown is a human-readable projection.
3. F-003 phase profile: `PHASE-PROFILE-T0036-SIM-FULL-DESIGN-V0.1` exists; project profile, material selection, and phase-profile references close; every phase satisfies the template; simulation-only and planned-not-executed boundaries hold.
4. F-004 coverage: all 46 catalog IDs are covered, including `ARCH-004`; missing, extra, and duplicate coverage are zero.
5. F-005 selection/profile boundary: project and phase selections have explicit IDs, versions, and scopes; parent/subset relation closes; materials are a strict `8/17` subset; templates are a strict `7/9` subset; path format is uniform and no out-of-scope implicit loading exists.
6. F-006 freshness: all 46 records contain `retrieved_at`, `http_status`, `final_url`, `page_title`, `failure_reason`, `verification_status`, and `source_observation`; HTTP and local status rules differ lawfully; `HTTP 200` does not imply `content_read`; failed access is not upgraded; timestamps, final URLs, and titles are observed rather than inferred.

The rereview must also check material classification, composition rules, design boundaries, reference closure across all 65 subjects, explicit non-acceptance wording, simulation/Runtime/Agent/Host truthfulness, the separately registered candidate-path gap, T-0035 administrative-only closure, and old-roadmap supersession without false remediation-completion claims.

## Independent Reproduction

The reviewer must independently run or rebuild the repair validator, YAML/Markdown/Schema parsing, catalog/register/coverage/reference closure, selection/profile subset checks, freshness invariants, `python -m pytest tests/codex_loop -q`, `python -m pytest -q`, `validate_state.py`, `audit_handoff.py`, and `git diff --check`.

Passing tests are evidence only and do not replace semantic rereview.

## Verdict Contract

Allowed verdicts: `PASS`, `REPAIR_REQUIRED`, `BLOCKED`, `USER_DECISION_REQUIRED`, `SCOPE_VIOLATION`.

`PASS` can mean only that the repaired T-0036 candidate package has sufficient evidence to enter a later user candidate-baseline decision. It does not mean user acceptance, version freeze, T-0036 closeout, T-0037 review authorization, Codex Host Integration, or certification of Runtime, Agent, role, or production capability.

## Registration Allowlist

- `.ai/evidence/T-0036/material-library-fresh-rereview-gate-request.v0.1.md`
- `.ai/evidence/T-0036/material-library-fresh-rereview-changed-path-baseline.v0.1.md`
- `.ai/evidence/T-0036/material-library-fresh-rereview-control-manifest.v0.1.md`
- `.ai/evidence/T-0036/material-library-fresh-rereview-registration-commands.v0.1.md`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`

The approval record is intentionally absent until a later explicit user approval.

## Future Execution Allowlist

Only after explicit approval and a later exact execution request may the rereview write:

- `.ai/evidence/T-0036/material-library-fresh-rereview.v0.1.md`
- `.ai/evidence/T-0036/material-library-fresh-rereview-commands.v0.1.md`
- `.ai/evidence/T-0036/material-library-fresh-rereview-validation.v0.1.md`
- `.ai/evidence/T-0036/material-library-fresh-rereview-changed-path-manifest.v0.1.md`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`

The actual changed set must be a strict subset of this allowlist.

## Explicit Forbidden Scope

- No modification of any of the 65 frozen subjects, the freeze manifest, or existing review, repair, full-suite, or reconciliation evidence.
- No repair of rereview findings; no candidate or global Project Governor modification.
- No candidate-baseline acceptance, version freeze, T-0036 closeout, T-0037 review creation/execution, or Host Integration.
- No installation or enablement of skill, MCP, agent, plugin, hook, automation, protocol, or runtime.
- No deployment, rollback execution, database, permission, secret, payment, production-data, migration, or external business-project action.

## Verification Plan

1. Before and after future rereview, require `65/65` path, size, and SHA-256 matches and an unchanged control manifest.
2. Require a genuinely fresh reviewer disclosure before substantive rereview.
3. Parse all modified YAML; run the two pytest commands, `validate_state.py`, `audit_handoff.py`, and `git diff --check`.
4. Compare actual changed paths to the exact execution allowlist and require a strict subset.
5. Treat any drift as `BLOCKED` and any scope breach as `SCOPE_VIOLATION`; stop immediately.

## Risks And Recovery

- False independence could make a rereview circular; stop before content review if independence cannot be demonstrated.
- Dirty-worktree overlap could overwrite user changes; enforce byte-level preimages and preserve unrelated paths.
- Passing validators/tests could be overclaimed as semantic or Runtime proof; keep verdict language evidence-only.
- Freeze or control drift invalidates the reviewed object; stop and prepare a new user-decision Gate rather than silently rebaseline.
- Preserve partial additive evidence on failure. Do not auto-delete it or reverse unrelated work. Destructive recovery requires a separate explicit Gate.

Current conclusion: `pending / user_decision_required / rereview_not_started / baseline_not_accepted`.
