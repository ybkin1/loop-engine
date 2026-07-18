# User Decision Packet: Real Project Governance Enforcement Architecture Review

Status: pending user decision
Task: T-0020
Gate: G-T-0020-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-REVIEW

## Decision Needed

Approve, reject, or request repair of the T-0020 review-only gate.

## Why This Gate Exists

T-0019 produced candidate enforcement architecture evidence to repair the
T-0018 P1 finding that Markdown governance rules over-relied on AI
self-discipline and lacked enforceable gate, checker, policy guard, wrapper,
and tool-entry controls.

This T-0020 gate exists only to authorize an independent review of that
candidate package.

## If You Approve

Codex may perform the T-0020 review-only workflow and produce review evidence
under `.ai/evidence/T-0020/`.

Acceptable review conclusions are:

- `PASS_FOR_BASELINE_CONSIDERATION`
- `REPAIR_REQUIRED`
- `BLOCKED_BY_SCOPE_OR_MISSING_EVIDENCE`

## If You Reject

Codex will not perform the T-0020 review. T-0019 remains a design-only
candidate package and is not baseline-approved.

## If You Request Repair

Codex may revise this gate package only, within `.ai` governance records, and
must not proceed into the T-0020 review until a repaired gate is explicitly
approved.

## Explicit Non-Authorization

Approval of this gate would not authorize:

- implementing any checker
- installing or enabling MCPs, skills, policy guards, wrappers, automations,
  protocols, runtimes, or tool behavior
- modifying `AGENTS.md`
- entering, creating, or modifying a real business project
- writing business code
- build, deployment, release, or rollback
- database, permission, secret, payment, production-data, or migration actions
- promoting T-0019 to baseline, active, installed, or real-project-applicable
  state

## Exact Gate ID To Approve

```text
G-T-0020-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-REVIEW
```

## Exact Approval Phrase

```text
批准 G-T-0020-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-REVIEW
```
