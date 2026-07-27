# S1 Requirements Baseline -- Loop Engineering System

## Role: Product-Manager
## Verdict: PASS
## Summary

The Loop engineering system (loop-engine-lab) is a governance plugin adapted from
zcode loop-engine v3.0.0 for Codex. It provides AI-driven software delivery
governance with role collaboration, quality gates, evidence chains, and a 12-phase
state machine. S1 requirements baseline documents what the system must do to be
complete and ready for real project use.

---

## 1. User Profiles

### UP-1: Non-Technical User
- No coding ability
- No project management background
- Works exclusively through Codex AI agent
- Needs: clear gate decisions, readable deliverables, automatic routing

### UP-2: Solo Developer with AI
- Some coding ability
- Uses AI as primary development tool
- Needs: flexible governance, minimal ceremony for simple tasks, full rigor for complex ones

### UP-3: AI Agent (Codex)
- The system's primary operator
- Needs: deterministic startup rules, fail-closed enforcement, clear task boundaries

---

## 2. Functional Requirements

### FR-A: Governance Core (COMPLETED)
- FR-A01: 12-phase state machine with transition validation
- FR-A02: Gate lifecycle (pending/approved/rejected/blocked)
- FR-A03: Phase constraints (C0-C12) with blocker/warning severity
- FR-A04: Reentry support for iteration (bug_fix/feature_add/refactor/requirement_change/quality_fix)
- FR-A05: Role isolation checks (self-review detection, cross-domain review)

### FR-B: Enforcement (COMPLETED)
- FR-B01: 11 hard constraints (C1: requirements baseline, C2: architecture baseline, C3: task package, C4: path scope, C5: verification, C6: independent review, C7: blocker check, C8: evidence freshness, C9: import validity, C10: contract test coverage, C11: file limit)
- FR-B02: EnforcementLevel (STRONG/MEDIUM/ADVISORY) with fail-closed behavior
- FR-B03: EnforcementHub bridge (Hook<->Core governance decisions)

### FR-C: Evidence Layer (COMPLETED)
- FR-C01: Causal evidence chain with TTL expiration
- FR-C02: Approval ledger (immutable approval records)
- FR-C03: Execution ledger (execution tracking with chain hash)
- FR-C04: Audit ledger (comprehensive audit trail)

### FR-D: Planning and Routing (COMPLETED)
- FR-D01: Intent analysis via NLP keyword detection
- FR-D02: Risk factor extraction and complexity scoring
- FR-D03: Loop mode recommendation (LIGHTWEIGHT/STANDARD/FULL)
- FR-D04: Phase profile generation per mode

### FR-E: Codex Integration (PENDING -- T-0041 scope)
- FR-E01: AGENTS.md startup rules activate Loop governance on session start
- FR-E02: Intent recognition triggers automatic Loop mode selection
- FR-E03: validate_state.py blocks progress on pending gates
- FR-E04: Gate guard blocks writes during pending gate state

### FR-F: Deep Codex Integration (FUTURE -- T-0042+)
- FR-F01: executor/agent_adapter connect to Codex multi_agent_v1_spawn_agent
- FR-F02: MCP tools (21) register as Codex MCP server endpoints
- FR-F03: Hook scripts run in Codex session context (not ZCode subprocess)
- FR-F04: Project initialization (init_project) works via Codex CLI

### FR-G: Real Project Support (FUTURE)
- FR-G01: Real project entry gate with user approval
- FR-G02: Project profile persistence across sessions
- FR-G03: Multi-session handoff continuity

### FR-H: Documentation and Usability (PENDING)
- FR-H01: AGENTS.md contains complete startup procedure
- FR-H02: Non-technical user can understand gate decisions
- FR-H03: Human Review Packet readable by non-developers

---

## 3. Non-Functional Requirements

### NFR-P: Performance
- NFR-P01: validate_state.py completes within 10 seconds on 200-file project
- NFR-P02: Hook scripts complete within 5 seconds (ZCode PreToolUse timeout)
- NFR-P03: intent_router.analyze() completes within 1 second

### NFR-S: Security
- NFR-S01: No hardcoded secrets, API keys, or tokens in codebase
- NFR-S02: Fail-closed: governance state corruption blocks all writes
- NFR-S03: Protected paths (AGENTS.md, stable/) require explicit user confirmation
- NFR-S04: Import checker (C9) detects undeclared third-party dependencies

### NFR-R: Reliability
- NFR-R01: Test coverage: 1053+ tests pass, core logic 100% green
- NFR-R02: Atomic YAML writes prevent corruption (tmp + os.replace)
- NFR-R03: Continuity manifest detects source drift across sessions
- NFR-R04: No silent data loss: all state changes are evidence-tracked

### NFR-M: Maintainability
- NFR-M01: All modules have clear docstrings
- NFR-M02: Import paths follow codex_loop.* package convention
- NFR-M03: Governance files (.ai/*) in structured YAML format
- NFR-M04: 17 sub-packages with clear responsibility boundaries

---

## 4. Acceptance Criteria

### AC-S1: S1 Gate Completion
- AC-S1-01: FR-A through FR-E requirements documented
- AC-S1-02: NFR-P through NFR-M documented with measurable criteria
- AC-S1-03: Exclusions explicitly listed
- AC-S1-04: User approves S1 gate

### AC-S1-05: validate_state passes clean
- AC-S1-06: No pending gates in system
- AC-S1-07: All tasks T-0001..T-0041 are completed or active with clear status

---

## 5. Exclusions

### EX-01: Not in S1 scope
- Real project entry (requires separate gate in S4+)
- Codex MCP tool registration (T-0042+)
- executor/agent_adapter deep adaptation (T-0042+)
- Global Codex installation (requires separate gate)
- Deployment to production (forbidden)
- Database, payment, secret, production data operations (forbidden)

### EX-02: Not in current iteration
- zcode sync/update (one-way adaptation only)
- Multi-user collaboration support
- Web UI or dashboard
- Performance benchmarking beyond basic timing

---

## 6. Evidence

- .ai/evidence/T-0041/s1-requirements-baseline.v0.1.md (this document)
- validate_state.py: [ok] state is usable
- Test suite: 1053+ passed, core modules all green
