# Finding/Verdict Schema Compatibility Matrix v0.3

| Producer | Consumer | Result | Required action |
|---|---|---|---|
| interface `Finding/v1.0` | `Finding/v2.0` | incompatible until migrated | map `reproducibility` to `reproduction.kind/steps`; add `impact`, `status`; preserve extras under namespaced extensions |
| audit `Finding/v1.0` | `Finding/v2.0` | incompatible until migrated | add `affected_scope`, `owner_role`, `status`; convert `reproduction`; retain confidence/profile fields |
| interface `Verdict/v1.0` | `Verdict/v2.0` | incompatible until migrated | add subject/hash/revision/profile/coverage/independence fields; normalize lists |
| audit `Verdict/v1.0` | `Verdict/v2.0` | incompatible until migrated | add `verdict_id`, `subject_ref`, `layer`, `requirement_coverage`, `authority_ref`; normalize lists |
| `Finding/v2.0` | v2.0 consumer | compatible | reject unknown top-level fields; default only documented optional fields |
| `Verdict/v2.0` | v2.0 consumer | compatible | reject unknown top-level fields; apply empty-list/object defaults |
| v2.x packet with namespaced extensions | v2.0 consumer | compatible if base valid | consumer may ignore unsupported keys only inside `extensions` |
| unsupported major | any consumer | incompatible | reject with `UNSUPPORTED_SCHEMA_MAJOR` |

## Migration Invariants

- Migration is explicit and produces a new packet; it never edits historical evidence.
- Missing required source meaning cannot be invented: return `MIGRATION_INPUT_INCOMPLETE`.
- Field collisions return `MIGRATION_CONFLICT`; unknown top-level fields return `UNKNOWN_FIELD`.
- Round-trip to v1.0 is not guaranteed and must not be claimed.

## Adversarial Vectors

- Two artifacts claim ownership of the same base ID: `DUPLICATE_CANONICAL_OWNER`.
- Profile redefines a base field: `PROFILE_BASE_CONFLICT`.
- Required field absent: `REQUIRED_FIELD_MISSING`.
- Undocumented top-level field: `UNKNOWN_FIELD`.
- Unsupported major version: `UNSUPPORTED_SCHEMA_MAJOR`.
- v1.0 packet sent without migration: `MIGRATION_REQUIRED`.
- Migration invents unavailable business truth: `MIGRATION_INPUT_INCOMPLETE`.
