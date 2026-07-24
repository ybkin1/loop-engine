# Machine Check Catalog And Adversarial Golden Vectors v0.2

Catalog ID: `MCAT-2026-07-16-R1`. Satisfies `OUT-08` and contributes to `WS-06`, `WS-07`, and `WS-08`.

This is an executable implementation specification, not checker implementation. Every checker consumes UTF-8 JSON, emits one JSON object, is deterministic, performs no writes, and exits `0` when the checker ran successfully regardless of PASS/FAIL verdict; malformed checker input exits `2`.

## 1. Common Checker Interface

Input:

```json
{"check_id":"MC-SCOPE-001","schema":"check-input/v1","requirements_revision":"T-0034-REQ-2026-07-16-R1","subject":{},"baselines":{},"parameters":{}}
```

Output:

```json
{"check_id":"MC-SCOPE-001","schema":"check-result/v1","verdict":"PASS","errors":[],"evidence":[],"blocked_effects":[],"deterministic_digest":"sha256"}
```

Canonical JSON uses UTF-8, LF, sorted object keys, no insignificant whitespace, integers for integral quantities, and arrays in contract-defined order. Digest is SHA-256 of canonical output excluding `deterministic_digest`.

## 2. Catalog

| Check ID | Input contract | Algorithm/oracle | PASS condition | Failure code |
|---|---|---|---|---|
| `MC-BASE-001` | baseline envelope + payload bytes | Recompute payload SHA-256 between markers and compare revision/source chain. | Hash, revision, source chain complete. | `BASELINE_HASH_MISMATCH` |
| `MC-COVER-001` | WS/OUT registry + coverage rows | Set equality for `WS-01..08` and `OUT-01..09`; require artifact, acceptance, tests, roles. | 17/17 rows complete. | `COVERAGE_INCOMPLETE` |
| `MC-SCOPE-001` | parent/child paths and effects | Canonicalize; reject traversal/escape; set-subset and inherited forbiddance. | Child is a provable subset. | `SCOPE_VIOLATION` |
| `MC-FANIN-001` | expected packet IDs + results/findings | Unique terminal result; propagate blockers; reject stale/conflict/missing. | Complete current fan-in. | `FANIN_BLOCKED` |
| `MC-TX-001` | current state, requested transition, guards | Lookup allowed edge and evaluate guards. | Edge legal and guards true. | `ILLEGAL_TRANSITION` |
| `MC-FENCE-001` | writer/current generation + fence | Compare generation and acknowledged fence. | Writer current and not fenced. | `GENERATION_FENCED` |
| `MC-SCHEMA-001` | schema definition + packet | Required/type/enum/unknown-field validation. | Packet exactly conforms. | `VALIDATION_ERROR` |
| `MC-COMPAT-001` | old/new schema | Classify removed/changed/default/enum/required fields. | Minor-compatible or declared major migration. | `BREAKING_CHANGE` |
| `MC-FRESH-001` | execution/latest revisions + deltas | Exact revision equality or complete impact/no-impact proof. | Current or proven no-impact. | `STALE_REBASE_REQUIRED` |
| `MC-AUDIT-001` | audit packet/result | Validate independence, mandatory roles/checks, finding refs, verdict rule. | Complete and rule-consistent. | `AUDIT_CONTRACT_INVALID` |
| `MC-DRIFT-001` | previous/current/PCC/golden/user goal | Field diff plus dimension rules and ledger trend. | All drift classified, no unauthorized blocker. | `DRIFT_REPAIR_REQUIRED` |
| `MC-PASS-001` | evidence verdict + requested layer | Enforce layer equality and authority. | No implicit layer upgrade. | `PASS_LAYER_VIOLATION` |
| `MC-CONV-001` | iteration history | Count retries/recurrence/no-progress and progress measures. | Within budget with measurable progress. | `NO_PROGRESS_ESCALATION` |
| `MC-PROTECT-001` | protected manifest + disk manifest | Exact path, size, SHA-256 equality. | Every protected item unchanged. | `PROTECTED_BASELINE_CHANGED` |
| `MC-PATH-001` | allowed paths + changed paths | Normalize and exact subset comparison. | Every changed path authorized. | `CHANGED_PATH_ESCAPE` |
| `MC-UTF8-001` | artifact bytes | Strict UTF-8 decode and replacement-character rejection. | All bytes valid. | `INVALID_UTF8` |

### Referenced Subchecks And Adversarial Cases

| Check ID | Deterministic oracle | Expected failure/verdict |
|---|---|---|
| `MC-PCC-001` | Required protected PCC fields are present. | `PCC_REQUIRED_FIELD_MISSING` |
| `MC-PCC-002` | Child protected values equal canonical parent absent approved revision. | `PCC_UNAUTHORIZED_OVERRIDE` |
| `MC-PCC-003` | Golden reference has path, size, full SHA-256, comparison policy. | `GOLDEN_REFERENCE_INCOMPLETE` |
| `MC-PCC-004` | Requested effect is explicitly listed in closed-world authority. | `AUTHORITY_MISSING` |
| `MC-PCC-005` | Source and semantic hashes match declared normalization trace. | `SEMANTIC_HASH_DIVERGENCE` |
| `MC-AUTH-001` | Authority reference, actor, effect and scope hashes are current. | `AUTHORITY_MISSING` |
| `MC-IDEMP-001` | Same idempotency key has same semantic hash. | `CONFLICT` |
| `MC-LEASE-001` | Committer owns unexpired lease in current generation. | `LEASE_INVALID` |
| `MC-AUDIT-002` | Every finding has requirement and disk evidence refs. | `FINDING_UNTRACEABLE` |
| `MC-AUDIT-003` | Severity maps to verdict without narrative override. | `VERDICT_RULE_VIOLATION` |
| `MC-AUDIT-004` | AssuranceProfile mandatory roles/checks are complete. | `ASSURANCE_COVERAGE_INCOMPLETE` |
| `MC-AUDIT-005` | Audit subject hashes equal frozen manifest. | `AUDIT_SUBJECT_STALE` |
| `MC-DRIFT-002` | Current protected invariants/golden hashes equal anchor or authorized delta. | `ANCHOR_DRIFT` |
| `MC-DRIFT-003` | Delivered acceptance traces to user goal and observable success. | `GOAL_DRIFT` |
| `MC-DRIFT-004` | Ledger is append-only and escalation thresholds are applied. | `DRIFT_LEDGER_INVALID` |
| `MC-REANCHOR-001` | Mandatory trigger covers user goal, product, architecture and lifecycle. | `REANCHOR_INCOMPLETE` |
| `MC-FIND-001` | Finding lifecycle transition is legal and evidence-backed. | `FINDING_TRANSITION_INVALID` |
| `MC-RECOVERY-001` | Failure class maps to declared non-destructive safe action. | `RECOVERY_CONTRACT_INVALID` |
| `MC-LOOP-001` | Governance output traces to requirement, evidence or delivery risk. | `GOVERNANCE_SELF_LOOP` |
| `ADV-PCC-001` | Summary omits user authority/protected fields. | `REPAIR_REQUIRED` |
| `ADV-PCC-002` | Latest message is automatic supersession. | `USER_DECISION_REQUIRED` |
| `ADV-TX-001` | Executor PASS conflicts with blocking verifier finding. | `REPAIR_REQUIRED` |
| `ADV-TX-002` | Old generation writes after fence. | evidence retained; commit rejected |
| `ADV-TX-003` | Blocking queue exists at closeout. | closeout rejected |
| `ADV-SCHEMA-001` | Candidate ID appears in committed revision slot. | `VALIDATION_ERROR` |
| `ADV-SCHEMA-002` | Local result claims task PASS. | `PASS_LAYER_VIOLATION` |
| `ADV-SCHEMA-003` | Forbidden effect hidden in unknown field. | `VALIDATION_ERROR` |
| `ADV-AUDIT-001` | Reviewer attempts to approve a gate. | action rejected |
| `ADV-AUDIT-002` | Prior PASS substitutes for current evidence. | `REPAIR_REQUIRED` |
| `ADV-AUDIT-003` | Missing baseline is treated as no defect. | `BASELINE_MISSING` |
| `ADV-DRIFT-001` | Minor style changes accumulate across checkpoints. | worsening anchor drift |
| `ADV-DRIFT-002` | Local checks pass but outcome misses user goal. | goal-drift blocker |
| `ADV-DRIFT-003` | Repair overwrites original ledger entry. | evidence-integrity failure |
| `ADV-DRIFT-004` | Approved revision breaks protected consumer. | compatibility finding |
| `ADV-PASS-001` | Informal approval is inferred as task PASS. | `PASS_LAYER_VIOLATION` |
| `ADV-CONV-001` | Same finding recurs without coverage gain. | freeze and escalate |
| `ADV-RECOVERY-001` | Partial evidence is deleted to clean report. | evidence violation |

## 3. Golden Vectors

### `GV-001` Complete Coverage

```json
{"check_id":"MC-COVER-001","subject":{"workstreams":["WS-01","WS-02","WS-03","WS-04","WS-05","WS-06","WS-07","WS-08"],"outputs":["OUT-01","OUT-02","OUT-03","OUT-04","OUT-05","OUT-06","OUT-07","OUT-08","OUT-09"],"rows_complete":17}}
```

Expected: `PASS`, no errors.

### `GV-002` Blanket Coverage Attack

```json
{"check_id":"MC-COVER-001","subject":{"workstreams":["COV-SCOPE-001"],"outputs":[],"rows_complete":1}}
```

Expected: `FAIL`, `COVERAGE_INCOMPLETE`, missing all `WS-*` and `OUT-*` IDs.

### `GV-003` Scope Subset PASS

```json
{"check_id":"MC-SCOPE-001","subject":{"parent_paths":[".ai/evidence/T-0034/a.md",".ai/HANDOFF.md"],"child_paths":[".ai/evidence/T-0034/a.md"],"parent_effects":["additive_design_write"],"child_effects":["additive_design_write"],"parent_forbidden":["implementation"]}}
```

Expected: `PASS`.

### `GV-004` Path Escape

```json
{"check_id":"MC-SCOPE-001","subject":{"parent_paths":[".ai/evidence/T-0034/"],"child_paths":[".ai/evidence/T-0034/../../gates.yaml"],"parent_effects":["write"],"child_effects":["write"]}}
```

Expected: `FAIL`, `SCOPE_VIOLATION`, blocked effect `write`.

### `GV-005` Fan-In Hidden Blocker

```json
{"check_id":"MC-FANIN-001","subject":{"expected":["E1","V1"],"results":[{"id":"E1","status":"completed","verdict":"PASS"},{"id":"V1","status":"completed","verdict":"REPAIR_REQUIRED","findings":[{"severity":"P1"}]}]}}
```

Expected: `FAIL`, `FANIN_BLOCKED`; candidate verdict `REPAIR_REQUIRED`.

### `GV-006` Late Old Generation

```json
{"check_id":"MC-FENCE-001","subject":{"writer_generation":4,"current_generation":5,"fenced_generations":[4],"consumer_ack":true}}
```

Expected: `FAIL`, `GENERATION_FENCED`; result retained as evidence, canonical write blocked.

### `GV-007` Candidate ID In Committed Slot

```json
{"check_id":"MC-SCHEMA-001","subject":{"schema":"RevisionRef/v1","packet":{"committed_revision":"candidate-17","candidate_revision":null}}}
```

Expected: `FAIL`, `VALIDATION_ERROR` at `committed_revision`.

### `GV-008` Stale Result Without Impact Proof

```json
{"check_id":"MC-FRESH-001","subject":{"execution_bound_revision":"R1","latest_known_revision":"R2","unconsumed_deltas":["D1"],"impact_proof":null}}
```

Expected: `FAIL`, `STALE_REBASE_REQUIRED`.

### `GV-009` Local PASS Upgrade Attack

Input JSON: {"check_id":"MC-PASS-001","subject":{"source_layer":"local_slice","source_verdict":"PASS","requested_layer":"task","authority_ref":null}}

Expected: `FAIL`, `PASS_LAYER_VIOLATION`.

### `GV-010` Missing Baseline

Input JSON: {"check_id":"MC-DRIFT-001","subject":{"anchor_baseline":null,"user_goal":"deliver usable software"}}

Expected: `FAIL`, `BASELINE_MISSING`; never zero drift.

### `GV-011` Goal Drift Despite Local PASS

Input JSON: {"check_id":"MC-DRIFT-001","subject":{"local_checks":"PASS","user_goal":"usable deployed product","current_outcome":"governance wording only","anchor_baseline":"R1"}}

Expected: `FAIL`, `DRIFT_REPAIR_REQUIRED`, dimension `goal`, blocked task PASS.

### `GV-012` No-Progress Loop

Input JSON: {"check_id":"MC-CONV-001","subject":{"iterations":[{"hash":"A","open_p1":2,"coverage":80},{"hash":"B","open_p1":2,"coverage":80}],"max_no_progress":1}}

Expected: `FAIL`, `NO_PROGRESS_ESCALATION`; next action is escalation.

### `GV-013` Protected Hash Change

Input JSON: {"check_id":"MC-PROTECT-001","subject":{"expected":[{"path":"x","size":10,"sha256":"AAAA"}],"actual":[{"path":"x","size":10,"sha256":"BBBB"}]}}

Expected: `FAIL`, `PROTECTED_BASELINE_CHANGED`.

### `GV-014` Oversized Bootstrap

Input JSON: {"check_id":"MC-BASE-001","subject":{"required_r0_bytes":9000,"bootstrap_budget_bytes":8000,"validation_reserve_bytes":1000,"closeout_reserve_bytes":1000}}

Expected: `FAIL`, `BOOTSTRAP_OVERSIZE`; admission refused before truncation.

### `GV-015` User Acceptance Inference

Input JSON: {"check_id":"MC-PASS-001","subject":{"source_layer":"user_acceptance","source_text":"looks good","requested_layer":"task","explicit_acceptance":false}}

Expected: `FAIL`, `PASS_LAYER_VIOLATION`; no technical/task closure inference.

### `GV-016` Valid Repair Stop Boundary

Input JSON: {"check_id":"MC-TX-001","subject":{"current":"VALIDATING","requested":"COMMIT_READY","guards":{"all_artifacts":true,"all_checks":true,"protected_hashes":true,"stop_before_review":true,"review_artifact_created":false}}}

Expected: `PASS`; result is `REPAIR_COMPLETED_AWAITING_REVIEW`, not artifact/task PASS.

## 4. Required Scenario Coverage

| Required scenario | Vectors |
|---|---|
| Micro/cumulative drift | `GV-010`, `GV-011`, `GV-012` |
| Style/golden-reference change | `GV-011` plus `MC-DRIFT-001` anchor policy |
| Authorization traps | `GV-004`, `GV-009`, `GV-015` |
| Controller rotation | `GV-006` |
| In-flight work and stale result | `GV-005`, `GV-008` |
| Oversized bootstrap | `GV-014` |
| False PASS | `GV-005`, `GV-009`, `GV-015`, `GV-016` |
| Missing baseline | `GV-010` |
| Protected evidence mutation | `GV-013` |
| Incomplete blanket coverage | `GV-002` |

## 5. Future Implementation Acceptance

A future checker implementation must run every vector byte-for-byte, produce the expected verdict/error/blocked effect, be deterministic across two runs, reject malformed input with exit `2`, perform no writes, and publish command/output/hash evidence. This artifact authorizes no implementation.
