# Finding/Verdict Schema Compatibility Matrix v0.4

Additive repair for `T0034-L0R3-RETRY1-F002-DEFAULTS`. Frozen v0.3 remains immutable.

| Producer | Consumer | Result | Required action |
|---|---|---|---|
| interface `Finding/v1.0` | `Finding/v2.0` | incompatible until migrated | map `reproducibility` to `reproduction.kind/steps`; add `impact`, `status`; preserve extras under namespaced extensions |
| audit `Finding/v1.0` | `Finding/v2.0` | incompatible until migrated | add `affected_scope`, `owner_role`, `status`; convert `reproduction`; retain confidence/profile fields |
| interface `Verdict/v1.0` | `Verdict/v2.0` | incompatible until migrated | produce a new v2.0 packet with subject/hash/revision/profile/coverage/independence fields and explicit required lists |
| audit `Verdict/v1.0` | `Verdict/v2.0` | incompatible until migrated | add `verdict_id`, `subject_ref`, `layer`, `requirement_coverage`, `authority_ref`, and explicit required lists |
| complete `Finding/v2.0` | v2.0 consumer | compatible | reject unknown top-level fields; default only documented optional fields |
| complete `Verdict/v2.0` with required lists present, including empty arrays | v2.0 consumer | compatible | validate first; read-model defaults may apply only after validation and only to optional fields |
| `Verdict/v2.0` missing `blocking_findings`, `unresolved_findings`, or `unverified_requirements` | v2.0 consumer | invalid | return `REQUIRED_FIELD_MISSING`; do not insert empty arrays before validation |
| v2.x packet with namespaced extensions | v2.0 consumer | compatible if base valid | consumer may ignore unsupported keys only inside `extensions` |
| unsupported major | any consumer | incompatible | reject with `UNSUPPORTED_SCHEMA_MAJOR` |

## Migration Invariants

- Migration is explicit and produces a new packet; it never edits historical evidence.
- Missing required source meaning cannot be invented: return `MIGRATION_INPUT_INCOMPLETE`.
- Empty arrays for required v2.0 verdict lists are valid only when explicitly emitted by a producer or materialized by a migration step with sufficient evidence.
- Field collisions return `MIGRATION_CONFLICT`; unknown top-level fields return `UNKNOWN_FIELD`.
- Round-trip to v1.0 is not guaranteed and must not be claimed.

## Adversarial Vectors

- Two artifacts claim ownership of the same base ID: `DUPLICATE_CANONICAL_OWNER`.
- Profile redefines a base field: `PROFILE_BASE_CONFLICT`.
- Required verdict list absent: `REQUIRED_FIELD_MISSING`.
- Required verdict list present as `[]`: valid for that field.
- Consumer inserts `[]` for a missing required verdict list before validation: `CONSUMER_DEFAULTING_SCOPE_ERROR`.
- Undocumented top-level field: `UNKNOWN_FIELD`.
- Unsupported major version: `UNSUPPORTED_SCHEMA_MAJOR`.
- v1.0 packet sent without migration: `MIGRATION_REQUIRED`.
- Migration invents unavailable business truth: `MIGRATION_INPUT_INCOMPLETE`.
