# Phase-Advance Gate Matrix — Trigger/Allow Tests (T-0085 AC-04)

| | |
|---|---|
| **Task** | T-0085 — AC-04 constraint coverage matrix through phase-advance entry points |
| **Role** | test-engineer |
| **Date** | 2026-07-31 |
| **Test file** | `tests/test_constraint_phase_advance.py` (21 tests: 20 passed, 1 xfail-documented) |
| **Entry points** | `EnforcementHub.should_allow_phase_advance(target_phase)` (hub, full disk context via `_build_context`) + `PhaseExecutor.execute_phase` smoke (T-0085 AC-02 wiring, executor.py Step 6b) |
| **Regression** | `tests/test_hard_constraints.py` + `tests/test_import_checker.py` + `tests/test_enforcement_hub.py`: **156 passed**; `tests/test_executor.py`: **33 passed** (developer wiring did not break existing executor tests) |

## 1. Per-constraint results through the phase-advance gate

| Constraint | Boundary tested | TRIGGER (violated → BLOCKED) | ALLOW (satisfied → allowed) | Verdict |
|---|---|---|---|---|
| C1-no-requirements | S1 → S2 | `test_trigger_blocked_without_approved_s1_gate` PASS — no approved S1 gate → blocked, C1 violation present | `test_allow_with_approved_s1_gate` PASS — S1+S2 gates approved → allowed | **VERIFIED** |
| C2-no-architecture | S2 → S3 | `test_trigger_blocked_without_approved_s2_gate` PASS — no approved S2 gate → blocked, C2 violation present | `test_allow_with_approved_s2_gate` PASS — S1+S2 gates approved → allowed | **VERIFIED** |
| C5-no-verification | S5 → S6 | `test_trigger_blocked_without_quality_results` + `test_trigger_blocked_with_failed_quality_results` PASS — absent / lint=FAIL quality evidence → blocked, C5 violation present | `test_allow_with_all_pass_quality_results` PASS (was xfail-pinned to the §3 hub defect — fixed, see §7); `test_pass_evidence_clears_c5_kernel_and_phase_table` PASS pins the fixed behavior | **VERIFIED** (fix: §7) |
| C6-no-independent-review | S4 → S5 | `test_trigger_blocked_without_review_evidence` PASS — no independent-reviewer evidence → blocked, C6 violation present. Also pinned: submitted FAIL verdict is WARNING-only, not a blocker (`test_non_pass_review_verdict_is_warning_not_blocker` PASS) | `test_allow_with_review_evidence` PASS — review PASS + compile PASS → allowed | **VERIFIED** |
| C8-stale-evidence | S2 → S3 | `test_trigger_blocked_with_expired_evidence` + `test_trigger_blocked_with_changed_evidence_hash` PASS — expired envelope / mismatched content hash → blocked, C8 violation present | `test_allow_with_fresh_evidence` PASS — unexpired envelope (hash-decoupled evidence_id) → allowed | **VERIFIED** (see §4 hash quirk) |
| C9-import-not-declared | S4 → S5 | `test_trigger_blocked_with_undeclared_import` PASS — `import requests` undeclared in requirements.txt → blocked, C9 violation present (fires in both the hub's explicit S4→S5 branch and `check_all`) | `test_allow_with_clean_imports` + `test_allow_with_declared_dependency` PASS — stdlib-only / declared dep → allowed | **VERIFIED** |
| C10-contract-test-missing | n/a at hub level | — | — | **NOT_VERIFIED** — dead at hub level (§2) |
| C11-task-file-limit | n/a at hub level | — | — | **NOT_VERIFIED** — dead at hub level (§2) |

## 2. C10/C11 — NOT_VERIFIED (dead at hub level, probe-pinned)

`EnforcementHub._build_context` (enforcement_hub.py:333-354) never sets `task_id`, and `HardConstraints.check_all` gates both C10 and C11 on `root is not None and task_id is not None` (hard_constraints.py:287-306). Therefore neither check can run in `should_allow_phase_advance` regardless of what a fixture project contains.

`test_c10_c11_not_active_at_hub_level` (PASS) pins this: a fixture with a contract file listing required tests (C10 trigger conditions) and a task with 20 allowed paths > default `max_files=10` (C11 trigger conditions) produces **zero** C10/C11 violations through the gate — the advance is allowed. This probe must be replaced with real trigger/allow tests the moment the hub context fix (task_id) lands.

## 3. C5 ALLOW — NOT_VERIFIED: hub defect found (do not ship as-is)

`EnforcementHub.should_allow_phase_advance` calls `check_phase_constraints(target_phase, approved, task_has_active=ha, compile_passed=compile_ok, user_gate_approved=...)` (enforcement_hub.py:538-540) **without forwarding `verification_passed`**. The phase-constraint table entry `C5-no-verification` for S6 (state_machine.py:417-420) therefore evaluates `verification_passed=False` **always**, so S5→S6 is blocked by a C7-mapped phase-constraint error even when `.ai/evidence/*/quality/quality_report.json` shows test/lint/build all PASS.

Proof pinned by `test_pass_evidence_satisfies_c5_kernel_but_phase_table_blocks` (PASS): with all-PASS quality evidence the decision contains **no C5 violation from the kernel check** (`check_all` is satisfied) yet `allowed=False` with `"C5-no-verification"` in the reason from the phase table. `test_allow_with_all_pass_quality_results` is marked xfail (non-strict) with this exact reason; it flips to XPASS when the hub forwards `verification_passed` — that is the signal to flip this row to VERIFIED.

Impact: with the T-0085 AC-02 wiring live, `execute_phase` will refuse every S5→S6 advance (fail-closed) until this hub gap is fixed. Note also that S6 requires an explicit user gate (`USER_GATE_PHASES`); the allow fixture supplies it (state.yaml `current_gate_id` → approved `gate_type: user-delivery`, `approval_actor: user`), so the user-gate requirement alone is not the blocker.

## 4. C8 hash-freshness quirk (observed, not a test failure)

`EnforcementHub._compute_evidence_hashes` (enforcement_hub.py:420-434) hashes the **envelope file itself** keyed by the evidence **directory name**, while the envelope's recorded `content_hash` is compared against it only when `evidence_id == dir name` (enforcement_hub.py:830). A recorded `content_hash` can therefore never equal the hash of the file that contains it — any envelope whose `evidence_id` equals its directory name is automatically "hash-stale". In practice only the expiry branch is usable for on-disk envelopes; the allow test uses an expiry-fresh envelope with an `evidence_id` decoupled from the dir name (the only hash-clean form the current hub supports). Worth a follow-up fix in the hub (hash the evidence artifact, not the envelope file).

## 5. execute_phase smoke results (real entry point, AC-02 wiring)

| Test | Result |
|---|---|
| `test_blocked_advance_does_not_persist_state` — S1→S2 without approved S1 gate → plan `BLOCKED` with `phase-advance-gate` step; `.ai/state.yaml` stays `S1-requirements` (no persist) | PASS |
| `test_allowed_advance_persists_state` — S1→S2 with gates approved → plan `COMPLETE`; `.ai/state.yaml` advances to `S2-architecture` | PASS |
| `test_gate_skipped_in_fixture_mode` — `fixture_mode=True` (TEST-ONLY harness) skips the gate; violating advance proceeds and persists | PASS |

The gate lives at executor.py Step 6b, runs after role execution and **before** `persist_state`, is skipped only for `fixture_mode`/`reentry`, and is fail-closed on gate evaluation errors (T-0083 semantics).

## 6. Coverage gaps closed by this file (vs coverage-inventory.md)

- C1/C2/C5/C6/C8: first trigger/allow tests through any phase-advance entry point (inventory §4.1 said "MISSING").
- C9: first S4→S5 hub-level trigger/allow tests (inventory: "S4→S5 branch never tested at hub level").
- C5: first test with `quality_results` set driving the C5 branch at hub level — surfaced the `verification_passed` wiring gap.
- C10/C11: confirmed and probe-pinned as inactive at hub level (NOT_VERIFIED, not faked).

## 7. C5 hub defect fix (developer, 2026-07-31) — supersedes §3

**Root cause.** `EnforcementHub.should_allow_phase_advance` (loop_core/enforcement_hub.py:545-549 pre-fix) called
`check_phase_constraints(target_phase, approved, task_has_active=ha, compile_passed=compile_ok,
user_gate_approved=...)` **without forwarding `verification_passed`**. `check_phase_constraints` defaults
`verification_passed=False` (fail-closed), so the S6 phase-constraint table entry `C5-no-verification`
(state_machine.py:419-421, evaluated at state_machine.py:557-558) always evaluated False — every S5→S6 advance
was refused (mapped to a C7 blocker violation) even when `.ai/evidence/*/quality/quality_report.json` showed
test/lint/build all PASS. The C5 kernel check (`HardConstraints.check_c5_verification`, hard_constraints.py:544)
was unaffected and passes with PASS evidence — only the phase-table path was broken.

**Fix.** `should_allow_phase_advance` now derives `verification_passed` from the `quality_results` the hub
already builds (`_build_context` → `_load_quality_results`, which reads `evidence/*/quality/quality_report.json`
check statuses and uppercases them) and forwards it to `check_phase_constraints`
(enforcement_hub.py:537, 545-547, 557):

```python
qr = ctx.get("quality_results", {})
verification_passed = all(qr.get(cn) == "PASS" for cn in ("test", "lint", "build"))
...
pc = check_phase_constraints(target_phase, approved, task_has_active=ha,
                              compile_passed=compile_ok,
                              verification_passed=verification_passed,
                              user_gate_approved=user_gate_approved)
```

This mirrors the kernel semantics of `check_c5_verification` (hard_constraints.py:570: required checks
`["test", "lint", "build"]`, each must equal `"PASS"`): **absent evidence → False → blocked; FAIL →
False → blocked; all PASS → True → allowed**. Fail-closed semantics preserved — no constraint weakened.

**Before vs after.**

| Scenario | Before fix | After fix |
|---|---|---|
| S5→S6, no quality_report.json (absent evidence) | BLOCKED (C5 phase table) | BLOCKED (C5 phase table) — unchanged |
| S5→S6, test/lint/build with lint=FAIL | BLOCKED (C5) | BLOCKED (C5) — unchanged |
| S5→S6, test/lint/build all PASS | **BLOCKED** (`"C5-no-verification"` phase-table error despite PASS evidence) — every real advance refused | **ALLOWED** — C5 satisfied in kernel and phase table |
| S5→S6, all PASS but no user gate | BLOCKED (user gate) | BLOCKED (user gate) — unchanged |

**Test results.**

- `tests/test_constraint_phase_advance.py`: **21 passed, 0 xfailed** (was 20 passed + 1 xfail). The pinned
  xfail `test_allow_with_all_pass_quality_results` now PASSES (xfail marker removed); the fail-closed triggers
  `test_trigger_blocked_without_quality_results` / `test_trigger_blocked_with_failed_quality_results` still
  PASS (absent / lint=FAIL evidence still blocks). The defect canary
  `test_pass_evidence_satisfies_c5_kernel_but_phase_table_blocks` (which its own docstring said would break
  when the hub was fixed) was flipped to `test_pass_evidence_clears_c5_kernel_and_phase_table`, now pinning the
  fixed behavior: `allowed=True`, `"C5-no-verification"` absent from the reason, no C7-mapped block.
- Regression: `tests/test_enforcement_hub.py` + `tests/test_executor.py` + `tests/test_hard_constraints.py`:
  **162 passed, 0 failed**; `tests/test_state_machine_enhanced.py` + `tests/test_loop_core.py`:
  **92 passed, 0 failed**.

**Matrix flip.** The C5-no-verification ALLOW row (§1) is now **VERIFIED** through the hub gate. §3 documents
the defect as found; this section records its resolution.
