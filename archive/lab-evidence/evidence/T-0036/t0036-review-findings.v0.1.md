# T-0036 Independent Review Findings v0.1

Verdict: `REPAIR_REQUIRED`.

## P0

None.

## P1

### T0036-F001 — Inline authority records are not bound to cited evidence

- Location: `scripts/governance_action.py:64`, `:66`, `:83`; `scripts/governor_lib.py:578`, `:625`.
- Evidence: inline action/command JSON is separate from `--action-evidence`/`--command-evidence-ref`. `load_inline_json_record()` verifies only that the cited path exists, then parses independently supplied JSON; no content/hash/request/user-text/action-ID binding exists.
- Reproduction: cite any existing `.ai/evidence/<task>/` file while providing separately constructed approval/execution JSON; the candidate accepts it.
- Impact: approval, execution authority, and validation evidence may cite files that do not contain the claimed fact, breaking authority containment and provenance.
- Minimum repair: lifecycle actions must load immutable records from evidence; if inline remains, persist and verify canonical JSON hash, request ID, user text, and action ID in the cited evidence.

### T0036-F002 — Same-turn prevention only rejects multiple CLI subcommands

- Location: `scripts/governance_action.py:24`; `scripts/governor_lib.py:658`; `tests/test_project_governor_consistency.py:148`, `:162`, `:178`, `:389`.
- Evidence: enforcement relies on mutually exclusive argparse subcommands and caller-selected unused request IDs. The same-process test only appends a second subcommand.
- Reproduction: one test call invokes three subprocesses with three request IDs and completes create -> approve -> execute successfully.
- Impact: one user turn can still traverse the full chain through multiple processes; the later-distinct-user-request invariant is not enforced.
- Minimum repair: bind transitions to an external, non-forgeable user turn/message identity and predecessor; require a distinct, later user-evidence record.

### T0036-F003 — Final-validation manifest accepts self-reported command success

- Location: `scripts/governor_lib.py:1296`, `:1299`, `:1305`, `:1330`; `tests/test_project_governor_consistency.py:619`.
- Evidence: binder trusts caller JSON for exit code, test count, argv, and timestamps; it does not execute argv or validate output/test identity.
- Reproduction: construct `exit_code: 0` and positive `test_count` without executing the declared test; bind succeeds.
- Impact: failed or unexecuted tests can produce a bound completion manifest.
- Minimum repair: use a controlled runner that executes argv and atomically binds environment, exit, output hash, test count, and fingerprints, or verify a signed immutable runner record.

### T0036-F004 — Generated HANDOFF drops main-controller orientation

- Location: `scripts/close_session.py:75`; `scripts/audit_handoff.py:21`.
- Evidence: generated template and required headings omit main-controller orientation, north star, user authority, and evidence-only boundary.
- Reproduction: temporary fixture close and audit both exit `0` while orientation is absent.
- Impact: fresh successors may lose product goal, controller role, and user decision authority, violating PCC protected semantics.
- Minimum repair: generate a structured orientation from canonical PCC/project records and audit its canonical IDs, hashes, and required semantics.

### T0036-F005 — Structured current Gate contradicts canonical state

- Location: `scripts/governor_lib.py:253`, `:268`, `:359`, `:1133`.
- Evidence: approval clears `state.current_gate_id`; `current_task_gate()` nevertheless selects the most recent approved Gate and projects it as structured `current_gate_id`.
- Reproduction: fixture state Gate is null while structured HANDOFF shows the approved Gate; close/audit pass.
- Impact: successors cannot determine the authoritative Gate projection; same-source generation/audit hides the contradiction.
- Minimum repair: define one canonical meaning. Either retain the execution Gate in state or make structured `current_gate_id` equal state and add a separate `approved_execution_gate_id`; audit both independently.

### T0036-F006 — Unverified lifecycle facts collapse to `none`

- Location: `scripts/close_session.py:48`, `:58`, `:107`; `scripts/audit_handoff.py:27`.
- Evidence: `Unverified` is derived only from literal `TBD` in five documents, not review/acceptance/install/activate/runtime lifecycle facts.
- Reproduction: fixture outputs `Unverified: - none` while those lifecycle effects are unperformed; close/audit pass.
- Impact: fresh sessions can form false completion judgments.
- Minimum repair: derive unverified items from task/Gate flags, verdict, acceptance, install/activate markers, and required evidence; reject lifecycle-inconsistent `none`.

### T0036-F007 — Stable Checkpoint can be emitted without proving stability

- Location: `scripts/governor_lib.py:391`, `:413`, `:414`, `:417`; `scripts/close_session.py:72`, `:132`.
- Evidence: only a transaction marker is checked; `active_transactions` is hard-coded empty, non-empty in-flight actors/deltas do not block generation, and the continuity hash covers only four summary fields.
- Reproduction: add `in_flight_actor_ids` or `unconsumed_deltas` in a fixture; code still emits a Stable Checkpoint.
- Impact: partial/in-flight state may be treated as a safe recovery point.
- Minimum repair: load a canonical transaction registry; reject normal stable checkpoints when transactions, in-flight actors, partial writes, or unconsumed deltas exist; bind complete protected semantics.

## P2

### T0036-F008 — governor_lib.py concentrates unrelated trust boundaries

- Location: `scripts/governor_lib.py:167`, `:237`, `:262`, `:519`, `:692`, `:1020`, `:1284`.
- Evidence: 1,382 lines combine transaction engine, evidence hashing, HANDOFF, path security, YAML parser, Gate lifecycle, and final binding; producer and auditor share the same expected-state builder.
- Impact: correlated bugs contaminate generation and audit, increase review cost, and hide defects through same-source comparison.
- Minimum repair: split schema/serialization, transaction, lifecycle, HANDOFF producer, independent audit canonicalizer, and validation runner.

### T0036-F009 — Evidence hashing is unbounded and follows arbitrary evidence files

- Location: `scripts/governor_lib.py:237`.
- Evidence: every checkpoint/audit recursively `rglob("*")` and `read_bytes()` for the entire evidence tree without file-count, per-file, total-byte, or reparse limits.
- Impact: large/abnormal evidence trees can cause high memory or latency; reparse files can incorporate project-external bytes.
- Minimum repair: hash an approved evidence manifest with streaming, bounded counts/bytes, and explicit symlink/junction/reparse rejection.

## P3

None.

## Boundary

No finding was repaired. Findings are independent review evidence only and do not authorize repair, installation, activation, runtime enablement, downstream tasks/Gates, or user acceptance.
