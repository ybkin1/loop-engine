# T-0085 Final Full Regression Results

| Field | Value |
|-------|-------|
| **Date** | 2026-07-31 |
| **Executor** | test-engineer (zcode-actor-ef751a6fd56b) |
| **Command** | `python -m pytest tests/ -q --tb=short` (full suite) + loop_self_audit + loop_guard_health + validate_state |
| **Python** | CPython 3.12.10 (C:\Python312), pytest 9.0.3 |
| **Platform** | Windows 10 x64 (win32), Git Bash |
| **Baseline ref** | HEAD 5f7b0c8 (v3.12.23, T-0083), working tree contains T-0085 changes |

## 1. Full test suite (tests/)

**Result: 2 failed, 2766 passed, 63 skipped, 16 xfailed — 189.64s (37 warnings)**

```
FAILED tests/test_governance_consistency.py::TestGovernanceConsistency::test_handoff_current_task_matches_state
FAILED tests/test_governance_consistency.py::TestGovernanceConsistency::test_handoff_current_gate_matches_state
= 2 failed, 2766 passed, 63 skipped, 16 xfailed, 37 warnings in 189.64s
```

### 1a. Prior state (from c9-fix-report.md, developer run)

`2740 passed, 63 skipped, 16 xfailed` with **7 failures** in
`tests/test_governance_consistency.py` + `tests/lab/test_project_governor_consistency.py`
(proven pre-existing at the time, caused by invalid YAML in the working-tree
`.ai/task_graph.yaml`, not by T-0085 code).

### 1b. The 7 pre-existing task_graph.yaml failures — GONE (verified)

- The working-tree `.ai/task_graph.yaml` YAML defect is fixed (git diff: +12 lines, valid).
- Baseline stash check: with all T-0085 tracked changes stashed, both governance-consistency
  files pass **76/76** (`tests/test_governance_consistency.py` 12 + `tests/lab/test_project_governor_consistency.py` 64).
- Working tree now shows **zero** task_graph YAML errors; suite grew to 2766 passed
  (test_constraint_phase_advance.py 21 tests added, etc.).

### 1c. The 2 remaining failures — NEW (not among the prior 7), governance handoff drift, not a code defect

Both failures are the same root cause: `.ai/state.yaml` was advanced to
`current_task_id: T-0085` / `current_gate_id: G-T-0085-REQUIREMENTS`, but
`.ai/HANDOFF.md` was never regenerated — it still declares **"T-0083 ACTIVE"** and
references neither `T-0085` nor `G-T-0085-REQUIREMENTS`.

- `test_handoff_current_task_matches_state`: asserts `state["current_task_id"]` (T-0085) appears in HANDOFF.md → AssertionError.
- `test_handoff_current_gate_matches_state`: asserts `state["current_gate_id"]` (G-T-0085-REQUIREMENTS) appears in HANDOFF.md → AssertionError.
- Verified NOT present on baseline (T-0083 state + T-0083 HANDOFF.md → both tests pass on stashed baseline).
- Classification: **NEW failures introduced by the T-0085 task-state transition without the
  corresponding HANDOFF.md update** (workflow/governance documentation drift). They are NOT
  caused by the C5/C9 code changes — all loop_core/enforcement/executor/hard-constraint/
  constraint-phase-advance tests pass, and the phase-advance gate probe suite passes.
- Remediation (out of test-engineer write scope — requires `.ai/HANDOFF.md`): regenerate
  HANDOFF.md for T-0085 (e.g. `close_session.py` / continuity producer) at task handoff.

### 1d. Risk assessment of the 2 failures

| Dimension | Verdict |
|-----------|---------|
| Code regression from T-0085 C5/C9 changes | **None detected** — all affected-module tests pass |
| Pre-existing failures (7 task_graph YAML) | **Fixed** — confirmed gone (0 YAML-related failures) |
| New failures | 2 × HANDOFF.md stale-reference (documentation drift, not code) |
| Skips/xfails | 63 skipped / 16 xfailed — identical to prior run (no new skips) |

## 2. tools/loop_self_audit.py

```
{
  "overall": "PASS",
  "failed": []
}
```

## 3. tools/loop_guard_health.py

```
Guards checked: 5
  ALIVE:  5
  DORMANT: 0
  BROKEN: 0
Overall: PASS
```

## 4. compile gate (S6-delivery compile evidence)

`python .ai/checkers/compile_gate.py <root> --paths loop_core --output .ai/evidence/T-0085/compile-evidence.json`

```
status: pass, exit_code: 0, compiled_files: 42, total_files: 42, failed_count: 0, errors: []
```

→ generated `.ai/evidence/T-0085/compile-evidence.json` (real, deterministic result).
This resolves the `COMPILE_EVIDENCE_MISSING` error reported by validate_state.

## 5. .zcode/tools/validate_state.py — EXIT=2, 4 errors (was 5 before compile gate)

```
[loop-governance] phase: S6-delivery
[loop-governance] current_task_id: T-0085
[error] in_progress requires approval evidence for current task: T-0085
[error] in_progress requires execution evidence for current task: T-0085
[error] ProjectContinuity invalid: Continuity source drift: .ai/gates.yaml
[error] PROJECT_CONTINUITY_SOURCE_DRIFT: Continuity source drift: .ai/gates.yaml
```

### 5a. Error classification

| Error | New vs pre-existing | Root cause | Remediation owner |
|-------|---------------------|------------|-------------------|
| `in_progress requires approval evidence` | NEW (evidence gap) | Gate `G-T-0085-REQUIREMENTS` in `.ai/gates.yaml` has no `approval_evidence` field and no `approval-evidence.json` under `.ai/evidence/T-0085/` (compare T-0083: `approval-evidence.json` present) | governance-controller / task workflow |
| `in_progress requires execution evidence` | NEW (evidence gap) | Same — no `execution_evidence` field and no `execution-evidence.json` (compare T-0083) | governance-controller / task workflow |
| `PROJECT_CONTINUITY_SOURCE_DRIFT: .ai/gates.yaml` | **PRE-EXISTING** — reproduced identically on stashed baseline (HEAD 5f7b0c8) | hash of `.ai/gates.yaml` recorded in `.ai/project_continuity.yaml` already drifted at HEAD; T-0085's +51-line gates.yaml additions perpetuate it | governance-controller (continuity repair) |
| ~~`COMPILE_EVIDENCE_MISSING`~~ | NEW — **RESOLVED in this run** | `.ai/evidence/T-0085/compile-evidence.json` now generated (42/42 compile pass) | — |

Note: the drift error is printed twice (once from `governance_invariant_errors`, once from the
ProjectContinuity block) — one root cause. Also resolved vs baseline: the working-tree
`task_graph.yaml` fix eliminated the baseline error `Historical task must appear exactly once
in task graph: T-0085 (found 0)`.

## 6. Conclusion

- **No code regression from T-0085**: full suite 2766 passed (+26 vs prior 2740), all 7
  pre-existing task_graph.yaml failures fixed, self-audit PASS, guard health PASS
  (5/5 ALIVE), compile gate PASS (42/42).
- **2 NEW pytest failures**: stale HANDOFF.md (references T-0083, state is T-0085) —
  documentation drift from the task-state transition, not code. Fix = regenerate HANDOFF.md.
- **validate_state EXIT=2** remains: 2 NEW governance evidence gaps (approval-evidence.json /
  execution-evidence.json for T-0085 — expected from the workflow, not yet produced) +
  1 PRE-EXISTING continuity drift (gates.yaml hash, also failing at HEAD before T-0085).
- **Gating impact**: the 2 handoff tests and the 2 evidence-gap errors must be closed by the
  governance workflow (HANDOFF.md regeneration + evidence files) before T-0085 can be
  considered fully green. No C5/C9 code-path regression exists.
