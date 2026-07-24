# T-0036 Repair RED -> GREEN Test Plan v0.1

Gate: `G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

This is a pre-implementation plan. No test or candidate file is changed by this document.

## Strategy

- One explicit candidate test entrypoint remains: `tests/test_project_governor_consistency.py`.
- Tests use temporary project fixtures, explicit candidate paths, `python -B`, process-local `PYTHONDONTWRITEBYTECODE=1`, and no inherited `PYTHONPATH`.
- Unit tests cover canonicalization and guards; integration tests run each CLI in a subprocess; adversarial tests attempt forgery, replay, concurrency, path escape, reparse escape, stale state, output spoofing, and partial failure.
- RED evidence must show the old candidate fails the new behavioral assertions. GREEN evidence must use the controlled runner, not caller-reported success.

## Scenario Matrix

| ID | Finding | Level | Scenario | RED expectation | GREEN acceptance |
|---|---|---|---|---|---|
| AUTH-001 | F001 | security/integration | Inline action JSON plus unrelated existing evidence | Old CLI accepts | Flags removed or rejected; no write |
| AUTH-002 | F001 | security/unit | Evidence bytes differ from envelope content hash | Old code does not compare | `AUTHORITY_EVIDENCE_MISMATCH`; no write |
| AUTH-003 | F001 | security/unit | Event actor/message/turn/predecessor does not match attestation | No trusted binding exists | `AUTHORITY_IDENTITY_MISMATCH`; no write |
| AUTH-004 | F001 | security/integration | No trusted host adapter in isolated CLI | Old CLI accepts file/inline record | `USER_DECISION_REQUIRED`; no write |
| TURN-001 | F002 | adversarial/e2e | Three subprocesses use three caller request IDs for create -> approve -> execute | Old chain reaches `in_progress` | First authority-bearing transition fails closed; chain cannot advance |
| TURN-002 | F002 | adversarial | Same trusted event/turn reused with different request IDs | Old request-ID check can be bypassed | Replay/same-turn rejected by event lineage |
| TURN-003 | F002 | concurrency | Two processes approve same Gate revision | No CAS guarantee | Exactly one CAS winner when a test adapter is injected; loser is stale and no contradictory state exists |
| TURN-004 | F002 | concurrency | Approval and execution race on stale predecessor | Old sequential file assumptions | Execution rejected until a later trusted event and current revision |
| RUN-001 | F003 | integration | Caller supplies fake exit 0/test count without running tests | Old bind succeeds | No self-report interface exists; no bound manifest |
| RUN-002 | F003 | integration | Controlled test command exits non-zero | Not actually executed by old binder | Actual exit captured; manifest cannot be `bound` |
| RUN-003 | F003 | adversarial | Test prints fake `Ran 999 tests` but test identity/exit is wrong | Caller controls count | Strict identity/count/output checks reject |
| RUN-004 | F003 | failure | Timeout or output limit exceeded | Old binder has no runner | Failure evidence written; no success bind |
| RUN-005 | F003 | stale/boundary | Subject changes between pre-fingerprint and command completion | Old snapshot catches some post drift only | Pre/post mismatch rejects and records actual command result |
| CONT-001 | F004 | contract | Normalized continuity lacks north star | Old HANDOFF still passes | Close fails `RECOVERY_REQUIRED`; no valid HANDOFF |
| CONT-002 | F004 | contract | User authority or evidence-only boundary omitted/changed | Old audit checks headings only | Independent auditor rejects exact protected field |
| CONT-003 | F004 | adversarial | Equivalent prose is present but structured block is absent | Old audit may pass prose/headings | Structured block required; prose cannot substitute |
| GATE-001 | F005 | integration | state current Gate null, approved Gate exists | Old HANDOFF projects approved Gate as current | current Gate remains null; approved execution Gate is separate |
| GATE-002 | F005 | adversarial | Producer output mutates current Gate ID | Same builder hides defect | Independent auditor compares state/gates and rejects |
| LIFE-001 | F006 | integration | No TBD, but review/acceptance/install/activate are unperformed | Old output says `none` | Machine-coded lifecycle uncertainty/non-performance is present |
| LIFE-002 | F006 | negative | Required lifecycle field absent or unknown | Old scan ignores it | Close/audit fail closed |
| LIFE-003 | F006 | positive | Every required lifecycle field is explicit and evidence-bound | Not represented | Empty unverified list allowed only after all consistency checks |
| CP-001 | F007 | negative | Transaction registry missing | Old Stable Checkpoint emitted | `NOT_ESTABLISHED`; no Stable label |
| CP-002 | F007 | negative | Active transaction exists | Old hard-codes empty | Stable generation rejected |
| CP-003 | F007 | negative | In-flight actor exists | Old still emits Stable | Stable generation rejected |
| CP-004 | F007 | negative | Unconsumed delta or partial-write marker exists | Old still emits Stable | Stable generation rejected |
| CP-005 | F007 | negative | Fence/generation/consumer acknowledgment missing or stale | Old does not require | Stable generation rejected |
| CP-006 | F007 | positive | Explicit empty registry, matching fence/revision, acknowledgment, and bounded evidence manifest | Not fully proven | Stable checkpoint emitted with complete protected hashes |
| ARCH-001 | F008 | static/contract | Auditor imports producer expected-state builder | Current design shares builder | Dependency assertion rejects any shared expected-state path |
| ARCH-002 | F008 | adversarial | Producer builder is corrupted/monkey-patched | Same-source audit may agree | Auditor independently rejects output |
| ARCH-003 | F008 | structural | `governor_lib.py` still owns authority, runner, producer, auditor, hashing, and registry | Current file owns all | Responsibility/import inventory matches six modules and narrow common primitives |
| HASH-001 | F009 | negative | Evidence count exceeds 256 or manifest limit | Old unbounded recursion | Rejected before hashing |
| HASH-002 | F009 | negative | One file exceeds 16 MiB or total exceeds 256 MiB/manifest limit | Old whole-file read | Rejected without whole-file allocation |
| HASH-003 | F009 | security | Undeclared file, absolute path, traversal, ADS, duplicate, or case collision | Old recursive scan chooses subjects | Closed manifest rejection |
| HASH-004 | F009 | security | Symlink/junction/reparse on ancestor or target escapes root | Old may follow file | Rejected before content inclusion |
| HASH-005 | F009 | adversarial | File identity/size changes during streaming read | Old has no identity fence | Pre/open/post mismatch rejects |
| HASH-006 | F009 | positive/performance | Bounded manifest with exact files | Old hashes recursive tree with `read_bytes()` | 1 MiB streaming chunks; count/total/hash bound in result |
| BND-001 | Boundary | integration | Candidate path appears in PATH/PYTHONPATH/startup discovery | Historical boundary expects zero | Counts remain zero |
| BND-002 | Boundary | integrity | Global Project Governor source, AGENTS.md, or markers drift | Historical baseline exists | Any drift blocks completion |
| BND-003 | Boundary | hygiene | `__pycache__`, `.pyc`, `.pyo`, symlink, junction, or unapproved file appears in candidate | Historical boundary expects none | Final completion blocked |

## Regression And Non-weakening Rules

- Preserve transaction rollback, concurrent-uncommitted-change, stale HANDOFF, path escape, duplicate-key, and stale final-subject protections.
- Replace tests that currently expect vulnerable inline JSON or three-process lifecycle success with explicit negative tests; retain the old reproduction as RED evidence.
- Do not skip, xfail, delete, rename away, or relax assertions solely to reach GREEN.
- Do not lower T0036-F001 through F007 from P1 or F008/F009 from P2 in repair evidence; only a fresh independent reviewer may reassess severity after full rereview.
- Test count is not an acceptance substitute. Every scenario ID must have an explicit result in the repair report.

## Required Evidence

- RED command, exit code, failing scenario IDs, and relevant output hashes.
- GREEN controlled-runner manifest with actual argv/environment/output/exit/test identity and subject fingerprints.
- Per-scenario PASS/FAIL/BLOCKED table.
- Protected-boundary postcheck and final candidate inventory.
- Fresh independent rereview remains a later separately authorized action.
