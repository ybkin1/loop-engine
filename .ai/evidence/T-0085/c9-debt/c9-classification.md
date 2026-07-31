# C9 Debt Classification — 237 Undeclared-Import Findings (T-0085 Part 1)

| | |
|---|---|
| **Task** | T-0085 — research phase |
| **Role** | quality-engineer |
| **Date** | 2026-07-31 |
| **Basis** | T-0083 B7 probe result ("C9: EXECUTED, 237 violations") reproduced 1:1 |
| **Method** | `HardConstraints.check_c9_import_validity(root='.', scan_paths=['.'])` run against repo state S6-delivery; every violation re-classified per-site by re-parsing the flagged file's AST node (`node.level`, actual import syntax) |

## Reproduction (exact match)

```
TOTAL violations: 237  (identical to T-0083 B7 probe: 237)
stdlib modules missed: 0
```

Classifier: `.ai/evidence/T-0085/c9-debt/classify_c9.py` (read-only on code; results in
`c9-raw-findings.json`, `c9-buckets.json`).

## How import_checker.py determines declared vs undeclared

`ImportChecker.check_directory(root, scan_paths)` (`loop_core/import_checker.py`):

1. **Declared set** = package names parsed from `pyproject.toml`
   (`[project].dependencies`, `optional-dependencies`, `build-system.requires`) +
   `requirements.txt`, lowercased. Current repo declares only: `pyyaml`,
   `pytest`, `pytest-cov`, `jsonschema`, `tomli`, `ruff`, `mypy`, `setuptools`,
   `wheel` (requirements.txt has **only** `PyYAML>=6.0`; `[project].dependencies`
   is absent — everything lives in optional-dependencies).
2. **Always valid**: stdlib (`sys.stdlib_module_names`), relative imports
   (checked via `module.startswith(".")`), and project-local modules (top-level
   name exists as a directory or `.py` **directly under root or a scan_path**).
3. Everything else: `top_level.lower() in declared_deps`, else BLOCKER.

## Summary table

| Category | Count | Examples | Fix |
|---|---|---|---|
| **TYPE-A1 — relative-import detection bug** | **5** | `from .verdicts import ...` (loop_core/security_scanner.py:26, static_analyzer.py:25), `from .enforcement import ...` (loop_core/contracts.py:35), `from .zcode_adapter/.claude_adapter import ...` (loop_engine/adapters/__init__.py:1) | Fix `import_checker.py._scan_file`: Python ≥3.8 AST gives `node.module` **without** leading dots for relative imports (`from .verdicts import X` → `module='verdicts', level=1`), so `module.startswith(".")` never matches. Check `node.level > 0` instead. |
| **TYPE-A2 — package-name vs import-name mapping missing** | **71** | `import yaml` in 27 loop_core files (approval_ledger.py:179/236/288, enforcement_hub.py:164/182/201, status_dashboard.py, inbox.py, planner.py, state_machine.py, task_queue.py …), hooks/scripts/*, tests/*, scripts/, agents/ | Add import-name→package-name map (`yaml`→`PyYAML`) in `_scan_file` (mirrors `importlib.metadata` reverse lookup). `pyyaml` IS declared (requirements.txt + optional-deps); the checker compares `"yaml" != "pyyaml"` and flags 71 sites. |
| **TYPE-A3 — nested project-local modules not recognized** | **160** | `governor_lib` (70; lives only under archive/lab-candidates/scripts/), `hook_common` (21; hooks/scripts/hook_common.py), `evidence_manifest` (11), `continuity_producer` (6), `transaction_registry` (5), `validation_runner` (5), `_hook_path` (4), `check_thresholds` (2), 20 sites inside tools/server.py importing `tool_*` modules | Widen project-local detection: `_is_project_local_module` only checks **root-level** names, so any module nested under hooks/, tools/, agents/…/scripts/, loop_engine/adapters/ is flagged. Search subdirectories of root (or accept a known-local-package list), or stop scanning non-root source trees. |
| **TYPE-B — real undeclared third-party debt** | **0** | — | None found: every non-A1/A2 name resolves to a `.py` file inside the repo. Note the honest caveat: `[project].dependencies` is empty, so a *fixed* checker would still require PyYAML there; no other runtime third-party imports exist. |
| **TYPE-C — optional / lazy / guarded third-party** | **1** | `playwright.sync_api` — scripts/runtime_delivery_gate.py:357, lazy `import` inside `try/except ImportError` that returns `NOT_RUN` gracefully | Optional dependency by design (browser smoke check). Declare `playwright` under `[project.optional-dependencies]` (e.g. `browser`) and/or make C9 exempt guarded lazy imports. |

**Total: 237 = 5 + 71 + 160 + 0 + 1.** Stdlib false positives: **0**
(`sys.stdlib_module_names` coverage is exact). **Real debt: 0** — all 236
non-C findings are tool defects (false positives); the 1 C finding is a
deliberate optional dep.

## Per-directory distribution of importing files (all 237)

| Importer dir | Count | Notes |
|---|---|---|
| tests/ | 109 | 46 in tests/lab/test_project_governor_consistency.py (imports archive-only `governor_lib`); test_cross_layer_safety.py 13; test_operations.py 7; test_hook_integration.py 5 |
| archive/ | 40 | lab-evidence **backup copies** of old scripts/tests (T-0030/T-0036 snapshots) — evidence, not live code |
| loop_core/ | 27 | 17× yaml + 3× relative-import bug + rest yaml across hooks-adjacent checks |
| tools/ | 24 | 20 in tools/server.py importing tool_* siblings; rest yaml |
| hooks/ | 22 | hook_common internal imports + yaml |
| scripts/ | 10 | yaml + playwright (1) |
| loop_engine/ | 3 | adapters relative imports (A1) |
| agents/ | 2 | yaml in quality-engineer/scripts/run_quality_gates.py |

## Root causes (tool defects, in `loop_core/import_checker.py`)

1. **Relative-import check is dead code on Python 3.8+** (`_scan_file`, both branches):
   `module.startswith(".")` never evaluates true because `ast.ImportFrom.module`
   carries no leading dots; the level is in `node.level`. 5 real relative imports
   flagged.
2. **No package-name ↔ import-name mapping**: import names (`yaml`) are compared
   byte-for-byte against declared distribution names (`pyyaml`). PyYAML is the
   canonical example; `dateutil`/`PIL`/`sklearn`/`cv2` etc. would hit the same
   class. 71 sites.
3. **Project-local detection only scans root level**: `_is_project_local_module`
   checks `root/<name>` / `scan_path/<name>` only. The repo's real packages are
   nested (`hooks/scripts/`, `tools/`, `agents/*/scripts/`, `loop_engine/adapters/`,
   `archive/lab-candidates/scripts/`), so 160 internal imports are flagged.
   Also, only *top-level* names can match — `tools.tool_state` style imports whose
   package `tools/` has no `__init__.py` still resolve at runtime via sys.path.

## Scan-scope observations (not defects, but inflate the number)

- `archive/lab-evidence/` contains **frozen backup copies** of T-0030/T-0036
  scripts and tests; 40 findings come from importing files inside archive/.
  If C9 scan_paths are restricted to live dirs (loop_core, hooks, tools,
  scripts, agents, loop_engine), the count drops to 197 and archive noise is gone.
- `tests/lab/test_project_governor_consistency.py` (46 sites) imports
  `governor_lib`, which **only exists in archive/** — the test suite has lab/
  fixtures depending on archived code. This is test-hygiene debt, not a runtime
  import debt.

## Consequence for S4/S5 enforcement

C9 is armed for S4-implementation/S5 (per `hard_constraints.py` gate wiring).
As implemented today it would block **every** S4/S5 write to loop_core/, hooks/,
tools/ (yaml sites alone block all of loop_core). The honest kernel semantics
require fixing import_checker.py first (A1/A2/A3), then declaring `pyyaml` in
`[project].dependencies`; no other runtime deps are missing. **No check was
weakened during this research.**
