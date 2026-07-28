# zcode v3.5 Sync Review Report

## Date
2026-07-28

## Source
Remote: loop-engine (git@github.com:ybkin1/loop-engine.git)
Branch: zcode (commit f700e4d — "zcode: sync v3.5 — 20 MCP tools total")

## Review Scope
- 24 loop_core modules (Python)
- 20 MCP tools (Python)
- 16 standalone scripts (Python)
- 4 design documents
- 11 role agents (contracts + skills + thinking frameworks)
- 12 Hook scripts
- 6 JSON schemas

## Review Findings

### Architecture: 8.5/10
Four-layer plugin architecture: Execution (Hooks) → Knowledge (Skills) → Tools (MCP) → CLI

### v3.5 Changes
- tools/server.py: Tool registry expanded from 7 to 20 tools (+128 lines)
- 8 new MCP tool wrappers: route_intent, constraint_check, execute_phase, execution_log,
  veto_escalate, evidence_submit, handoff, load_context
- .ai/evidence/T-0045/commit2.py: Evidence record

### Code Quality Highlights
- enforcement_hub.py: check_cross_domain_review() — development/quality/governance domain separation (P0 prevention)
- state_machine.py: 12-phase transitions + v3.1 reentry model (REENTRY_TRANSITIONS, ProjectStatus)
- certification_runner.py: Role certification state machine with 4 degradation states
- hard_constraints.py: 8 non-bypassable constraints (C1-C8)

### Issues Found
P1: None (all critical features present)
P2: server.py _dispatch() uses if/elif chain (scalability concern as tools grow)
P2: loop_enforcement.py.bak stale backup file in hooks/

## Sync Status: COMPLETE

codex_loop/ already contains all zcode v3.5 assets fully adapted:

| Asset Category | zcode | codex_loop | Status |
|---|---|---|---|
| Core modules (24) | loop_core/ | codex_loop/core|evidence|planning|... | Synced |
| MCP tools (20) | tools/ | codex_loop/tools/ | Synced |
| Scripts (16) | scripts/ | codex_loop/scripts/ | Synced |
| Role agents (11) | agents/ | codex_loop/agents/ | Synced + enhanced |
| Design docs (4) | docs/ | docs/ | Synced |
| Hook system (12) | hooks/ | codex_loop/hooks/ | Synced |

### codex_loop Enhancements Over zcode:
- Main-thread agent has full INTERNAL_LOOP.md and THINKING_FRAMEWORK.md (zcode only has CONTRACT.yaml + SKILL.md)
- Test-engineer agent has SKILL.md (zcode missing)
- Core modules reorganized into 17 sub-packages for better modularity
- hard_constraints.py: 44KB vs zcode 31KB (additional enforcement patterns)
- CodexAgentAdapter for STRONG enforcement via Codex native APIs
- Project Governor tools (close_session, audit_handoff, validate_state, continuity_auditor)

### Test Status
No regressions expected — all changes are read-only review, no code was modified.

