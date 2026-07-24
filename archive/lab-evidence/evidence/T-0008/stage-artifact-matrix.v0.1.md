# Stage Artifact Matrix v0.1

Status: candidate design
Task: T-0008

## Purpose

This matrix defines the minimum artifacts the AI should proactively produce at each lifecycle stage.

The user should not need to ask for these documents one by one. The AI should generate the map, draft the artifacts, review them, and present summaries plus gate decisions.

## Matrix

| Stage | Required AI Artifacts | Acceptance Standard | Evidence |
| --- | --- | --- | --- |
| S0 Idea Intake | goal statement, scope boundary, non-goals, initial assumptions, proposed gate | user can see what will and will not happen | task file, gate record, commands evidence |
| S1 Domain Model | actor map, role/responsibility matrix, business object map, workflow map, exception map, source-of-truth matrix, assumptions ledger | user can batch-correct the business model | domain-model candidate, Q&A log, correction log |
| S2 Discovery Baseline | problem statement, target users, use cases, MVP hypothesis, risks, open questions | product intent is understandable before PRD | discovery baseline, risk register, open-question log |
| S3 PRD Baseline | PRD, user journeys, functional requirements, non-functional requirements, acceptance criteria, requirement traceability | every major requirement traces to a user/business goal | PRD, acceptance criteria, traceability matrix |
| S4 Architecture Baseline | architecture overview, component map, integration map, data authority model, technology choice rationale, constraints, ADR candidates | architecture is reviewable before detailed design | architecture design, decisions, risk notes |
| S5 Detailed Design | API contracts, data model, UX spec, workflow/state design, security design, observability design, test strategy, release plan, future-state partition | implementation could be planned without asking basic design questions | design package, cross-doc index, gap assessment |
| S6 Implementation Planning | milestone plan, sprint plan, task breakdown, dependency graph, test plan, evidence plan | coding work is sequenced and gateable | implementation plan, task graph, quality gates |
| S7 Coding | code changes, migration candidates if needed, local tests, implementation notes | changes stay inside approved scope and pass agreed checks | diff summary, commands evidence, test output |
| S8 Testing And Repair | test report, defect list, repair plan, regression evidence, residual risk assessment | user can decide whether quality risk is acceptable | test evidence, review report, known issues |
| S9 Release Gate | release readiness report, rollback plan, monitoring checklist, approval request | release decision is explicit and reversible where possible | release gate, readiness evidence |
| S10 Operate And Handoff | handoff, evidence index, open decisions, next prompt, status validation | next session can resume without chat memory | HANDOFF.md, PROGRESS.md, validate output |

## Design Package Minimum For Complex Projects

For a complex project, S5 should not be a single architecture note. It should include at least:

- `README.md` or design package index
- `prd.md`
- `end-to-end-functional-specification.md`
- `domain-model.md`
- `role-responsibility-approval-matrix.md`
- `architecture-design.md`
- `api-contract-specification.md`
- `data-model-design.md`
- `frontend-ux-specification.md`
- `workflow-state-design.md`
- `security-implementation-spec.md`
- `observability-monitoring-design.md`
- `error-code-catalog.md`
- `contract-test-specification.md`
- `release-rollback-plan.md`
- `risk-register.md`
- `mvp-scope-definition.md`
- `sprint-execution-plan.md`
- `phase-2-3-target-state.md`
- `design-granularity-gap-assessment.md`

## Artifact Quality Rules

Each artifact should declare:

- status: candidate, reviewed, approved, active, installed, or superseded
- scope and non-goals
- assumptions
- dependencies
- user decisions required
- references to related artifacts
- acceptance or review criteria

## Traceability Rules

The AI must maintain traceability across:

- goal to PRD requirement
- requirement to workflow
- workflow to API/data/UX design
- API/data/UX design to tests
- security risk to mitigation
- release risk to monitoring/rollback
- open question to user decision

## Evidence Rules

Every meaningful stage must write:

- command evidence
- generated artifacts
- review findings
- repair records
- validation output when applicable
- gate decision records when user approval is required
