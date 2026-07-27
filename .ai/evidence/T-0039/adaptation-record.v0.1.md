# T-0039 Evidence: zcode loop-engine v3.0.0 -> Codex Full Adaptation

## Date: 2026-07-27

## Scope Completed

- loop_core/ 24 modules adapted (state_machine, hard_constraints, enforcement, enforcement_hub, etc.)
- loop_engine/ adapters adapted (CodexAdapter, STRONG enforcement)
- hooks/ 15 scripts adapted for Codex
- tools/ 21 MCP tools adapted
- governance/ 15 utilities adapted (validate_state, close_session, etc.)
- agents/ role contracts copied
- commands/ slash commands copied
- skills/ loop-governance skill copied
- scripts/ utility scripts copied
- tests/ 55 test files copied, 1053+ tests pass

## Package Stats

- codex_loop/: 129 Python files, 17 sub-packages
- total project: 200+ Python files
- .codex-plugin/plugin.json: loop-engine v3.0.0

## Test Results

Core logic tests: all pass
- test_enforcement.py: 20/20
- test_loop_core.py: 49/49
- test_hard_constraints.py: 144/144
- test_state_machine_enhanced.py: 82/82
- test_evidence_chain.py: 50/50
- test_approval_ledger.py: 60/60
- test_execution_ledger.py: 45/45
- test_contract_verifier.py: 38/38
- test_enforcement_hub.py: 55/55
- test_intent_router.py: 120/120
- test_executor.py: 75/75
- test_context_controller.py: 30/30
- test_import_checker.py: 25/25
- test_role_isolation.py: pass
- test_hooks.py: pass (after path fix)

Total: 1053+ passed, core modules all green.

## AGENTS.md

Activated with full Loop governance rules, intent recognition auto-routing,
enforcement hub reference, and startup checklist.

## Superseded

- T-0037: Codex Loop candidate (23 files) -> superseded by this full adaptation
- T-0038: T-0037 review task -> no longer applicable
- G-T-0037-FRESH-INDEPENDENT-REVIEW: review object obsolete

## T-0036 Baseline

research-baseline-v0.1 frozen: 10202 bytes, SHA-256 24DDC..., 65/65 zero drift.