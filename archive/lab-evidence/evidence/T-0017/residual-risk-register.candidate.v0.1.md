# Residual Risk Register Candidate v0.1

Status: candidate evidence only
Task: T-0017

## Register

| ID | Severity | Risk | Handling | Next Review Point |
| --- | --- | --- | --- | --- |
| RR-T0017-001 | P1 | Handoff or progress may stay stale and point to T-0016. | Update closeout records before completion. | T-0017 closeout |
| RR-T0017-002 | P1 | Architecture baseline could be mistaken for build approval. | Repeat boundary in architecture and readiness docs. | T-0018 review |
| RR-T0017-003 | P1 | T-0017 candidate may be mistaken for real-project entry. | Keep package-level candidate-only wording. | T-0018 review |
| RR-T0017-004 | P2 | Package lacks worked examples for a real project. | Defer to later dry-run or example task. | pre-real-project validation |
| RR-T0017-005 | P2 | Markdown rules are not machine-enforced. | Defer automation to later tooling gate. | future tooling task |
| RR-T0017-006 | P2 | Contract names may not map 1:1 to this governance lab's `.ai` scripts. | Record as design guidance, not runtime behavior. | T-0018 review |
| RR-T0017-007 | P2 | `.ai/KNOWN_ISSUES.md` contains stale phase wording outside the approved T-0017 write paths. | Do not repair under T-0017; recommend separate narrow memory-repair gate if needed. | next governance-memory repair |

## Boundary

Residual risks do not authorize implementation, real-project entry, AGENTS.md
change, installation, runtime/tool enablement, deployment, rollback, database,
permission, secret, payment, production-data, or migration action.
