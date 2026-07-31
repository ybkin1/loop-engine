# Constraint Coverage Inventory — C1..C11 (T-0085 Part 3)

| | |
|---|---|
| **Task** | T-0085 — research phase |
| **Role** | quality-engineer |
| **Date** | 2026-07-31 |
| **Method** | grep of tests/ for each `check_c{n}_*` function, `ConstraintID.C{n}_*`, and integration paths (`check_all`, `EnforcementHub.should_allow_write` / `should_allow_phase_advance`, `PhaseExecutor.execute_phase`) |

## 1. Unit-level coverage (direct calls to each check function)

| Constraint | Test file(s) | Test classes (count) | Trigger (violate) | Allow (pass) | Notes |
|---|---|---|---|---|---|
| C1-no-requirements | tests/test_hard_constraints.py | TestC1RequirementsBaseline (8) | yes | yes | baseline-file parsing + gate-status logic |
| C2-no-architecture | tests/test_hard_constraints.py | TestC2ArchitectureBaseline (6) | yes | yes | |
| C3-no-task-package | tests/test_hard_constraints.py | TestC3TaskPackage (6) | yes | yes | |
| C4-path-out-of-scope | tests/test_hard_constraints.py | TestC4PathScope (8) | yes | yes | |
| C5-no-verification | tests/test_hard_constraints.py | TestC5Verification (6) | yes | yes | pass / test≠PASS / lint-missing / build-missing / non-S6 no-op / target_phase=None warning |
| C6-no-independent-review | tests/test_hard_constraints.py | TestC6IndependentReview (8) | yes | yes | incl. PASS vs other verdicts |
| C7-blocker-exists | tests/test_hard_constraints.py + tests/test_hook_integration.py | TestC7Blockers (9) | yes | yes | hook path covered too |
| C8-stale-evidence | tests/test_hard_constraints.py | TestC8EvidenceFreshness (7) | yes | yes | envelope expiry + hash |
| C9-import-not-declared | tests/test_import_checker.py | TestImportCheckerBasics (17) + TestC9HardConstraint (6) + TestEdgeCases (4) = **27** | yes | yes | C9: declared dep / stdlib / relative / local; check_all S4 gate; not-run-outside-S4/S5 |
| C10-contract-test-missing | tests/test_contract_verifier.py | TestHardConstraintsC10 (4) + TestCheckContractTestCoverage (3) + TestVerifyContractCoverage (4) | yes | yes | |
| C11-task-file-limit | tests/test_contract_verifier.py | TestHardConstraintsC11 (5) | yes | yes | |

`tests/test_hard_constraints.py` total: 78 tests / 11 classes (incl. TestCheckAll 12, TestEvidenceEnvelope 5, TestConstraintCheckResult 3).

## 2. Integration-level coverage

| Path | Tests | What is exercised | Gaps |
|---|---|---|---|
| `HardConstraints.check_all` | tests/test_hard_constraints.py TestCheckAll (12) + test_import_checker.py `test_c9_in_check_all_s4_phase` / `test_c9_not_run_outside_s4_s5` | all-pass; C4 fail; no-active-tasks (C3); C1 missing for S4; **C5 missing for delivery** (line 896); C6 missing in S4; C7 blocked gate; C8 stale; aggregation; warnings-not-fail; C1/C2 repeat-stable; C9 phase-gating | C10/C11 never exercised through check_all (they require `root` **and** `task_id` in context — TestCheckAll builds contexts without `task_id`) |
| `EnforcementHub.should_allow_write` | tests/test_enforcement_hub.py TestShouldAllowWrite (4) + TestFailClosedCorruption (12) | C3/C4/C7 blocking through hub; fail-closed on corrupt `.ai` governance | only 4 tests; C5/C6/C8/C9 branches untestable here by design (write path has `target_phase=None`) |
| `EnforcementHub.should_allow_phase_advance` | tests/test_enforcement_hub.py TestShouldAllowPhaseAdvance (4) + corrupted-state test | valid S0→S1 allowed (weak assert — only "doesn't crash"), skip-phase blocked (C7), invalid phase string blocked, blocked-task blocked (C7), fail-closed on corruption | **No test with `quality_results` set for S5→S6 → C5 branch never exercised at hub level; no S4→S5 test → C9 branch never exercised at hub level** |
| `PhaseExecutor.execute_phase` (the real phase-advance path) | tests/test_executor.py TestExecutePhase (5) + TestBlockedRolePreventsAdvance (1) + TestPersistState (3) | first-phase succeeds; invalid transition blocked (state-machine graph only); valid forward transition; state persisted; blocked role prevents advance | HardConstraints are NOT wired into this path at all — no C5/C6/C9 test possible until wiring exists |
| `check_phase_constraints` (state_machine) | tests/test_state_machine_enhanced.py TestPhaseConstraints (8) + TestCheckPhaseConstraints (7) | S4 requires C1/C2/C6-type constraints; **S6 blockers include C5/C6/C7** (`test_s6_missing_verification_fails`, `test_s6_missing_independent_review_fails`); non-blocker warning | phase-constraint table only — not the HardConstraints kernel |
| `can_transition_phase` / `can_enter_phase` | tests/test_state_machine_enhanced.py (TestBackwardCompatibility 10, TestResolveGateStatus 8) | transition graph, gate preconditions | — |

## 3. Per-constraint verdict: which constraints lack trigger/allow tests at each layer

| Constraint | Unit | check_all | should_allow_write | should_allow_phase_advance | execute_phase (real advance) |
|---|---|---|---|---|---|
| C1 | yes | yes | via hub (indirect) | **missing** | not wired |
| C2 | yes | yes | via hub (indirect) | **missing** | not wired |
| C3 | yes | yes | yes | — (n/a) | not wired |
| C4 | yes | yes | yes | — (n/a, no target_path in phase ctx) | not wired |
| C5 | yes | yes | — (n/a by design) | **MISSING — no trigger/allow test exists for C5 through any phase-advance entry point** | not wired |
| C6 | yes | yes | — (n/a) | **missing** (only via check_all inside the method) | not wired |
| C7 | yes | yes | yes | yes | partial (blocked-role) |
| C8 | yes | yes | — (n/a) | **missing** | not wired |
| C9 | yes | yes | — (n/a) | **missing** (S4→S5 branch never tested at hub level) | not wired |
| C10 | yes | **missing** (`task_id` never in check_all test contexts) | — (n/a) | — (n/a) | not wired |
| C11 | yes | **missing** (same) | — (n/a) | — (n/a) | not wired |

## 4. Key structural findings

1. **C5/C6/C8/C1/C2 have NO trigger/allow test through any phase-advance entry point.** The only code that builds a context with `target_phase` (needed for C5) is `EnforcementHub.should_allow_phase_advance` (loop_core/enforcement_hub.py:480), and its 4 tests never set `quality_results`, so the C5 branch (lines 529-557) executes but never fires. C9's S4→S5 branch (line 550) is likewise untested.
2. **C10/C11 are dead in every integration path**: `check_all` requires `context["task_id"]` (hard_constraints.py:288-289) and `EnforcementHub._build_context` (enforcement_hub.py:333-354) never sets `task_id` or `max_files` — so C10/C11 only ever run via direct unit calls or T-0083's manual probe.
3. **C4 is correctly write-domain-only**: `should_allow_phase_advance` builds context without `target_path`, so C4 is skipped (hard_constraints.py:232 `if target_path is not None`). Same for C3 — it runs, but task package is a write/entry concern.
4. **The real phase-advance path (`PhaseExecutor.execute_phase`) has zero HardConstraints involvement** — only `can_transition_phase`/`can_enter_phase`/compile-gate (state-machine + executor level). This is the T-0083 §2.13 "dormant kernel" gap: 10/11 constraints can execute in the write path (B7), but the phase-transition domain still executes none of them.
5. Constraint tests that exist are genuine trigger+allow pairs (not just smoke): every C1-C9 check function has both pass and violate tests at unit level. The deficit is integration depth, not unit depth.
