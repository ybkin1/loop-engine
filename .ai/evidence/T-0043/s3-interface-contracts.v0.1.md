# S3 Interface Contract Design

## Role: Module-Architect
## Verdict: PASS

## Core Package Interfaces

### core/state_machine -> all
- Phase enum (S0-S11), GateStatus, TaskStatus
- can_transition_phase(current, target) -> StateValidationResult
- can_approve_gate(status, verdicts, required_roles) -> StateValidationResult
- check_phase_constraints(phase, approved_ids, ...) -> StateValidationResult
- phase_needs_user_gate(phase) -> bool
- init_project(root, name) -> dict

### core/hard_constraints -> hooks
- HardConstraints.check_all(context) -> ConstraintCheckResult
- ConstraintID enum (C1-C11), Severity (BLOCKER/WARNING)
- EvidenceEnvelope (evidence_id, content_hash, TTL)

### core/enforcement_hub -> hooks
- EnforcementHub(project_root).should_allow_write(path, allowed) -> EnforcementDecision
- EnforcementHub.should_allow_phase_advance(phase) -> EnforcementDecision
- quick_check(project_root) -> EnforcementDecision

### runtime/codex_adapter -> core/contracts
- CodexAdapter implements HostAdapter ABC
- read_file, write_file, execute, launch_agent
- load_state, save_state, load_gates, load_tasks
- freeze_evidence, check_evidence_freshness

### planning/intent_router -> runtime, cli
- IntentRouter.analyze(description, context) -> IntentAnalysis
- IntentRouter.should_escalate(analysis) -> (bool, str)
- ChangeType enum, complexity scoring

### evidence/evidence_chain -> governance
- EvidenceEnvelope.wrap(content, path, parent, ttl)
- EvidenceChain with verify_chain(), detect_broken_links()

### governance/validate_state -> AGENTS.md
- Main entry: python codex_loop/governance/validate_state.py <root>
- Output: [loop-governance] phase, task, [ok] or [error]

## Error Handling Contract

All governance operations use fail-closed:
- Corrupt state.yaml -> BLOCKED, return exit 2
- Missing required files -> GovernanceError with code
- Invalid YAML -> PROJECT_CONTINUITY_INVALID

## Versioning

Schema versions: state=1, gates=1, task_graph=1
Continuity: ProjectContinuity/v1, PCC-2026-07-16-R1
