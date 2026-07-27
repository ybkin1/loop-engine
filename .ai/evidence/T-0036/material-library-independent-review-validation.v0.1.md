# T-0036 独立评审验证证据 v0.1

## Review validation

- review report: .ai/evidence/T-0036/material-library-independent-review.v0.1.md
- review commands: .ai/evidence/T-0036/material-library-independent-review-commands.v0.1.md
- reviewer identity: 019f8e41-8ff8-7fa0-be82-448aa615f271
- reviewer context: fresh spawned read-only context without parent thread history
- reviewer verdict: REPAIR_REQUIRED
- findings: F-001/P1, F-002/P1, F-003/P1, F-004/P2, F-005/P2, F-006/P2

## Deterministic checks

- frozen subjects before review: 58/58 path, size, SHA-256 matches
- frozen subjects after review: 58/58 path, size, SHA-256 matches
- catalog/schema YAML parse: PASS
- catalog material count: 46
- required metadata fields non-empty: 46/46 for 17 required fields
- authority enum validation: 1 violation, DOC-001 / industry_practice
- source-register ID closure: 8 catalog IDs absent; documented as F-002
- coverage matrix expansion: 45 IDs versus 46 catalog IDs; ARCH-004 missing; documented as F-004
- simulation phase-profile instance closure: missing concrete instance; documented as F-003
- simulation profile/selection scope: 17 versus 8 selected materials without explicit subset/version relation; documented as F-005
- per-material retrieved_at: 0/46; documented as F-006

## Governance validation

- validate_state.py: PASS
- audit_handoff.py: PASS
- git diff --check: PASS
- changed paths are limited to the Gate's separately allowed additive review evidence and governance projection files.
- frozen T-0036 candidate inputs and historical evidence remain unchanged.

## Boundary validation

- review verdict is evidence-only.
- repair_authorized: false
- rereview_authorized: false
- candidate_baseline_acceptance_authorized: false
- version_freeze_authorized: false
- downstream T-0037 review authorized: false
- Host Integration authorized: false
