# Exception Waiver Register Candidate v0.1

Status: candidate evidence only
Task: T-0017

## Purpose

Define how future real-project work may record exceptions without silently
weakening safety or quality gates.

## Waiver Record

```yaml
waiver_id:
task_id:
artifact_or_gate:
rule:
reason:
scope:
requested_by:
approved_by:
approval_source:
expires_at_or_revisit_when:
risk:
mitigation:
evidence:
```

## Allowed Waiver Classes

- trivial task simplification
- glue code traceability exception
- deferred non-critical artifact
- pre-production operational placeholder
- greenfield schema exception before real data exists

## Non-Waivable Items

- user gate approval
- real-project entry gate
- AGENTS.md/rule/runtime/tool enablement gate
- deployment gate
- rollback gate
- database, permission, secret, payment, production-data, or migration gate
- P0 security rules
- hardcoded secrets
- production PII in logs or tests
- reviewer PASS treated as user approval

## Expiry Rule

Every waiver must have a revisit point. Permanent waivers are not allowed.

## Boundary

This candidate register does not grant any exception. It only defines how a
future approved task should record one.
