# Gate Approval: G-T-0016-STARTUP-RULES-ACCEPTANCE-SMOKE-TEST

## Decision

Approved by explicit user message.

## Approval Text

```text
批准 G-T-0016-STARTUP-RULES-ACCEPTANCE-SMOKE-TEST
```

## Recorded At

```text
2026-07-08T17:02:27+08:00
```

## Scope

This gate authorizes only a narrow post-installation startup-rules acceptance /
smoke-test task:

- create `.ai/tasks/T-0016.md`
- create `.ai/evidence/T-0016/`
- record startup validation evidence
- verify `AGENTS.md` presence, installed content, and SHA256
- verify startup-routing expectations from `AGENTS.md`
- update `.ai/state.yaml`, `.ai/task_graph.yaml`, `.ai/gates.yaml`,
  `.ai/PROGRESS.md`, and `.ai/HANDOFF.md` only as needed for T-0016
- run `validate_state.py`, `close_session.py`, and `audit_handoff.py`

## Forbidden Scope

- do not modify `AGENTS.md`
- do not alter T-0015 execution evidence
- do not enter, create, or modify a real business project
- do not write business code
- do not implement, build, deploy, release, or roll back
- do not install or enable skill, MCP, external agent runtime, automation,
  protocol service, or tool behavior
- do not change global or project runtime behavior
- do not change databases, permissions, secrets, payment systems, production
  data, or migrations
- do not treat validator success, reviewer PASS, tests, or AI recommendation
  as user approval

## Boundary

Approval of this gate is not approval for any later real-project entry,
implementation, build, deployment, rollback, runtime/tool enablement, or
high-risk action.
