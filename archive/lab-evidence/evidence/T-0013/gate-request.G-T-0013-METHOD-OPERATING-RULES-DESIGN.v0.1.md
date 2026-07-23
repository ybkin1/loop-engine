# Gate Request: G-T-0013-METHOD-OPERATING-RULES-DESIGN v0.1

Status: pending user decision
Task: T-0013
Requested at: 2026-07-08T13:49:48+08:00
Requested by: AI
Approval required from: user

## Purpose

Ask the user whether to accept the T-0013 Method Operating Rules / Installation Design package as a candidate basis for a later separately gated installation or rule-change task.

This gate request does not install, enable, activate, or apply the baseline-approved method.

## Proposed Gate Record

```yaml
id: G-T-0013-METHOD-OPERATING-RULES-DESIGN
task_id: T-0013
gate_type: installation-operating-rules-design-only
requested_lifecycle_transition:
  artifact_id: loop-engineering-method.operating-rules-design
  from: null
  to: candidate
status: pending
decision: pending
requested_at: "2026-07-08T13:49:48+08:00"
requested_by: ai
approval_required_from: user
scope: decide whether to accept the T-0013 operating-rules design package as a candidate for later separately gated installation/rule-change work
allowed_paths:
  - .ai/tasks/T-0013.md
  - .ai/evidence/T-0013/
  - .ai/state.yaml
  - .ai/task_graph.yaml
  - .ai/gates.yaml
  - .ai/PROGRESS.md
  - .ai/HANDOFF.md
allowed_actions:
  - read AGENTS.md and current .ai governance context
  - read T-0008, T-0009, T-0010, T-0011, and T-0012 method evidence
  - create T-0013 task and evidence
  - create a candidate operating-rules design package
  - create an AGENTS.md candidate change draft as evidence only
  - create a user decision packet
  - create read-only subagent review evidence
  - record this gate as pending
  - update .ai state, task graph, gates, PROGRESS, and HANDOFF for the pending user decision
  - run validate_state.py and stop on the pending gate
forbidden_actions:
  - approve this gate without explicit user approval
  - treat this pending gate as approval
  - install or enable the repaired Loop engineering method
  - modify AGENTS.md
  - change global or project runtime behavior
  - enter a real business project root
  - create or modify real business project files
  - write business project code
  - implement
  - build
  - deploy
  - release
  - roll back
  - install or enable skill, MCP, agent, automation, protocol, or tool behavior
  - change databases, permissions, secrets, payment systems, production data, or migrations
  - treat reviewer PASS, validator success, tests, AI recommendation, T-0011 review, or T-0012 baseline approval as installation, activation, runtime behavior, or real-project application approval
high_risk_flags:
  deployment: false
  rollback: false
  database: false
  permission: false
  secret: false
  payment: false
  production_data: false
  migration: false
  runtime_behavior: false
evidence_required:
  - .ai/evidence/T-0013/commands.md
  - .ai/evidence/T-0013/gate-request.G-T-0013-METHOD-OPERATING-RULES-DESIGN.v0.1.md
  - .ai/evidence/T-0013/user-decision-packet.method-operating-rules-design.v0.1.md
  - .ai/evidence/T-0013/operating-rules-design.candidate.v0.1.md
  - .ai/evidence/T-0013/lifecycle-boundary-review.v0.1.md
  - .ai/evidence/T-0013/risk-and-forbidden-scope-review.v0.1.md
validation_required:
  - validate_state.py must report the pending gate blocker after gate registration
exit_criteria:
  - user explicitly approves, rejects, or requests repair of this design gate
  - no installation, runtime behavior change, AGENTS.md modification, or real-project application occurs during T-0013
```

## What Approval Would Mean

Approval would mean:

- the user accepts the T-0013 operating-rules design package as a candidate basis for future work
- a later task may use it to prepare a separate installation/rule-change gate
- the design package may be referenced as evidence in that later task

Approval would not mean:

- the method is installed
- the method is enabled
- `AGENTS.md` may be modified immediately
- runtime behavior changes
- a real project may be entered or modified
- any implementation, build, deployment, release, rollback, database, permission, secret, payment, production-data, or migration action is authorized

## User Decision Needed

The user must explicitly approve, reject, or request repair of:

```text
G-T-0013-METHOD-OPERATING-RULES-DESIGN
```

Until then, this gate remains pending and blocks further governed work.
