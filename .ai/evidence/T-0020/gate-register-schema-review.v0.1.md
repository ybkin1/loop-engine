# Gate Register Schema Review v0.1

Status: evidence
Task: T-0020

## Verdict

```text
passed_with_p2_refinement
```

## Evidence Reviewed

- `.ai/evidence/T-0019/machine-readable-gate-register-schema.candidate.v0.1.md`
- `gate-register.md`

## What Passed

The schema covers the major lifecycle and enforcement concepts required for a
future machine-readable register:

- lifecycle stage and stage status
- target project kind, root, evidence root, and entry gate
- action family, artifact kind, lifecycle stage, required gates, and mandatory
  checkers
- gate bindings with approval source and blocking behavior
- required artifacts and freshness targets
- checker items with status, runtime, unavailable policy, result refs, evidence
  refs, exceptions, and timestamps
- forbidden scope for deployment, rollback, database, permissions, secrets,
  payment, production data, migrations, `AGENTS.md`, and runtime/tool enablement
- transition controls for pending, missing, stale, failed, unavailable, and
  reviewer/validator misuse cases

## P2 Finding

`FIND-T0020-P2-001`: The gate register schema has strong forbidden-scope
fields, but its positive authorization model is less explicit than its denial
model.

Specifically, the register should add first-class `allowed_actions`,
`allowed_action_classes`, and `allowed_tools` fields, or explicitly reference
the approved gate fields that provide them. Without this, a future
implementation may over-rely on inferring allowed behavior from the absence of
forbidden behavior.

## Recommendation

Before implementation, refine the schema so every action decision can answer:

- which approved gate authorized this action class
- which allowed action/path/tool matched
- which forbidden rule was checked
- which evidence record proves the decision

## Baseline Consideration Impact

Non-blocking for baseline consideration because the candidate already captures
the core `pending is blocking` model. Blocking before implementation.
