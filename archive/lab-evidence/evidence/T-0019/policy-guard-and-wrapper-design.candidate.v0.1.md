# Policy Guard And Wrapper Design Candidate v0.1

Status: candidate evidence only
Task: T-0019

## Purpose

Design a future policy guard / wrapper that would classify requested actions
before sensitive work occurs.

This is not an implementation and does not enable a wrapper.

## Guard Responsibilities

1. Read latest user request.
2. Classify requested action family and sensitive action classes.
3. Load `.ai/state.yaml`, `.ai/gates.yaml`, current task, and gate register.
4. Check for pending gates.
5. Check whether the requested action is inside approved gate scope.
6. Check allowed paths, forbidden paths, and target project root.
7. Check mandatory checker status for the current lifecycle stage.
8. Deny or require a separate explicit gate for high-risk action classes.
9. Emit structured decision evidence before allowing the action.

## Candidate Guard Decision Shape

```yaml
guard_decision_id: GD-<task-id>-<timestamp>
task_id: T-XXXX
request_summary: <text>
classified_action:
  action_family: authoring | implementation | verification | review | closeout
  artifact_kind: <kind>
  sensitive_action_classes:
    - <class>
target:
  project_root: <path>
  paths:
    - <path>
gate_context:
  current_gate_id: <gate id or null>
  approved_gate_ids:
    - <gate id>
  pending_gate_ids: []
register_context:
  register_ref: <path>
  blocking_items: []
decision: allow | deny | require_user_gate | require_repair | require_checker
reason: <text>
evidence_ref: <path>
```

## Guard Decision Rules

| Condition | Decision |
| --- | --- |
| Any unrelated pending gate exists | `deny` |
| Latest user request approves the exact pending gate | `allow_gate_recording_only` |
| Real-project root is requested without real-project entry gate | `require_user_gate` |
| File write outside approved allowed paths | `deny` |
| High-risk class lacks separate approved gate | `require_user_gate` |
| Mandatory checker is missing or stale | `require_checker` |
| Checker unavailable with `fail_closed` | `require_repair` |
| Reviewer/test/validator evidence is treated as approval | `deny` |

## Wrapper Entry Points

Candidate future wrappers:

| Wrapper | Would Guard |
| --- | --- |
| `governed_startup` | Session startup, task selection, current gate check. |
| `governed_write` | File writes, apply patches, generated artifacts. |
| `governed_command` | Shell commands, build, test, deployment commands. |
| `governed_real_project_entry` | Changing cwd or target root to a real project. |
| `governed_closeout` | Task completion, handoff, evidence locks, audit. |

## Guard Placement Options

| Option | Strength | Weakness |
| --- | --- | --- |
| Agent self-check | No install needed. | Easy to skip. |
| Script wrapper | Deterministic and auditable. | Only works when commands go through wrapper. |
| MCP guard | Centralizes state and checker logic. | Requires separate MCP/tool enablement gate. |
| Pre-tool hook | Hard to skip for supported tools. | Requires runtime/tool behavior change gate. |
| Platform-level enforcement | Strongest. | Outside T-0019 scope and requires explicit enablement. |

## Non-Authorization

T-0019 does not create, install, configure, or enable any wrapper, MCP, hook,
guard, runtime behavior, or tool behavior.
