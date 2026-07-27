# T-0036 Fresh Independent Rereview After Path-Closure Repair Gate Request v0.1

Gate ID: `G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-PATH-CLOSURE-REPAIR-V0-1`

Status: `pending / user_decision_required / rereview_not_started / baseline_not_accepted`

## Decision Contract

This Gate requests a user decision on a future fresh, independent, read-only rereview of the repaired T-0036 material-library candidate.

- Gate creation is not approval.
- User approval is not rereview execution.
- After approval, the user must separately send the exact execution request.
- Approve: `批准 G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-PATH-CLOSURE-REPAIR-V0-1`
- Reject: `拒绝 G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-PATH-CLOSURE-REPAIR-V0-1`
- After approval only, execute: `执行 G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-PATH-CLOSURE-REPAIR-V0-1`

## Only Rereview Baseline

The only baseline is `.ai/evidence/T-0036/material-library-residual-path-repair-freeze-manifest.v0.1.md`.

- Declared, parsed, and unique subjects: `65 / 65 / 65`.
- Registration precheck: `65/65` path, byte size, and full SHA-256 matches; mismatches `0`.
- Manifest size: `9835` bytes.
- Manifest SHA-256: `DEF89CBB72A5A910CCC0A8C519F03C2B4E8F1526962B2415DB4DE893DFA13CFC`.
- Any subject or manifest drift requires `BLOCKED`; no rereview may proceed.

Prior review, repair, coordination, Gate preparation, validators, tests, and AI conclusions are background evidence only. They are not a fresh rereview verdict.

## Independence Contract

- The rereview must be performed by a reviewer subagent in a genuinely fresh context.
- That reviewer must not have participated in any earlier T-0036 repair, review, rereview, coordination, or Gate preparation.
- The reviewer must disclose agent/session identity, parent-history inheritance, visible inputs, read-only boundary, independence limitations, and unverified items.
- If independence cannot be established, stop before substantive review with `BLOCKED` or `USER_DECISION_REQUIRED`.
- The reviewer conclusion is an evidence-only verdict; it cannot approve a Gate, accept a baseline, freeze a version, close T-0036, or authorize downstream work.

## Required Independent Reconstruction

The reviewer must independently rebuild and check:

1. F-001 through F-006, using `.ai/tasks/T-0036.md` and the frozen candidate rather than accepting repair claims as conclusions.
2. F-003 P1-P2 `human_decision.evidence_packet` closure to `materials/material-library-review-packet.md`.
3. F-005 `selected_templates` closure to `materials/profiles/material-selection-record.yaml`.
4. Catalog, canonical register, Markdown projection, coverage, and freshness closure at `46/46`, with zero prohibited conflicts or omissions.
5. Phase/profile/selection reference closure, including materials strict subset `8/17` and templates strict subset `7/9`.
6. All 65 frozen objects by relative path, byte size, and full SHA-256.
7. `simulation-only`, `planned-not-executed`, and `baseline_not_accepted` boundaries.
8. The isolated candidate-path verification gap, T-0035 administrative-completion boundary, and old-roadmap supersession without false remediation-completion claims.

The reviewer must run the repair validator, YAML/Markdown parsing, `python -m pytest tests/codex_loop -q`, `python -m pytest -q`, `validate_state.py`, `audit_handoff.py`, and `git diff --check`. Passing deterministic checks is evidence only and does not replace semantic review.

Allowed verdicts: `PASS`, `REPAIR_REQUIRED`, `BLOCKED`, `USER_DECISION_REQUIRED`, `SCOPE_VIOLATION`.

`PASS` means only that the frozen repaired candidate has sufficient evidence to enter a later user candidate-baseline decision. It is not user acceptance, version freeze, T-0036 closeout, T-0037 review authorization, Host Integration authorization, or proof of Runtime/Agent/production capability.

## Registration Allowlist

- `.ai/evidence/T-0036/material-library-path-rereview-gate-request.v0.1.md`
- `.ai/evidence/T-0036/material-library-path-rereview-changed-path-baseline.v0.1.md`
- `.ai/evidence/T-0036/material-library-path-rereview-control-manifest.v0.1.md`
- `.ai/evidence/T-0036/material-library-path-rereview-registration-commands.v0.1.md`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`

The actual registration changed set must be a subset of these seven paths.

## Future Execution Allowlist

Only after explicit approval and a later exact execution request may the independent reviewer write:

- `.ai/evidence/T-0036/material-library-path-rereview.v0.1.md`
- `.ai/evidence/T-0036/material-library-path-rereview-commands.v0.1.md`
- `.ai/evidence/T-0036/material-library-path-rereview-validation.v0.1.md`
- `.ai/evidence/T-0036/material-library-path-rereview-changed-path-manifest.v0.1.md`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`

The actual execution changed set must be a subset of these seven paths.

## Explicit Forbidden Scope

- Do not modify any frozen object, the freeze manifest, or existing evidence.
- Do not repair any finding inside this rereview Gate.
- Do not accept the candidate baseline, freeze a version, or close T-0036.
- Do not create or execute T-0037 review.
- Do not enter Host Integration, Runtime, Agent, deployment, or a real project.
- Do not install or enable a skill, MCP, agent, plugin, hook, automation, protocol, or tool behavior.
- Do not perform rollback execution, database, permission, secret, payment, production-data, or migration actions.

## Validation And Recovery

1. Require the only baseline to match `65/65` before and after any future rereview.
2. Require the control manifest to remain byte-identical and independence disclosure to pass before substantive review.
3. Parse all YAML and Markdown inputs used for conclusions; run all required deterministic commands.
4. Compare actual changed paths to the exact phase allowlist; drift returns `BLOCKED`, and any path/effect breach returns `SCOPE_VIOLATION`.
5. Preserve unrelated dirty-worktree changes and any partial additive evidence. Do not auto-delete, reset, checkout, silently rebaseline, or perform destructive recovery.
6. Any correction, repair, destructive recovery, or scope expansion requires a separate explicit user Gate.

Current conclusion: `pending / user_decision_required / rereview_not_started / baseline_not_accepted`.
