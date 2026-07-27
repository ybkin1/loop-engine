# T-0036 Repair Gate Sidecar Audit v0.1

Gate: `G-T-0036-REPAIR-F001-F006-V0-1`
Purpose: read-only evidence used while preparing the Gate. These conclusions do not approve the Gate.

## Re-run status

Three fresh read-only subagent contexts were relaunched after the session breakpoint. Each was restricted to `.ai/`, the 58 frozen inputs, and existing evidence. None modified, created, deleted, or normalized a file; none executed repair or network retrieval.

The re-run independently confirmed: frozen inputs `58/58`, path/size/SHA-256 matches `58/58`, drift `0`; `catalog=46`; `source-register=38`; missing IDs `AGENT-002, AGENT-003, ARCH-004, API-004, CODE-002, CODE-003, LOOP-001, LOOP-002`; one known DOC-002 status conflict; coverage `45/46`; project/phase material selection `17/8` with actual subset; and no concrete phase-profile instance.

## Consolidated evidence

### Root cause and minimal correction

- F-001: change only `materials/catalog.yaml` DOC-001 `authority` from `industry_practice` to the existing Schema enum value `community_method`; do not expand the enum.
- F-002: make catalog and source register a 46-ID closed set, add the eight missing IDs, and reconcile DOC-002 from actual recorded evidence. F-002 and F-006 use one source-register change set.
- F-003: add one aggregate candidate instance with ID `PHASE-PROFILE-T0036-SIM-FULL-DESIGN-V0.1`; link it bidirectionally to the project profile and phase selection and validate the full phase set.
- F-004: change the architecture coverage range from `ARCH-001..003` to `ARCH-001..004`; no exclusion is supported by current evidence.
- F-005: preserve existing IDs but add explicit version, scope, parent/subset relation, normalized repository paths, and a phase-profile reference. The generic profile templates are included to prevent regeneration of the same ambiguity.
- F-006: use a machine-readable canonical source register and schema with one retrieval record per material; the Markdown register remains a human-readable projection. Record real HTTP/final URL/title/failure values and explicit local/not-observed sentinels; never infer success.

### Design decisions fixed for this Gate

- `PHASE-PROFILE-T0036-SIM-FULL-DESIGN-V0.1` is one aggregate candidate profile containing a `phases` list; each phase entry retains the template fields `phase_id`, `entry_conditions`, `activities`, `exit_conditions`, `human_decision`, `tailoring`, and `forbidden_transition`.
- `materials/profiles/project-profile.yaml` and `materials/profiles/material-selection-record.yaml` are updated additively with the same selection ID/version/scope vocabulary used by the simulation instances.
- `materials/source-register.yaml` is canonical for machine checks; `materials/source-register.md` is a projection and must declare that relationship. `materials/source-register-schema.yaml` constrains the canonical records.

## Limitations

The subagents did not perform fresh HTTP retrieval, decide user acceptance, approve the Gate, modify frozen inputs, perform repair, perform rereview, accept a baseline, freeze a version, review T-0037, or enter Host Integration.
