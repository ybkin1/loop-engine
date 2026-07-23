# Harness Depth Comparison v0.1

Status: evidence
Task: T-0009
Reference mode: read-only benchmark

## Reference Directory

`C:\Users\Administrator\Documents\trae_projects\yb\harness\.codex\tasks\tk-20260614-001-agentic-backend-orchestration-design\artifacts`

The directory was read only. It was not modified.

## Observed Benchmark Shape

The Harness benchmark is a document system, not a single design note. It includes:

- README index with document groups, reading paths, cross-document references, phase ownership, changelog, and governance summary
- core architecture and protocol documents
- API contract specification
- frontend UX specification
- security implementation specification
- contract test specification
- monitoring and alerting design
- role/responsibility/approval matrix
- MVP scope and sprint execution plan
- risk register
- detailed supplemental designs
- phase 2-3 target-state references

## Top Depth Signals

| Lines | Relative Path |
| ---: | --- |
| 3165 | `api-contract-specification.md` |
| 3148 | `frontend-ux-specification.md` |
| 2030 | `design-supplements/design-o-mcp-integration-architecture.md` |
| 1546 | `design-supplements/design-v-field-service-dispatch-execution.md` |
| 1526 | `design-supplements/design-t-email-intake-deep-link.md` |
| 1381 | `design-supplements/design-r-end-to-end-functional-specification.md` |
| 1347 | `design-supplements/design-u-data-supplement-subflow.md` |
| 1158 | `data-optimization-scratchpad-multiview-design.md` |
| 1141 | `data-optimization-knowledge-links-design.md` |
| 1112 | `security-implementation-spec.md` |

## Representative Section Depth

Harness API coverage includes versioning, auth, rate limits, pagination, common response wrappers, auth endpoints, chat endpoints, workflow endpoints, case endpoints, knowledge endpoints, profile endpoints, admin endpoints, SSE events, error responses, device endpoints, spare endpoints, and notification endpoints.

Harness frontend coverage includes layout, responsive breakpoints, navigation, component strategy, component specifications, interaction patterns, state management, accessibility, keyboard shortcuts, target workspace information architecture, and design tokens.

Harness security coverage includes authentication, authorization/RBAC, row-level security, tool permission execution, data protection, sensitive fields, redaction, secrets, API security, input validation, and audit trails.

Harness contract-test coverage includes request and response schema validation, error responses, SSE events, pagination, test organization, contract evolution, CI integration, local execution, and coverage targets.

Harness monitoring coverage includes metrics, dashboards, alert rules, runbooks, implementation roadmap, acceptance standards, and NFR baselines.

## Gap Against T-0008

T-0008 recognizes this target depth but does not yet provide the machinery to create it:

- no artifact schema catalog
- no cross-document ID and traceability system
- no document package index template
- no role-specific completion criteria
- no design-depth acceptance threshold
- no dry-run test showing the method can generate a Harness-like package

## Repair Implication

The next method repair should not simply add more prose. It should add operational templates and checks so AI can produce a design package with comparable breadth, while still asking the non-technical user only for business corrections and gate decisions.
