# S2 Architecture Baseline -- Loop Engineering System

## Role: System-Architect
## Verdict: PASS

## 1. Architecture Overview

The Loop engineering system follows a layered plugin architecture adapted
from zcode loop-engine v3.0.0. It is deployed as a Codex project-level package
(codex_loop/) with 17 sub-packages organized into 4 layers:

`
Layer 4: Interface    [cli/, commands/, skills/]
Layer 3: Execution    [runtime/, hooks/, tools/, governance/, scripts/]
Layer 2: Domain       [core/, evidence/, planning/, roles/]
Layer 1: Foundation   [context/, packets/, quality/, agents/, materials]
`

## 2. Module Decomposition (17 sub-packages)

### Foundation Layer
- materials/: Material library loader
- agents/: 11 role contract definitions
- context/: Context builder and security policy
- packets/: Functional work packets, human review packets
- quality/: Quality checks, veto escalation

### Domain Layer
- core/: State machine, hard constraints, enforcement, contracts,
  models, store, constants, exceptions, import_checker, contract_verifier,
  context_controller, enforcement_hub
- evidence/: Evidence chain, approval ledger, execution ledger, audit ledger
- planning/: Router, intent router, phases, task graph, work packets
- roles/: Role capability certification, subagent manifest, degradation

### Execution Layer
- runtime/: CodexAdapter, executor, agent adapter, runner, cost tracker
- hooks/: gate_guard, loop_enforcement, role_isolation, path_guard,
  ledger_guard, session_brief, loop_auto_activate, template_injector
- tools/: MCP tools server + 20 tool implementations
- governance/: validate_state, close_session, continuity auditor/producer,
  governor_lib, task_contract, evidence_manifest
- scripts/: install, uninstall, certification, mutation testing

### Interface Layer
- cli/: Command-line interface
- commands/: Slash commands (loop-validate, loop-verify-chain, loop-cost)
- skills/: loop-governance skill definition

## 3. Dependency Graph

core/ is the hub -- all layers depend on it, it depends on nothing internal:
  core/ -> (stdlib only: yaml, json, hashlib, pathlib, dataclasses, enum, re, ast, logging)
  evidence/ -> core/
  planning/ -> core/
  roles/ -> core/
  runtime/ -> core/, evidence/
  hooks/ -> core/, runtime/
  tools/ -> core/, evidence/
  governance/ -> core/, evidence/
  context/ -> core/
  packets/ -> core/, materials/
  quality/ -> core/
  agents/ -> (file-based contracts, no Python deps)
  cli/ -> core/, runtime/
  materials/ -> core/
  scripts/ -> core/, runtime/
  commands/ -> (document files)
  skills/ -> (document files)

## 4. Interface Contracts

### core/state_machine.py -> all modules
- Phase, GateStatus, TaskStatus enums
- can_transition_phase, can_approve_gate, can_enter_phase
- check_phase_constraints, phase_needs_user_gate
- RoleIsolationCheck, StateValidationResult

### core/hard_constraints.py -> hooks/, governance/
- HardConstraints class with check_all(context)
- ConstraintID, Severity, ConstraintViolation
- EvidenceEnvelope

### core/enforcement_hub.py -> hooks/
- EnforcementHub.should_allow_write(target, allowed_paths)
- EnforcementHub.should_allow_phase_advance(phase)
- EnforcementDecision with fail-closed behavior

### core/contracts.py -> runtime/
- HostAdapter ABC (read_file, write_file, execute, launch_agent, etc.)
- CodexAdapter implements HostAdapter for Codex

### evidence/* -> governance/, runtime/
- EvidenceEnvelope with TTL, causal chain
- ApprovalLedger, ExecutionLedger, AuditLedger

### planning/intent_router.py -> cli/, runtime/
- IntentRouter.analyze(description) -> IntentAnalysis
- LoopMode, RiskLevel, ChangeType

## 5. Data Models

### State (state.yaml)
schema_version, project_name, current_phase, current_task_id,
current_gate_id, loop_mode, notes

### Gates (gates.yaml)
gates[]: id, task_id, gate_type, status, decision, execution_status

### Tasks (task_graph.yaml)
tasks[]: id, title, status, created_at, phase

### Project Continuity (project_continuity.yaml)
schema, contract_id, project_id, source_manifest, source_sha256,
project_continuity: user_origin, product_identity, protected_decisions,
authorization_boundaries, lifecycle, evidence_index

### Evidence Envelopes
envelope_id, content_hash, created_at, ttl_days, causal_parent_hash

## 6. Security Boundaries

- Governance files (.ai/*): write-protected during pending gates
- Protected paths (AGENTS.md): require explicit user confirmation
- Agent isolation: developer != reviewer enforced by role_isolation hook
- Import validity: C9 constraint checks undeclared dependencies
- Secret detection: context/policy.py assert_no_secret_markers
- Fail-closed: corrupt governance state blocks all writes

## 7. Deployment Structure

Project-local deployment only:
  loop-engine-lab/
    AGENTS.md              <- Loop governance rules
    .codex-plugin/         <- Codex plugin manifest
    codex_loop/            <- Python package (17 sub-packages)
    tests/                 <- Test suite (55 files)
    .ai/                   <- Governance data

No global Codex installation. No system PATH modification.
