# Reference Depth Benchmark v0.1

Status: candidate evidence
Task: T-0008
Reference mode: read-only benchmark

## Reference Directory

`C:\Users\Administrator\Documents\trae_projects\yb\harness\.codex\tasks\tk-20260614-001-agentic-backend-orchestration-design\artifacts`

This directory was used only as a design-depth benchmark. It was not modified.

## Observed Shape

The benchmark is not a single PRD. It is a design package with 48 files covering:

- architecture and orchestration design
- plan-card and event protocols
- API contracts
- data models
- front-end UX specification
- security implementation
- role and approval matrix
- monitoring and alerting
- contract tests
- risk register
- MVP scope
- sprint execution plan
- detailed subflow designs
- Phase 2-3 target-state references
- design granularity gap assessment
- cross-document index and reading paths

## Depth Signal

The largest files are in the thousands of lines:

| File | Lines |
| --- | ---: |
| `api-contract-specification.md` | 3165 |
| `frontend-ux-specification.md` | 3148 |
| `design-supplements/design-o-mcp-integration-architecture.md` | 2030 |
| `design-supplements/design-v-field-service-dispatch-execution.md` | 1546 |
| `design-supplements/design-t-email-intake-deep-link.md` | 1526 |
| `design-supplements/design-r-end-to-end-functional-specification.md` | 1381 |

## Method Implication

The target depth requires an AI-led production system for design artifacts, not a slow user interview.

A usable Loop method must:

- build a domain model before asking detailed questions
- generate a document map before writing isolated documents
- produce candidate artifacts in batches
- run cross-role review and cross-document traceability checks
- ask the user only for high-value business choices, factual corrections, and gate decisions
- separate MVP, later phases, and non-goals early
- keep evidence, gates, and handoff updated as first-class artifacts

## Constraint

This benchmark does not authorize using or modifying the referenced business project. It only calibrates the expected design-document depth for T-0008.
