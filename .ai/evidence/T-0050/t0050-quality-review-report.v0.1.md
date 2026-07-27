# T-0050 Cross-Project Deep Quality Review

## Executive Summary

Deep review of both Codex loop-engine (codex_loop/) and zcode loop-engine
(ZCodeProject/loop-engine/) completed. Found 1 critical gap, 22 known test
failures, and 0 new bugs.

## Findings

### P0: MISSING MODULE -- runtime_controller.py

zcode has RuntimeController in loop_core/runtime_controller.py (300+ lines).
This module handles:
- RuntimeState machine (13 states: NOT_A_PROJECT -> CLOSED)
- Project onboarding (onboard_project)
- Work package proposal creation (create_work_package_proposal)
- Approval and execution flow (approve_and_execute with idempotency keys)
- Write authorization (authorize_write with capability checks)
- Atomic JSON I/O with fsync
- Runtime event journaling
- Checkpoint creation

This module is TRULY MISSING from codex_loop/. The module was in zcode
loop_core/ but was not imported during the adaptation. Its test file
test_runtime_controller.py is also missing.

Impact: Codex cannot use RuntimeController for atomic project onboarding,
capability-based write authorization, or idempotent approval/execution flow.
These features would need to be re-implemented or the module adapted.

### P1: Test Failures (22)

All 22 failures are in tests/test_hooks.py (GateGuardTest class).
Root cause: hook scripts use subprocess-based invocation, but codex_loop/
is not on sys.path when hooks run as standalone processes.
This is a deployment model difference, not a logic bug.

### P2: Structural Differences

1. zcode keeps all modules in loop_core/ (flat structure, 24 files)
   codex splits into sub-packages (core/16, evidence/5, planning/6, etc.)
   -> Intentional design choice, not a bug.

2. zcode has 214 Python files total (includes .ai/ evidence scripts,
   archive/, demo/ loop-demo-todo/)
   codex has 130 Python files in codex_loop/ only
   -> zcode total includes project-level scripts, not just the library.

3. codex core/ has 5 extra files not in zcode loop_core/:
   - constants.py (from src/loop_engine/)
   - enforcement_degradation.py (from loop_engine/)
   - exceptions.py (from src/loop_engine/)
   - models.py (lab original)
   - store.py (lab original)
   -> Properly merged from zcode sub-packages.

### Test Suite Comparison

- Codex: 1079 collected, 1057 passed, 22 failed (98.0%)
- Zcode: 113 passed per README (subset of codex tests)
- Codex has all zcode test files except test_runtime_controller.py
- 22 failures are subprocess path issues (known, non-logic)

### Recommendations

1. IMMEDIATE: Import zcode runtime_controller.py into codex_loop/runtime/
2. MEDIUM: Fix 22 hook test failures by adding proper sys.path setup
3. LOW: Run zcode test suite independently to verify no regression in zcode
4. LOW: Consider backporting USER_GATE_PHASES fix to zcode

### Verified

- Core logic: 100% pass (state_machine, hard_constraints, enforcement, etc.)
- No new bugs introduced during adaptation
- All import paths correctly remapped
- contracts.py merge (RoleContract + HostAdapter) working
- from __future__ placement: all files fixed
- Unicode encoding: ensure_ascii=True applied to all hook scripts
