# User Decision Packet

## Gate

```text
G-T-0018-REAL-PROJECT-DELIVERY-ARCHITECTURE-GOVERNANCE-REVIEW
```

## Decision Options

Approve:

```text
批准 G-T-0018-REAL-PROJECT-DELIVERY-ARCHITECTURE-GOVERNANCE-REVIEW
```

Reject:

```text
拒绝 G-T-0018-REAL-PROJECT-DELIVERY-ARCHITECTURE-GOVERNANCE-REVIEW
```

Request repair:

```text
修复 G-T-0018-REAL-PROJECT-DELIVERY-ARCHITECTURE-GOVERNANCE-REVIEW
```

## What Approval Allows

Approval allows Codex to perform a review-only assessment of the T-0017
candidate package and produce T-0018 review evidence.

Expected review focus:

- lifecycle and gate consistency
- real-project entry isolation
- product discovery usefulness
- domain model and PRD completeness
- architecture baseline quality
- detailed design package depth
- implementation readiness boundaries
- review and quality gates
- traceability and evidence schema
- security, data, deployment, and high-risk boundaries
- handoff and context hygiene
- residual risks from T-0017
- whether Markdown-only rules are sufficient
- controls that rely on AI self-discipline
- whether to recommend a later enforcement architecture task

## What Approval Does Not Allow

Approval does not allow Codex to enter a real business project, write business
code, implement, build, deploy, release, roll back, modify `AGENTS.md`, repair
T-0017 artifacts, install or enable skill/MCP/runtime/tool behavior, change
global or project runtime behavior, or touch database, permission, secret,
payment, production-data, or migration resources.

## Expected Output If Approved

The review should classify findings by severity as `P0`, `P1`, `P2`, or `P3`
and recommend one of:

- `repair required`
- `baseline consideration ready`
- `reject / supersede`
- `defer to later dry-run`

If enforcement architecture is incomplete, the review should recommend a later
separate task such as `T-0019` for MCP / skill / policy guard design.
