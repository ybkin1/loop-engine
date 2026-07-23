# Primary, Execution, Audit, And Repair Loop Governance Design - T-0029

This is planning input only. It does not install, enable, call, or orchestrate agents or automation.

## Roles

- Primary: derives a bounded prompt from the approved task and governance snapshot.
- Execution: performs only the prompt scope and produces evidence.
- Audit: independently checks task requirements, evidence, tests, acceptance, and forbidden scope.
- Repair: addresses only enumerated audit findings.

## Required Separation

- Execution and audit contexts must be independent.
- Audit cannot approve gates or expand scope.
- Primary cannot convert audit PASS into user approval.
- Repair prompt cannot add features or new architecture unrelated to findings.
- Each cycle has a unique iteration ID and immutable input/output evidence.

## Cycle State Machine

`authorized -> execution_requested -> execution_complete -> audit_requested -> pass | repair_required -> repair_requested -> repair_complete -> audit_requested`

The cycle terminates on audit pass, user stop/change-direction, blocked evidence, budget limit explicitly set by user, or a newly required gate.

## Prompt Contract

Each generated prompt must include:

- task/gate/iteration IDs.
- exact objective and allowed paths/actions.
- forbidden scope.
- required startup validation.
- required evidence outputs.
- acceptance criteria and test commands.
- stop condition and escalation conditions.

## Audit Contract

Audit reports structured findings with severity, invariant/acceptance reference, file/evidence location, reproduction, and required repair. Verdicts are evidence only.

## Repair Contract

Primary converts only unresolved findings into a repair prompt. Closed findings cannot be reopened without new evidence. Repair cannot change gate scope.

## User Control

After current task acceptance, the primary asks whether to continue to a separately gated next task or change direction. It must not auto-create or auto-approve the next task/gate.

## Separate Gate Requirement

Any actual subagent orchestration, automation, MCP, skill, tool, hook, plugin, protocol, or runtime enablement requires a later independent explicit user gate with installation paths, permissions, failure modes, validation, and rollback.

