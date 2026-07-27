# T-0036 Residual F-003/F-005 Path Repair Gate Request v0.1

Gate ID: `G-T-0036-REPAIR-F003-F005-PATH-CLOSURE-V0-1`

Status: `pending / user_decision_required`

## Decision Requested

Approve or reject this narrowly bounded repair Gate. Gate creation is not user approval and creates no repair authority. User approval is also not repair execution: after approval, Codex must wait for a separate exact execution request.

- Approval: `批准 G-T-0036-REPAIR-F003-F005-PATH-CLOSURE-V0-1`
- Rejection: `拒绝 G-T-0036-REPAIR-F003-F005-PATH-CLOSURE-V0-1`
- Later execution request: `执行 G-T-0036-REPAIR-F003-F005-PATH-CLOSURE-V0-1`

This Gate does not authorize fresh rereview, candidate-baseline acceptance, version freeze, T-0037 review, or Host Integration.

## Preconditions And Findings

- T-0036 remains `active` in `S0-method-repair`.
- Fresh independent rereview returned evidence-only `REPAIR_REQUIRED` for residual F-003 and F-005.
- `validate_state.py` passed before registration and no pending Gate existed.
- F-003: `.ai/evidence/T-0036/simulation/phase-profile.v0.1.yaml` P1-P2 `human_decision.evidence_packet` points to nonexistent `.ai/evidence/T-0036/material-library-review-packet.md`; existing target is `materials/material-library-review-packet.md`.
- F-005: `.ai/evidence/T-0036/simulation/project-profile.v0.1.yaml` `selected_templates` contains nonexistent `materials/templates/material-selection-record.yaml`; existing target is `materials/profiles/material-selection-record.yaml`.

## Exact Registration Paths

- `.ai/evidence/T-0036/material-library-residual-path-repair-gate-request.v0.1.md`
- `.ai/evidence/T-0036/material-library-residual-path-repair-changed-path-baseline.v0.1.md`
- `.ai/evidence/T-0036/material-library-residual-path-repair-registration-commands.v0.1.md`
- `.ai/evidence/T-0036/material-library-residual-path-repair-sidecar-audit.v0.1.md`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`

## Exact Future Repair Paths

Only after approval and a later exact execution request may these paths change:

- `.ai/evidence/T-0036/simulation/phase-profile.v0.1.yaml`
- `.ai/evidence/T-0036/simulation/project-profile.v0.1.yaml`
- `.ai/evidence/T-0036/material-library-residual-path-repair-commands.v0.1.md`
- `.ai/evidence/T-0036/material-library-residual-path-repair-validation.v0.1.md`
- `.ai/evidence/T-0036/material-library-residual-path-repair-changed-path-manifest.v0.1.md`
- `.ai/evidence/T-0036/material-library-residual-path-repair-freeze-manifest.v0.1.md`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`

## Exact Mechanical Repair

1. In `phase-profile.v0.1.yaml`, replace every P1-P2 occurrence of `.ai/evidence/T-0036/material-library-review-packet.md` with `materials/material-library-review-packet.md`.
2. In `project-profile.v0.1.yaml`, replace `materials/templates/material-selection-record.yaml` with `materials/profiles/material-selection-record.yaml`.

No line reordering, formatting, normalization, refactor, or other content change is allowed.

## Forbidden Scope And Effects

- Do not modify any material, test, global Project Governor, T-0037/T-0038, `codex_loop`, runtime, or other frozen object except the two exact YAML repair targets after both required user messages.
- Do not modify prior review, repair, validation, freeze, or Gate evidence.
- Do not enable or change any skill, MCP, agent, automation, protocol, installation, activation, deployment, database, permission, secret, payment, production-data, migration, or real-project behavior.
- Do not perform repair during registration. Stop after Gate registration and governance validation.

## Validation And Recovery

- Before repair, require exact preimage size/SHA-256 matches for both YAML targets and unchanged 65-subject freeze.
- After repair, require YAML parse, exact two-string diff, reference existence, changed-path allowlist closure, `validate_state.py`, `audit_handoff.py`, and `git diff --check`.
- Create a new post-repair freeze manifest; never overwrite the existing 65-subject freeze manifest.
- On drift, unexpected multiplicity, parse failure, or scope breach, stop with `BLOCKED` or `SCOPE_VIOLATION`; preserve unrelated user changes and do not perform destructive rollback.

Current conclusion: `pending / user_decision_required / repair_not_started / rereview_not_started / baseline_not_accepted / version_not_frozen`.
