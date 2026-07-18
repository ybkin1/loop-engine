# T-0034 L0R2 P1 Repair Cross-File Consistency v0.1

- Requirements baseline and hash vectors use the same algorithm ID, payload count, SHA-256, terminal-LF rule, and failure codes.
- Controller schema artifact uniquely defines `Finding/v2.0` and `Verdict/v2.0`.
- Neutral audit artifact references those schemas and defines distinct profile IDs without redefining the base.
- Compatibility matrix uses the same v2.0 IDs, migration field mappings, unknown-field policy, and major-version rejection rule.
- Frozen v0.2 artifacts remain historical evidence and are never claimed compatible without migration.
- Repair completion is distinct from independent rereview, artifact PASS, T-0034 closeout, and user acceptance.
