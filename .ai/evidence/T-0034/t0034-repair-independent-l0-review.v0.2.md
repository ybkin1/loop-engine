# T-0034 Fresh Independent L0 Read-Only Review v0.2

Gate: `G-T-0034-FRESH-INDEPENDENT-L0-READ-ONLY-REVIEW-V0-2`

Requirements revision: `T-0034-REQ-2026-07-16-R1`

Assurance profile: `A3` fresh-context, protected hashes, full coverage, recovery, authority, product, architecture, API/protocol, QA, security, continuity, and governance-boundary overlays.

## Independence Declaration

The reviewer reconstructed the baseline from `.ai/PROJECT.md`, `.ai/tasks/T-0034.md`, canonical Gate/state/graph records, the canonical requirements baseline, and the frozen review subjects. Repair-author conclusions were treated as claims to reproduce, not proof. The review was read-only toward all fourteen frozen subjects. No repair, closeout, downstream task, implementation, installation, activation, candidate/global modification, or user-acceptance inference occurred.

## Frozen Subject Admission

All fourteen subjects matched the Gate and freeze manifest by exact project-relative path, byte size, and full SHA-256 before review. UTF-8 decoding succeeded. No review output existed before execution.

## Independent Deterministic Results

- Canonical registries: exactly `WS-01..08`, `OUT-01..09`, and `AC-01..12`.
- Coverage matrix: eight unique WS rows and nine unique OUT rows with artifact, acceptance, tests, roles, and status columns.
- Machine catalog: 52 referenced `MC-*`/`ADV-*` IDs and 52 definitions; set equality passed.
- Golden vectors: `GV-001..016`; ten fenced JSON blocks and eight inline JSON examples parsed.
- YAML: `.ai/gates.yaml`, `.ai/state.yaml`, and `.ai/task_graph.yaml` parsed.
- Authority/lifecycle review found no implementation, installation, activation, downstream, closeout, or user-acceptance authorization in the frozen subjects.

## Findings

### `T0034-L0R2-F001` — P1 — Canonical payload hash scope is not reproducible as declared

- Requirements: `AUTH-04`, `AC-07`, `OUT-01`, `MC-BASE-001`.
- Evidence: `.ai/evidence/T-0034/t0034-requirements-baseline.v0.2.md`, envelope `hash_scope` and the bytes between `CANONICAL-PAYLOAD` markers.
- Reproduction:
  1. Strictly select UTF-8 LF bytes between marker lines, excluding marker lines, as declared.
  2. Hash the resulting 7,122 bytes, including the LF immediately before the end marker.
  3. Actual SHA-256 is `212BA36B34F4071822DD6879DC94950889EDDE42CA209E424D599AE9BBD976C4`.
  4. The declared SHA-256 `A262B227ABA88E1CF3F235BF7CA9F9FB3023985F5EFDF017FAE05F8FF169582F` is obtained only after additionally stripping the trailing LF, which `hash_scope` does not specify.
- Impact: two conforming implementations can disagree about the canonical baseline hash; freshness, continuity, protected-baseline, and compatibility checks cannot use a single reproducible oracle.
- Required disposition: additive repair must define exact boundary-newline handling and update the declared hash or payload accordingly, then receive fresh independent rereview.
- Blocked effects: artifact PASS, T-0034 closeout, downstream design reliance.

### `T0034-L0R2-F002` — P1 — Same-version `Finding/v1.0` and `Verdict/v1.0` schemas conflict across canonical artifacts

- Requirements: `OUT-04`, `OUT-05`, `AC-03`, `AC-08`, `MC-SCHEMA-001`, `MC-COMPAT-001`.
- Evidence:
  - `.ai/evidence/T-0034/controller-agent-interface-schemas.v0.2.md`, section 9.
  - `.ai/evidence/T-0034/neutral-audit-charter-assurance-schemas.v0.2.md`, sections 6-7.
- Reproduction:
  - Interface `Finding/v1.0` requires `affected_scope`, `reproducibility`, and `owner_role`; audit `Finding/v1.0` instead requires `confidence`, `role_overlay`, `reproduction`, `impact`, and `recommended_disposition`.
  - Interface `Verdict/v1.0` requires `layer`, `requirement_coverage`, and `authority_ref`; audit `Verdict/v1.0` instead requires `subject_hash`, `requirements_revision`, `assurance_profile_id`, `coverage_complete`, `unresolved_findings`, `unverified_requirements`, `reviewer_independence`, and `authority_effect`.
  - Neither artifact declares one definition as an extension/profile of the other, a canonical merged schema, optionality/defaults, or a major-version boundary.
- Impact: `MC-SCHEMA-001` has no unique same-version schema oracle; controller/auditor packets can each conform locally while being mutually incompatible, breaking evidence fan-in and verdict transport.
- Required disposition: establish one canonical base schema plus explicitly versioned extensions/profiles, define required/optional fields and compatibility behavior, update cross-file references and golden vectors, then receive fresh independent rereview.
- Blocked effects: artifact PASS, interface implementation admission, T-0034 closeout, downstream design reliance.

## Verdict

```yaml
verdict_id: T0034-L0R2-V001
value: REPAIR_REQUIRED
coverage_complete: true
blocking_findings:
  - T0034-L0R2-F001
  - T0034-L0R2-F002
unverified_requirements: []
authority_effect: evidence_only
task_closeout_authorized: false
user_acceptance_asserted: false
```

The verdict follows the frozen rule that any unresolved P1 requires `REPAIR_REQUIRED`. It does not authorize repair, modify any artifact, close T-0034, create downstream tasks, or assert task/project/user PASS.

## Residual Risk And Next Safe Action

P2/P3 improvement opportunities were not elevated because the two P1 contract defects already block artifact PASS. Stop at review evidence. Any repair requires a separate pending repair Gate with exact additive paths, immutable baselines, validation, recovery, and a later separate rereview decision.
