# AI Role Review Loop v0.1

Status: candidate design
Task: T-0008

## Purpose

The repaired Loop method must make the AI perform the multi-role review that a real project team would normally provide.

This is not a claim that AI review equals human approval. It is a structured way to find gaps before asking the user to decide.

## Review Roles

| Role | Review Focus |
| --- | --- |
| Product Reviewer | Does the design solve the stated business problem, and is MVP scope coherent? |
| Domain Reviewer | Are roles, responsibilities, data authority, workflows, and exceptions realistic? |
| Architecture Reviewer | Are boundaries, dependencies, state, integration, and future extension clear? |
| Backend Reviewer | Are API contracts, data models, transactions, errors, and idempotency implementable? |
| Frontend Reviewer | Are screens, interactions, loading/error states, and handoff contracts clear? |
| QA Reviewer | Are acceptance criteria, test levels, fixtures, regressions, and release gates sufficient? |
| Security Reviewer | Are trust boundaries, permissions, secrets, sensitive data, and audit logs covered? |
| Operations Reviewer | Are observability, alerts, deployment, rollback, and support workflows clear? |
| Project Reviewer | Are milestones, dependencies, risks, and decision points sequenced correctly? |
| Handoff Reviewer | Can the next session resume from disk without relying on chat memory? |
| Governance Reviewer | Are gates, evidence, and forbidden-scope rules respected? |

## Severity Scale

| Severity | Meaning | Required Action |
| --- | --- | --- |
| P0 | Unsafe or gate-breaking flaw | Stop and ask for user decision or repair before continuing |
| P1 | Major design blocker | Repair before baseline approval |
| P2 | Important gap or inconsistency | Repair or explicitly defer with rationale |
| P3 | Minor clarity or polish issue | Fix opportunistically or record as non-blocking |

## Review Loop

1. AI drafts a candidate artifact batch.
2. AI runs role reviews against the batch.
3. AI produces a findings table with severity, artifact, issue, impact, and repair.
4. AI repairs P0/P1/P2 findings or asks the user when the repair changes business scope.
5. AI reruns review on the repaired batch.
6. AI produces a baseline recommendation only when remaining risks are explicit.
7. User approves, rejects, narrows, or requests repair.

## Cross-Document Review

The role review must include cross-document consistency checks:

- every PRD requirement has at least one workflow and acceptance criterion
- every workflow state has an owner, trigger, data source, and terminal condition
- every API endpoint maps to a product capability or system need
- every sensitive data field has an access rule and audit implication
- every UI action maps to an API/event/state transition
- every release risk maps to a test, monitor, or rollback step
- every deferred feature is marked as later phase or non-goal

## User Interaction Rule

The user should not receive raw review noise. The AI should present:

- blocking issues
- business decisions required
- material tradeoffs
- proposed repairs
- what will change if approved

The full findings table remains in evidence.

## Anti-Patterns

The method must avoid:

- treating a single AI answer as review
- asking the user to do specialist review
- calling validator success a design approval
- hiding uncertain assumptions
- pushing implementation forward while P0/P1 design issues remain

## Output

Each review cycle should produce:

- `role-review.<stage>.vX.md`
- `gap-assessment.<stage>.vX.md`
- `repair-plan.<stage>.vX.md`
- updated artifacts
- gate recommendation when stage transition is ready
