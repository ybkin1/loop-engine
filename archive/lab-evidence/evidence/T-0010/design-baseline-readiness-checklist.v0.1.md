# Design Baseline Readiness Checklist v0.1

Status: candidate repair evidence
Task: T-0010

## Purpose

Define what must be true before a repaired method package or generated project design can be recommended for baseline approval.

## Lifecycle Readiness

- [ ] Artifact is at least `repaired`.
- [ ] Review rerun completed.
- [ ] No unresolved P0.
- [ ] No unresolved P1.
- [ ] Major P2 findings fixed or explicitly deferred.
- [ ] Baseline candidate state is recorded separately from baseline approval.
- [ ] User baseline approval gate is still separate.
- [ ] Installation or runtime behavior gate is still separate.

## Artifact Coverage

- [ ] Package index exists.
- [ ] PRD exists when product behavior is in scope.
- [ ] Domain model exists.
- [ ] Architecture exists.
- [ ] API schema exists when backend behavior is in scope.
- [ ] Data model exists when persisted data is in scope.
- [ ] Workflow/state design exists.
- [ ] UX schema exists when user interface is in scope.
- [ ] Security schema exists.
- [ ] Test/QA schema exists.
- [ ] Observability/SRE schema exists when operated service is in scope.
- [ ] Release/rollback schema exists before release planning.
- [ ] Risk register exists.
- [ ] Sprint or execution plan exists before implementation planning.
- [ ] Handoff exists.

## Traceability

- [ ] Each `REQ-*` links to `GOAL-*`, `AC-*`, `WF-*`, and `TEST-*`.
- [ ] Each `WF-*` links to owner, data, UI/API/event, and terminal state.
- [ ] Each `API-*` links to requirement, data, error, and test.
- [ ] Each sensitive `DATA-*` links to `SEC-*`.
- [ ] Each release risk links to test, monitor, or rollback.
- [ ] No orphan MVP requirement remains.
- [ ] Conflicts are resolved or explicitly deferred.

## Role Review

- [ ] Product review complete.
- [ ] Domain review complete.
- [ ] Architecture review complete.
- [ ] Backend/API review complete when applicable.
- [ ] Frontend/UX review complete when applicable.
- [ ] QA/test review complete.
- [ ] Security review complete.
- [ ] DevOps/SRE review complete when applicable.
- [ ] Governance/audit review complete.
- [ ] Handoff/context review complete.

## User Decision Packet

- [ ] Assumptions needing user confirmation are batched.
- [ ] No more than 3 direct questions are asked in one packet.
- [ ] Decisions include options, tradeoffs, and recommendations.
- [ ] Gate scope and non-authorized actions are explicit.
- [ ] User approval remains explicit and separate.

## Complexity Bands

| Band | Typical Scope | Baseline Expectation |
| --- | --- | --- |
| Small | Single workflow or narrow internal tool | Core PRD, domain, workflow, UX/API as needed, tests, risk, handoff. |
| Medium | Several roles, integrations, or data ownership concerns | Full package index, PRD, domain, architecture, API/data/UX, security, QA, observability, risk, sprint plan. |
| Complex | Multi-role, cross-department, production operations, compliance, or high-risk resources | Harness-like package with deep schemas, traceability matrix, role review, release/rollback, runbooks, and baseline-readiness review. |

## Exit Outcomes

Allowed outcomes:

- `baseline_candidate_recommended`
- `repair_required_again`
- `blocked_needs_user_decision`
- `not_ready`
- `superseded`

Disallowed outcomes:

- install method because checklist passed
- enter real project because checklist passed
- approve baseline because AI recommends it
- skip user gate because validation passed

## T-0010 Status

T-0010 repairs the method candidate enough to request a review-rerun / baseline-readiness review. It does not itself complete that review.
