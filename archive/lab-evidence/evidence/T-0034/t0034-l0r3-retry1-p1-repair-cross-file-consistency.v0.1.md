# T-0034 L0R3 Retry1 P1 Repair Cross-File Consistency v0.1

- `hash-framing-golden-vectors.v0.4.md` preserves the v0.3 canonical payload count and SHA-256 while repairing the `HF-003` adversarial vector into a reproducible `MARKER_CARDINALITY_ERROR`.
- `hash-framing-golden-vectors.v0.4.md` keeps `PAYLOAD_TERMINAL_LF_ERROR` only for the reproducible extra-terminal-LF payload case.
- `controller-agent-interface-schemas.v0.4.md` removes the ambiguity between required verdict lists and default insertion by forbidding pre-validation defaults for required fields.
- `finding-verdict-schema-compatibility-matrix.v0.4.md` matches the schema artifact: complete v2.0 verdict packets must include required lists, missing required lists return `REQUIRED_FIELD_MISSING`, and pre-validation default insertion is a consumer error.
- Migration rules remain evidence-preserving and may not invent missing business truth.
- Repair completion is distinct from independent rereview, artifact PASS, T-0034 closeout, project PASS, and user acceptance.
