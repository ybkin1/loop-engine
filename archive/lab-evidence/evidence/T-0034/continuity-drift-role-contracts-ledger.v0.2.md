# Continuity And Drift Role Contracts And Ledger v0.2

Contract ID: `CDRL-2026-07-16-R1`. Satisfies `OUT-06` and contributes to `WS-02` and `WS-07`.

## 1. Drift Dimensions

| Dimension | Comparison | Detects |
|---|---|---|
| `step_drift` | Current stable state vs immediately previous stable state | Sudden omissions, unauthorized local changes, lost findings, changed interfaces. |
| `anchor_drift` | Current state vs approved canonical baseline/golden reference | Cumulative micro-drift, architecture/style/interface divergence, authority erosion. |
| `goal_drift` | Current/delivered outcome vs user north star and observable success | Locally coherent work that no longer solves the user's problem or reduces burden. |

Drift is reported as `severity`, `trend`, `authorization`, `impact`, `evidence`, and `correction_status`; no false-precision percentage is allowed.

## 2. Continuity Checker Contract

```yaml
role: ContinuityChecker/v1.0
inputs: [previous_checkpoint, current_checkpoint, PCC, changed_path_manifest]
outputs: [continuity_acknowledgment, step_drift_findings, missing_field_findings]
mode: deterministic_lightweight
may_edit: false
may_approve: false
```

Responsibilities:

- Verify checkpoint required fields, generation, transaction inventory, hashes, authority, evidence manifest, and next action.
- Compare current/previous stable state and classify step drift.
- Return `ACK`, `REPAIR_REQUIRED`, or `BLOCKED`; never repair.

## 3. Drift Auditor Contract

```yaml
role: DriftAuditor/v1.0
inputs: [PCC, current_state, previous_state, golden_references, user_goal, DriftLedger]
outputs: [step_assessment, anchor_assessment, goal_assessment, findings, evidence_only_verdict]
mode: fresh_context_deep_review
may_edit: false
may_approve: false
```

The auditor must inspect all three drift dimensions, cumulative trend, approved/unapproved deltas, and whether governance work is displacing delivery.

## 4. Continuity Repair Planner Contract

```yaml
role: ContinuityRepairPlanner/v1.0
inputs: [authorized_findings, PCC, exact_allowed_paths, protected_baselines]
outputs: [repair_plan, finding_to_change_map, validation_plan, recovery_plan]
may_edit: false
may_execute: false
may_expand_scope: false
```

The planner proposes the minimum additive correction for enumerated findings. It cannot silently re-baseline, delete evidence, modify unaffected files, or convert an audit verdict into approval.

## 5. Re-anchor Auditor Contract

```yaml
role: ReanchorAuditor/v1.0
inputs: [user_origin, product_north_star, PCC, full_current_product_state, roadmap, DriftLedger]
outputs: [goal_alignment, architecture_alignment, lifecycle_alignment, cumulative_drift_verdict]
trigger: phase_boundary|installation|activation|release|major_revision|repeated_drift
may_edit: false
may_approve: false
```

Re-anchor is whole-product reassessment, not an incremental diff review. It checks that the system still serves the user, preserves product identity and engineering invariants, and is moving toward real delivery.

## 6. `DriftLedger/v1.0`

```yaml
drift_ledger:
  ledger_id: string
  project_id: string
  canonical_revision: string
  entries:
    - drift_id: string
      detected_at: timestamp
      detector_role: string
      dimension: step|anchor|goal
      subject_refs: [EvidenceRef]
      baseline_ref: EvidenceRef
      previous_state_ref: EvidenceRef|null
      severity: P0|P1|P2|P3
      trend: new|stable|worsening|improving|recurrent
      authorization: approved|unapproved|conflicted|unknown
      affected_invariants: [string]
      impact: string
      evidence_refs: [EvidenceRef]
      correction_status: open|planned|repaired_pending_review|verified|accepted_risk|rebaselined
      correction_ref: EvidenceRef|null
      approval_ref: string|null
  cumulative_summary:
    open_by_dimension: {step: integer, anchor: integer, goal: integer}
    recurrent_patterns: [string]
    blocked_effects: [string]
    next_reanchor_trigger: string
```

Ledger entries are append-only. Correction changes status through a new event; original detection facts remain immutable.

## 7. Drift Rules

- `DRIFT-R01`: Any unapproved protected-invariant change is at least P1 and blocks dependent effects.
- `DRIFT-R02`: Missing baseline yields `BASELINE_MISSING`, not zero drift.
- `DRIFT-R03`: Three related P2 micro-drifts or two recurrences escalate trend to P1 review priority.
- `DRIFT-R04`: Goal drift blocks task/project PASS even when local checks pass.
- `DRIFT-R05`: Style, API, architecture, and visual drift use their declared golden comparison policy.
- `DRIFT-R06`: Approved change is not automatically safe; impact, compatibility, and user-goal alignment still require evidence.
- `DRIFT-R07`: Re-baseline requires explicit authority, source diff, impact assessment, new hashes, and lineage.
- `DRIFT-R08`: Repair without rereview remains `repaired_pending_review`.

## 8. Continuity Acknowledgment

```yaml
continuity_acknowledgment:
  checkpoint_id: string
  consumer_id: string
  consumer_generation: integer
  recovered_requirements_revision: string
  recovered_pcc_hash: string
  recovered_authority_hash: string
  recovered_transactions: [string]
  semantic_equivalence: PASS|REPAIR_REQUIRED|BLOCKED
  differences: [string]
  acknowledged_at: timestamp
```

Acknowledgment is invalid if any protected field is absent, any active transaction is lost, or the consumer generation is not current.

## 9. Machine Checks And Adversarial Scenarios

- `MC-DRIFT-001`: compare protected fields between previous/current checkpoints.
- `MC-DRIFT-002`: compare current invariants and golden hashes with anchor baseline.
- `MC-DRIFT-003`: trace output acceptance criteria to user goal.
- `MC-DRIFT-004`: validate ledger append-only lifecycle and escalation.
- `MC-REANCHOR-001`: verify mandatory trigger and complete whole-product dimensions.
- `ADV-DRIFT-001`: ten individually minor style deviations accumulate; expected worsening anchor drift.
- `ADV-DRIFT-002`: all tests pass but output no longer serves user goal; expected goal-drift blocker.
- `ADV-DRIFT-003`: repair overwrites original ledger entry; expected evidence-integrity failure.
- `ADV-DRIFT-004`: approved interface revision breaks a protected consumer; expected compatibility finding, not automatic PASS.

Review roles after a separate review Gate: continuity, product, architecture, API/style golden-reference, and evidence-integrity.

## 10. Boundary

These role contracts and ledger schema do not instantiate actors, run audits, repair artifacts, re-baseline, or authorize acceptance/closeout.
