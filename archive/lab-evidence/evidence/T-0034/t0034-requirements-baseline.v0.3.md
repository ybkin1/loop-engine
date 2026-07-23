# T-0034 Requirements Baseline v0.3

Additive repair for `T0034-L0R2-F001`. The frozen v0.2 artifact remains immutable.

## Canonical Envelope

- `algorithm_id`: `T0034-HASH-FRAMING/v0.3`
- `payload_byte_count`: `1587`
- `payload_sha256`: `1D3CC20D39AE0971C56E102E1602D967987011FB2D2896E60B32F4CCB993DAFF`
- Hash scope: exact UTF-8 bytes after the LF ending the unique begin-marker line and before the first byte of the unique end-marker line. The LF immediately before the end marker is the required payload terminal LF and is included. No trimming or normalization is permitted.

## Reproduction

```python
raw = path.read_bytes()
assert not raw.startswith(b"\xef\xbb\xbf")
assert b"\r" not in raw
begin = b"<!-- CANONICAL-PAYLOAD-BEGIN -->"
end = b"<!-- CANONICAL-PAYLOAD-END -->"
lines = raw.splitlines(keepends=True)
begin_rows = [i for i, line in enumerate(lines) if line == begin + b"\n"]
end_rows = [i for i, line in enumerate(lines) if line in (end, end + b"\n")]
assert len(begin_rows) == 1 and len(end_rows) == 1 and begin_rows[0] < end_rows[0]
start = sum(map(len, lines[:begin_rows[0] + 1]))
stop = sum(map(len, lines[:end_rows[0]]))
payload = raw[start:stop]
assert payload.endswith(b"\n") and not payload.endswith(b"\n\n")
assert len(payload) == 1587
assert hashlib.sha256(payload).hexdigest().upper() == "1D3CC20D39AE0971C56E102E1602D967987011FB2D2896E60B32F4CCB993DAFF"
```

<!-- CANONICAL-PAYLOAD-BEGIN -->
schema_id: T0034RequirementsBaseline/v0.3
supersedes_for_findings:
  - T0034-L0R2-F001
base_artifact:
  path: .ai/evidence/T-0034/t0034-requirements-baseline.v0.2.md
  sha256: 41931EE234718792F6CE386EBBD1F300FBA386EAF8ACE7F62EC542054FB6F1B7
normative_effect:
  - preserve every v0.2 requirement and acceptance obligation
  - replace only the ambiguous canonical-payload hash framing contract
hash_framing:
  encoding: UTF-8
  bom: forbidden
  line_endings: LF only
  begin_marker: "<!-- CANONICAL-PAYLOAD-BEGIN -->"
  end_marker: "<!-- CANONICAL-PAYLOAD-END -->"
  marker_cardinality: exactly one begin and one end marker
  marker_order: begin before end
  payload_start: first byte after the LF terminating the begin-marker line
  payload_end: first byte of the end-marker line
  marker_lines_included: false
  begin_marker_terminating_lf_included: false
  end_marker_preceding_lf_included: true
  payload_terminal_lf: exactly one and included in byte count and SHA-256
  extraction: locate exact marker lines after UTF-8/BOM/LF preflight; slice bytes from payload_start inclusive to payload_end exclusive; do not trim or normalize
failure_rules:
  bom_present: INVALID_BOM
  crlf_or_cr_present: INVALID_LINE_ENDINGS
  marker_missing: MARKER_CARDINALITY_ERROR
  marker_duplicate: MARKER_CARDINALITY_ERROR
  marker_order_wrong: MARKER_ORDER_ERROR
  payload_missing_terminal_lf: PAYLOAD_TERMINAL_LF_ERROR
  payload_extra_terminal_lf: PAYLOAD_TERMINAL_LF_ERROR
verification:
  golden_vectors: .ai/evidence/T-0034/hash-framing-golden-vectors.v0.3.md
  algorithm_id: T0034-HASH-FRAMING/v0.3
<!-- CANONICAL-PAYLOAD-END -->
