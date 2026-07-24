# Failure Mode And Recovery Design Candidate v0.1

Status: candidate evidence only
Task: T-0019

## Purpose

Define how future enforcement should behave when evidence, checkers, gates, or
tool restrictions fail.

## Failure Modes

| Failure | Default Handling | Recovery |
| --- | --- | --- |
| Missing gate register | Fail closed for new governed stages. | Create register under approved repair gate. |
| Missing required artifact | Block stage promotion. | Produce artifact or record approved deferral if waivable. |
| Pending user gate | Block all work beyond gate package repair/decision. | User approves, rejects, or requests repair. |
| Checker not run | Keep register item `pending`. | Run checker or create valid unavailable-checker exception. |
| Checker unavailable | Apply `on_unavailable`. | Install checker only under later enablement gate, or provide manual evidence. |
| Checker failed | Block directly bound gate. | Repair affected artifact and rerun checker. |
| Stale checker result | Block if target artifact changed after `run_at`. | Rerun checker. |
| Stale handoff | Block closeout or next startup. | Repair HANDOFF under governance-memory repair scope. |
| Forbidden scope attempted | Deny action and record policy violation. | Create separate gate if action is still desired. |
| Gate approval ambiguity | Treat as not approved. | Ask for exact gate ID approval. |
| Reviewer PASS used as approval | Deny gate transition. | Record reviewer output as evidence only and ask user. |
| Exception missing expiry | Treat exception invalid. | Add revisit/expiry or reject exception. |
| Audit detects tampering | Block task. | User intervention and repair evidence required. |

## Unavailable Checker Policies

| Checker Class | Default |
| --- | --- |
| Security, secret, permission, production-data | `fail_closed` |
| Database, migration, deployment, rollback | `fail_closed` |
| Artifact schema, traceability, handoff | `manual_evidence` when automation is unavailable |
| Advisory documentation quality | `warn` only when not tied to baseline/release promotion |

## Recovery Decision Tree

```text
failure detected
  if high-risk or non-waivable:
    block and require explicit user gate
  else if checker unavailable:
    apply on_unavailable
    if manual_evidence allowed:
      require structured manual evidence
    else:
      block until checker or exception repaired
  else if missing/stale evidence:
    regenerate evidence inside approved scope
  else if scope conflict:
    narrow scope or request separate gate
  rerun validation
```

## Non-Waivable Recovery Boundaries

The following cannot be recovered by informal note or AI judgment:

- approval of a user gate
- real-project entry
- implementation writes
- deployment
- rollback
- database or migration action
- permission changes
- secret handling
- payment action
- production data action
- AGENTS.md, skill, MCP, wrapper, runtime, automation, protocol, or tool
  behavior enablement
- hardcoded secrets
- P0 security violations

## Loop Limit

If the same blocking condition repeats three consecutive governed turns, mark
the task blocked or request explicit user intervention rather than continuing to
claim progress.

## Boundary

This is a recovery design. It does not authorize any recovery action outside a
future approved gate.
