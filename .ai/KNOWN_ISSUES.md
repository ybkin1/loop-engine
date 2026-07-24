# Known Issues

## Open

- Bash command interception is not available via ZCode hooks. `gate_guard` blocks Write/Edit but shell commands (`echo > file`, `cp`, `mv`) can bypass. ENFORCEMENT_LEVEL: MEDIUM (honest).
- ProjectContinuity auto-generation has a timing issue: first-run always shows ACCEPTANCE.md drift because the continuity file includes itself in its source manifest.
- Seeded defects test project exists but is not automatically invoked by the mutation tester (manual verification only).
- E2E integration test (test_E2E_CURRENT_001) is skipped due to lab fixture dependency.

## Recently Closed

- 2026-07-22: Stale project memory files (CONTRACTS.md, PROGRESS.md, KNOWN_ISSUES.md, DECISIONS.md) updated to reflect current project state (T-0033).
- 2026-07-22: Phase inconsistency fixed — constants.py synced to 12 phases matching loop_core/state_machine.py.
- 2026-07-22: zcode_adapter.py docstring fixed from STRONG to MEDIUM.
- 2026-07-22: T-0022~T-0032 completed full S0~S6 lifecycle with 193 passing tests.
- 2026-07-22: Independent audit by external AI validated Loop Core architecture and identified stale memory issues (now fixed).

## Historical (pre-merge)

- 2026-07-07: T-0005 closeout rerun passed; unified-governance-architecture.v0.2.1 installed as project-local AGENTS.md.
- 2026-07-07: Placeholder content in CONTRACTS.md, ACCEPTANCE.md, KNOWN_ISSUES.md replaced under T-0004.
