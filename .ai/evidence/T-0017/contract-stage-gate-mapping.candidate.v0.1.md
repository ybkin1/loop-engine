# Contract Stage Gate Mapping Candidate v0.1

Status: candidate evidence only
Task: T-0017

## Purpose

Map stage, artifact, contract family, and gate so future real-project work does
not lose the connection between delivery flow and quality checks.

## Mapping

| Stage | Key Artifacts | Contract Families | Gate |
| --- | --- | --- | --- |
| S0 Idea Intake | product intent, scope boundary | intent, task tracking | discovery/design gate |
| S1 Domain Model | actors, objects, source-of-truth, workflows | requirement refinement, scenario traceability | domain correction gate |
| S2 Discovery | discovery baseline, risk register | document depth, review gates | discovery baseline gate |
| S3 PRD | PRD, acceptance, requirements traceability | PRD output, scenario traceability | PRD baseline gate |
| S4 Architecture | architecture nodes, ADRs, data ownership | architecture blueprint, architecture breakdown | architecture baseline gate |
| S5 Detailed Design | API/data/UX/security/test design | design output, execution traceability | detailed design gate |
| S6 Planning | work packets, dev plan, dependency graph | work packet governance, dev plan output | implementation readiness gate |
| S7 Coding | code/config changes, tests | coding, security, testing, traceability | build gate |
| S8 Testing/Repair | test report, review report, findings | testing standards, review gates | review/repair gate |
| S9 Release | release readiness, smoke, monitoring, rollback | deployment governance, resilience, observability | deployment gate |
| S10 Handoff | handoff, evidence index, known issues | closeout, dirty hygiene | closeout/iteration gate |

## Checker Principle

Checkers are evidence producers. They cannot approve a gate.

## Boundary

This mapping is guidance for future gated work. It does not enable any checker,
runtime behavior, tool, or automation.
