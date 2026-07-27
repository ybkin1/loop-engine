# T-0036 Fresh Independent Rereview Validation v0.1

Gate: `G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-REPAIR-V0-1`

Verdict: `REPAIR_REQUIRED`

This is an evidence-only verdict. It does not authorize repair, candidate-baseline acceptance, version freeze, T-0036 closeout, T-0037 review, or Host Integration.

## Acceptance Matrix

| check | result |
| --- | --- |
| reviewer independence | PASS; fresh context `/root/fresh_rereview_auditor_retry`, no parent history |
| frozen subjects | 65/65 path, size, and SHA-256 matches |
| freeze manifest | 10029 bytes; SHA-256 `1CE2751794FBF643CD68976A70EFBD31FF6CACD3EECB0F70746BE45F0236783F`; ASCII `?` = 0 |
| F-001 authority schema | PASS; catalog 46, enum violations 0; DOC-001 authority legal |
| F-002 source register closure | PASS; catalog/register/Markdown IDs 46/46; conflicts 0 |
| F-003 phase profile | REPAIR_REQUIRED; residual nonexistent `human_decision.evidence_packet` path in P1-P2 |
| F-004 coverage | PASS; 46/46 including `ARCH-004`; missing/extra/duplicate 0 |
| F-005 selection/profile boundary | REPAIR_REQUIRED; residual nonexistent selected template path |
| F-006 freshness | PASS; fields/invariants 46/46; HTTP/local 44/2 |
| repair validator | PASS |
| focused pytest | PASS; 28 passed |
| full pytest | PASS; 41 passed, 5 subtests passed |
| validate_state.py | PASS |
| audit_handoff.py | PASS |
| git diff --check | PASS |

## Post-Review Freeze Requirement

Before and after evidence recording, the 65-subject freeze must remain `65/65` with unchanged manifest size, SHA-256, and ASCII `?` count. Any drift is `BLOCKED`; any changed path outside the execution allowlist is `SCOPE_VIOLATION`.

## Post-Execution Verification

- Final freeze check: `65/65`; manifest size `10029`; SHA-256 `1CE2751794FBF643CD68976A70EFBD31FF6CACD3EECB0F70746BE45F0236783F`; ASCII `?` = `0`.
- `validate_state.py`: PASS; `audit_handoff.py`: PASS; `git diff --check`: PASS.
- Gate state: `approved / review_completed_repair_required`; pending Gate count `0`; `rereview_authorized=true` records the exact execution authorization, while all repair, baseline-acceptance, version-freeze, T-0037, and Host Integration flags remain false.
- Actual changed paths are a strict subset of the seven-path execution allowlist; frozen subjects, control manifest, and prior evidence did not drift.

## Residual Findings

- F-003 residual reference closure: `.ai/evidence/T-0036/simulation/phase-profile.v0.1.yaml` P1-P2 `human_decision.evidence_packet` points to `.ai/evidence/T-0036/material-library-review-packet.md`, which does not exist. The actual user packet is `materials/material-library-review-packet.md`; P7 already uses that path. The validator reports `phase_profile_ref=1/1` but does not check this nested evidence path.
- F-005 residual path boundary: `.ai/evidence/T-0036/simulation/project-profile.v0.1.yaml` `selected_templates` contains `materials/templates/material-selection-record.yaml`, which does not exist. The actual selection profile is `materials/profiles/material-selection-record.yaml`. Subset counts and IDs pass, but path loading closure does not.

## Other Semantic Checks

65 frozen-object references, material categories, composition/design boundaries, user-facing `baseline_not_accepted` wording, simulation-only/planned-not-executed markers, T-0035 administrative-only boundary, and old roadmap supersession were consistent. The isolated-candidate verification gap remains open and is outside this material-library verdict. No network re-fetch or real Runtime/Agent/Host behavior was performed.
