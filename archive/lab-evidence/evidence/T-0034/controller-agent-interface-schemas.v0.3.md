# Controller-Agent Interface Schemas v0.3

Additive repair for `T0034-L0R2-F002`; frozen v0.2 remains immutable.

## Canonical Ownership

This artifact is the sole canonical owner of `Finding/v2.0` and `Verdict/v2.0`. No other artifact may redefine either schema ID. Domain artifacts may define profiles that reference these IDs and add requirements only under a distinct profile ID.

## Finding/v2.0

```yaml
schema_id: Finding/v2.0
additional_properties: false
required: [schema_id, finding_id, severity, title, requirement_refs, evidence_refs, affected_scope, reproduction, impact, owner_role, status]
optional:
  confidence: {type: number, minimum: 0, maximum: 1}
  role_overlay: {type: string}
  recommended_disposition: {type: string}
  extensions: {type: object, default: {}, keys: namespaced}
fields:
  schema_id: {const: Finding/v2.0}
  finding_id: {type: string, min_length: 1}
  severity: {enum: [P0, P1, P2, P3]}
  title: {type: string, min_length: 1}
  requirement_refs: {type: array, items: string, min_items: 1}
  evidence_refs: {type: array, items: EvidenceRef, min_items: 1}
  affected_scope: {type: array, items: string, min_items: 1}
  reproduction: {type: object, required: [kind, steps], additional_properties: false}
  impact: {type: string, min_length: 1}
  owner_role: {type: string, min_length: 1}
  status: {enum: [open, resolved, accepted_risk, blocked]}
```

## Verdict/v2.0

```yaml
schema_id: Verdict/v2.0
additional_properties: false
required: [schema_id, verdict_id, subject_ref, subject_hash, requirements_revision, assurance_profile_id, layer, status, coverage_complete, requirement_coverage, blocking_findings, unresolved_findings, unverified_requirements, evidence_refs, reviewer_independence, authority_ref, authority_effect]
defaults:
  blocking_findings: []
  unresolved_findings: []
  unverified_requirements: []
  extensions: {}
fields:
  schema_id: {const: Verdict/v2.0}
  verdict_id: {type: string, min_length: 1}
  subject_ref: {type: string, min_length: 1}
  subject_hash: {type: string, pattern: '^[A-F0-9]{64}$'}
  requirements_revision: {type: string, min_length: 1}
  assurance_profile_id: {type: string, min_length: 1}
  layer: {enum: [L0, L1, L2, L3]}
  status: {enum: [PASS, REPAIR_REQUIRED, BLOCKED, USER_DECISION_REQUIRED, SCOPE_VIOLATION]}
  coverage_complete: {type: boolean}
  requirement_coverage: {type: array, items: RequirementCoverage}
  blocking_findings: {type: array, items: string}
  unresolved_findings: {type: array, items: string}
  unverified_requirements: {type: array, items: string}
  evidence_refs: {type: array, items: EvidenceRef, min_items: 1}
  reviewer_independence: {type: IndependenceDeclaration}
  authority_ref: {type: string, min_length: 1}
  authority_effect: {const: evidence_only}
  extensions: {type: object, keys: namespaced}
```

## Compatibility And Change Rules

- Unknown top-level fields are rejected. Extension data is allowed only under `extensions` with reverse-DNS or project-qualified keys.
- Adding an optional field is minor-compatible; adding/changing/removing a required field, changing meaning/type/enum, or tightening accepted values is breaking and requires a new major schema ID.
- Producers must emit exactly one declared schema ID. Consumers must reject unsupported major versions and may ignore unsupported namespaced extension keys only inside `extensions`.
- `Finding/v1.0` and `Verdict/v1.0` remain historical and are not mutually compatible across the two v0.2 artifacts. They must be migrated before transport into a v2.0 consumer.
