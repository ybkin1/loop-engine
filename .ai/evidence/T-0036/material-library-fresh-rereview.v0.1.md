---
document_id: loop-engine-lab-material-library-fresh-rereview-t0036-v0.1
title: T-0036 修复后全新独立只读复审报告
document_class: evidence_only_rereview
gate_id: G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-REPAIR-V0-1
reviewer_agent_id: /root/fresh_rereview_auditor_retry
reviewer_context: fresh_context_without_parent_history
verdict: REPAIR_REQUIRED
---

# T-0036 修复后全新独立只读复审报告

## 1. 身份、独立性与边界

- Reviewer/session: `/root/fresh_rereview_auditor_retry`; numeric agent/session ID was not exposed by the collaboration API.
- Parent-session history: `no`; the reviewer did not inherit the main controller's conversation history.
- The reviewer did not participate in F-001..F-006 repair, full-suite fixture repair, continuity/legacy reconciliation, Gate preparation, or candidate-baseline decisions.
- Visible inputs included T-0036, the original independent review, the post-repair freeze and repair evidence, reconciliation validation, materials catalog/schema/register/coverage, profiles/templates, simulation profiles, and governance state/HANDOFF/gates/task graph.
- Boundary: read-only inspection and command execution only; no file creation, modification, deletion, repair, baseline acceptance, version freeze, T-0036 closeout, T-0037 review, or Host Integration.
- Limitations: no fresh network retrieval; no real model, Runtime, Agent, Host, or isolated-candidate behavior certification.

## 2. Frozen Input Preflight

The only review baseline was `.ai/evidence/T-0036/material-library-repair-freeze-manifest.v0.1.md`.

| check | result |
| --- | --- |
| declared subjects | 65 |
| parsed and unique subjects | 65 / 65 |
| path, byte size, full SHA-256 matches | 65 / 65 |
| mismatches | 0 |
| freeze manifest size | 10029 bytes |
| freeze manifest SHA-256 | `1CE2751794FBF643CD68976A70EFBD31FF6CACD3EECB0F70746BE45F0236783F` |
| freeze manifest ASCII `?` | 0 |

The preflight passed, so substantive review proceeded. The frozen subjects and freeze manifest remained read-only.

## 3. Review Method

The reviewer independently reconstructed acceptance from `.ai/tasks/T-0036.md` and `material-library-independent-review.v0.1.md`. Repair validation, tests, and prior AI conclusions were treated as claims to reproduce, not as proof of PASS.

The review independently parsed the catalog, schema, canonical YAML register, Markdown projection, coverage matrix, profiles, templates, simulation project/material/phase profiles, and freshness fields. It also rebuilt reference, subset, and path-boundary checks that were not covered by the existing repair validator.

## 4. Findings And Checks

### F-001: PASS

The catalog contains 46 unique records; required schema fields close; authority enum violations are 0. DOC-001 uses `authority=community_method`, compatible with `source_type=methodology` and the schema enum. No enum widening was used to hide an error.

### F-002: PASS

Catalog, canonical YAML register, and Markdown projection each close over 46 unique IDs. Missing, extra, duplicate, and verification-status conflicts are 0. YAML is declared canonical and Markdown is a human-readable projection. Markdown table escaping changes some display punctuation but does not change IDs or statuses.

### F-003: REPAIR_REQUIRED

The concrete `PHASE-PROFILE-T0036-SIM-FULL-DESIGN-V0.1` instance exists. Project, phase, material-selection, and phase-profile references close; all 11 phases have the required template core fields; `simulation_only=true` and `planned_not_executed=true` remain true.

Residual reference-closure failure: P1-P2 `human_decision.evidence_packet` entries in `.ai/evidence/T-0036/simulation/phase-profile.v0.1.yaml` point to `.ai/evidence/T-0036/material-library-review-packet.md`, which does not exist. The actual packet is `materials/material-library-review-packet.md`, already used by P7. The repair validator reports `phase_profile_ref=1/1` but does not inspect this nested path.

### F-004: PASS

Coverage independently expands to all 46 catalog IDs, including `ARCH-004`; missing, extra, and duplicate coverage are 0.

### F-005: REPAIR_REQUIRED

Project and phase IDs, versions, scopes, parent/subset relations, and strict subsets close: materials are 8/17 and templates are 7/9. However, `.ai/evidence/T-0036/simulation/project-profile.v0.1.yaml` includes `materials/templates/material-selection-record.yaml` in `selected_templates`; that path does not exist. The actual selection profile is `materials/profiles/material-selection-record.yaml`. This violates the selected-scope path-loading boundary even though subset counts pass.

### F-006: PASS

All 46 records contain the required freshness fields and satisfy the observed status invariants. HTTP/local split is 44/2; statuses are 37 `content_read`, 2 `url_verified_only`, and 7 `access_blocked`. Failed access was not upgraded and local sentinels are explicit. `HTTP 200` was not treated as automatic `content_read`.

## 5. Cross-File Semantic Checks

- The 65 frozen objects remain path/hash closed.
- Material classification, composition rules, and design boundaries remain candidate-material boundaries and are not promoted to Loop rules.
- The user-facing packet continues to state `candidate / ready_for_independent_review / baseline_not_accepted` and does not claim user acceptance.
- Simulation markers remain design-only and do not certify Runtime, Agent, model, Host, or production capability.
- The isolated-candidate verification gap remains explicitly open and is not folded into this material-library verdict.
- T-0035 remains administrative completion only, not product PASS, user acceptance, Runtime implementation, installation, or activation.
- Old T-0035..T-0039 numeric mapping supersession is explicit; unresolved historical work is not claimed complete.

## 6. Reproduction Results

- Repair validator: PASS; catalog 46, authority violations 0, register 46/46, coverage 46/46, freshness 46/46, phase reference 1/1, materials 8/17, templates 7/9.
- YAML parsing: 10 files PASS.
- Markdown UTF-8 reads: 8 files PASS.
- `python -m pytest tests/codex_loop -q`: 28 passed.
- `python -m pytest -q`: 41 passed, 5 subtests passed.
- `validate_state.py`: PASS.
- `audit_handoff.py`: PASS.
- `git diff --check`: PASS.

Tests and validators are evidence only and do not replace the semantic path review.

## 7. Unverified Items

Fresh network retrieval and external source-content truth were not performed. Isolated-candidate path behavior, real model behavior, Runtime/Agent/Host capability, user candidate-baseline decision, final version freeze, T-0036 closeout, and T-0037 review remain unverified and unauthorized.

## 8. Evidence-Only Verdict

Verdict: `REPAIR_REQUIRED`.

The verdict is caused by residual F-003 and F-005 reference/path-boundary failures. It authorizes no repair and does not imply candidate-baseline acceptance, version freeze, T-0036 closure, T-0037 review, Host Integration, or any runtime/production certification. A separate repair Gate is required before any later rereview.
