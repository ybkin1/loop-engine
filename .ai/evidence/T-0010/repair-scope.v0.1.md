# Repair Scope v0.1

Status: candidate repair evidence
Task: T-0010
Gate: G-T-0010-METHOD-CANDIDATE-REPAIR

## Purpose

Repair the T-0008 Loop engineering method candidate based on T-0009 findings while keeping all outputs candidate-only.

This repair does not approve, install, enable, or apply the method. It only creates a stronger candidate package for a later review-rerun or baseline-readiness review.

## Source Findings

The repair uses T-0009 as source evidence:

- F-001 P1: missing formal method lifecycle state model
- F-002 P1: missing executable repair loop
- F-003 P1: missing real-project entry isolation protocol
- F-004 P1: missing Harness-depth artifact schemas
- F-005 P2: missing user decision packet and interaction budget
- F-006 P2: missing confidence, source, owner, and conflict fields
- F-007 P2: missing cross-document traceability IDs
- F-008 P2: incomplete UX state and accessibility schema
- F-009 P2: missing design-level QA gates
- F-010 P2: incomplete security and high-risk action schema
- F-011 P2: incomplete observability, runbook, and alert schema
- F-012 P2: missing handoff contamination checks
- F-013 P3: missing complexity bands and exit conditions
- F-014 P3: gate decision status and task completion status need separation

## Repair Deliverables

| Deliverable | Covers |
| --- | --- |
| `method-lifecycle-state-model.v0.1.md` | F-001, F-014 |
| `gate-request-template.v0.1.md` | F-001, F-003, F-014 |
| `real-project-entry-gate-template.v0.1.md` | F-003 |
| `artifact-schema-catalog.v0.1.md` | F-004 through F-011 |
| `traceability-id-system.v0.1.md` | F-006, F-007, F-009 |
| `user-decision-packet-template.v0.1.md` | F-005 |
| `repair-loop-protocol.v0.1.md` | F-002 |
| `handoff-context-hygiene-checklist.v0.1.md` | F-012 |
| `design-baseline-readiness-checklist.v0.1.md` | F-001 through F-013 |
| `repair-summary.v0.1.md` | consolidated coverage |
| `next-gate-recommendation.v0.1.md` | next decision |

## Allowed Scope

- Create `.ai/tasks/T-0010.md`.
- Create `.ai/evidence/T-0010/`.
- Read `.ai/evidence/T-0008/` and `.ai/evidence/T-0009/`.
- Read Harness artifacts only as a design-depth benchmark if needed.
- Write T-0010 candidate repair evidence.
- Update `.ai/state.yaml`, `.ai/task_graph.yaml`, `.ai/gates.yaml`, `.ai/PROGRESS.md`, and `.ai/HANDOFF.md`.
- Run `validate_state.py`.

## Forbidden Scope

- Do not continue the concrete T-0007 product sample.
- Do not modify Harness artifacts.
- Do not create a real product project.
- Do not enter a real business project root.
- Do not create or modify real business project files.
- Do not write business project code.
- Do not build, implement, deploy, or roll back.
- Do not modify `AGENTS.md`.
- Do not install or enable skill, MCP, agent, automation, or protocol behavior.
- Do not change global or project runtime behavior.
- Do not change databases, permissions, secrets, payment systems, production data, or migrations.
- Do not treat validator success, reviewer PASS, tests, or AI recommendations as user approval.
- Do not treat this repair as baseline approval.
- Do not treat the repaired candidate method as installed or active operating rules.

## Candidate-Only Boundary

The repaired method package may be used only as evidence for a later review. It is not a standing instruction for future projects until a separate user-approved baseline and installation/rule-change gate says so.
