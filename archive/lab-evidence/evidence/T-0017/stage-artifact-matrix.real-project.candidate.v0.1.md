# Stage Artifact Matrix For Real Projects Candidate v0.1

Status: candidate evidence only
Task: T-0017

## Purpose

Define the minimum artifacts Codex should proactively produce. The user should
not need to know which documents to ask for.

## Matrix

| Stage | Required Artifacts | Acceptance Standard |
| --- | --- | --- |
| S0 Idea Intake | `product-intent`, scope boundary, assumptions, proposed gate | user can see what will and will not happen |
| S1 Domain Model | actor map, responsibility matrix, object catalog, source-of-truth matrix, workflow map | user can batch-correct business facts |
| S2 Discovery | discovery baseline, scenario map, risk register, open questions | MVP and non-goals are understandable |
| S3 PRD | PRD, acceptance criteria, requirement traceability | every MVP requirement has goal and acceptance link |
| S4 Architecture | architecture baseline, component map, integration map, data ownership, ADR candidates | architecture is reviewable before detailed design |
| S5 Detailed Design | API/data/UX/workflow/security/observability/test/release design as applicable | implementation can be planned without inventing basics |
| S6 Planning | work packets, dependency graph, dev plan, evidence plan | packets are traceable and verifiable |
| S7 Coding | code changes, tests, command evidence, changed-path audit | changes stay inside approved paths |
| S8 Testing/Repair | test report, review report, repair plan, residual risk | user can decide whether risk is acceptable |
| S9 Release | release readiness, rollback plan, monitoring checklist | release decision is explicit |
| S10 Handoff | HANDOFF, evidence index, next prompt, status validation | next session can resume without chat memory |

## Artifact Quality Rules

Each artifact should declare:

- status
- scope and non-goals
- assumptions
- sources
- related IDs
- review status
- user decisions required
- forbidden interpretations

## Minimum Boundary Text

Every package-level artifact should state whether it is:

- candidate evidence only
- user-approved baseline
- active reference
- installed behavior
- real-project execution authorization

When in doubt, the answer is candidate evidence only.
