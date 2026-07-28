# T-0055 Contract Reconciliation Matrix

## Audit result

The current implementation and tests still contain legacy 11-role assumptions:

- `loop_core/role_capability.py` has no canonical `ROLE_IDS` registry.
- `create_default_profiles()` still contains an inline 11-role list.
- `tests/test_role_capability.py` still asserts 11 roles.
- Certification profiles are persisted as per-role JSON files, while `agents/references/certification-system.md` specifies historical YAML records under `.ai/certifications/{role_id}/` and expiry/revalidation fields.
- `RoleCapabilityProfile` currently stores `certified_at` but does not persist or enforce an expiry date.
- `ROLE_CHALLENGES` currently has one challenge per role, while the profile reference describes multiple competency challenges per role.

## Required reconciliation

1. Canonical registry must contain all 12 discovered role directories.
2. Every canonical role must have exactly one registered challenge set or an explicit multi-challenge registry entry.
3. Role count tests must derive from the canonical registry and compare it with `agents/*/SKILL.md` + `CONTRACT.yaml` directories.
4. Certification persistence must preserve historical records and current projection separately.
5. Admission must fail closed for missing, malformed, or expired certification metadata.
6. Expiry and revalidation semantics must be tested with deterministic clock/fixture inputs.
7. No reconciliation may promote certification state without challenge and independent-review evidence.

## Current implementation status

This matrix records the confirmed drift. Runtime changes are not marked complete until the source diff is observable, tests are updated, and independent evidence is generated.
