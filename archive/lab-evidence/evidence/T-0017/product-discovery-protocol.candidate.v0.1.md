# Product Discovery Protocol Candidate v0.1

Status: candidate
Task: T-0017

## Purpose

Help a non-technical user move from a rough product idea to a reviewable
product baseline while keeping technical and project-management burden inside
Codex.

This protocol is design-only. It does not approve a real project, code change,
build, deployment, or production action.

## Operating Principle

Codex should build a visible product and domain model before asking many
questions. The user should correct business truth, priorities, and tradeoffs;
Codex should own structure, decomposition, evidence, and review discipline.

## Flow

### S0 Idea Intake

Capture:

- target user
- problem or pain point
- desired outcome
- business context
- constraints, deadlines, and forbidden scope
- data or high-risk resources likely involved

Output:

- `product-intent.v0.1.md`
- initial assumptions ledger
- proposed discovery gate

Gate:

- user confirms direction or requests repair

### S1 Domain Model First

Create a model before detailed PRD writing:

- actors and roles
- responsibility map
- business object catalog
- source-of-truth matrix
- main workflows
- exception workflows
- open assumptions ledger

Output:

- `domain-model.candidate.v0.1.md`
- `business-workflow-map.candidate.v0.1.md`
- `assumptions-ledger.v0.1.md`

Gate:

- user batch-corrects business facts

### S2 Discovery Baseline

Convert the model into a stable discovery package:

- problem statement
- target users and use cases
- MVP candidate
- non-goals
- scenario map
- risk register
- first acceptance criteria

Output:

- `discovery-baseline.candidate.v0.1.md`
- `scenario-map.candidate.v0.1.md`
- `risk-register.v0.1.md`

Gate:

- user approves, narrows, or redirects discovery baseline

### S3 Product Baseline

Draft product behavior in user-visible language:

- PRD
- user journeys
- functional requirements
- non-functional requirements
- acceptance criteria
- traceability from goals to requirements

Output:

- `prd.candidate.v0.1.md`
- `acceptance-criteria.v0.1.md`
- `requirement-traceability-matrix.v0.1.md`

Gate:

- user approves product scope and tradeoffs

## Interaction Budget

- Ask one high-value question at a time during discovery.
- Batch assumptions for correction instead of asking the user to manage a
  questionnaire.
- Ask technical questions only when they change product cost, risk, timeline,
  privacy, or operations.
- Offer a recommended default when the user lacks technical context.

## Acceptance Standard

Discovery is ready to move toward architecture only when:

- the target user and primary workflows are clear
- MVP and non-goals are explicit
- acceptance criteria are testable
- sensitive data and high-risk areas are identified
- open questions are either answered or explicitly deferred
- no requirement lacks a business goal or acceptance path

## Forbidden Interpretations

- A product brief is not PRD approval unless separately gated.
- PRD approval is not architecture approval.
- Architecture approval is not implementation approval.
- Discovery approval is not deployment or release permission.
