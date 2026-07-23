# Repair Recommendations v0.1

Status: evidence
Task: T-0009

## Recommendation Summary

T-0008 should go through a repair-only task before any baseline approval or installation gate is considered.

The repair should preserve the strong direction of T-0008:

- AI leads modeling and document generation
- user provides goals, business truth, tradeoffs, and gate decisions
- T-0007 remains only a stress-test sample unless explicitly reopened
- installation and real-project application remain separately gated

The repair should add enforcement detail.

## Required P1 Repairs

1. Add a method lifecycle state model.

   Required states: `candidate`, `reviewed`, `repair_required`, `repaired`, `baseline_candidate`, `baseline_approved`, `active_reference`, `installed`, `superseded`.

   Each state needs allowed actions, forbidden interpretations, required evidence, and transition gates.

2. Add a repeatable repair loop protocol.

   Required evidence: findings, repair plan, changed artifact list, diff summary, rerun review, residual risk, and next gate recommendation.

3. Add real-project entry isolation.

   Required fields: target project root, allowed paths, forbidden paths, changed-path baseline, path audit, no-write directories, permitted commands, verification plan, and exit gate.

4. Add artifact schema catalog.

   Required schemas: PRD, domain model, architecture, API, data model, workflow/state, UX, security, test, observability, release/rollback, risk, sprint plan, handoff, and baseline readiness.

## Important P2 Repairs

- Add a user decision packet template.
- Add interaction budget rules to prevent long low-level Q&A.
- Add confidence/source/owner/conflict fields to domain artifacts.
- Add cross-document traceability IDs.
- Add UX state and accessibility requirements.
- Add design-level QA gates.
- Add security-sensitive data and high-risk action checklists.
- Add SRE runbook and alert fields.
- Add handoff contamination checks.
- Add complexity bands for the 1-2 week target.

## Suggested Repair Evidence Package

For a future T-0010 repair-only task:

- `commands.md`
- `repair-scope.v0.1.md`
- `method-lifecycle-state-model.v0.1.md`
- `gate-request-template.v0.1.md`
- `real-project-entry-gate-template.v0.1.md`
- `artifact-schema-catalog.v0.1.md`
- `traceability-id-system.v0.1.md`
- `user-decision-packet-template.v0.1.md`
- `repair-loop-protocol.v0.1.md`
- `handoff-context-hygiene-checklist.v0.1.md`
- `design-baseline-readiness-checklist.v0.1.md`
- `repair-summary.v0.1.md`
- `next-gate-recommendation.v0.1.md`

## Recommended Baseline Rule

Do not approve, install, or apply the repaired method until:

- P1 findings are repaired
- major P2 findings are repaired or explicitly deferred
- the artifact schema catalog exists
- the lifecycle state model separates candidate, baseline, active reference, and installed behavior
- a review rerun produces no unresolved P0/P1 findings
- the user explicitly approves a later baseline gate

Validator success is evidence only. It is not baseline approval.
