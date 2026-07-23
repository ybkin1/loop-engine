# Next Gate Recommendation v0.1

Status: evidence
Task: T-0018

## Recommendation

Open a later separate design/repair gate:

```text
G-T-0019-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-DESIGN
```

Suggested task:

```text
T-0019: Real Project Governance Enforcement Architecture Design
```

## Purpose

Repair the P1 enforcement gap found in T-0018 by designing how T-0017's
Markdown governance rules become enforceable, auditable, and hard to skip in
future real-project work.

## Proposed Scope

- Design a machine-readable gate register for lifecycle stages.
- Define mandatory checker catalog and blocking semantics.
- Define how `validate_state.py` or later scripts detect missing evidence,
  pending stage checks, and forbidden scope.
- Define policy-guard or wrapper behavior for real-project entry and high-risk
  actions.
- Define tool-entry restrictions for deployment, rollback, database,
  permission, secret, payment, production-data, migration, `AGENTS.md`, skill,
  MCP, automation, protocol, runtime, and tool behavior changes.
- Define unavailable-checker failure modes.
- Define evidence paths and closeout/audit behavior.

## Proposed Forbidden Scope

- Do not install or enable any skill, MCP, policy guard, wrapper, automation,
  protocol, runtime, or tool behavior.
- Do not modify `AGENTS.md`.
- Do not enter a real business project.
- Do not implement business code.
- Do not build, deploy, release, or roll back.
- Do not change databases, permissions, secrets, payment systems, production
  data, or migrations.

## Not Recommended Next

Do not proceed from T-0018 directly to baseline consideration, real-project
entry, implementation, installation, or runtime/tool enablement.
