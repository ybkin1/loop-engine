# Role Review Findings v0.1

Status: evidence
Task: T-0009
Reviewed target: T-0008 candidate method design

## Executive Result

T-0008 is directionally strong and safer than the T-0006/T-0007 linear interview approach. It correctly shifts structured project work to AI roles and keeps the user responsible for business truth and gate decisions.

It is not ready for baseline approval or installation. It needs a repair pass that converts high-level method concepts into enforceable templates, schemas, checklists, and state transitions.

## P0 Findings

No P0 findings.

Rationale: T-0008 explicitly says it is candidate-only, does not modify `AGENTS.md`, does not enable runtime behavior, and keeps real-project entry, implementation, installation, deployment, rollback, high-risk resources, and gate approval separate.

## Findings Table

| ID | Severity | Role | Finding | Impact | Repair Recommendation |
| --- | --- | --- | --- | --- | --- |
| F-001 | P1 | Governance/Audit | Candidate, reviewed, repaired, baseline-approved, active, installed, and superseded states are named but not defined as a formal lifecycle with allowed transitions. | Future sessions could confuse candidate evidence with approved baseline or installed behavior. | Add a method-artifact lifecycle table with state definitions, transition triggers, required evidence, and forbidden interpretations. |
| F-002 | P1 | Project Manager | The review and repair loop is described, but not operationalized as task sequence, evidence names, rerun criteria, or completion rules. | A later repair task may be inconsistent or may skip rerun review after repairs. | Define a repeatable repair cycle: findings -> repair plan -> patched artifacts -> diff summary -> rerun review -> residual risk -> next gate. |
| F-003 | P1 | Governance/Audit | Real-project entry is separately gated, but there is no concrete project-root isolation protocol or changed-path audit requirement. | A future session could enter or write a real business project while believing a method gate is sufficient. | Add a real-project entry gate template requiring target root, allowed paths, forbidden paths, changed-path baseline, and exit criteria. |
| F-004 | P1 | Architect | Harness-depth generation is described as a target, but T-0008 lacks artifact schemas that tell AI exactly how to generate comparable documents. | The method may still produce shallow documents with correct names. | Add document templates or required sections for PRD, architecture, API, data, UX, security, tests, observability, release, risk, and handoff artifacts. |
| F-005 | P2 | Product Manager | User workload is narrowed conceptually, but no interaction budget or correction packet format is defined. | The method may drift back into long Q&A despite the new premise. | Add a user-decision packet template with assumptions, decisions, tradeoffs, and max-question guidance per gate. |
| F-006 | P2 | Domain Analyst | Domain modeling artifacts are listed, but source-of-truth confidence, unknown ownership, and role-conflict resolution are not formal fields. | Business-domain assumptions may look more certain than they are. | Add confidence, evidence source, owner, and unresolved conflict columns to domain and data authority matrices. |
| F-007 | P2 | Backend/API Reviewer | API, data, workflow, event, and error-code artifacts are listed, but no traceability schema ties them together. | Implementation planning may start with contract gaps. | Add cross-artifact IDs and required links: requirement -> workflow -> API/event -> data -> test. |
| F-008 | P2 | Frontend/UX Reviewer | UX specification is listed, but required screen states, error states, empty states, responsive behavior, accessibility, and API contracts are not defined. | The design baseline may be incomplete for frontend implementation. | Add a UX artifact schema with page map, state model, interactions, loading/error/empty states, accessibility, and API dependencies. |
| F-009 | P2 | QA/Test Reviewer | Testing is present as a stage, but method-level quality gates and design-level tests are not specified. | The method cannot prove candidate docs are baseline-ready. | Add design quality gates: artifact coverage, traceability, contradiction scan, risk-to-test mapping, and residual-risk approval. |
| F-010 | P2 | Security Reviewer | Security review topics are listed, but threat modeling, sensitive-data classification, permission matrix, audit logging, and secret-handling evidence requirements are not formalized. | Security may remain a checklist rather than an auditable design artifact. | Add a security artifact schema and a high-risk gate checklist for secrets, permissions, production data, and migrations. |
| F-011 | P2 | DevOps/SRE Reviewer | Observability, release, and rollback are listed, but environment assumptions, alert thresholds, runbooks, and operational ownership are not required fields. | Release readiness could be asserted without operational evidence. | Add observability/release schemas with metrics, alerts, runbooks, rollback, smoke checks, and owner assumptions. |
| F-012 | P2 | Handoff/Context Reviewer | T-0008 warns against handoff pollution, but does not define contamination checks for test-case details such as T-0007. | Future method sessions may accidentally resume concrete product samples as current mainline. | Add a handoff context hygiene checklist: current mainline, quarantined test cases, forbidden carryover, and next gate. |
| F-013 | P3 | Project Manager | The 1-2 week target is useful, but lacks project-size bands and exit conditions for small, medium, and complex work. | Estimates may become overconfident. | Add complexity bands and design-baseline completion criteria. |
| F-014 | P3 | Governance/Audit | Gate status includes `completed`, while existing gate records mostly use `approved` plus task status for completion. | Naming may confuse gate decision status with task completion. | Clarify gate decision status versus task execution completion. |

## Baseline Readiness

Recommended status for T-0008 after this review:

```text
candidate-reviewed: true
repair-required: true
baseline-approved: false
installed: false
active-as-operating-rule: false
```
