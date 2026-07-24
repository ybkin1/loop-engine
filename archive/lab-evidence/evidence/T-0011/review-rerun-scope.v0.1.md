# Review Rerun Scope v0.1

Status: evidence
Task: T-0011
Gate: G-T-0011-METHOD-REPAIR-REVIEW-RERUN

## Purpose

Review the T-0010 repaired candidate package after the T-0009 findings, and decide whether the package is ready to be recommended as `baseline_candidate`.

## Reviewed Sources

- `.ai/evidence/T-0008/` for the original method candidate context.
- `.ai/evidence/T-0009/` for original review findings and repair recommendations.
- `.ai/evidence/T-0010/` for repaired candidate evidence.

## Review Roles

- product
- domain
- architecture
- backend/API
- frontend/UX
- QA/test
- security
- DevOps/SRE
- governance/audit
- handoff/context

## Review Standard

- No unresolved P0 may remain.
- No unresolved P1 may remain before `baseline_candidate`.
- Major P2 findings must be repaired or explicitly deferred with owner, rationale, and next review point.
- Candidate, baseline, active reference, installed behavior, and real-project application must remain separate.

## Forbidden Scope Confirmation

No review step authorizes installation, `AGENTS.md` changes, real-project entry, business project file writes, implementation, deployment, rollback, high-risk operations, or runtime behavior changes.
