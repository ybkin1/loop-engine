# Real Project Entry Gate Template v0.1

Status: candidate repair evidence
Task: T-0010

## Purpose

Prevent method-design gates from being mistaken for permission to enter or write a real business project.

Real-project entry must be a separate explicit gate even when a method, baseline, or discovery protocol has been approved.

## Required Gate Fields

```yaml
id: G-<task-id>-REAL-PROJECT-ENTRY
task_id: <T-XXXX>
gate_type: real-project-entry
status: pending
decision: pending
target_project_root: <absolute path>
target_project_name: <name>
business_context: <short description>
entry_mode: <read-only-audit|discovery-evidence-only|design-only|implementation>
allowed_paths:
  - <explicit path under target_project_root>
forbidden_paths:
  - <explicit path or pattern>
no_write_directories:
  - <directory>
allowed_commands:
  - <read-only or scoped command>
forbidden_commands:
  - deploy
  - rollback
  - migration
  - destructive delete
  - permission change
  - secret read/write
  - payment action
  - production data action
changed_path_baseline: <evidence path>
path_audit_output: <evidence path>
verification_plan: <evidence path or bullets>
exit_gate_required: true
```

## Entry Preconditions

- User names the target project root explicitly.
- The root exists and is distinct from the governance lab unless the user says otherwise.
- The gate states whether work is read-only, design-only, or implementation.
- Allowed paths are explicit and narrower than the whole machine.
- Forbidden paths and no-write directories are explicit.
- A changed-path baseline is captured before any write-capable work.
- A path audit is captured after work.
- High-risk actions have their own separate gate.

## Changed-Path Baseline

Before write-capable work, capture:

- current root path
- timestamp
- file list or VCS status when available
- ignored/generated directories policy
- known dirty files
- user-owned changes that must not be reverted

## Path Audit

After work, record:

- changed paths
- created paths
- deleted paths
- paths intentionally left unchanged
- confirmation that all changes are under allowed paths
- confirmation that forbidden paths and no-write directories were not modified

## Exit Gate

Real-project entry ends only when an exit gate records:

- what was done
- what remains unverified
- changed-path audit
- validation/test evidence
- handoff path
- next allowed step
- whether continued real-project access is still approved

## Strict Separations

- Method repair gate does not authorize real-project entry.
- Baseline approval gate does not authorize real-project entry.
- Installation gate does not authorize real-project entry.
- Read-only real-project entry does not authorize writes.
- Design-only real-project entry does not authorize implementation.
- Implementation gate does not authorize deployment, rollback, migration, permission changes, secrets, payment actions, or production-data changes.
