# T-0050 Integration Verification Report

**Date:** 2026-07-27  
**Project:** loop-engine (v3.4.0)  
**Task:** End-to-end integration verification of anti-hallucination mechanisms on loop-engine's OWN codebase ("eat your own dog food")

---

## 1. ImportGate on loop-engine

**Tool:** Manual AST-based import scan (verified against `pyproject.toml` declared dependencies)

**Result: FAIL (2 undeclared imports found)**

| # | File | Undeclared Import | Resolution |
|---|------|-------------------|------------|
| 1 | `loop_core/import_checker.py` (line 193) | `tomli` | Add `tomli` to dev dependencies OR switch to stdlib `tomllib` (3.11+) and bump `requires-python` |
| 2 | `loop_core/project_map_schema.py` (line 331) | `jsonschema` | Add `jsonschema` to `pyproject.toml` dependencies |

**Note:** `pyyaml` is imported as `yaml` across many files -- this is correctly declared in `pyproject.toml` as `pyyaml>=6.0`. No false positive.

**Systems verified:**
- `loop_core/import_checker.py` exists and was itself scanned (dogfooding)
- `loop_core/contract_verifier.py` exists and was scanned

**Evidence:** `.ai/evidence/T-0050/import-check-self.json`

---

## 2. CompileGate on loop-engine

**Tool:** `.ai/checkers/compile_gate.py` (dogfooded on itself)

**Result: PASS (52/52 files compiled successfully)**

```json
{
  "status": "pass",
  "exit_code": 0,
  "compiled_files": 52,
  "total_files": 52,
  "failed_count": 0,
  "errors": []
}
```

**Systems verified:**
- `compile_gate.py` correctly uses `py_compile` to validate all Python files
- Targets: `loop_core/`, `hooks/scripts/`, `.zcode/tools/`
- No syntax errors or compile failures

**Evidence:** `.ai/evidence/T-0050/compile-gate-self.json`

---

## 3. Contract Verifier on Existing Contracts

**Result: NO-OP (no interface contracts found)**

- No `interface-contract.yaml` files exist in any `.ai/evidence/*/` directory
- `loop_core/contract_verifier.py` is implemented and test-covered (35 tests in `tests/test_contract_verifier.py`)
- 12 agent-level `CONTRACT.yaml` files exist under `agents/*/` (role definition contracts, not interface contracts)
- Contract verifier correctly returns empty results when no contracts exist (no false positives)

---

## 4. Validation Chain Results

### 4a. repair_continuity.py

```
[repair_continuity] No hash drift detected.
```

**PASS** -- exit code 0. Works without state access (reads only `project_continuity.yaml`).

### 4b. validate_state.py --repair

```
[error] VALIDATION_ERROR: HANDOFF project-continuity block must be fenced JSON
```

**FAIL (exit 2)** -- The `PROJECT-GOVERNOR-PROJECT-CONTINUITY` comment block in HANDOFF.md is empty but `parse_json_block()` expects a fenced JSON block (` ```json ... ``` `).

**Assessment:** This is the governance mechanism CORRECTLY detecting a missing structured contract. The --repair mode handles continuity hash drift but not empty structured blocks. This is a real governance gap that should be addressed.

### 4c. Pytest Results

```
125 passed, 4 failed
```

| Test File | Pass | Fail | Notes |
|-----------|------|------|-------|
| `test_enforcement_hub.py` | 49 | 3 | Bug: `UnboundLocalError` for `ctx` variable in `should_allow_phase_advance()` |
| `test_contract_verifier.py` | 35 | 0 | All pass |
| `test_cross_layer_safety.py` | 41 | 1 | COMPILE_EVIDENCE_MISSING for T-002 (missing evidence file) |

### 4d. Test Failures Detail

**BUG 1: enforcement_hub.py `should_allow_phase_advance()` (lines 461/480)**
- `ctx` is referenced on line 461 but only assigned on line 480
- Affected tests: `test_valid_advance_allowed`, `test_skip_phase_blocked`, `test_advance_with_blocked_tasks`
- Fix: Move `ctx = self._build_context(target_phase=target_phase)` before line 461

**BUG 2: T-002 missing compile evidence**
- `test_valid_project_in_progress_with_evidence` expects no hard errors but T-002 at S4-implementation requires compile evidence
- Missing file: `evidence/T-002/compile-evidence.json`

---

## 5. Anti-Deadlock Final Check

### 5a. Governance File Exemptions

| Hook | Exemption Mechanism | Status |
|------|---------------------|--------|
| `gate_guard.py` | `is_governance_project()` + exempt path patterns | PASS |
| `role_isolation.py` | `GOVERNANCE_EXEMPT` list: .ai/gates.yaml, .ai/state.yaml, .ai/task_graph.yaml, .ai/project_continuity.yaml | PASS |
| `loop_enforcement.py` | `is_governance_write()` function + GOVERNANCE_EXEMPT patterns | PASS |

### 5b. repair_continuity Without State Access

- `repair_continuity.py` reads only `project_continuity.yaml` -- no dependency on `state.yaml`
- Successfully verified: `[repair_continuity] No hash drift detected.`

**PASS**

### 5c. close_session Auto-Repair Before Render

- `close_session.py` (line 19-23): imports and calls `repair_continuity()` before rendering handoff
- Catches exceptions silently (best-effort, non-critical)

**PASS**

### 5d. Cross-Layer Safety Tests (Anti-Deadlock)

All anti-deadlock tests in `test_cross_layer_safety.py` passed:
- `test_corrupt_state_gate_guard_exempts_governance_write` PASSED
- `test_corrupt_state_role_isolation_exempts_governance_write` PASSED
- `test_corrupt_state_loop_enforcement_exempts_governance_write` PASSED
- `test_all_hooks_governance_write_on_corrupt_state_no_deadlock` PASSED
- `test_all_hooks_pass_on_clean_project` PASSED

**PASS**

---

## Summary

| Check | Result | Details |
|-------|--------|---------|
| ImportGate (self-scan) | **FAIL** | 2 undeclared imports: `tomli` (import_checker.py), `jsonschema` (project_map_schema.py) |
| CompileGate (self-compile) | **PASS** | 52/52 files compile successfully |
| Contract Verifier | **PASS** (no-op) | No interface contracts exist yet; verifier works correctly |
| repair_continuity | **PASS** | No hash drift detected |
| validate_state --repair | **FAIL** | HANDOFF.md missing fenced JSON block for PROJECT-CONTINUITY |
| test_enforcement_hub.py | 49/52 pass | 3 failures: `UnboundLocalError` for `ctx` variable |
| test_contract_verifier.py | 35/35 pass | All pass |
| test_cross_layer_safety.py | 41/42 pass | 1 failure: T-002 missing compile evidence |
| Anti-Deadlock | **PASS** | All hooks exempt governance files; close_session auto-repairs; cross-layer tests pass |

## Action Items

1. **CRITICAL:** Fix `enforcement_hub.py` line 461 -- move `ctx = self._build_context(...)` before line 461
2. **HIGH:** Add `tomli` to `pyproject.toml` dev dependencies (or switch to `tomllib` and bump `requires-python` to 3.11+)
3. **HIGH:** Add `jsonschema` to `pyproject.toml` dependencies
4. **MEDIUM:** Add fenced JSON block to HANDOFF.md PROJECT-GOVERNOR-PROJECT-CONTINUITY section
5. **LOW:** Generate compile-evidence.json for T-002
