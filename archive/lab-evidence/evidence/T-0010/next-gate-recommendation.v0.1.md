# Next Gate Recommendation v0.1

Status: candidate repair evidence
Task: T-0010

## Recommendation

Open a review-rerun / baseline-readiness review gate next.

Recommended gate:

```text
G-T-0011-METHOD-REPAIR-REVIEW-RERUN
```

Recommended type:

```text
review-rerun / baseline-readiness-review-only
```

## Purpose

Review the T-0010 repaired candidate package and decide whether it can be promoted to `baseline_candidate` for a later separate user baseline approval gate.

## Proposed Allowed Actions

- create `.ai/tasks/T-0011.md`
- create `.ai/evidence/T-0011/`
- read `.ai/evidence/T-0008/`, `.ai/evidence/T-0009/`, and `.ai/evidence/T-0010/`
- review T-0010 from product, domain, architecture, backend/API, frontend/UX, QA/test, security, DevOps/SRE, governance/audit, and handoff/context roles
- assess whether P1 repairs are sufficient
- assess whether major P2 repairs are sufficient or need deferral
- produce review-rerun findings, residual risk, and baseline-readiness recommendation
- update approved `.ai` governance files
- run `validate_state.py`

## Proposed Forbidden Actions

- do not install or enable the repaired method
- do not modify `AGENTS.md`
- do not enter a real business project root
- do not create or modify real business project files
- do not continue T-0007 product sample
- do not modify Harness artifacts
- do not build, implement, deploy, roll back, migrate, change permissions, handle secrets, process payments, or touch production data
- do not treat review PASS as baseline approval
- do not treat validator success as user approval

## Later Gates Still Required

Even if T-0011 passes, separate gates are still required for:

- baseline approval
- activation/reference use
- installation or `AGENTS.md` update
- real-project application
- implementation
- release or high-risk actions

## Not Recommended Next

Do not recommend installation, `AGENTS.md` modification, or real-project application immediately after T-0010. The repaired candidate needs review-rerun evidence first.
