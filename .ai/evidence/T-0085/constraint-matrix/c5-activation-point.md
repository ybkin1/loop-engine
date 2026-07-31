# C5 Activation Point — Phase-Advance Investigation (T-0085 Part 2)

| | |
|---|---|
| **Task** | T-0085 — research phase |
| **Role** | quality-engineer |
| **Date** | 2026-07-31 |
| **Scope** | Where phase advancement happens; where C5 (and the dormant C1/C2/C6/C8/C9 kernel) should be wired; minimal safe change; existing test coverage |

## 1. Where phase advancement actually happens

| Entry point | Call chain | Writes `.ai/state.yaml` |
|---|---|---|
| `tools/tool_execute_phase.py:23` (MCP tool, registered in tools/server.py:181/420-421) | `run()` → `PhaseExecutor.execute_phase(phase, root)` | yes |
| `tools/loop_execute_phase.py` (CLI two-layer model) | → `execute_phase(...)` | yes |

Inside `PhaseExecutor.execute_phase` (loop_core/executor.py:532):
- Step 1: `can_transition_phase(current_phase, phase)` (executor.py:562 → state_machine.py:112, PHASE_TRANSITIONS graph at state_machine.py:53-66)
- Step 2: `can_enter_phase(...)` (executor.py:588 → state_machine.py:147)
- Step 2b: compile gate for S5 (executor.py:606) — the only quality gate in the advance path
- Step 7: `persist_state()` (executor.py:688) → `_write_state()` (executor.py:280-306) atomically writes `current_phase: <target>` to `.ai/state.yaml` (tmp + os.replace)

**`loop_core/runtime_controller.py` has NO phase-advance method** (grep for advance/transition/phase-methods: zero hits). `scripts/runtime_delivery_gate.py` runs S6 runtime checks (artifact manifest, service startup, browser smoke) and writes evidence — it never touches `current_phase`.

**Today the advance path consults only the state machine** (`can_transition_phase`, `can_enter_phase`) plus the executor compile gate. HardConstraints are not involved anywhere in it.

## 2. Where C5 should be wired

The wiring target already exists and is correct: **`EnforcementHub.should_allow_phase_advance(target_phase)`** (loop_core/enforcement_hub.py:480-566). It:
- FAILS CLOSED on corrupt/missing `.ai` governance state (line 487)
- builds the full context via `_build_context(target_phase=target_phase)` (line 529 → enforcement_hub.py:333-354), which sets `current_phase`, `target_phase`, `phase_gates`, `gates`, `tasks`, **`quality_results`** (`_load_quality_results`, reads `.ai/evidence/*/quality/quality_report.json` checks), **`review_status`** (independent-reviewer verdict), `evidence_list`, `current_hashes`, `root`, `scan_paths`
- runs `can_transition_phase` + `can_enter_phase` + `check_phase_constraints` (with compile + user-gate evidence) as C7 violations
- runs **C9 explicitly on S4→S5** (line 550)
- runs **`self._hc.check_all(ctx)`** (line 557) → this is where **C5 fires** (check_all passes `target_phase` to `check_c5_verification`, hard_constraints.py:244-250; C5 requires `target_phase == S6-DELIVERY` and `quality_results` test/lint/build all PASS, hard_constraints.py:538-607), plus C1, C2, C6 (current_phase=S4), C7, C8.

**Recommended wiring point**: inside `PhaseExecutor.execute_phase`, between the entry/compile checks (after line 622) and `persist_state` (line 688):
```
hub = EnforcementHub(project_root)
decision = hub.should_allow_phase_advance(phase)
if not decision.allowed: → return PhasePlan(status=BLOCKED, blocked steps with reason), WITHOUT writing state.yaml
```
Equivalently at the tool layer (tools/tool_execute_phase.py:23) before calling `execute_phase` — but inside `execute_phase` keeps the gate in the domain layer and covers both the MCP tool and the CLI.

**Do NOT wire C5 into the write path** (hooks/scripts/loop_enforcement.py / `EnforcementHub.should_allow_write`): writes never advance phases and T-0083 deliberately keeps `target_phase=None` there (B7 limitation #1); C5 with `target_phase=None` is a no-op with a warning (hard_constraints.py:550-558).

## 3. Callers of `should_allow_phase_advance`

**Zero production callers.** Grep of loop_core/, hooks/, tools/, scripts/, loop_engine/, agents/ shows the method is referenced only by `tests/test_enforcement_hub.py` (TestShouldAllowPhaseAdvance, 4 tests + corrupted-state fail-closed test at line 617). `EnforcementHub` itself is instantiated in production only by `tools/tool_governance_status.py:9` and `tools/tool_state.py:8` (status/state reporting — neither calls `should_allow_phase_advance`). This is the T-0083 gap-analysis §2.13 "dormant control kernel": the phase-transition domain runs none of C1/C2/C5/C6/C8/C9.

## 4. Minimal safe change to activate C5 without breaking the write path

1. In `PhaseExecutor.execute_phase` (loop_core/executor.py), after the compile-gate block and before `persist_state`: instantiate `EnforcementHub(project_root)` and call `should_allow_phase_advance(phase)`.
2. On `allowed=False`: return a `PhasePlan(status=StepStatus.BLOCKED)` whose steps carry the blocker messages (mirroring how transition/entry failures are already returned at executor.py:564-576/590-601), and **do not call persist_state** — `.ai/state.yaml` stays at the current phase.
3. Add an escape/guard for `fixture_mode` if needed for legacy fixtures, but note `should_allow_phase_advance` fails closed on corrupt governance by design (same semantics as `should_allow_write`).
4. Consequences: C5 fires exactly at S5→S6 (test/lint/build must be PASS in `.ai/evidence/*/quality/quality_report.json`), C6 at S3→S4/S4→S5 (REVIEW_REQUIRED_PHASES), C9 at S4→S5, C1/C2 at S1/S2 entry, C8 on stale envelopes. The write path is untouched (still `target_phase=None`), so no write-path regression — C5/C9 currently flag nothing there anyway (probe: C5 EXECUTED 0 violations; C9 armed only at S4/S5).
5. **Caution**: activating `should_allow_phase_advance` in FULL mode will block S5→S6 until quality evidence shows test/lint/build PASS and S4→S5 until C9 passes — and C9 today produces **237 false-positive blockers** (see c9-debt/c9-classification.md). C9 must be fixed (import_checker.py defects A1/A2/A3) before C9-in-advance-path becomes usable; C5 is safe to activate immediately.

## 5. Tests covering phase advance today

| File | Covers | Does it exercise C5? |
|---|---|---|
| tests/test_enforcement_hub.py — TestShouldAllowPhaseAdvance (4) + TestFailClosedCorruption (12, incl. phase-advance fail-closed at :617) | `should_allow_phase_advance`: valid S0→S1, skip-phase blocked, invalid name blocked, blocked-task blocked | **No** — no test sets `quality_results` or targets S6, so the C5 branch (and the C9 S4→S5 branch) never fires |
| tests/test_executor.py — TestExecutePhase (5), TestBlockedRolePreventsAdvance (1), TestPersistState (3) | `execute_phase` transition graph, blocked-role advance prevention, state persistence | No — HardConstraints not wired into this path |
| tests/test_state_machine_enhanced.py — TestCheckPhaseConstraints (7), TestPhaseConstraints (8), TestBackwardCompatibility (10) | phase-constraint table incl. S6 requires C5/C6/C7 (`test_s6_missing_verification_fails`, :358); `can_transition_phase`/`can_enter_phase` | Phase-constraint table level only (state_machine.check_phase_constraints), not the HardConstraints kernel |
| tests/test_hard_constraints.py — TestC5Verification (6) + TestCheckAll (12, incl. `test_fails_when_verification_missing_for_delivery`, :896) | `check_c5_verification` unit (pass/violate/no-op/warning) + `check_all` with target_phase=S6 | At kernel level only — no phase-advance entry point |
| tests/test_runtime_delivery_gate.py (14 tests) | S6 runtime projection/dispatch gate for read/write/bash — **not the phase machine**; no phase-advance tests here | No |
| tests/test_loop_core.py, tests/deep_probe_v35.py, tests/test_deep_qa_probe.py | reference `execute_phase`/`can_transition_phase` | No |

**Conclusion**: no test anywhere drives C5 through a phase-advance entry point. Once wiring lands (section 4), the required new tests are: (a) `should_allow_phase_advance(S6)` blocks with missing/failed test/lint/build and allows with all PASS; (b) `execute_phase(S5→S6)` blocked without PASS evidence and state.yaml unchanged; (c) S4→S5 triggers C9 (post import_checker fix); (d) hub C1/C2/C6/C8 branches at phase boundaries.
