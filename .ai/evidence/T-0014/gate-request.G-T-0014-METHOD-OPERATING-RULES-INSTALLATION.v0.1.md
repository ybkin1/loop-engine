# Gate Request: G-T-0014-METHOD-OPERATING-RULES-INSTALLATION v0.1

Status: pending user decision
Task: T-0014
Requested at: 2026-07-08T15:01:30+08:00
Requested by: AI
Approval required from: user

## Purpose

Ask the user whether the prepared installation / rule-change package for the repaired Loop engineering method operating rules is acceptable.

This request prepares a future `AGENTS.md` rule-change package. T-0014 does not apply the diff, does not modify `AGENTS.md`, does not install or enable the repaired method, and does not change runtime behavior.

If the user later approves this gate, the recommended next step is to open T-0015 or a new phase to execute the exact approved package with fresh startup validation.

## Exact Future Installation Target File List

Future installation target path:

```text
AGENTS.md
```

No other target path is included. The proposed future write would change project-local `AGENTS.md` startup / operating-rule text only; it would not install or enable any plugin, skill, MCP, external agent runtime, automation, protocol service, tool behavior, business project, database, permission, secret, payment, production-data, or migration path.

## Proposed Gate Record

```yaml
id: G-T-0014-METHOD-OPERATING-RULES-INSTALLATION
task_id: T-0014
gate_type: installation-rule-change-gate-preparation
requested_lifecycle_transition:
  artifact_id: loop-engineering-method.operating-rules
  from: baseline_approved_reference_only
  to: pending_installation_decision
status: pending
decision: pending
requested_at: "2026-07-08T15:01:30+08:00"
requested_by: ai
approval_required_from: user
scope: decide whether the exact prepared AGENTS.md operating-rules package may be used by a later separate execution task
allowed_paths:
  - .ai/tasks/T-0014.md
  - .ai/evidence/T-0014/
  - .ai/state.yaml
  - .ai/task_graph.yaml
  - .ai/gates.yaml
  - .ai/PROGRESS.md
  - .ai/HANDOFF.md
proposed_future_target_paths:
  - AGENTS.md
allowed_actions:
  - read AGENTS.md and current .ai governance context
  - read T-0013 operating-rules design evidence
  - create T-0014 task and evidence records
  - create the user decision packet
  - create the proposed AGENTS.md unified diff as evidence only
  - record exact target file list and changed-path baseline
  - prepare rollback, recovery, validation, risk, lifecycle, startup verification, and failure recovery plans
  - use subagents for read-only review only
  - record this gate as pending
  - update .ai state, task graph, gates, PROGRESS, and HANDOFF for the pending user decision
  - run validate_state.py and stop on the pending gate
forbidden_actions:
  - approve this gate without explicit user approval
  - set this gate to approved during T-0014
  - treat this pending gate as approval
  - modify AGENTS.md
  - apply the proposed diff
  - install or enable the repaired Loop engineering method
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
  - treat reviewer PASS, validator success, tests, AI recommendation, subagent review, T-0012 baseline approval, or T-0013 design approval as installation or runtime authorization
high_risk_flags_for_t0014_preparation:
  deployment: false
  rollback: false
  database: false
  permission: false
  secret: false
  payment: false
  production_data: false
  migration: false
  runtime_behavior: false
high_risk_flags_if_future_installation_is_executed:
  deployment: false
  rollback: true
  database: false
  permission: false
  secret: false
  payment: false
  production_data: false
  migration: false
  runtime_behavior: true
evidence_required:
  - .ai/evidence/T-0014/commands.md
  - .ai/evidence/T-0014/gate-request.G-T-0014-METHOD-OPERATING-RULES-INSTALLATION.v0.1.md
  - .ai/evidence/T-0014/user-decision-packet.method-operating-rules-installation.v0.1.md
  - .ai/evidence/T-0014/agents-md.proposed-diff.v0.1.patch
  - .ai/evidence/T-0014/changed-path-baseline.v0.1.md
  - .ai/evidence/T-0014/rollback-recovery-plan.v0.1.md
  - .ai/evidence/T-0014/validation-plan.v0.1.md
  - .ai/evidence/T-0014/installation-risk-review.v0.1.md
  - .ai/evidence/T-0014/lifecycle-boundary-review.v0.1.md
  - .ai/evidence/T-0014/startup-behavior-verification-plan.v0.1.md
  - .ai/evidence/T-0014/failure-recovery-steps.v0.1.md
  - .ai/evidence/T-0014/subagent-review-summary.v0.1.md
validation_required:
  - validate_state.py must pass before T-0014 records the new pending gate
  - validate_state.py must report the pending gate blocker after gate registration
  - AGENTS.md hash must remain equal to the changed-path baseline during T-0014
exit_criteria:
  - T-0014 records this gate as pending
  - user explicitly approves, rejects, or requests repair
  - no installation, runtime behavior change, AGENTS.md modification, or real-project application occurs during T-0014
```

## What User Approval Would Mean

Approval would mean:

- the user accepts the T-0014 package as the exact candidate basis for a later separate execution task
- the future target path is limited to `AGENTS.md`
- the future content is limited to `.ai/evidence/T-0014/agents-md.proposed-diff.v0.1.patch`
- T-0015 or a new phase should rerun startup validation before any write

Approval would not mean:

- T-0014 may apply the diff
- any AI, reviewer, validator, test, or subagent may approve the gate
- any skill, MCP, external agent runtime, automation, protocol service, or tool behavior is enabled
- any real business project may be entered
- deployment, release, rollback, database, permission, secret, payment, production-data, or migration action is authorized

## User Decision Needed

The user must explicitly approve, reject, or request repair of:

```text
G-T-0014-METHOD-OPERATING-RULES-INSTALLATION
```

Until then, this gate remains pending and blocks further governed implementation or rule-change work.
