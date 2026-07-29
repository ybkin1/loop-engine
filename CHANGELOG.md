# Changelog

## v3.4.0 (2026-07-24) — T-0047 + T-0048: 治理硬化 + 收尾

### Fixed (T-0047)
- **FAIL-CLOSED**: `enforcement_hub.py` — corrupted/missing governance YAML now blocks writes (was: silent pass through)
- **FAIL-CLOSED**: `role_isolation.py` — state read error now returns exit 2 DENY (was: exit 0 silent pass)
- `executor.py` `_write_state()`: atomic write via `.tmp` + `os.replace()` (T-0048)

### Added (T-0047)
- `tests/test_role_isolation.py` — 8 tests (normal, self-review, corruption, fail-closed)
- `tests/test_enforcement_hub.py` — 12 fail-closed corruption tests
- Hook split modules: `_hook_state.py`, `_hook_path.py`, `_hook_config.py`, `_hook_sync.py` (T-0048)

### Completed
- T-0041: vertical slice verification (23 tests, S0→S6 trail documented)
- T-0043: role capability certification (11 roles, 23 tests)
- T-0044: Qoder improvements port (6/7 items; atomic write fixed in T-0048)
- T-0042: Loop engineering optimization (see v3.1.0)

## v3.1.0 (2026-07-23) — T-0042: Loop 工程优化

### Added
- **Change iteration**: `REENTRY_TRANSITIONS` — 5 change types: bug_fix, feature_add, refactor, requirement_change, quality_fix
- **Project lifecycle**: `ProjectStatus` enum (draft, released, maintenance)
- **Reentry validation**: `validate_reentry()` with status-aware phase admission
- **Shell tokenizer**: quote/escape-aware Bash command extraction (`_hook_bash.py`, 155 lines)
- **Bash enhancement**: detection for curl, wget, tar, pip, npm, rsync, scp, openssl
- **Deep QA probes**: 75 new probe tests covering enforcement edge cases

### Changed
- `hook_common.py`: reduced from 998 to 830 lines (Bash logic extracted to `_hook_bash.py`)
- `zcode_adapter.py`: `ENFORCEMENT_LEVEL` MEDIUM → STRONG

### Fixed
- 5 issues found and fixed via deep QA probe testing:
  1. Shell tokenizer false positives on `\binstall\b` patterns
  2. Tokenizer segmentation with nested quotes
  3. Change type detection gaps in Chinese keyword matching
  4. Negation detection in shell commands
  5. Role capability state persistence after profile reload

## v3.0.0 (2026-07-23) — T-0040: EnforcementHub + HARD 阻断

### Added
- `enforcement_hub.py` (473 lines): Hook↔Core bridge
- `EnforcementLevel` enum: HARD, PARTIAL, ADVISORY
- Role domain separation: DEVELOPMENT_ROLES, QUALITY_ROLES, GOVERNANCE_ROLES
- `tests/test_enforcement_hub.py`: 39 tests

### Changed
- `role_isolation.py` v2.0: FULL mode self-review → HARD block (exit 2)

## v2.0.0 (2026-07-23) — T-0034: Runtime Controller

### Added
- `runtime_controller.py`, `approval_record.py`, `agent_adapter.py`, `executor.py`
- `state_machine.py`: phase transition graph, gate resolution, constraint checking
- 24 agent definitions, 30+ modules

## v1.0.0 (2026-07-22) — T-0022~T-0027: Loop Engine 初始交付

### Added
- Loop Engine plugin: hooks, MCP tools, skills, commands
- 11 agent role contracts
- S0→S6 governance phase machine
- Quality gate system
- docs/: requirements, architecture, interface contract, delivery
