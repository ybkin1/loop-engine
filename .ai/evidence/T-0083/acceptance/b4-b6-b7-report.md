# B4 + B6 + B7 Acceptance Report — Single-source consolidation + self-review blocking + HardConstraints kernel activation

- **Task**: T-0083
- **Gate**: G-T-0083-REQUIREMENTS
- **Role**: developer
- **Actor**: zcode-actor-88fa0d759f84
- **Date**: 2026-07-31
- **Scope**: B7 (gap-analysis §2.13 HardConstraints kernel activation), B6 (gap-analysis §3.2 self-review blocking), B4 (gap-analysis §3.3 single-source consolidation)

## 1. B7 — HardConstraints kernel activation in the write path (gap-analysis §2.13)

### Before
`hooks/scripts/loop_enforcement.py` constructed the HardConstraints context with
`current_phase=None, target_phase=None, phase_gates={}, quality_results={}, review_status={},
evidence_list=[]` and **no `root`/`task_id` keys**. Trace of `check_all()`: C1/C2 returned early
(`relevant_phases` never matches None), C5 returned early (`target_phase=None`), C6 returned early
(`current_phase=None`), C8 iterated an empty list, C9/C10/C11 returned early (`root` is None).
**Only C3/C4/C7 executed** — the "non-bypassable control kernel" enforced one third of itself.

### After
New builder `build_hard_constraints_context()` (loop_enforcement.py) populates every key the
C-functions read, from actual governance state:

| Context key | Source | Checks activated |
|---|---|---|
| `current_phase` | `state.yaml current_phase` | C1/C2/C6 (phase gating) |
| `phase_gates` | `hook_common.load_phase_gates_for_context` | C1/C2 |
| `gates`, `tasks`, `target_path`, `allowed_paths` | gates.yaml / task_graph.yaml / task contract (unchanged) | C3/C4/C7 |
| `quality_results` | `.ai/evidence/quality/quality_report.json` (check name → status) | C5 |
| `review_status` | task evidence dir JSONs with `role: independent-reviewer` (mirrors `EnforcementHub._load_review_status`) | C6 |
| `evidence_list` + `current_hashes` | task evidence dir (`evidence_envelope.json` parsed as-is; other evidence JSONs wrapped with no expiry + live content hash) | C8 |
| `root` + `scan_paths` | project root | C9 (S4/S5 only) |
| `root` + `task_id` + `max_files` | project root + task contract `max_files` | C10/C11 |
| `target_phase` | deliberately `None` — writes never advance phases (RuntimeController domain) | C5 stays a phase-transition-domain check (see limitations) |

### Real probe (check_all with the populated context, repo state S6-delivery / T-0083)

```
state.current_phase = S6-delivery | task_id = T-0083
phase_gates: {}            quality_results: {lint: BLOCKED, typecheck: BLOCKED, test: PASS,
                           coverage: BLOCKED, audit: PASS, build: BLOCKED, compile: PASS}
evidence_list: 5 envelopes (approval/compile/execution/guard-health/report, guard-health/self-audit)
C1: EXECUTED, 0 violations    C2: EXECUTED, 0 violations
C3: EXECUTED, 0 violations    C4: EXECUTED, 1 violation  (see limitations)
C5: EXECUTED, 0 violations    C6: EXECUTED, 0 violations
C7: EXECUTED, 0 violations    C8: EXECUTED, 0 violations (5 real envelopes, all fresh)
C9: EXECUTED, 237 violations  C10: EXECUTED, 0 violations
C11: EXECUTED, 0 violations
```

Per-constraint count of executed checks: **10/11 execute in the populated write path** (was 3/11).
Per-constraint count of constraints that can *block* at the current repo phase (S6-delivery):
C4 (scope), C7 (blockers), C8 (stale evidence), C10/C11 (soft warnings). C1/C2/C6/C9 are armed but
legitimately dormant at S6 (C1/C2/C6 apply in S2-S4; C9 applies in S4/S5) — verified by the probe:
when the project enters S4-implementation, a fixture WITHOUT approved S1/S2 baselines and WITHOUT
independent-review evidence is now BLOCKED by C1+C2+C6 (see new test
`test_s4_write_without_approved_baselines_or_review_blocks`).

### Test impact (fixtures were wrong, checks NOT weakened)
Two tests expected S4 writes to pass with no phase baselines and no review evidence — unrealistic
under an active kernel. Fixed the fixtures to mirror real governance (approved
S1-requirements/S2-architecture gates + independent-reviewer PASS evidence in `tests/test_enforcement.py`
and `tests/test_runtime_delivery_gate.py`). New tests assert the kernel's blocking behavior and B6
(see §2). `tests/test_enforcement.py` + `tests/test_runtime_delivery_gate.py`: **45 passed** (was 42 + 2 failures before fixture fix).

## 2. B6 — Self-review blocking (gap-analysis §3.2)

### Before
`trace_review_evidence_isolation` only LOGGED self-review (`SELF_REVIEW_TRACE`), never blocked —
"never returns a blocking verdict". A direct self-review (reviewer_session_id == developer_session_id)
did not stop the gate.

### After
`trace_review_evidence_isolation` now **returns `bool`**: when review evidence shows
`reviewer_session_id == developer_session_id`, and blocking is enabled
(`enforcement.self_review_block`, default `true`, added to `hook_common.DEFAULT_CONFIG`), and
`loop_mode == FULL` → returns `True` → the caller logs `BLOCKED: SELF_REVIEW evidence detected
(reviewer==developer session)` and returns `EXIT_BLOCK`.

- **Opt-out**: `.zcode/skills/loop-governance/config.yaml` → `enforcement: {self_review_block: false}`
  restores trace-only behavior (projects can opt out).
- **STANDARD mode**: not blocked (trace only) — blocking is a FULL-mode policy per mission.

### Tests (new)
- `test_self_review_evidence_blocks_business_write_in_full_mode` — self-review evidence → rc=2, stderr contains `SELF_REVIEW` + `BLOCKED`.
- `test_self_review_block_opt_out_allows_write` — `self_review_block: false` → rc=0, trace logged.

## 3. B4 — Single-source consolidation (gap-analysis §3.3)

### Before
`agents/quality-engineer/scripts/run_quality_gates.py` was marked DEPRECATED ("Prefer
loop_core.static_analyzer.analyze_project()") yet was still the operative quality chain producing
the `quality_report.json` the enforcement hook requires — two sources of truth for the same check
(§3.3 evidence (a)).

### After
- Header comment: DEPRECATED → **"LEGACY WRAPPER — delegates to loop_core canonical APIs; retained
  for evidence-format compatibility"**.
- `collect_results()` now folds the canonical APIs into the same report via
  `_collect_canonical_checks()`:
  - `static_analysis` ← `loop_core.static_analyzer.analyze_project()` (value = error count;
    PASS when 0 errors, else FAIL — static-analysis errors are quality issues, not blockers).
  - `security` ← `loop_core.security_scanner.scan_security()` (fail-closed: critical → BLOCKED,
    high → FAIL, else PASS).
  - Both carry `execution_evidence` (exit_code + command) so
    `check_quality_gate_evidence`'s authenticity validation can verify they ran; both carry
    `findings`/`files_scanned` detail for machine consumers.
  - Canonical API unavailable → fail-closed BLOCKED item (consistent with T-0083 AC-07).
- `generate_report()` honors pre-computed canonical statuses (FAIL/BLOCKED) verbatim instead of
  routing unknown names through `check()` (which would have turned a canonical FAIL into a
  spurious PASS).
- `loop_core` import path fixed for scanning foreign project directories
  (`parents[3]` = repo root, which the script does not live inside).

### End-to-end verification (scratch project, report written to scratch `.ai/evidence/quality/`)
```
script exit: 0 | schema: quality_report/v1 | overall: PASS | blocked_by: []
  static_analysis PASS value= 0 | exec_ev exit_code= 0
  security PASS value= {'critical': 0, 'high': 0} | exec_ev exit_code= 0
check_quality_gate_evidence: True | 质量证据已通过（overall=PASS，证据真实性校验通过）
```
Schema compatibility with `check_quality_gate_evidence` (`overall` field, `execution_evidence`
consistency rules) verified: PASS items with exit_code=0 pass authenticity checks; the hook's
evidence checker accepts the consolidated report.

## 4. Test results (real numbers)

| Suite | Before | After |
|---|---|---|
| `tests/test_enforcement.py` + `tests/test_runtime_delivery_gate.py` | 42 passed, **2 failed** (fixtures lacked baselines/review) | **45 passed** (incl. 2 new B6 tests + 1 new B7 test) |
| `tests/test_hooks.py` | 15 passed | **15 passed** |
| `tests/test_quality_gates.py` + `tests/test_check_thresholds.py` + `tests/test_code_quality.py` | 52 passed | **52 passed** |
| Broader sweep (hook_guards, hook_integration, bypass_matrix, bash_readonly, governance_consistency, hard_constraints, import_checker, plugin_cache_sync, contract_verifier) | — | **524 passed, 15 xfailed** |

No checks were weakened; two failing tests were fixed because their S4 fixtures were unrealistic
under an active constraint kernel (the kernel now correctly blocks what those fixtures allowed).

## 5. Honest remaining limitations

1. **C5 remains dormant in the write path by design**: `check_c5_verification` requires
   `target_phase == S6-delivery`; writes never advance phases (`target_phase=None` per mission
   prescription — phase transitions are RuntimeController's domain). C5 executes (probe:
   EXECUTED, 0 violations) but cannot block from the write hook. If C5 enforcement on delivery is
   wanted, it belongs in the phase-transition path (RuntimeController), not per-write.
2. **C4 input gap (pre-existing, not introduced by B7)**: `load_task_contract` parses English
   `allowed_paths:` sections; T-0083's task file declares paths under the Chinese `## 允许路径`
   heading, so the contract's `allowed_paths` is `[]` and C4's "no allowed_paths" BLOCKER would
   fire if the hook reached the kernel for a business write. The repo's runtime projection gate
   (DISPATCH_REQUIRED) currently prevents reaching the kernel, so this is latent. The task file
   should use the English section or the parser should learn the Chinese heading (not done here —
   out of B4/B6/B7 scope).
3. **C9 activation surfaces real dependency-declaration debt**: probing C9 on the repo reports
   237 undeclared-import violations (top: `yaml` — pyproject declares `pyyaml` in
   optional-dependencies, not mapped to import name; plus project-local modules like `hook_common`,
   `check_thresholds` flagged as undeclared). C9 is armed for S4/S5 phases only (dormant at
   S6-delivery). When the project enters S4/S5, writes will be blocked until dependencies are
   declared in `[project].dependencies`/`requirements.txt` — the honest kernel semantics; we did
   NOT weaken C9.
4. **C8 envelopes for generic evidence JSONs carry no expiry** (`expires_at=None` → always fresh)
   unless `evidence_envelope.json` with `expires_at` exists — no false-positive staleness, but
   expiry-based staleness only bites for projects that publish proper envelopes.
5. **`phase_gates` mapping**: `load_phase_gates_for_context` maps `gate_type` →
   phase; the repo's real gates use `user-*` gate_types, so `phase_gates={}` today — C1/C2 will
   genuinely enforce once typed gates (or an id-suffix mapping) exist. Fixtures now demonstrate the
   C1/C2/C6 blocking behavior with typed gates.
6. **B6 scope**: blocks business writes only (governance/evidence writes remain exempt — evidence
   creation must stay possible); STANDARD mode keeps trace-only behavior; opt-out config is
   available for projects that cannot run an independent reviewer session.
