# Loop Engine Method Diagnosis v0.1

Status: candidate design
Task: T-0008

## Diagnosis Summary

The current T-0006/T-0007 method is useful for lightweight clarification, but it is not sufficient for complex software delivery.

The central problem is role inversion: the method implicitly asks a non-technical solo user to behave like a project manager, product manager, architect, domain analyst, QA lead, and delivery reviewer. That is the opposite of the target Loop premise.

For the intended user, the AI Agent must do the structured modeling work first, then ask the user to correct high-value assumptions and approve gates.

## What Failed In T-0006/T-0007

T-0006 produced a candidate entry protocol, and T-0007 used a one-question-at-a-time discovery flow as a stress test. The stress test exposed these weaknesses:

- the interaction focused on individual questions before the business domain had a visible model
- the user had to notice missing roles, missing flows, and wrong decomposition
- the AI asked for workflow details before producing a domain map, data authority map, subflow map, and exception model
- each answer updated a few local artifacts, but the whole design package did not expand to professional project-design depth
- the method did not create a complete document architecture before drafting content
- cross-document consistency, traceability, and role review were not first-class loops
- the user communication cost grew linearly with system complexity

## Depth Mismatch

The Harness artifacts benchmark shows that a serious project design baseline can include dozens of documents across architecture, API, data, UX, security, monitoring, tests, risks, MVP scope, sprint plan, future-state design, and gap assessment.

A question-by-question interview cannot efficiently generate that level of coverage because every missing topic must be discovered through user prompting. For a non-technical solo user, this can stretch into 8-12 weeks or longer, while still leaving blind spots.

The repaired method should target a 1-2 week design-baseline cycle for a substantial project:

- AI produces the first model and artifact map within 1-2 days
- AI drafts candidate documents in batches
- AI runs role review and gap repair loops
- the user reviews summaries, corrections, and gate decisions instead of authoring the structure

## Root Causes

### 1. Interview-First Bias

The current flow starts by asking the user what matters. That is reasonable for shallow discovery, but weak for complex systems. The better default is model-first:

- infer likely domain structure
- mark assumptions explicitly
- produce candidate diagrams and matrices
- ask the user to correct the model in batches

### 2. Missing Role Simulation

A professional team would review the same idea from multiple perspectives. The current flow did not consistently simulate:

- product management
- domain analysis
- architecture
- backend/API design
- frontend/UX design
- QA and release
- security and permissions
- operations and observability
- project planning
- audit and handoff

### 3. Artifact Blindness

The current method creates evidence files, but it does not start from a full artifact matrix. Without a matrix, the process cannot know what is missing.

### 4. Weak Traceability

Requirements, roles, workflows, data ownership, APIs, screens, tests, and gates must trace to each other. The current flow updates documents, but does not force a traceability audit.

### 5. User Cognitive Overload

The intended user should not need to know which documents a professional software project requires. The AI should present:

- what it assumed
- what it generated
- what is risky
- what decision is needed now

## Required Repair

T-0008 should convert Loop from a linear interview method into an AI-led engineering method:

1. Intake the raw idea.
2. Generate a domain model candidate.
3. Generate an artifact map.
4. Draft documents in batches.
5. Run multi-role review.
6. Run gap and traceability assessment.
7. Repair documents.
8. Ask the user for focused corrections and gate decisions.
9. Baseline the design.
10. Continue into implementation planning only after explicit approval.

## Non-Negotiable Boundary

This diagnosis is a candidate design artifact only. It does not install a new method, modify `AGENTS.md`, enable tools, enter a real project, or approve implementation.
