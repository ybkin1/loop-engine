# Implementation Targets And Boundaries v0.1

Status: evidence
Task: T-0022

## Future Prototype Target Area

A later implementation gate may propose creating prototype files only under
the governance lab project:

```text
C:\Users\Administrator\.codex\loop-engine-lab
```

## Candidate Future Write Targets

These are planning candidates, not approved writes:

- `.ai/schemas/gate-register.schema.yaml`
- `.ai/schemas/checker-result.schema.yaml`
- `.ai/checkers/catalog.yaml`
- `.ai/checkers/validate_gate_register.py`
- `.ai/checkers/run_governance_checks.py`
- `.ai/policies/tool-entry-restrictions.yaml`
- `.ai/guards/policy_guard.py`
- `.ai/guards/guard_decision.schema.yaml`
- `.ai/tests/samples/`
- `.ai/tests/test_governance_checks.py`
- `.ai/evidence/<future-task-id>/`

## Explicit Non-Targets

- `AGENTS.md`
- `C:\Users\Administrator\.codex\skills\`
- MCP, plugin, automation, hook, or runtime configuration files
- Any real business project root
- Build, deployment, database, secret, permission, payment, production-data,
  migration, or rollback files

## Future Implementation Boundary

The first future implementation should be a lab-local prototype only. It may
produce scripts and sample data, but must not install them as mandatory
runtime behavior or tool-entry enforcement.

## Separate Gates Still Required

- Prototype implementation gate.
- Installation/rule-change gate if `AGENTS.md` or startup behavior changes.
- Runtime/tool enablement gate if any guard, hook, MCP, skill, automation, or
  wrapper becomes active.
- Real-project entry gate for any named business project.
- Deployment, rollback, database, permission, secret, payment,
  production-data, and migration gates for those action classes.
