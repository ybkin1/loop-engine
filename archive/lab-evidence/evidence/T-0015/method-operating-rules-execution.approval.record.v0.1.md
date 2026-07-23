# Approval Record: G-T-0015-METHOD-OPERATING-RULES-EXECUTION v0.1

Task: T-0015
Gate: G-T-0015-METHOD-OPERATING-RULES-EXECUTION
Recorded at: 2026-07-08T16:35:40+08:00

## User Approval

The user explicitly approved the pending T-0015 execution gate with this
message:

```text
批准 G-T-0015-METHOD-OPERATING-RULES-EXECUTION
```

Approval actor:

```text
user
```

Approval source:

```text
explicit_user_message
```

## Approved Meaning

This approval authorizes T-0015 to apply the exact approved T-0014 patch:

```text
.ai/evidence/T-0014/agents-md.proposed-diff.v0.1.patch
```

Target path:

```text
AGENTS.md
```

## Boundary

This approval does not authorize altering the approved diff, modifying files
outside T-0015 scope, enabling skill/MCP/external agent runtime/automation/
protocol service/tool behavior, entering a real business project, or performing
build, deploy, rollback, database, permission, secret, payment, production-data,
or migration actions.

## Verification Before Recording

Before recording this approval:

```text
AGENTS.md SHA256=DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87
git apply --check: passed
```
