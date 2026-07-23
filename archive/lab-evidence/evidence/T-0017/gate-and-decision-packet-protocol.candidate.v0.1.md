# Gate And Decision Packet Protocol Candidate v0.1

Status: candidate evidence only
Task: T-0017

## Purpose

Define how Codex should ask a non-technical user for decisions without forcing
them to judge engineering details.

## Gate Types

| Gate | Purpose |
| --- | --- |
| Discovery gate | Allow discovery artifacts. |
| Domain correction gate | Confirm or repair inferred domain model. |
| PRD baseline gate | Approve product behavior baseline. |
| Architecture baseline gate | Approve architecture as design reference. |
| Detailed design gate | Approve implementable design package. |
| Implementation readiness gate | Approve a build gate request for a named slice. |
| Build gate | Approve scoped code/config changes. |
| Review/repair gate | Approve repairs after findings. |
| Deployment-prep gate | Approve deployment preparation only. |
| Deployment gate | Approve actual deployment. |
| Rollback gate | Approve rollback action. |
| High-risk gate | Approve DB, permission, secret, payment, production-data, or migration action. |
| Installation/rule-change gate | Approve AGENTS.md, skill, MCP, agent, automation, protocol, runtime, or tool behavior change. |
| Closeout gate | Approve completion, archive, or pause when needed. |

## Gate Record Fields

```yaml
id:
task_id:
gate_type:
status:
decision:
requested_at:
requested_by:
approval_required_from: user
approval_actor:
approval_source:
approval_text:
recorded_at:
scope:
allowed_paths:
forbidden_paths:
allowed_actions:
forbidden_actions:
evidence:
validation_plan:
risk_review:
rollback_or_recovery_plan:
exit_criteria:
notes:
```

`approval_actor`, `approval_source`, `approval_text`, and `recorded_at` are
required after approval.

## User Decision Packet

Each packet should include:

- plain-language summary
- what Codex assumed
- decision needed
- recommended option
- tradeoffs
- risks or conflicts
- proposed gate ID
- exact reply format
- what approval allows
- what approval does not allow

## Decision Budget

Ask the user for no more than three decisions in one packet. Prefer one when
the next step depends on a single gate.

## Forbidden Interpretations

- A recommendation is not approval.
- A subagent conclusion is not approval.
- A review result is not approval.
- A validator result is not approval.
- A user correction of facts is not a build or deployment approval.
