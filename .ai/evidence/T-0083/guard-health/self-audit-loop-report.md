# T-0083 Self-Audit Loop Implementation Report (AC-04 + AC-08)

- **Date**: 2026-07-31
- **Role**: test-engineer
- **Task**: T-0083 (Loop 元治理层 — 自举审计回路 + 端到端切片常态化)
- **Git commit (audit time)**: d01b53e

## 1. Scripts built

### 1.1 `tools/loop_self_audit.py` (AC-04 — dogfooding audit loop)

Scripts the baseline audit battery that T-0082 Phase 0 performed manually:

| Check | Command | Notes |
|-------|---------|-------|
| `validate_state` | `.zcode/tools/validate_state.py <root>` | rc 0/2 = OK (rc 2 = expected idle NO_ACTIVE_TASK) |
| `guard_health` | `tools/loop_guard_health.py --json` | rc 0 = PASS, rc 2 = guard broken/missing |
| `compile` (full only) | `compileall -q loop_core/` | |
| `pytest_core` (full only) | pytest `test_loop_core.py` + `test_verdicts.py` + `test_guard_health.py` | core-only to bound runtime |
| `security_scan` (full only) | `loop_core.security_scanner.scan_security` | prints `critical/high/verdict` |
| `static_analysis` (full only) | `loop_core.static_analyzer.analyze_project` | prints `errors/warnings/verdict` |

Output: `.ai/evidence/T-0083/guard-health/self-audit.json` (full JSON, per-check rc/stdout/stderr, `failed` list, `overall` PASS/FAIL). Exit code 0 = PASS, 2 = FAIL.

Usage: `python tools/loop_self_audit.py` (full) / `python tools/loop_self_audit.py --quick` (validate_state + guard health only).

### 1.2 `tools/loop_vertical_slice.py` (AC-08 — S1→S6 slice validation)

Validates (does NOT execute — phases require human gates) the S1→S6 vertical slice evidence chain for a task:

| Check | Requirement |
|-------|-------------|
| `S1_requirements_gate` | user-approved gate for the task in `.ai/gates.yaml` |
| `S2_task_registered` | `.ai/tasks/<TASK>.md` exists |
| `S4_implementation_evidence` | ≥1 phase evidence dir under `.ai/evidence/<TASK>/` |
| `S5_quality_evidence` | ≥3 files across `phase-3`/`phase-5` dirs |
| `S6_acceptance` | `.ai/evidence/<TASK>/phase-6/acceptance-report.md` exists |

Usage: `python tools/loop_vertical_slice.py --task T-0083`. Exit 0 = PASS, 2 = FAIL.

## 2. Real run results

### 2.1 Self-audit (quick): `python tools/loop_self_audit.py --quick`

```
{
  "overall": "FAIL",
  "failed": ["guard_health", "validate_state"]
}
```
Exit code 2. Full JSON at `.ai/evidence/T-0083/guard-health/self-audit.json` (git d01b53e, 2026-07-31T11:03:49Z).

**Honest findings (NOT fixed — outside this agent's ownership):**

1. **`guard_health` rc=2 — tool missing.** `tools/loop_guard_health.py` does not exist yet. Python exits rc=2 when the script file cannot be opened, and the audit's guard-health logic (rc 2 = guard broken) correctly flags it. The Guard Health Check implementation is owned by the guard-health agent; this audit loop is designed to report it until it lands. Do NOT interpret this as a guard regression — it is a pending deliverable.

2. **`validate_state` rc=1 — `.ai/task_graph.yaml` is currently invalid YAML.** `governor_lib.load_yaml` fails on `.ai/task_graph.yaml` line 927 (`expected <block end>, but found '<block sequence start>'`). Root cause: the T-0083 entry (`id: T-0083`) was appended after the top-level `edges:` key at `tasks:` list indentation, producing a sequence item nested under `edges:`. The file has uncommitted changes (+12 lines, `git status` shows `.ai/task_graph.yaml` modified) — consistent with a concurrent governance-controller edit in progress (T-0082 evidence shows ongoing state/gate fixes). `.ai/task_graph.yaml` is outside this agent's allowed paths (tools/, tests/, .ai/evidence/T-0083/ only), so it was NOT modified. Governance-controller owns the fix.

### 2.2 Vertical slice validation

**T-0082 (completed slice) — expected PASS:**
```
{
  "S1_requirements_gate": {"ok": true, "detail": "1 user-approved gates"},
  "S2_task_registered":   {"ok": true, "detail": "task file exists"},
  "S4_implementation_evidence": {"ok": true, "detail": "7 phase dirs: ['baseline', 'phase-1'..'phase-6']"},
  "S5_quality_evidence":  {"ok": true, "detail": "8 files in phase-3/phase-5 dirs"},
  "S6_acceptance":        {"ok": true, "detail": "acceptance-report.md exists"}
}
overall: PASS, exit 0
```

**T-0083 (in progress) — expected partial FAIL:**
```
{
  "S1_requirements_gate": {"ok": true,  "detail": "1 user-approved gates"},
  "S2_task_registered":   {"ok": true,  "detail": "task file exists"},
  "S4_implementation_evidence": {"ok": true, "detail": "5 phase dirs: ['acceptance', 'baseline', 'gap-analysis', 'guard-health', 'research']"},
  "S5_quality_evidence":  {"ok": false, "detail": "0 files in phase-3/phase-5 dirs"},
  "S6_acceptance":        {"ok": false, "detail": "MISSING"}
}
overall: FAIL, exit 2
```
Correct behavior: S5/S6 are downstream phases not yet reached. S1 (user-approved requirements gate G-T-0083-REQUIREMENTS, `approval_actor: user`) and S2 already hold.

## 3. Notes / cross-references

- Guard health check implementation: owned by guard-health agent (T-0083 scope item). This report's `guard_health` FAIL is the audit loop working as designed — it detects the guard tool is not yet installed. Re-run `tools/loop_self_audit.py --quick` after the guard-health agent lands `tools/loop_guard_health.py`.
- `.ai/task_graph.yaml` YAML breakage: governance-controller ownership; `validate_state` will go green once the T-0083 entry is correctly placed under `tasks:`.
- Full-mode audit (`pytest_core`) references `tests/test_guard_health.py`, which is not yet created (guard-health agent's test); full mode will report pytest rc=4 until that test file exists. Quick mode is unaffected.
- All run artifacts: `.ai/evidence/T-0083/guard-health/self-audit.json`.
