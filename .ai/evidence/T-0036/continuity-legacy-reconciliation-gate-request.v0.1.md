# T-0036 Pre-Rereview Continuity And Legacy Reconciliation Gate Request v0.1

Gate ID: `G-T-0036-PRE-REREVIEW-CONTINUITY-LEGACY-RECONCILIATION-V0-1`

Status: `pending / user_decision_required / execution_not_started`

## Decision Requested

Approve or reject a bounded governance reconciliation before any T-0036 fresh independent rereview Gate is prepared. Creation is not approval. Approval is not execution. The recommended branch is: administratively complete T-0035, explicitly supersede the old T-0035..T-0039 numeric mapping, and preserve the unresolved Project Governor remediation/install/activate/reverify program as unassigned future work for later rescheduling.

- Approve: `批准 G-T-0036-PRE-REREVIEW-CONTINUITY-LEGACY-RECONCILIATION-V0-1`
- Reject: `拒绝 G-T-0036-PRE-REREVIEW-CONTINUITY-LEGACY-RECONCILIATION-V0-1`
- After approval only, execute: `执行 G-T-0036-PRE-REREVIEW-CONTINUITY-LEGACY-RECONCILIATION-V0-1`

Approval of this exact Gate selects the recommended branch above. Selecting another option requires a revised pending Gate; it must not be improvised during execution.

## Current Problems, Root Causes, And Severity

| severity | finding | root cause / evidence |
| --- | --- | --- |
| P1 | HANDOFF presents the old `REPAIR_REQUIRED` review and says repair is not executed. | Repair and 65-subject freeze completed, but HANDOFF lines 17-22 were not reconciled. |
| P1 | HANDOFF allows another F-001..F-006 repair and reports six full-suite failures. | Lines 92 and 115 predate completed repair evidence: focused `13 passed`, full suite `41 passed, 5 subtests passed`, candidate suite `28 passed`. |
| P1 | `audit_handoff.py` fails `Semantic Classification mismatch: 当前问题与状态`. | With `current_gate_id=null`, the schema requires `gate_status=none` and no `approved_not_started_gate_ids` clause; HANDOFF line 62 says `repair_completed` and adds that clause. |
| P1 | An approved historical T-0035..T-0039 Project Governor route was silently collided with new Loop task IDs. | T-0032 and the T-0034 downstream plan preserve the old mapping; no record explicitly supersedes it, while task graph now reuses T-0035..T-0038. |
| P1 | Candidate consistency tests do not test the isolated candidate. | The candidate test hard-codes global `SCRIPTS` and `TEMPLATES`; `13 passed` and repository `41 passed` prove current global behavior only. |
| P2 | T-0035 remains `active` despite content-level Acceptance evidence. | Task and graph agree with each other but were never administratively closed; `commands.md` is empty, so fresh closeout evidence is required. |
| P2 | `PROGRESS.md`, state notes, task graph, and T-0036 notes contain stale projections. | Later tasks/repairs were added without reconciling long-lived memory. |
| P2 | The 65-subject freeze manifest has unreadable prose. | Lines 1, 3, and 5 contain 82 literal ASCII `0x3F` bytes; the 65 path/size/SHA-256 triples themselves verify `65/65`. |
| P2 | Candidate/global drift is not registered as an open verification gap. | `close_session.py` and `audit_handoff.py` hashes differ; `governor_lib.py` and `validate_state.py` match. |

## Read-Only Audit Facts

- `validate_state.py`: PASS before registration.
- `audit_handoff.py`: FAIL before registration only for `Semantic Classification mismatch: 当前问题与状态`.
- Startup pending gates: none.
- Freeze verification: 65 records parsed; 65/65 path, size, and SHA-256 match; mismatch 0.
- Candidate/global: `governor_lib.py` and `validate_state.py` match; `close_session.py` and `audit_handoff.py` differ.
- Subagent conclusions are evidence only and do not approve this Gate.

## T-0035 Decision Options

1. **Recommended: administrative `completed`.** Acceptance is covered by the v0.2 design and validation evidence. Execution must add reproducible closeout evidence because the old command log is empty. This means task-scope completion only, not product PASS, user acceptance, Runtime implementation, installation, activation, or Host Integration.
2. **`superseded`.** Not recommended: no replacement task or document supersedes the completed v0.2 design outcome.
3. **Keep `active`.** Use only if the user identifies a specific unmet Acceptance item and blocker; current evidence does not identify one.

## Old Roadmap Decision Options

1. **Recommended: explicitly supersede and rebaseline the numeric mapping.** Preserve the historical file unchanged; record that its T-0035..T-0039 IDs no longer identify the planned Project Governor stages. Preserve isolated candidate repair/verification, installation, activation, and reverification as unassigned future work, to be rescheduled under new IDs by a later Gate.
2. **Retire the old program.** Requires explicit acceptance of the unresolved T-0031 risks and a named replacement; not recommended on current evidence.
3. **Pause without rescheduling.** Record `deferred/suspended` and a revisit condition; safer than silent collision but less clear than rebaseline.

## Exact Future Execution Allowlist

- `.ai/HANDOFF.md`
- `.ai/state.yaml`
- `.ai/task_graph.yaml`
- `.ai/tasks/T-0035.md`
- `.ai/tasks/T-0036.md`
- `.ai/DECISIONS.md`
- `.ai/KNOWN_ISSUES.md`
- `.ai/PROGRESS.md`
- `.ai/gates.yaml`
- `.ai/evidence/T-0036/material-library-repair-freeze-manifest.v0.1.md`
- `.ai/evidence/T-0036/continuity-legacy-reconciliation-execution-commands.v0.1.md`
- `.ai/evidence/T-0036/continuity-legacy-reconciliation-validation.v0.1.md`
- `.ai/evidence/T-0036/continuity-legacy-reconciliation-changed-path-manifest.v0.1.md`
- `.ai/evidence/T-0036/t0035-administrative-closeout-validation.v0.1.md`

The changed set must be a strict subset of this list. Preimages and absent markers are in `continuity-legacy-reconciliation-changed-path-baseline.v0.1.md`.

## Explicit Forbidden Scope

- Every path not listed in the Exact Future Execution Allowlist is forbidden. The entries below call out especially sensitive members of that complement; they do not widen the allowlist.
- No modification of any of the 65 frozen subjects except the three prose-only lines of the freeze manifest itself; every subject path/size/SHA-256 triple is immutable.
- No modification of old independent-review, repair, or validation evidence.
- No modification of `candidates/T-0030-project-governor-repair/**`, `C:/Users/Administrator/.codex/skills/project-governor/**`, repository `AGENTS.md`, `codex_loop/**`, `materials/**`, `docs/**`, or `tests/**`.
- No T-0036 independent rereview, candidate acceptance, version freeze, T-0037 review, installation, activation, Host Integration, skill/MCP/plugin/hook/automation/protocol enablement, or real-project entry.
- No deployment, rollback execution, database, permission, secret, payment, production-data, or migration action.

## Exact Candidate Diff

The stable-content unified diff is frozen in `continuity-legacy-reconciliation-planned-unified-diff.v0.1.patch`. It selects the recommended T-0035 and roadmap branches. Runtime-produced timestamps, command output, fingerprints, and Gate lifecycle evidence are additive facts and may not alter the stable-content choices. Any required stable-content deviation stops execution and requires a revised Gate.

## Verification Plan

1. Before execution, re-hash every current allowlist path against the baseline; stop on drift unless the drift is solely the separately recorded Gate approval transition.
2. Verify the freeze manifest before editing: 65/65 exists, size matches, SHA-256 matches.
3. Apply only the frozen stable-content diff and additive evidence writes.
4. Verify the freeze manifest after editing: all 65 path/size/SHA-256 triples are byte-identical; all 65 subjects still match disk.
5. Parse all modified YAML; require `validate_state.py` PASS, `audit_handoff.py` PASS, and `git diff --check` PASS after Gate execution is recorded complete with no pending Gate.
6. Prove T-0035 task and task graph both equal `completed`; map each Acceptance item to evidence in the new closeout record.
7. Prove the old roadmap decision is explicit and traceable, while the historical downstream plan file remains byte-identical.
8. Prove the candidate-path gap is registered but candidate/global files remain byte-identical to the pre-execution state.
9. Prove changed paths are a strict subset of the allowlist and all unrelated pre-existing user changes remain untouched.

## Risks

- Administrative completion could be misread as product acceptance; every projection must retain the explicit non-acceptance boundary.
- Roadmap supersession could be misread as remediation completion; unresolved candidate verification/install/activate/reverify work must remain open and unassigned.
- Prose repair could accidentally alter frozen triples; byte-level triple comparison is mandatory before and after.
- Dirty-worktree overlap could overwrite user work; preimage checks must stop on unexplained drift.
- Candidate/global tests can produce false confidence; no isolated-candidate PASS may be claimed.

## Rollback And Failure Recovery

- Preserve all preimages, hashes, and the user's unrelated dirty worktree.
- On drift, parse failure, triple change, scope breach, or validation failure, stop and record truthful `BLOCKED` or `reconciliation_incomplete`; do not claim completion.
- Do not auto-delete additive evidence or reverse unrelated changes. A destructive rollback requires a separate explicit Gate.
- A non-destructive correction may only use the same allowlist and frozen stable-content choices; otherwise prepare a revised pending Gate.

## Fresh Independent Rereview Entry Conditions

- This Gate is explicitly approved and later separately executed.
- Governance reconciliation validation is complete; no pending Gate remains.
- `validate_state.py`, `audit_handoff.py`, YAML parse, and `git diff --check` pass.
- T-0035 administrative state and task graph agree; old roadmap disposition is explicit.
- Freeze prose is readable and all 65 triples/subjects remain unchanged.
- Candidate-path verification gap remains open and is not falsely closed by global test passes.
- A new, separate fresh independent rereview Gate is prepared, approved, and later exactly executed; this Gate cannot create or run it.

Current conclusion: `pending / user_decision_required / no_repair_executed`.
