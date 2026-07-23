# Real Project Entry Protocol Candidate v0.1

Status: candidate
Task: T-0017

## Purpose

Define how Codex may enter a real software project without confusing method
design, discovery, architecture planning, implementation, deployment, or
high-risk operations.

This document is a candidate protocol. It is not a real-project entry approval
and does not authorize any business project file change.

## Entry Principle

Real-project entry is always a separate explicit user gate.

No approved method, baseline, review PASS, validator success, subagent result,
handoff, or candidate design may be treated as permission to enter or write a
real project.

## Entry Modes

| Mode | Meaning | Writes Allowed |
| --- | --- | --- |
| `read-only-audit` | Inspect a named project and report facts. | none |
| `discovery-evidence-only` | Create or update discovery/governance evidence. | approved `.ai` evidence paths only |
| `design-only` | Produce design artifacts for the named project. | approved design evidence paths only |
| `implementation` | Modify project code/config in a named slice. | explicit allowed paths only |

Each mode requires its own scope. A narrower mode never implies a broader mode.

## Required Gate Fields

```yaml
id: G-<task-id>-REAL-PROJECT-ENTRY
task_id: <T-XXXX>
gate_type: real-project-entry
status: pending
decision: pending_user_decision
target_project_root: <absolute path>
target_project_name: <name>
business_context: <short statement>
entry_mode: read-only-audit | discovery-evidence-only | design-only | implementation
allowed_paths:
  - <absolute or project-relative path>
forbidden_paths:
  - <path or pattern>
no_write_directories:
  - <path>
allowed_commands:
  - <command or command family>
forbidden_actions:
  - deploy
  - rollback
  - database
  - permission
  - secret
  - payment
  - production_data
  - migration
changed_path_baseline: <evidence path>
verification_plan: <evidence path or bullets>
exit_gate_required: true
```

## Startup Sequence

1. Read the latest user request.
2. Confirm the governance project root and the target real-project root.
3. Read current `.ai` state, task, gates, task graph, progress, and handoff.
4. Run deterministic validation before any real-project action.
5. Stop if a pending gate exists unless the latest user message explicitly
   approves, rejects, or requests repair of that gate.
6. Confirm the requested action matches the approved entry mode.
7. Capture changed-path baseline before any write-capable work.

## Entry Preconditions

- The target project root is explicit.
- The root is distinct from the governance lab unless the user says otherwise.
- Allowed paths are narrower than the whole machine.
- Forbidden paths and no-write directories are explicit.
- High-risk actions are listed as forbidden unless separately gated.
- The user understands discovery/design does not authorize implementation.
- If `.ai` is missing in the target project, initialization requires its own
  explicit permission.

## Exit Requirements

Real-project entry ends only after evidence records:

- what was read or changed
- changed paths and created paths
- commands and validation results
- unverified items
- boundary confirmation
- next allowed step
- whether continued access remains approved

## Non-Negotiable Separations

- Method design does not authorize real-project entry.
- Real-project entry does not authorize implementation unless mode says so.
- Implementation does not authorize build, release, deployment, rollback, or
  high-risk resource action.
- Read-only entry never authorizes writes.
- Subagents may review evidence only unless a later gate gives a specific,
  disjoint write scope.
