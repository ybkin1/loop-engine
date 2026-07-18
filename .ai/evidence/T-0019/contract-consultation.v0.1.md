# Contract Consultation v0.1

Status: evidence
Task: T-0019

## Purpose

Record which local contracts informed the T-0019 enforcement architecture
candidate.

## Contracts Consulted

| Contract | Why It Was Consulted | Design Impact |
| --- | --- | --- |
| `gate-register.md` | T-0018 found that Markdown rules lack machine blocking. | Adopt `pending is blocking`, register as truth, freeze-on-pass, and unavailable checker semantics. |
| `verification-checker.md` | T-0019 must define checker catalog and result shape. | Adopt structured checker result shape, gate binding, manual evidence, and checker-as-evidence principle. |
| `exception-governance.md` | T-0019 must handle unavailable checkers and non-waivable rules. | Define explicit exception records, non-waivable gate classes, and fail-closed handling. |
| `action-governance.md` | T-0019 must classify actions before tool use. | Use action family, artifact kind, route profile, mandatory checker refs, and negative activation constraints. |
| `security-governance.md` | T-0019 covers secrets, permissions, and security-sensitive actions. | Mark P0 security checks as fail-closed and non-waivable. |
| `data-management.md` | T-0019 covers database and migration gates. | Separate schema design, migration safety, data validation, and actual DB change authorization. |
| `deployment-governance.md` | T-0019 covers deployment and rollback restrictions. | Separate deployment prep, deployment, rollback, artifact, smoke, monitoring, and evidence gates. |
| `production-merge-governance.md` | T-0019 covers production data and production action restrictions. | Treat production as read-only except approved pipeline actions and require merge/deployment gate evidence. |

## Boundary

This consultation produced design evidence only. It did not install, enable, or
modify any contract, checker, MCP, skill, wrapper, runtime behavior, tool
behavior, `AGENTS.md`, real project, database, deployment, rollback,
permission, secret, payment, production data, or migration resource.
