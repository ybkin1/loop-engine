# T-0083 Guard Health Check — Implementation Report (AC-03, AC-05)

**Role**: quality-engineer
**Date**: 2026-07-31
**Status**: EXECUTED — subsystem built, death tests green, live battery reports honestly
**Status (FIX)**: 2026-07-31 — gate_guard fixture isolation applied; battery now **overall PASS** (see §7)

## 1. What was built

| File | Purpose |
|---|---|
| `loop_core/guard_health.py` | Guard Health subsystem: fixture battery (7 controls / 5 guards), stdin-simulation runner, per-guard verdict (ALIVE/DORMANT/BROKEN/NOT_VERIFIED), summary, JSON report writer |
| `tools/loop_guard_health.py` | CLI: run battery, `--json` output, `--report` writes `.ai/evidence/T-0083/guard-health/report.json`; exit 0 = PASS, exit 2 = FAIL |
| `tests/test_guard_health.py` | 8 pytest tests incl. mutation (guard-death) test; **8/8 PASS** |

Battery design (mirrors gap-analysis §6.1): every guard owns at least one
**negative control** (must block) and, where applicable, a **positive control**
(must pass). Zero blocked negatives = DORMANT; crash (exception / timeout /
exit code outside {0, 2}) = BROKEN.

| Control | Guard | Kind | Expectation |
|---|---|---|---|
| GC-001 | gate_guard | negative | pending-gate write must block |
| GC-002 | content_guard | negative | hardcoded secret in Write must block |
| GC-003 | content_guard | positive | clean content must pass |
| GC-004 | bash_content_guard | negative | `echo ... > file` redirect must block |
| GC-005 | bash_content_guard | positive | read-only command must pass |
| GC-006 | ledger_guard | negative | Edit on ledger file must block |
| GC-007 | path_guard | negative | outside-root write must block |

## 2. Real battery results (2026-07-31, `tools/loop_guard_health.py --report`)

```
Guards checked: 5
  ALIVE:   4
  DORMANT: 1
  BROKEN:  0
Overall: FAIL (exit 2)
```

| Guard | Status | blocked/neg | allowed/pos | Notes |
|---|---|---|---|---|
| bash_content_guard | **ALIVE** | 1/1 | 1/1 | redirect write blocked; read-only passed |
| content_guard | **ALIVE** | 1/1 | 1/1 | secret write blocked; clean write passed |
| ledger_guard | **ALIVE** | 1/1 | 0/0 | Edit on `.ai/ledger/executions.jsonl` blocked |
| path_guard | **ALIVE** | 1/1 | 0/0 | outside-root write blocked |
| gate_guard | **DORMANT** | 0/1 | 0/0 | see §3 |

JSON evidence: `.ai/evidence/T-0083/guard-health/report.json`.

## 3. gate_guard DORMANT — honest analysis (no unsafe fix applied)

gate_guard is reported **DORMANT**, not because it crashed, but because its only
negative control (GC-001: "pending gate blocks write") cannot fire in the current
repository state:

- `.ai/gates.yaml` contains **no pending gates**; `G-T-0083-REQUIREMENTS` is
  `approved` + `execution_status: in_progress` for the current task (T-0083).
- gate_guard's lifecycle logic therefore **correctly allows** the fixture write
  (rc=0) — this is the guard working as designed, not a dead guard.
- GC-001 can only produce a block when a pending gate exists. Satisfying it would
  require either modifying `hooks/scripts/gate_guard.py` (read-only, owned by
  another agent) or writing a fake pending gate into `.ai/gates.yaml` (outside
  T-0083 allowed paths; would corrupt governance state). Per mission rules, no
  unsafe fix was forced; the DORMANT verdict is reported as-is.

**Impact**: overall = FAIL, CLI exit 2. This is the intended posture — a guard
whose negative control never fires keeps the governance chain from claiming green.
Recommended follow-up: a pending-gate environment (e.g. CI fixture repo with a
pending gate) would let GC-001 verify gate_guard end-to-end.

## 4. Mutation test (guard death detection, AC-05)

`test_mutation_removing_backslash_makes_fixture_pass` reproduces the exact
corruption class that killed bash_content_guard in T-0082: it removes a backslash
from `DANGEROUS_PATTERNS[0]` (`\s+` → `s+`) and re-runs the fixture in-process.

- With the mutated (dead) regex: `echo "evil" > tests/tmp_evil.txt` → **rc=0**
  (blocked nothing — guard death reproduced).
- With the live regex: same fixture → **rc=2** (blocked).
- Conclusion: the negative-control fixture **discriminates** guard death; if the
  guard's patterns break, the battery and tests go red instead of staying green.

## 5. Test suite

```
tests/test_guard_health.py: 8 passed
  - battery runs and reports every guard (no crash)
  - mutation test: broken regex => fixture stops blocking (death detected)
  - content_guard blocks secret write (rc=2)
  - bash_content_guard blocks redirect write (rc=2)
  - content_guard allows clean content (rc=0)
  - summary overall = FAIL on BROKEN guard
  - summary overall = FAIL on DORMANT guard
  - summary overall = PASS when all guards ALIVE
```

## 6. Documented deviations from the task skeleton (found during implementation)

1. **Battery `kind` parameter**: the skeleton's `GuardControl(...)` calls omitted
   the `kind` positional (dataclass order is `control_id, guard, description,
   kind, tool_input, expect_block`), which made the tool_input dict land in
   `kind` and every control run as "positive". Fixed by passing `kind` explicitly.
2. **GC-003 content** is `"x = 1\n"` (trailing newline): the skeleton's `"x = 1"`
   trips ruff W292 ("No newline at end of file") and fails the positive control
   for a lint artifact, not a guard defect (verified: with newline, rc=0).
3. **BROKEN vs DORMANT semantics**: the skeleton's status logic made DORMANT
   unreachable — a negative control that runs but does not block always records
   an error, and `errors and blocked == 0` classified the guard as BROKEN. The
   implementation now distinguishes: crash (exception/timeout/rc ∉ {0,2}) =
   BROKEN; ran cleanly but blocked zero negatives = DORMANT (matches the module
   docstring contract).
4. **overall = FAIL on DORMANT**: the skeleton returned PASS unless a guard was
   BROKEN; AC-05 test requirement #6 states BROKEN *or* DORMANT must fail the
   summary. A guard blocking zero negative controls is a dead guard — FAIL is
   the honest verdict (this is why the live run exits 2 with gate_guard DORMANT).

## 7. FIX (2026-07-31): gate_guard fixture isolation — gate_guard now ALIVE

### 7.1 Problem

The original battery ran every control against the **real repository state**.
GC-001 ("pending gate blocks write") could therefore never fire: the real
`.ai/gates.yaml` has no pending gate (G-T-0083-REQUIREMENTS is approved), so
gate_guard correctly allowed the fixture write and was flagged **DORMANT**
(even though the guard logic is alive and correct).

### 7.2 Fix — isolated fixture projects

`loop_core/guard_health.py`:

- `GuardControl` gained an optional `fixture: dict | None = None` field mapping
  relative paths to file contents (e.g. `.ai/state.yaml`, `.ai/gates.yaml`).
- The runner materializes a `tempfile.TemporaryDirectory()` for such controls,
  writes the fixture files (creating parent dirs), and runs the hook script
  with `cwd=fixture_dir` and `hook_input["cwd"]=fixture_dir`, so
  `project_root()` resolves to the fixture — the guard evaluates against the
  fixture's governance state, not the real repo's. Temp dir is cleaned up after
  each control.
- **GC-001** now runs in a fixture with a `pending` gate (G-PENDING, task T-X,
  matching `current_task_id`) — gate_guard must block (rc=2).
- **GC-008** (new positive control) runs in a fixture with an `approved` +
  `execution_status: in_progress` gate (G-APPROVED, task T-X) — gate_guard
  must allow (rc=0). Target `.ai/tasks/X.md` is **not** in the
  decision-recording exemption list (`.ai/gates.yaml`, `.ai/state.yaml`,
  `.ai/task_graph.yaml`, `.ai/project_continuity.yaml`), and gate_guard has no
  other task-scope requirement on the target path, so the same target isolates
  gate_guard's pending/approved lifecycle logic for both controls (verified
  empirically: GC-001 rc=2, GC-008 rc=0).

Also fixed a pre-existing CLI bug in `tools/loop_guard_health.py`: with
`--json`, `summary` was never assigned (the non-JSON branch was skipped), so
the CLI crashed with `UnboundLocalError` after printing valid JSON. `summary`
is now computed once before branching.

### 7.3 Updated battery results (2026-07-31)

```
Guards checked: 5
  ALIVE:   5
  DORMANT: 0
  BROKEN:  0
Overall: PASS (exit 0)
```

| Guard | Status | blocked/neg | allowed/pos | Notes |
|---|---|---|---|---|
| bash_content_guard | **ALIVE** | 1/1 | 1/1 | redirect write blocked; read-only passed |
| content_guard | **ALIVE** | 1/1 | 1/1 | secret write blocked; clean write passed |
| gate_guard | **ALIVE** | 1/1 | 1/1 | GC-001 blocked in pending-gate fixture; GC-008 passed in approved-gate fixture |
| ledger_guard | **ALIVE** | 1/1 | 0/0 | Edit on `.ai/ledger/executions.jsonl` blocked |
| path_guard | **ALIVE** | 1/1 | 0/0 | outside-root write blocked |

### 7.4 Tests & self-audit

- `tests/test_guard_health.py`: **9/9 PASS** (added
  `test_gate_guard_fixture_isolation_pending_blocks_approved_passes`, which
  asserts gate_guard blocked=1 and allowed=1 via the battery runner — the
  fixture materialization path is covered end-to-end).
- `tools/loop_self_audit.py --quick`: **overall PASS, exit 0** (guard_health
  rc=0 and validate_state pass).

JSON evidence: `.ai/evidence/T-0083/guard-health/report.json` (regenerated).
