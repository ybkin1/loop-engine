# C9 Fix Report — import_checker defects + C5 phase-advance wiring + C10/C11 context (T-0085)

| | |
|---|---|
| **Task** | T-0085 — developer implementation |
| **Role** | developer |
| **Date** | 2026-07-31 |
| **Basis** | c9-classification.md (237 findings: 5 A1 + 71 A2 + 160 A3 + 0 B + 1 C), c5-activation-point.md, coverage-inventory.md |
| **Gate** | G-T-0085-REQUIREMENTS (approved) |

## Fix 1 — import_checker.py (3 defect classes)

### 1a: Relative-import detection (TYPE-A1, 5 findings)

| | |
|---|---|
| Before | `_scan_file` checked `module.startswith(".")` for `ast.ImportFrom`. On Python 3.8+ the AST strips leading dots — `from .verdicts import X` yields `module='verdicts', level=1`, so the guard never matched and 5 real relative imports were flagged as undeclared third-party. |
| After | `if node.level > 0: continue` — relative imports are always valid (project-local by definition). `module is None` (invalid `from import X`, never present in parsed AST) also skipped. |

### 1b: Import-name → distribution-name mapping (TYPE-A2, 71 findings)

| | |
|---|---|
| Before | Import names compared byte-for-byte against declared distribution names: `import yaml` vs declared `pyyaml` → 71 false blockers. |
| After | Module-level `IMPORT_NAME_TO_PACKAGE` map (`yaml→pyyaml`, `cv2→opencv-python`, `PIL→Pillow`, `sklearn→scikit-learn`, `bs4→beautifulsoup4`, `dateutil→python-dateutil`, `jwt→PyJWT`, `dotenv→python-dotenv`, `zmq→pyzmq`, `skimage→scikit-image`, `Crypto→pycryptodome`, `serial→pyserial`, `ruamel→ruamel.yaml`, `yaml_include→pyyaml-include`) + `_resolve_package_name()` applied in both `ast.Import` and `ast.ImportFrom` branches. Unmapped names still compared directly, so genuinely undeclared imports are still flagged. |

### 1c: Project-local module detection (TYPE-A3, 160 findings)

| | |
|---|---|
| Before | `_is_project_local_module` only checked root/scan-path level names — any module nested under hooks/, tools/, agents/, archive/, scripts/, ... was flagged (governor_lib, hook_common, evidence_manifest, tool_* siblings, ...). |
| After | Added `_collect_local_module_names(root)`: one cached tree walk (skips hidden dirs/`__pycache__`) collects every first path segment (top-level dirs such as hooks/, tools/, agents/) and every `*.py` file stem anywhere in-repo (e.g. `archive/lab-candidates/scripts/governor_lib.py` → `governor_lib`). `_is_project_local_module` consults the set (exact + lowercase) after the original root-level checks. A module is project-local if any of its top-level segments matches an in-repo dir OR a same-named `.py` exists in-repo. |

### 1d: Declared dependencies (real debt)

| | |
|---|---|
| Before | `[project].dependencies` empty; only requirements.txt (`PyYAML>=6.0`) + optional-dependencies. |
| After | `pyproject.toml` `[project].dependencies = ["PyYAML>=6.0"]` (the only runtime third-party distribution actually imported — per research TYPE-B: 0 genuine undeclared runtime deps). Added `[project.optional-dependencies].browser = ["playwright>=1.40"]` for the lazy guarded playwright import in scripts/runtime_delivery_gate.py (research TYPE-C). `pyyaml-include` NOT used anywhere — not added. |

## Fix 2 — C5 (and C1/C2/C6/C8/C9/C10/C11) wired into phase advance (AC-02)

| | |
|---|---|
| Before | `PhaseExecutor.execute_phase` consulted only `can_transition_phase`/`can_enter_phase`/compile gate; HardConstraints had **zero** involvement in the real phase-advance path. `EnforcementHub.should_allow_phase_advance` had zero production callers (dormant kernel). |
| After | In `execute_phase` (loop_core/executor.py), immediately before Step 7 `persist_state`, the new Step 6b runs `_check_phase_advance_gate(project_root, phase)`: instantiates `EnforcementHub` and calls `should_allow_phase_advance(target_phase)` (C5 on S5→S6, C9 on S4→S5, C1/C2/C6/C7/C8 + C10/C11 via `check_all`). On BLOCKED: `plan.status = StepStatus.BLOCKED` + a `phase-advance-gate` RoleStep carrying the reason, returned WITHOUT writing `.ai/state.yaml` (phase does not advance). On exception: **fail-closed** by default (T-0083 semantics; `hooks/scripts/hook_common.should_fail_closed` consulted, default True; `config.yaml hooks.fail_closed_on_error=false` is the DEBUG-ONLY fail-open escape). Guarded to `not fixture_mode` (TEST-ONLY simulation harness; production entry point `tools/tool_execute_phase.py` uses `PhaseExecutor()` → gate active) and `not reentry` (re-running the CURRENT phase is not an advance; `can_transition_phase(cp, cp)` would always block). Write path (hooks) untouched. |

## Fix 3 — C10/C11 dead in integration path

| | |
|---|---|
| Before | `EnforcementHub._build_context` never set `task_id`, and `check_all` gates C10/C11 behind `context["task_id"]` — C10/C11 returned early in every integration path (only unit-direct calls exercised them). |
| After | `_build_context` now sets `task_id` (from `state.current_task_id`) and `max_files: 10`; C10/C11 now run inside `should_allow_write` / `should_allow_phase_advance` through `check_all`. Both are SOFT (WARNING) by design — they report but never block. `ConstraintContext` TypedDict updated (`task_id`, `max_files`, `root`, `scan_paths`). Verified: without `task_id` C11 dead (0), with `task_id` C11 fires (12 paths > limit → WARNING). |

## Verification results

### C9 count

```
C9 violations (scan_paths=[loop_core, hooks, tools]): 0  (was 237)
C9 violations (scan_paths=['.'] full repo):           0  (was 237)
```

All 237 findings (5 A1 + 71 A2 + 160 A3 + 1 C) eliminated by tool fixes + honest dep declarations. Negative control: undeclared `pandas`/`bogus_pkg_xyz` still flagged; `yaml`/`cv2`/`PIL` only pass when PyYAML/opencv-python/Pillow are declared; relative + nested-local imports pass.

### Test suites

| Suite | Result |
|---|---|
| tests/test_import_checker.py + tests/test_hard_constraints.py | **105 passed** (2.12s) |
| tests/test_executor.py + tests/test_enforcement_hub.py + tests/test_runtime_delivery_gate.py | **99 passed** (8.88s) |
| Full tests/ | **2740 passed, 63 skipped, 16 xfailed** — 7 failures in tests/test_governance_consistency.py + tests/lab/test_project_governor_consistency.py are **pre-existing** (verified by stashing all T-0085 changes and re-running: identical 7 failures on baseline; caused by invalid YAML in the working-tree `.ai/task_graph.yaml`, not by this work) |

### Phase-advance gate probe (standalone, not a permanent test)

| Scenario | Result |
|---|---|
| 1: gate patched ALLOW → `execute_phase(S1)` | gate invoked exactly once with target=S1; plan COMPLETE; state.yaml advanced to S1 |
| 2: gate patched BLOCKED → `execute_phase(S1)` | plan BLOCKED with `phase-advance-gate` step (reason preserved); state.yaml UNCHANGED (still S0) — no persist |
| 3: real hub `should_allow_phase_advance(S1)` on healthy governed project | decision computed through the kernel: blocked because S1 is a USER_GATE_PHASE without explicit user-approved gate evidence (correct C7/user-gate semantics) |
| 4: gate raises exception | fail-closed: plan BLOCKED, state.yaml unchanged |

## Honest remaining findings

1. **User-gate phases now enforce through the advance path (behavior change, intended)**: any production transition into S1/S6 via `execute_phase` requires explicit user-gate evidence in gates.yaml (`approval_actor=user` / `approval_source=explicit_user_message` heuristic + `current_gate_id` structural match), and S5→S6 additionally requires test/lint/build all PASS in `.ai/evidence/*/quality/quality_report.json` (C5). `tool_execute_phase` callers must record that evidence or transitions will be blocked — this is the kernel working as designed, not a defect.
2. **C10/C11 remain SOFT (WARNING)**: they now execute in integration paths but never block (by design). If any task wants them HARD, that is a config/severity decision outside this task.
3. **Fixture-mode escape**: the gate is skipped when `fixture_mode=True` (documented TEST-ONLY simulation harness that fabricates PASS verdicts) and when `reentry=True` (re-running the current phase is not an advance). Production phase transitions (fixture_mode=False) always run the gate.
4. **Fail-open escape exists for DEBUG only**: `config.yaml hooks.fail_closed_on_error=false` converts gate *exceptions* (not violations) to warnings; default is fail-closed (T-0083 semantics).
5. **`tests/lab/` test-hygiene debt remains** (test_project_governor_consistency.py imports archive-only governor_lib): no longer a C9 false positive (governor_lib resolves as project-local), but the lab fixture depending on archived code is still test hygiene debt, and `.ai/task_graph.yaml` in the working tree is invalid YAML (pre-existing; breaks 7 governance-consistency tests regardless of this task).
6. **No check was weakened.** All constraint severities, trigger conditions, and fail-closed semantics are unchanged; only the tool (import_checker) was fixed and the dormant phase-advance kernel was wired in.

## Files changed

- `loop_core/import_checker.py` — A1 (node.level), A2 (IMPORT_NAME_TO_PACKAGE + `_resolve_package_name`), A3 (`_collect_local_module_names` cached tree walk)
- `loop_core/executor.py` — Step 6b phase-advance gate + `_check_phase_advance_gate` (fail-closed) + module logger
- `loop_core/enforcement_hub.py` — `_build_context` sets `task_id`/`max_files`
- `loop_core/hard_constraints.py` — `ConstraintContext` TypedDict documents `task_id`/`max_files`/`root`/`scan_paths`
- `pyproject.toml` — `[project].dependencies = ["PyYAML>=6.0"]`, `[project.optional-dependencies].browser = ["playwright>=1.40"]`
