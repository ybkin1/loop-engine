# T-0006 Commands And Validation Evidence

Status: evidence
Task: T-0006
Recorded at: 2026-07-07T14:22:05+08:00
Scope: real product delivery entry design only

## User Gate

The user explicitly approved creating T-0006:

```text
真实产品交付入口设计 / first product discovery protocol / real-project application candidate
```

Goal:

- design how Codex helps a user without coding or project-management background move from a rough product idea into real software delivery
- cover requirement clarification, product definition, acceptance criteria, technical approach, implementation planning, verification, review, handoff, and iteration entry

Allowed scope:

- create T-0006 task and evidence
- update `.ai/state.yaml`
- update `.ai/task_graph.yaml`
- update `.ai/gates.yaml`
- update `.ai/PROGRESS.md`
- update `.ai/HANDOFF.md`
- produce T-0006 design content

Forbidden scope:

- do not enter a real business project
- do not create or modify real business project files
- do not modify `AGENTS.md`
- do not install or enable skill/MCP/agent/automation/protocol
- do not deploy or roll back
- do not touch database, permission, secret, payment, production data, or migration resources

## Pre-T-0006 Validation

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0005
[ok] state is usable
```

## Planned Updates

- Create `.ai/tasks/T-0006.md`.
- Create `.ai/evidence/T-0006/commands.md`.
- Create `.ai/evidence/T-0006/real-product-delivery-entry-design.v0.1.md`.
- Update `.ai/state.yaml` to `current_task_id: T-0006`.
- Add T-0006 to `.ai/task_graph.yaml`.
- Record `G-T-0006-DESIGN-REAL-PRODUCT-ENTRY` in `.ai/gates.yaml`.
- Update `.ai/PROGRESS.md`.
- Update `.ai/HANDOFF.md`.

## Boundary Notes

- T-0006 is a design task only.
- No real business project was entered by this task.
- No real business project files were created or modified by this task.
- `AGENTS.md` is not modified by this task.
- No skill, MCP, agent, automation, or protocol behavior is installed or enabled by this task.
- No deployment, rollback, database, permission, secret, payment, production data, or migration action is authorized by this task.

## Completed Updates

- Created `.ai/tasks/T-0006.md`.
- Created `.ai/evidence/T-0006/commands.md`.
- Created `.ai/evidence/T-0006/real-product-delivery-entry-design.v0.1.md`.
- Updated `.ai/state.yaml` to `current_task_id: T-0006`.
- Added T-0006 to `.ai/task_graph.yaml`.
- Recorded `G-T-0006-DESIGN-REAL-PRODUCT-ENTRY` in `.ai/gates.yaml`.
- Updated `.ai/PROGRESS.md`.
- Updated `.ai/HANDOFF.md`.

## Post-T-0006 Validation

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0006
[ok] state is usable
```

## Post-T-0006 Handoff Audit

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0006
```

## Boundary Checks

```text
AGENTS.md SHA256 DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87
.ai/evidence/T-0006/real-product-delivery-entry-design.v0.1.md exists: True
.ai/tasks/T-0006.md exists: True
```

No real business project was entered.
No real business project files were created or modified.
No skill, MCP, agent, automation, or protocol behavior was installed or enabled.
No deployment, rollback, database, permission, secret, payment, production data, or migration action occurred.

## Repair Gate G-T-0006-REPAIR-CANDIDATE-AND-MEMORY

Recorded at: 2026-07-07T14:55:17+08:00

The user explicitly approved repairing T-0006 candidate and stale memory only.

Allowed scope:

- update `.ai/evidence/T-0006/real-product-delivery-entry-design.v0.1.md` Required Artifacts list to include the nine-stage artifacts
- update `.ai/CONTRACTS.md` stale T-0005/T-0006 wording
- update `.ai/KNOWN_ISSUES.md` stale T-0005/T-0006 wording
- update `.ai/DECISIONS.md` current decision state
- update `.ai/evidence/T-0006/commands.md`
- update `.ai/gates.yaml`
- update `.ai/PROGRESS.md`
- update `.ai/HANDOFF.md`
- run `validate_state.py`
- run `audit_handoff.py`

Forbidden scope:

- do not modify `AGENTS.md`
- do not enter a real business project
- do not create real business project files
- do not create T-0007
- do not install or enable skill/MCP/agent/automation/protocol
- do not deploy or roll back
- do not touch database, permission, secret, payment, production data, or migration resources
- do not mark T-0006 approved or active beyond candidate design

## Pre-Repair Validation

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0006
[ok] state is usable
```

## Repair Updates

- Repaired `real-product-delivery-entry-design.v0.1.md` Required Artifacts list to include `discovery-q-and-a.v0.1.md`, `build-gate-request.v0.1.md`, `verification-evidence.md`, `review-report.md`, and `iteration-decision.v0.1.md`.
- Updated `.ai/CONTRACTS.md` to remove the stale statement that T-0005 closeout must rerun before T-0006 can begin.
- Updated `.ai/KNOWN_ISSUES.md` to remove the stale statement that T-0005 closeout must rerun before T-0006 can begin.
- Updated `.ai/DECISIONS.md` to record current T-0005 installation, T-0005 closeout pass, T-0006 candidate creation, and this repair gate.
- Recorded `G-T-0006-REPAIR-CANDIDATE-AND-MEMORY` in `.ai/gates.yaml`.
- Updated `.ai/PROGRESS.md` and `.ai/HANDOFF.md`.

## Post-Repair Validation

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0006
[ok] state is usable
```

## Post-Repair Handoff Audit

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0006
```

## Post-Repair Boundary Checks

- `AGENTS.md` SHA256 remains `DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87`.
- `.ai/tasks/T-0007.md` exists: `False`.
- T-0006 remains candidate design only.
- No real business project was entered.
- No real business project files were created or modified.
- No skill, MCP, agent, automation, or protocol behavior was installed or enabled.
- No deployment, rollback, database, permission, secret, payment, production data, or migration action occurred.
- Historical T-0005 evidence remains unchanged; stale current-memory wording was repaired in T-0006 candidate, `CONTRACTS.md`, `KNOWN_ISSUES.md`, `DECISIONS.md`, `gates.yaml`, `PROGRESS.md`, and `HANDOFF.md`.
