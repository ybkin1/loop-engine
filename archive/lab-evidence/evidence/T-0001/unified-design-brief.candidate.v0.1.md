# Unified Design Brief Candidate v0.1

Status: candidate
Approved: false
Installed: false
Write authority: docs-only inside current task evidence

## 1. Current Task

Design a unified system for:

1. Loop 工程工作模式: how Codex completes every task through a reliable loop.
2. 规范架构: what rules, context, roles, and boundaries Codex must load before acting.

The two tracks must not drift apart. The governance architecture defines the rails; loop engineering defines how work moves on those rails.

## 2. User Position

The user has no coding background and no project management background.

Codex must carry the professional burden:

- clarify rough requirements;
- detect product logic problems;
- plan the project;
- define deliverables and acceptance standards;
- implement in small verified tasks;
- review, repair, verify, and hand off;
- keep candidate, reviewed, user-approved, active, and installed states separate.

The user should only need to provide goals, answer business questions, and approve gates.

## 3. Track A: Loop Engineering Work Mode

Loop engineering answers: "How does Codex complete one task without drifting, self-certifying, or skipping verification?"

Minimum loop:

```text
Coordinator -> Task Card -> Author/Executor -> Candidate/Output -> Reviewer -> Findings -> Repair -> Verification -> Run Summary -> User Gate if needed
```

Required design topics:

- loop roles: Coordinator, Author, Reviewer, Repair, QA, Handoff, Auditor;
- task card schema;
- candidate output rules;
- review report schema;
- repair task schema;
- verification evidence requirements;
- run summary schema;
- loop stop states;
- loop iteration limit;
- user gate escalation rules.

Required loop stop states:

- PASS_RECOMMENDED
- FAIL_REPAIRABLE
- BLOCKED_MISSING_CONTEXT
- BLOCKED_AUTHORITY_CONFLICT
- NEED_USER_GATE
- LOOP_LIMIT_REACHED
- OUT_OF_SCOPE

## 4. Track B: Governance Architecture

Governance architecture answers: "What must Codex read, believe, avoid, and preserve before it starts a task?"

Required design topics:

- user-origin and mission;
- authority boundary;
- operating principles;
- phase packs;
- role briefs;
- required reading matrix;
- session contract;
- document lifecycle;
- registry;
- gate policy;
- AGENTS.md entry rules.

Recommended layers:

```text
Layer 0: Global invariants
Layer 1: Project-level norms
Layer 2: Phase-level norms
Layer 3: Role-level norms
Layer 4: Session Contract for the current task
```

Lower layers may narrow higher layers, but must not override them.

## 5. Integration Rule

Every meaningful task must start with context assembly:

```text
Intent Recognition
  -> Phase Detection
  -> Required Reading Matrix
  -> Session Contract
  -> Task Card
  -> Loop Run
```

The Session Contract is not an approved protocol. It is a temporary task-specific contract assembled from approved or candidate sources. It cannot grant permissions.

## 6. Session Contract Minimum Fields

Each non-trivial session should receive:

- session_id
- task_id
- project_phase
- task_intent
- assigned_role
- user_origin_summary
- stance
- objective
- inherited_rules
- must_read
- forbidden_sources
- forbidden_actions
- allowed_outputs
- authority_boundary
- acceptance_criteria
- review_plan
- pass_conditions
- stop_conditions
- user_gate_conditions
- expected_artifacts
- handoff_requirements

## 7. First Candidate Deliverables

The first design package should produce these candidate artifacts:

1. Project Charter Candidate
2. Loop Engineering Protocol Candidate
3. Governance Architecture Protocol Candidate
4. Required Reading Policy Candidate
5. Context Assembly Protocol Candidate
6. Session Contract Template Candidate
7. Task Card Template Candidate
8. Review Report Template Candidate
9. AGENTS.md Entry Rules Candidate
10. Review Plan Candidate

None of these are approved or installed until the user explicitly approves a promotion gate.

## 8. Review Standard

Reviewer-Auditor must fail the candidate if it:

- lets candidate content become approved automatically;
- lets reviewer PASS become user approval;
- lets task cards grant real authority;
- lets each session invent its own norms;
- lacks required reading rules;
- lacks task-level loop closure;
- lacks user gate rules;
- makes the user responsible for technical/project-management judgment;
- optimizes for documents instead of real software delivery.

Passing requires:

- no P0 findings;
- no blocking P1 findings;
- clear distinction between Loop Engineering and Governance Architecture;
- clear integration through Required Reading, Session Contract, and Task Card;
- clear next step for the user.

## 9. Immediate Next Step

Coordinator should generate the first execution task card:

```text
Task: Produce the unified governance architecture candidate package.
Mode: no-write design.
Allowed output: candidate documents only.
Reviewer: Reviewer-Auditor session.
Gate: user approval required before any promotion or installation.
```

