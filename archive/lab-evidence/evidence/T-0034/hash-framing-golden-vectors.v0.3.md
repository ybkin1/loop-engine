# T-0034 Hash Framing Golden Vectors v0.3

Normative algorithm: `T0034-HASH-FRAMING/v0.3`. Inputs are complete byte sequences.

| ID | Condition | Expected result | Payload bytes | SHA-256 when extracted |
|---|---|---|---:|---|
| HF-001 | LF file, unique ordered markers, payload `alpha\nbeta\n` | PASS | 11 | `E49C81E2D2F84E259D40E2FB8192F3BCD198B355184845D76D8F58807D0D78EE` |
| HF-002 | one extra terminal LF | `PAYLOAD_TERMINAL_LF_ERROR` | 12 | `5165F3B17AEA57B67F743932E42EF92C7A365DD9B0A511CBEC7FFE904E8DCC08` diagnostic only |
| HF-003 | missing terminal LF | `PAYLOAD_TERMINAL_LF_ERROR` | 10 | `BBFB79E82216BD2DB1AD2C507D44DDF80AEB12F64F9562056AFE93AAD43154D9` diagnostic only |
| HF-004 | any CRLF or bare CR | `INVALID_LINE_ENDINGS` before extraction | n/a | n/a |
| HF-005 | UTF-8 BOM prefix | `INVALID_BOM` before extraction | n/a | n/a |
| HF-006 | begin or end marker missing | `MARKER_CARDINALITY_ERROR` | n/a | n/a |
| HF-007 | either marker repeated | `MARKER_CARDINALITY_ERROR` | n/a | n/a |
| HF-008 | end marker before begin marker | `MARKER_ORDER_ERROR` | n/a | n/a |

Execution order: byte preflight; exact full-line marker cardinality; marker order; exact untrimmed slice; exactly-one-terminal-LF check; byte count and SHA-256. Marker text quoted inside payload or prose is not a marker line. The baseline must reproduce `1587` bytes and `1D3CC20D39AE0971C56E102E1602D967987011FB2D2896E60B32F4CCB993DAFF`.
