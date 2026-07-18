# Controller-Agent Interface Schemas v0.4

Additive repair for `T0034-L0R3-RETRY1-F002-DEFAULTS`. Frozen v0.3 remains immutable.

## Canonical Ownership

This artifact is the current additive owner for `Finding/v2.0` and `Verdict/v2.0` after the v0.4 repair. It supersedes only the v0.3 required/default ambiguity for `Verdict/v2.0`; all non-conflicting v0.3 ownership, extension, migration, and unknown-field rules remain in force.

## Finding/v2.0

`Finding/v2.0` is unchanged by this repair. Producers must emit all required fields listed in v0.3. Consumers reject unknown top-level fields and may ignore unsupported namespaced keys only inside `extensions`.

## Verdict/v2.0

```yaml
schema_id: Verdict/v2.0
additional_properties: false
required: [schema_id, verdict_id, subject_ref, subject_hash, requirements_revision, assurance_profile_id, layer, status, coverage_complete, requirement_coverage, blocking_findings, unresolved_findings, unverified_requirements, evidence_refs, reviewer_independence, authority_ref, authority_effect]
optional:
  extensions: {type: object, default: {}, keys: namespaced}
producer_required:
  blocking_findings: emit [] when there are no blocking findings
  unresolved_findings: emit [] when there are no unresolved findings
  unverified_requirements: emit [] when there are no unverified requirements
consumer_defaulting:
  before_wire_validation: forbidden for required fields
  after_wire_validation: allowed only for optional read-model conveniences and optional extensions
missing_field_behavior:
  required_field_absent_in_canonical_v2_packet: REQUIRED_FIELD_MISSING
  optional_extensions_absent: default to {}
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

## Compatibility Rule

Canonical `Verdict/v2.0` validation happens before any consumer read-model defaulting. A consumer must not turn a canonical v2.0 packet with a missing required list into a valid packet by inserting `[]`. Producers are responsible for emitting explicit empty arrays when the values are empty.

Migration tools may materialize explicit empty arrays only while producing a new v2.0 packet and only when the migration input supplies enough evidence to justify emptiness. If that evidence is unavailable, migration returns `MIGRATION_INPUT_INCOMPLETE` rather than inventing business truth.
