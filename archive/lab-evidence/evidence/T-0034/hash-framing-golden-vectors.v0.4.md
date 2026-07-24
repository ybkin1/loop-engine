# T-0034 Hash Framing Golden Vectors v0.4

Additive repair for `T0034-L0R3-RETRY1-F001-HF003`. Frozen v0.3 remains immutable.

## Normative Clarification

Algorithm `T0034-HASH-FRAMING/v0.3` recognizes begin and end markers only as exact full-line markers. The payload slice starts after the LF that terminates the begin-marker line and stops immediately before the first byte of the end-marker line. Therefore the LF immediately before a valid end-marker line is part of the payload.

Consequence: a non-empty payload inside a valid full-line marker frame always has at least the LF immediately before the end marker. A byte sequence that places the end marker directly after `alpha\nbeta` does not contain a full-line end marker and must return `MARKER_CARDINALITY_ERROR`; it must not be reported as `PAYLOAD_TERMINAL_LF_ERROR`.

`PAYLOAD_TERMINAL_LF_ERROR` remains valid for the reproducible case where an extracted payload ends in more than one LF. A "missing terminal LF" payload is not a valid external golden vector under this full-line marker framing rule.

## Repaired Vectors

| ID | Condition | Expected result | Payload bytes | SHA-256 when extracted |
|---|---|---|---:|---|
| HF-001 | LF file, unique ordered full-line markers, payload `alpha\nbeta\n` | PASS | 11 | `E49C81E2D2F84E259D40E2FB8192F3BCD198B355184845D76D8F58807D0D78EE` |
| HF-002 | unique ordered full-line markers, payload `alpha\nbeta\n\n` | `PAYLOAD_TERMINAL_LF_ERROR` | 12 diagnostic | `5165F3B17AEA57B67F743932E42EF92C7A365DD9B0A511CBEC7FFE904E8DCC08` diagnostic |
| HF-003 | malformed frame with end marker immediately after `alpha\nbeta` and no LF before the end marker | `MARKER_CARDINALITY_ERROR` | n/a | n/a |
| HF-004 | any CRLF or bare CR | `INVALID_LINE_ENDINGS` before marker scan | n/a | n/a |
| HF-005 | UTF-8 BOM prefix | `INVALID_BOM` before marker scan | n/a | n/a |
| HF-006 | begin or end full-line marker missing | `MARKER_CARDINALITY_ERROR` | n/a | n/a |
| HF-007 | either full-line marker repeated | `MARKER_CARDINALITY_ERROR` | n/a | n/a |
| HF-008 | end full-line marker before begin full-line marker | `MARKER_ORDER_ERROR` | n/a | n/a |

## Reproduction Contract

Validation order is byte preflight, exact full-line marker cardinality, marker order, exact untrimmed payload slice, then exactly-one-terminal-LF check. Marker-like text inside payload or prose is not a marker unless it occupies the complete line.

The canonical baseline payload still reproduces 1587 bytes and SHA-256 `1D3CC20D39AE0971C56E102E1602D967987011FB2D2896E60B32F4CCB993DAFF`. This v0.4 vector repair changes only the adversarial `HF-003` expected result so the vector is independently reproducible.
