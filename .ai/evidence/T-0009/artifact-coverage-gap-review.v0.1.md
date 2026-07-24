# Artifact Coverage Gap Review v0.1

Status: evidence
Task: T-0009

## Coverage Summary

T-0008 defines a useful artifact matrix, but it remains a catalog more than a production method. The next repair should turn each artifact category into a schema with required sections, traceability fields, status labels, review checks, and expected evidence.

## Coverage Matrix

| Area | T-0008 Coverage | Gap | Severity |
| --- | --- | --- | --- |
| Method lifecycle | Status labels mentioned | No formal lifecycle transitions or state meanings | P1 |
| Gate protocol | Gate principles and fields listed | No gate request template or real-project gate variant | P1 |
| Repair loop | Review and repair loop described | No repair evidence package, diff summary, or rerun criteria | P1 |
| Artifact map | Stage artifact matrix exists | No artifact dependency graph or minimum completeness checklist | P2 |
| Domain model | Actor, role, object, workflow, data authority listed | No confidence/source/conflict fields | P2 |
| PRD | PRD and requirements listed | No PRD skeleton or requirement ID scheme | P2 |
| Architecture | Component/integration/data authority listed | No architecture decision template or interface inventory schema | P2 |
| Backend/API | API/data/workflow/error listed | No endpoint template, event schema, idempotency, transaction, or error catalog requirements | P2 |
| Frontend/UX | UX spec listed | No screen-state schema, accessibility, responsive, error/empty/loading state requirements | P2 |
| QA/Test | Test strategy listed | No design-review tests, contract-test readiness, regression matrix, or release criteria template | P2 |
| Security | Trust, auth, data, audit topics listed | No threat model, data classification, permission matrix, or sensitive action gate checklist | P2 |
| DevOps/SRE | Observability, alerts, rollback listed | No metrics, SLO, alert, runbook, environment, or ownership schema | P2 |
| Handoff | Handoff rules listed | No contamination checklist or handoff audit rubric | P2 |
| User interaction | Managerial interface principle listed | No decision packet template, interaction budget, or batch correction format | P2 |

## Missing Method-Level Artifacts

The repaired method should add candidate documents such as:

- `method-lifecycle-state-model.v0.1.md`
- `gate-request-template.v0.1.md`
- `real-project-entry-gate-template.v0.1.md`
- `artifact-schema-catalog.v0.1.md`
- `traceability-id-system.v0.1.md`
- `user-decision-packet-template.v0.1.md`
- `repair-loop-protocol.v0.1.md`
- `handoff-context-hygiene-checklist.v0.1.md`
- `design-baseline-readiness-checklist.v0.1.md`
- `method-dry-run-test-plan.v0.1.md`

## Minimum Repair Standard

Before T-0008 can become a baseline candidate, each artifact class should answer:

- what file should exist
- when it is required
- what sections it must contain
- what IDs or references it must expose
- which role reviews it
- what makes it pass or fail
- what user decision it may require
- what evidence proves it was checked
