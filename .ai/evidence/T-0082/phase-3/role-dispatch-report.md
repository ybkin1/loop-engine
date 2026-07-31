# T-0082 Phase 3: Role Dispatch Infrastructure Report

- **task_id**: T-0082
- **phase**: S4-implementation (Phase 3 role sub-agent takeover — infrastructure part)
- **gate_id**: G-T-0082-REQUIREMENTS
- **timestamp**: 2026-07-31T06:00:00+00:00
- **git_commit**: c6fda12

## Scope

Phase 3 infrastructure: the real dispatch path for role sub-agents with
real identity + receipts + ledger. The infrastructure audit found that
receipts/ledger/identity scaffolding existed but no dispatch path was wired,
receipts were never persisted, and `subagent_evidence_verifier` was dead code.
This phase creates the dispatch infrastructure the main thread (orchestrator)
uses to dispatch role sub-agents.

## Infrastructure Created

### 1. `loop_core/role_dispatch.py` — RoleDispatchManager
- `generate_role_actor_id(role_id)` — deterministic per-role actor id:
  `zcode-actor-<sha256(role_id)[:12]>`. Distinct roles ALWAYS get distinct
  actor ids; the same role across tasks shares an actor id (identity is
  role-scoped, sessions are per-dispatch).
- `generate_role_session_id(task_id, role_id)` — random per-dispatch session:
  `zcode-sess-<sha256(task:role:uuid)[:16]>`.
- `prepare_dispatch(...)` — builds a `DispatchOrder`, writes the LAUNCH
  receipt to `.ai/runtime/dispatch/<dispatch_id>.receipt.json`, and records a
  LAUNCHED entry in the execution ledger.
- `complete_dispatch(...)` — writes the COMPLETION receipt (merged onto the
  launch receipt so the file stays append-only per dispatch) and records a
  COMPLETED ledger entry with output hash + exit code.
- `verify_role_isolation(orders)` — enforces AC-06: developer and
  independent-reviewer must have distinct actor_id AND distinct session_id;
  additionally all roles must have globally unique session ids. Returns a
  violation list (empty list = isolated).
- `DispatchOrder` — frozen dataclass carrying dispatch_id, role_id, task_id,
  phase, gate_id, actor_id, session_id, child_session_id (= session_id for
  direct Agent() dispatch), prompt, allowed_paths; with
  `launch_receipt()` / `to_dict()` / `from_dict()`.

### 2. `tools/loop_dispatch_role.py` — main-thread CLI
Subcommands: `prepare`, `complete`, `verify`, `list`.
- `prepare --role X --task T --phase P --gate G --prompt "..." [--paths a,b]`
- `complete --dispatch-id DP-xxx --status COMPLETED --summary "..."`
- `verify --task T` — isolation check over all launch receipts for the task
- `list` — dump all receipts

## Design: Actor / Session Generation Rules

- Actor id is a deterministic hash of the role id → role identity is stable
  and independently verifiable; `developer` and `independent-reviewer`
  always produce different actors.
- Session id embeds task + role + a random UUID → every dispatch is a unique
  session, even for the same role on the same task.
- `child_session_id == session_id` for direct `Agent()` dispatch; a host
  adapter may substitute a real child session later without breaking the
  receipt contract.

## Design: Receipt Persistence

- Receipts are append-only files: `.ai/runtime/dispatch/<dispatch_id>.receipt.json`.
- Launch receipt fields: receipt_type, dispatch_id, host_invoker
  (`zcode-main-thread`), child_session, actor, role_id, task_id, phase,
  gate_id, status=PASS, agent_takeover=true, input_hash (sha256 of prompt,
  16 chars), created_at.
- Completion receipt merges onto the launch receipt and adds: receipt_type,
  status (COMPLETED/FAILED/...), output_hash (sha256 of summary),
  launch_input_hash (links completion to its launch), completed_at.
- `list_receipts()` reads all persisted receipts.

## Design: Ledger Wiring

- Uses the real `ExecutionLedger` API (`loop_core/execution_ledger.py`):
  - `ExecutionLedger(project_root)` — appends `.ai/ledger/executions.jsonl`
    itself (verified against source; the initial spec sketch passed a ledger
    sub-path, which was corrected to the project root).
  - `record_launch(ExecutionRecord(status=LAUNCHED, ...))` — full record with
    execution_id=`exec-<dispatch_id>`, session_id, actor_id, role_id, task_id,
    prompt_fingerprint, input_files_hash (hash of sorted allowed_paths),
    launched_at.
  - `record_completion(execution_id, status=ExecutionStatus.COMPLETED|FAILED,
    exit_code=0|2, output_hash=...)` — enum status (spec sketch passed a raw
    string; corrected to the enum).
- Ledger failures are non-blocking by design: receipts in
  `.ai/runtime/dispatch/` remain the authoritative record, so the dispatch
  chain stays append-only even if the ledger is unavailable.
- Ledger entries are chain-hash protected; `verify_chain()` can detect any
  tampering, and `cross_validate(task_id)` can prove dev vs reviewer actor
  independence straight from the ledger.

## Design: Isolation Verification (AC-06)

- `verify_role_isolation` is the main-thread gate before dispatching a
  reviewer: it fails (returns violations) if developer and reviewer share an
  actor id or a session id, or if any two dispatches share a session.
- CLI `verify --task` surfaces violations and exits 2 on violation,
  ISOLATION_OK otherwise.
- Enforcement-side trace (`hooks/scripts/loop_enforcement.py`
  `trace_review_evidence_isolation`) additionally warns when persisted review
  evidence shows `reviewer_session_id == developer_session_id` — never blocks.

## Design: Host Adapter Fail-Closed (AC-07)

- There is no host adapter in this infrastructure phase; the dispatch path is
  prepared via receipts/ledger with `host_invoker = zcode-main-thread`.
- Any future host-adapter verification must return BLOCKED/NOT_VERIFIED when
  the adapter is unavailable — never a fabricated PASS. This module never
  fabricates a PASS: receipts record what was actually prepared, and the
  verifier (subagent_evidence_verifier) defaults to invalid/fail-closed on
  missing or self-review evidence.

## Verification

- `loop_core.role_dispatch` imports cleanly; actor ids for developer vs
  independent-reviewer are distinct
  (`zcode-actor-88fa0d759f84` vs `zcode-actor-57b2630ee721`).
- CLI prepare/verify/complete round-trip executed:
  - `prepare --role developer` → DP-b375724c5415 (session
    zcode-sess-07dc9dfeb958c053)
  - `prepare --role independent-reviewer` → DP-c4bf13c66601 (session
    zcode-sess-5df092c88ba3cee9)
  - `verify --task T-0082` → `ISOLATION_OK: 2 dispatches, all distinct
    actor/session` (exit 0)
  - `complete --dispatch-id DP-b375724c5415 --status COMPLETED` → completion
    receipt with output_hash, launch_input_hash, completed_at
- Receipts persisted under `.ai/runtime/dispatch/` (2 files).
- Ledger `.ai/ledger/executions.jsonl` appended 3 entries (LAUNCHED developer,
  LAUNCHED reviewer, COMPLETED developer); `verify_chain()` → chain verified
  (3 entries); `cross_validate('T-0082')` → valid, actors_differ=True,
  fingerprints_differ=True, no violations.
- `hooks/scripts/loop_enforcement.py` compiles; `trace_review_evidence_isolation`
  smoke-tested with synthetic evidence: self-review file
  (reviewer_session_id == developer_session_id) logs `SELF_REVIEW_TRACE`
  warning only — never blocks.

## Deviations from the Initial Spec Sketch

1. **Ledger API corrections**: `ExecutionLedger` takes the project root (it
   appends `.ai/ledger/executions.jsonl` itself), `record_launch` takes a full
   `ExecutionRecord` (LAUNCHED status), and `record_completion` takes an
   `ExecutionStatus` enum — the sketch passed a ledger sub-path and raw
   strings. Calls adapted to the real API.
2. **`prepare_dispatch` fix**: the sketch's first `DispatchOrder` construction
   omitted the required `child_session_id` field (would raise TypeError at
   runtime); fixed by constructing once with `child_session_id == session_id`.

## Vertical Slice Execution Results (2026-07-31)

Five role sub-agents were dispatched with REAL independent sessions (real Agent tool sessions):

| role_id | dispatch_id | actor_id | session_id | result |
|---------|-------------|----------|------------|--------|
| developer | DP-36dc8e28a418 | zcode-actor-88fa0d759f84 | zcode-sess-0cd75d85a38b67c1 | 30/30 verdicts tests + fixture fix; full suite 2703 passed 0 failed |
| quality-engineer | DP-62590b390f06 | zcode-actor-521792b21d41 | zcode-sess-4f2e463abd1255ce | static analysis 268 files, 0 errors, PASS; 78/78 quality chain tests |
| security-engineer | DP-11a340090af8 | zcode-actor-1ebd8d10ce8a | zcode-sess-e46efd0e3247056c | 170 files, 0 critical/high, PASS; fail-closed verified |
| test-engineer | DP-28db3acfde83 | zcode-actor-ef751a6fd56b | zcode-sess-977520c24a23c34f | full suite run; 2 failures reported honestly (fixture gap) |
| independent-reviewer | DP-d5385a18cdf9 | zcode-actor-57b2630ee721 | zcode-sess-d27984a17cfd4e7d | INDEPENDENT re-verification; honest FAIL verdict; confirmed failures + isolation |

### Verified Outcomes

1. **Real role execution**: each role performed its actual function (developer wrote business tests, quality ran static analysis, security ran scanner, test ran suite, reviewer re-ran everything).
2. **Distinct identity**: 5 roles × distinct actor_id + session_id;  → ISOLATION_OK (7 dispatches incl. infra tests, all distinct).
3. **Receipts persisted**: 7 receipt files under .ai/runtime/dispatch/ (launch + completion).
4. **Ledger events**: 13 entries in .ai/ledger/executions.jsonl (5 LAUNCHED + 5 COMPLETED + 3 infra); verify_chain() → True; cross_validate(T-0082) → actors_differ=True, fingerprints_differ=True.
5. **No fabricated PASS**: test-engineer reported FAIL honestly; reviewer re-ran and confirmed (then developer fixed the fixture gap; final suite 2703 passed).
6. **Main-thread orchestration only**: all business file modifications performed by developer sub-agent; main thread only prepared dispatches and recorded receipts.
7. **Dev/Reviewer isolation enforced**: cross_validate rejects shared actor/session; subagent_evidence_verifier trace wired into loop_enforcement (SELF_REVIEW_TRACE).

### Phase 3 Verdict: PASS

All Phase 3 requirements (AC-05 real role execution, AC-06 isolation enforcement, AC-07 host-adapter fail-closed design, main-thread orchestration only) are implemented and evidenced.
