# Tool Entry Restriction Model Candidate v0.1

Status: candidate evidence only
Task: T-0019

## Purpose

Define which action classes should require explicit gates before future tools
or wrappers allow them.

## Sensitive Action Classes

| Class | Examples | Required Gate | Default Without Gate |
| --- | --- | --- | --- |
| `real_project_entry` | Entering or writing to a real business project root. | Real-project entry gate naming target root. | deny |
| `implementation_write` | Code/config writes in a real project. | Implementation/build gate with allowed paths. | deny |
| `build_or_release_prep` | Build, package, release-prep commands that change artifacts or behavior. | Build or deployment-prep gate. | deny |
| `deployment` | Deploying to staging or production. | Deployment gate. | deny |
| `rollback` | Running rollback scripts or reverting production behavior. | Rollback gate. | deny |
| `database_change` | DDL, DML, schema writes, seed against shared DB. | Database gate. | deny |
| `migration` | Creating or applying migrations. | Migration gate. | deny |
| `permission_change` | IAM, RBAC, ACL, authz, server permissions. | Permission gate. | deny |
| `secret_handling` | Reading, writing, rotating, exporting secrets. | Secret gate. | deny |
| `payment_action` | Payment provider changes, charges, refunds, settlement. | Payment gate. | deny |
| `production_data_action` | Reading/writing production data or PII. | Production-data gate. | deny |
| `agents_md_change` | Modifying `AGENTS.md` or startup rules. | Installation/rule-change gate. | deny |
| `skill_mcp_runtime_tool_enablement` | Installing/enabling skill, MCP, automation, protocol, wrapper, runtime, or tool behavior. | Runtime/tool enablement gate. | deny |
| `destructive_filesystem` | Recursive delete/move outside approved write set. | Destructive operation gate. | deny |

## Required Gate Fields

Every gate that authorizes a sensitive class must include:

```yaml
id: <gate id>
task_id: <task id>
gate_type: <class-specific type>
status: approved
approval_actor: user
approval_source: explicit_user_message
approval_text: <exact text>
recorded_at: <ISO8601>
target_project_root: <absolute path or null>
allowed_paths:
  - <path>
forbidden_paths:
  - <path or pattern>
allowed_actions:
  - <action>
forbidden_actions:
  - <action>
validation_required:
  - <validation>
risk_review: <path or text>
rollback_or_recovery_plan: <path or text>
evidence_required:
  - <path>
exit_criteria:
  - <condition>
```

## Tool Classification

Future guard logic should classify tools by effect, not by command name alone.

| Tool Family | Restriction Trigger |
| --- | --- |
| shell | Command verbs, cwd, target paths, environment, network target, and known deploy/db/secret tools. |
| apply patch / file write | Target path and sensitive file class. |
| browser / browser automation | Target domain, localhost app effect, production admin surfaces. |
| git | Branch, commit, tag, push, merge, revert, reset, checkout, clean. |
| package manager | Install, update, publish, audit fix, global install. |
| cloud / infra CLI | Any command that can mutate remote resources. |
| database CLI | Any command that can read/write shared or production data. |

## Blocking Examples

| Attempt | Required Decision |
| --- | --- |
| Run `npm run build` in a real project after design only. | Build gate. |
| Edit `.env.production`. | Secret or deployment config gate. |
| Apply a migration file. | Migration gate and database gate. |
| Modify `AGENTS.md`. | Installation/rule-change gate. |
| Enable a policy guard hook. | Runtime/tool behavior enablement gate. |
| Enter a business repo to inspect files. | Real-project entry gate, even if read-only when policy requires it. |

## Boundary

This model is not active enforcement. It is a candidate policy for a later
implementation or tool-entry enablement gate.
