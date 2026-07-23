# Repair Loop Protocol v0.1

Status: candidate repair evidence
Task: T-0010

## Purpose

Make review and repair executable. A finding should lead to traceable repair evidence, not just a recommendation.

## Loop Overview

```text
findings -> repair scope -> repair plan -> changed artifact list -> diff summary -> rerun review -> residual risk -> next gate recommendation
```

## Required Evidence

| Step | Evidence |
| --- | --- |
| Findings | `role-review-findings.<stage>.vX.md` or equivalent |
| Repair scope | `repair-scope.vX.md` |
| Repair plan | `repair-plan.vX.md` or section inside scope |
| Changed artifact list | `changed-artifacts.vX.md` or commands evidence |
| Diff summary | `diff-summary.vX.md` or repair summary |
| Rerun review | `review-rerun.vX.md` |
| Residual risk | `residual-risk.vX.md` or section inside rerun review |
| Next gate | `next-gate-recommendation.vX.md` |

## Finding Record Schema

```yaml
id: FIND-<severity>-<number>
source_task: <T-XXXX>
severity: P0|P1|P2|P3
role: <review role>
artifact: <path or artifact ID>
finding: <issue>
impact: <why it matters>
repair_recommendation: <repair>
owner: <AI role or user if business truth is required>
source: <evidence path>
confidence: high|medium|low|unknown
status: open|repair_planned|repaired|deferred|blocked
linked_ids:
  - <ART-* or REQ-* etc>
```

## Repair Plan Schema

```yaml
repair_id: REPAIR-<number>
findings:
  - FIND-*
allowed_scope:
  - <scope>
forbidden_scope:
  - <scope>
artifacts_to_create:
  - <path>
artifacts_to_update:
  - <path>
validation:
  - <command or review>
user_decisions_required:
  - <DEC-* or none>
exit_criteria:
  - <condition>
```

## Rerun Review Criteria

A repair is not ready for baseline recommendation until rerun review confirms:

- no unresolved P0
- no unresolved P1
- major P2 fixed or explicitly deferred with rationale
- lifecycle state is correct
- traceability checks pass or gaps are documented
- user decision packet is available for remaining business decisions
- forbidden scope was not crossed

## Residual Risk Rules

Residual risk must record:

- risk ID
- affected artifacts
- severity
- owner
- reason it remains
- mitigation or deferral rationale
- user decision needed, if any
- next review point

## Completion Rule

The repair loop can end only with one of:

- `baseline_candidate_recommended`
- `repair_required_again`
- `blocked_needs_user_decision`
- `rejected_or_superseded`

## T-0010 Application

T-0010 completes the first repair pass and recommends a later review-rerun / baseline-readiness review. It does not itself perform baseline approval, installation, or real-project application.
