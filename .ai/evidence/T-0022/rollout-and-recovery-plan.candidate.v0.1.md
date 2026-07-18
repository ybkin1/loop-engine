# Rollout And Recovery Plan Candidate v0.1

Status: candidate evidence
Task: T-0022

## Rollout Sequence

| Step | Scope | Required Gate |
| --- | --- | --- |
| 1 | Create lab-local prototype files and sample tests. | Prototype implementation gate |
| 2 | Run prototype on governance-lab sample data only. | Verification/smoke-test gate |
| 3 | Decide whether prototype may affect startup or closeout workflow. | Installation/rule-change gate |
| 4 | Enable wrapper, MCP, hook, skill, automation, protocol, or tool behavior. | Runtime/tool enablement gate |
| 5 | Apply to a named real business project. | Real-project entry gate |

## Recovery Boundaries

If a future prototype is wrong, recovery should be limited to the same
approved scope that created it. Removing or disabling installed/runtime
behavior requires a separate rollback or runtime/tool gate if that behavior
was ever enabled.

## Fail-Closed Defaults

- Security, secret, permission, production-data, database, migration,
  deployment, rollback, payment, and tool-entry checks fail closed.
- Ambiguous gate approval is treated as not approved.
- Missing evidence lock blocks stage promotion.
- Stale handoff blocks closeout until repaired.

## Manual Recovery Evidence

Allowed manual recovery evidence must name:

- failed check
- affected gate
- exact repair scope
- user decision if required
- validation command and result
- remaining forbidden scope

## Boundary

This rollout plan does not authorize rollout, installation, enablement,
rollback, real-project entry, or high-risk action.
