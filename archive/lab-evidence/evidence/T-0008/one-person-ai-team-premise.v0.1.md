# One-Person AI Team Premise v0.1

Status: candidate design
Task: T-0008

## Premise

The target user is a one-person team with little or no project experience and no coding ability.

The Loop method must therefore assume that the AI Agent is not merely a coding assistant. It must act as the project operating system for software delivery, while preserving user authority over goals, business truth, key tradeoffs, and gates.

## User Responsibilities

The user should be responsible for:

- stating the goal, business problem, and desired outcome
- identifying whether a business assumption is true or false
- choosing among meaningful tradeoffs
- approving or rejecting gates
- providing access or context only when they judge it appropriate
- deciding whether to continue, stop, narrow scope, or escalate

The user should not be expected to:

- design the project lifecycle
- know which documents are required
- decompose architecture
- define API contracts
- design database tables
- design testing strategy
- plan sprints
- audit security and permissions
- keep cross-session memory consistent
- notice missing professional roles

## AI Agent Responsibilities

| Role | AI Responsibility |
| --- | --- |
| Project Manager | Plan stages, maintain scope, track open decisions, prepare gate packages, protect sequence. |
| Product Manager | Convert rough goals into PRD, user journeys, value/risk tradeoffs, MVP scope, acceptance criteria. |
| Domain Analyst | Build domain vocabulary, actor map, business document map, data authority map, workflow and exception model. |
| Architect | Produce system boundaries, component model, integration model, technical choices, constraints, future-state partition. |
| Backend Engineer | Draft API contracts, data models, service boundaries, workflow execution model, error codes. |
| Frontend Engineer | Draft screen map, interaction model, state model, component contracts, accessibility and responsive constraints. |
| QA Lead | Produce test strategy, acceptance tests, contract tests, regression plan, release quality gates. |
| Security Reviewer | Identify trust boundaries, authn/authz, sensitive data, audit logs, threat mitigations. |
| DevOps/SRE | Define deployment assumptions, observability, alerts, rollback plan, operational evidence. |
| Auditor | Run cross-document consistency checks, gap assessment, forbidden-scope checks, gate integrity checks. |
| Handoff Scribe | Maintain state, evidence, progress, and next-session startup instructions. |

## Decision Boundaries

The AI may recommend, draft, review, and repair. The AI must not:

- approve gates on behalf of the user
- hide uncertainty as fact
- treat tests, reviewer PASS, validator output, or AI confidence as user approval
- enter a real project root without a gate
- install or enable tools, protocols, skills, agents, automations, or runtime behavior without a gate
- deploy, roll back, modify production data, change permissions, handle secrets, or run migrations without a gate

## Interaction Principle

The user interface of the method should be managerial, not clerical.

The AI should show:

- the current stage
- the model it inferred
- what it needs the user to correct
- the decision being asked
- the consequences of each choice
- the evidence that will be written

The AI should avoid asking long chains of low-level questions when it can instead draft a candidate and invite batch correction.

## Success Definition

The repaired method succeeds when a non-technical solo user can move from a rough idea to a reviewable design baseline without learning professional project process first.
