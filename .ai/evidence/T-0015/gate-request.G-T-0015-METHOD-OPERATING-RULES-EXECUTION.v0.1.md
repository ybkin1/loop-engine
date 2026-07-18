# Gate Request: G-T-0015-METHOD-OPERATING-RULES-EXECUTION v0.1

Status: pending user decision
Task: T-0015
Requested at: 2026-07-08T16:26:02+08:00
Requested by: AI
Approval required from: user

## Purpose

Ask whether T-0015 may execute the exact `AGENTS.md` operating-rules diff that
was approved as a future execution basis in T-0014.

T-0014 approval is not execution authorization. This T-0015 gate is required
before `AGENTS.md` can be modified.

## Exact Execution Package

Approved source patch:

```text
.ai/evidence/T-0014/agents-md.proposed-diff.v0.1.patch
```

Execution target:

```text
AGENTS.md
```

Current baseline hash:

```text
DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87
```

Dry-run result:

```text
git apply --check: passed
```

## Approval Would Allow

- Apply the exact approved T-0014 patch to `AGENTS.md`.
- Record execution evidence under `.ai/evidence/T-0015/`.
- Rerun `validate_state.py`.
- Verify the applied content and startup-rule boundary.
- Update `.ai` governance records only as needed to close T-0015.

## Approval Would Not Allow

- Alter the approved diff.
- Modify files outside the approved T-0015 paths.
- Enable skill, MCP, external agent runtime, automation, protocol service, or tool behavior.
- Enter, create, or modify a real business project.
- Build, deploy, release, roll back, or touch database, permission, secret,
  payment, production-data, or migration resources.
- Treat reviewer PASS, validator success, tests, AI recommendation, or prior
  T-0014 approval as a substitute for this T-0015 approval.

## User Decision Needed

Approve, reject, or request repair of:

```text
G-T-0015-METHOD-OPERATING-RULES-EXECUTION
```

Until then, T-0015 is blocked and `AGENTS.md` must remain unchanged.
