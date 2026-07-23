# Gate And Handoff Protocol v0.1

Status: candidate design
Task: T-0008

## Purpose

This protocol defines how user approval, evidence, and handoff should work in the repaired Loop method.

## Gate Principles

1. A gate is a user decision, not an AI conclusion.
2. Validator success is evidence only.
3. Reviewer PASS is evidence only.
4. Tests are evidence only.
5. AI recommendations are evidence only.
6. Any real-project entry, code implementation, installation, enablement, deployment, rollback, migration, permission change, secret handling, payment action, or production-data action requires a separate explicit gate.

## Gate Types

| Gate Type | Purpose | Example |
| --- | --- | --- |
| Discovery Gate | Allow AI to create discovery artifacts | approve domain model discovery |
| Design Gate | Allow AI to draft candidate design documents | approve architecture candidate design |
| Baseline Gate | Approve a design baseline as the reference for planning | approve PRD/architecture baseline |
| Implementation Gate | Allow coding inside a defined scope | approve Sprint 1 implementation |
| High-Risk Gate | Allow risky operation | approve migration, deploy, permission change |
| Installation Gate | Allow rule/runtime/tool/protocol changes | approve AGENTS.md update or tool enablement |
| Release Gate | Allow release or rollout | approve production release |
| Closeout Gate | Approve completion or archival | approve task closeout |

## Gate Record Fields

Each gate record should include:

- `id`
- `task_id`
- `gate_type`
- `status`
- `decision`
- `recorded_at`
- `scope`
- `allowed_paths`
- `allowed_actions`
- `forbidden_actions`
- `evidence`
- `notes`

For high-risk gates, add:

- risk summary
- rollback plan
- verification plan
- owner or approving user
- explicit expiry or boundary when applicable

## Gate Status

| Status | Meaning |
| --- | --- |
| pending | waiting for user approval or rejection |
| approved | user explicitly approved the gate |
| rejected | user explicitly rejected the gate |
| superseded | later gate replaced it |
| completed | gate work finished and evidence is recorded |

## Handoff Rules

`HANDOFF.md` should stay short and operational. It should contain:

- current phase and current task
- allowed scope
- forbidden scope
- recent changes
- verified items
- unverified items
- evidence location
- integration impact
- pending gates and blockers
- next session first step
- copyable startup prompt

Stable decisions should go to stable memory files only when allowed by the active gate. T-0008 does not update stable decision memory because the approved scope did not include `DECISIONS.md`.

## Resume Protocol

At the start of a governed session:

1. Read the latest user request.
2. Confirm project root.
3. Read `.ai/state.yaml`, `.ai/HANDOFF.md`, and the current task file.
4. Read `.ai/gates.yaml` and `.ai/task_graph.yaml` when task state or gate scope matters.
5. Run `validate_state.py`.
6. If pending gates exist, stop and ask the user to approve or reject.
7. Continue only inside approved task and gate scope.

## Evidence Protocol

Each task should keep evidence under `.ai/evidence/<task-id>/`.

Evidence should record:

- user gate text
- scope and forbidden scope
- commands and validation output
- generated artifacts
- review findings
- repair history
- boundary checks

## Handoff Anti-Patterns

Avoid:

- using handoff as the only project memory
- burying pending gate decisions in long prose
- omitting forbidden scope
- claiming work is approved because validation passed
- carrying concrete product details into a method-level session when they are only test cases

## T-0008 Boundary

This protocol is a candidate design artifact only. It does not modify the installed `AGENTS.md` file and does not change runtime behavior.
