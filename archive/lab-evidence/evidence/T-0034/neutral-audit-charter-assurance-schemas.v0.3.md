# Neutral Audit Charter Assurance Schemas v0.3

Additive repair for `T0034-L0R2-F002`; frozen v0.2 remains immutable.

## Canonical References

- Canonical `Finding/v2.0` owner: `.ai/evidence/T-0034/controller-agent-interface-schemas.v0.3.md`.
- Canonical `Verdict/v2.0` owner: `.ai/evidence/T-0034/controller-agent-interface-schemas.v0.3.md`.
- This artifact does not redefine either base schema.

## AuditFindingProfile/v1.0

References `Finding/v2.0` and additionally requires `confidence`, `role_overlay`, and `recommended_disposition`. The canonical `reproduction` object replaces the audit-v0.2 scalar `reproduction` and interface-v0.2 `reproducibility` forms.

## AuditVerdictProfile/v1.0

References `Verdict/v2.0`; all audit-specific fields are already canonical base fields. It requires `assurance_profile_id` to identify an approved audit profile and requires a complete `reviewer_independence` declaration. `authority_effect` remains exactly `evidence_only`.

## Profile Rules

- A profile may make canonical optional fields required, constrain namespaced `extensions`, or narrow an enum only under a new profile major version.
- A profile cannot redefine base field type, meaning, default, or requiredness for other profiles.
- Packets identify both the base `schema_id` and applicable profile ID.
- Unknown top-level fields remain rejected; audit additions use `extensions.audit.t0034` when no canonical field exists.
- Review verdicts remain evidence only and never approve Gates, close tasks, or assert user acceptance.
