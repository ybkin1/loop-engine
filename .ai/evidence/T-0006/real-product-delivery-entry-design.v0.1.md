# Real Product Delivery Entry Design v0.1

Status: candidate design
Task: T-0006
Recorded at: 2026-07-07T14:22:05+08:00

## 0. Purpose

This document defines the first product discovery protocol / real-project application candidate for Codex-managed software delivery.

The goal is to help a user without coding or project-management background turn a rough product idea into a real, usable, deployable, verifiable, and sustainably iterable software product.

This design is not a real-project entry approval. It defines how a future real-project entry should work.

## 1. Primary User

The primary user:

- has a product goal, pain point, workflow, or business idea
- may not know how to write requirements
- may not know how software projects are planned or verified
- should not need to manage tickets, architecture, tests, reviews, or handoff details manually
- must still own goals, priorities, tradeoffs, and gate approvals

Codex should act as a one-person product engineering team inside approved boundaries.

## 2. Operating Principles

- Product delivery is the purpose; governance is the guardrail.
- Codex asks for human judgment only where human judgment matters.
- Codex owns technical decomposition, implementation planning, verification design, review discipline, and handoff records.
- Every real-project step requires a clear artifact, acceptance condition, and gate.
- Reviewer PASS, validator success, tests, or AI recommendation never replace user approval.
- No deployment, rollback, production data, secret, payment, database, permission, migration, or real-project file change occurs without a separate explicit gate.

## 3. Entry Preconditions

Before applying this protocol to a real project, the session must have:

- explicit user approval to start a real-project discovery task
- target project root or permission to create/select one
- stated product idea or problem area
- declared forbidden areas, if any
- project-governor state initialized or permission to initialize it

If a real project root is not approved, Codex must stay in design/discovery-only mode.

## 4. Discovery Flow

The entry flow has nine stages.

### Stage 1: Intent Capture

Codex captures the user's rough idea in plain language:

- who the product is for
- what problem it solves
- what result would make the user happy
- whether this is personal, internal, commercial, or experimental
- whether there are deadlines, budget limits, or technical constraints

Output:

- `product-intent.v0.1.md`

Gate to advance:

- user confirms the intent summary is directionally correct

### Stage 2: One-Question Clarification

Codex interviews the user one question at a time until the product shape is clear enough to draft a product brief.

Question priority:

1. user and use case
2. must-have outcome
3. data involved
4. workflow and roles
5. acceptance examples
6. constraints and risks
7. launch context

Codex should avoid asking the user to make technical decisions unless the decision affects product tradeoffs.

Output:

- `discovery-q-and-a.v0.1.md`

Gate to advance:

- Codex states assumptions and the user accepts, corrects, or adds missing facts

### Stage 3: Product Definition

Codex drafts a product definition that is readable by a non-technical user.

Required sections:

- target user
- problem statement
- product promise
- main workflows
- MVP scope
- out-of-scope list
- assumptions
- risks

Output:

- `product-brief.v0.1.md`

Gate to advance:

- user approves the product brief or requests changes

### Stage 4: Acceptance Design

Codex turns product intent into testable acceptance criteria.

Acceptance criteria should include:

- user-visible behavior
- examples of valid and invalid inputs
- success and failure states
- performance or reliability expectations when relevant
- data privacy and safety expectations when relevant
- manual verification steps the user can understand

Output:

- `acceptance-criteria.v0.1.md`

Gate to advance:

- user approves the acceptance criteria

### Stage 5: Technical Approach Candidate

Codex proposes a technical approach without yet implementing.

Required sections:

- likely app type
- architecture sketch
- data model candidate
- integration needs
- testing strategy
- deployment-readiness path
- main risks and alternatives
- files or areas expected to change

Output:

- `technical-approach.candidate.v0.1.md`

Gate to advance:

- user approves the approach or asks for alternatives

### Stage 6: Implementation Plan

Codex breaks the work into small, verifiable slices.

Each slice must include:

- user-visible outcome
- expected files or modules
- verification method
- review checkpoint
- rollback or recovery note when relevant

Output:

- `implementation-plan.v0.1.md`

Gate to advance:

- user approves the implementation plan

### Stage 7: Build Gate

Before touching real project files, Codex must ask for a build gate.

The build gate must name:

- project root
- allowed paths
- forbidden paths
- first implementation slice
- validation commands
- evidence location
- rollback boundary

Output:

- `build-gate-request.v0.1.md`

Gate to advance:

- explicit user approval

### Stage 8: Verify, Review, Handoff

After implementation slices, Codex must produce evidence.

Required evidence:

- commands run
- tests or manual checks
- changed files
- review findings
- unresolved risks
- user-facing verification instructions
- handoff summary

Output:

- `verification-evidence.md`
- `review-report.md`
- `HANDOFF.md`

Gate to advance:

- user accepts the slice or approves repair

### Stage 9: Iteration Entry

After the first usable slice, Codex helps the user decide what happens next.

Options:

- accept and pause
- repair defects
- expand scope
- prepare deployment
- prepare user testing
- create next iteration

Output:

- `iteration-decision.v0.1.md`

Gate to advance:

- explicit user decision

## 5. Required Artifacts For A Real Project

A real project using this protocol should create or maintain:

- `.ai/state.yaml`
- `.ai/HANDOFF.md`
- `.ai/PROGRESS.md`
- `.ai/gates.yaml`
- `.ai/task_graph.yaml`
- `.ai/tasks/<task-id>.md`
- `.ai/evidence/<task-id>/commands.md`
- `.ai/evidence/<task-id>/product-intent.v0.1.md`
- `.ai/evidence/<task-id>/discovery-q-and-a.v0.1.md`
- `.ai/evidence/<task-id>/product-brief.v0.1.md`
- `.ai/evidence/<task-id>/acceptance-criteria.v0.1.md`
- `.ai/evidence/<task-id>/technical-approach.candidate.v0.1.md`
- `.ai/evidence/<task-id>/implementation-plan.v0.1.md`
- `.ai/evidence/<task-id>/build-gate-request.v0.1.md`
- `.ai/evidence/<task-id>/verification-evidence.md`
- `.ai/evidence/<task-id>/review-report.md`
- `.ai/evidence/<task-id>/iteration-decision.v0.1.md`

The exact files may be adapted for the project, but the roles of intent, acceptance, technical approach, plan, verification, review, and handoff must remain covered.

## 6. User Interaction Contract

Codex should:

- summarize what it heard before designing
- ask one important question at a time when the answer materially changes the product
- offer defaults when the user lacks technical context
- explain tradeoffs in product language
- keep the user out of low-level implementation mechanics unless approval is needed
- clearly say when a gate is required

Codex should not:

- pretend uncertainty is resolved
- turn reviewer PASS into user approval
- enter business project files without a gate
- deploy or prepare production changes without a gate
- ask the user to make framework choices unless those choices affect product outcomes

## 7. Gate Model

Recommended gates for future real-project use:

- `DISCOVERY-GATE`: approve interviewing and writing product discovery artifacts
- `PRODUCT-BRIEF-GATE`: approve product definition
- `ACCEPTANCE-GATE`: approve acceptance criteria
- `TECHNICAL-APPROACH-GATE`: approve architecture candidate
- `IMPLEMENTATION-PLAN-GATE`: approve implementation slices
- `BUILD-GATE`: approve real file changes for a named slice
- `REVIEW-REPAIR-GATE`: approve repairs after review
- `DEPLOYMENT-PREP-GATE`: approve deployment preparation only
- `DEPLOYMENT-GATE`: approve actual deployment
- `ITERATION-GATE`: approve next iteration or scope expansion

Gate names may be adapted per project, but gate boundaries must be explicit.

## 8. Definition Of Ready For Real Project Entry

The project is ready to enter real project discovery when:

- the user has approved a real-project discovery gate
- the project root is known or creation is approved
- forbidden paths and high-risk actions are named
- Codex can write discovery evidence without touching production-sensitive resources
- the user understands that discovery does not equal implementation or deployment

## 9. Definition Of Ready For Implementation

A real project is ready for implementation only when:

- product brief is approved
- acceptance criteria are approved
- technical approach is approved
- implementation plan is approved
- build gate names allowed paths and validation commands
- rollback or recovery expectations are stated
- evidence location is defined

## 10. Review And Verification Standard

Every implementation slice should be checked on four axes:

- product behavior matches acceptance criteria
- technical implementation follows project conventions
- tests or manual checks prove the change
- handoff explains what changed, what remains risky, and what to do next

If any axis fails, Codex should recommend repair rather than asking the user to debug.

## 11. Handoff Standard

At the end of a real-project session, handoff should state:

- current product phase
- current task
- user-approved scope
- forbidden scope
- recent changes
- verified items
- unverified items
- evidence location
- blockers
- exact next step
- copyable startup prompt

## 12. T-0006 Result

This task produces a design candidate only.

It does not:

- enter a real business project
- create or modify real business project files
- modify `AGENTS.md`
- install or enable skill/MCP/agent/automation/protocol behavior
- deploy or roll back
- touch database, permission, secret, payment, production data, or migration resources

## 13. Recommended Next Step

After T-0006 is reviewed, the next likely step is a separate gate for either:

- repairing this T-0006 candidate, or
- approving a first real-project discovery task that applies this protocol to a named project or product idea

No real-project application should be inferred from this design.
