# Loop-DORA Metrics Report

- **Status**: NOT_VERIFIED
- **Window**: 2026-07-06T17:44:53+08:00 → 2026-08-01T01:26:07.107031+00:00
- **Generated**: 2026-08-01T01:26:44.781587+00:00
- **Git commit**: e2eb30d9ceb00ef2528ce88f518d0ef429ba6b68
- **Task**: T-0090 (phase S6-delivery)
- **Tool**: loop_metrics v1.0.0
- **SLO source**: defaults (B2 §1.2 table); .ai/slo.yaml absent

**Missing data (14):** transitions (.ai/ledger/phase_transitions.jsonl); guard_decisions (.ai/ledger/guard_decisions.jsonl); runtime_events (.ai/ledger/runtime-events.jsonl); phase_dwell_time; rework_cycles_from_transitions; guard_block_pass_error_rates; drift_events; evidence_regeneration_events; sli:guard_block_rate; sli:drift_event_rate; sli:delta_quality_pass_rate; sli:evidence_regeneration_rate; sli:defect_fail_verdict_rate; sli:ac_invest_rate

## Error budget

- **Status**: HEALTHY
- **Remaining**: 100.0 / 100.0 units
- **Consumed**: 0.0 units (breaches 0.0 + releases 0.0)
- **Note**: advisory only (wave 1): budget exhaustion is reported, no release path is blocked by this module

## DORA metrics

| Metric | Value | Basis / note |
|---|---|---|
| `gate_rejection_rate` | 0.0 | rejected / (approved + rejected) |
| `gate_rejection_rate_by_phase` | {"S1-requirements": 0.0, "S2-architecture": 0.0, "S4-implementation": 0.0, "S5-quality": 0.0, "S6-delivery": 0.0} |  |
| `gate_rejection_rate_by_gate_type` | {"baseline-approval-only": 0.0, "installation": 0.0, "installation-operating-rules-design-only": 0.0, "installation-rule-change-execution": 0.0, "installation-rule-change-gate-preparation": 0.0, "post-installation-startup-rules-verification": 0.0, "real-project-delivery-architecture-governance-design": 0.0, "real-project-delivery-architecture-governance-review": 0.0, "real-project-governance-enforcement-architecture-design": 0.0, "real-project-governance-enforcement-architecture-review": 0.0, "repair-only / candidate-update-only": 0.0, "review-rerun / baseline-readiness-review-only": 0.0, "scope-expansion": 0.0, "state-sync": 0.0, "user-acceptance": 0.0, "user-activation": 0.0, "user-approval": 0.0, "user-cleanup": 0.0, "user-closeout-review": 0.0, "user-closeout-review-rerun": 0.0, "user-delivery": 0.0, "user-design": 0.0, "user-discovery-approval": 0.0, "user-implementation": 0.0, "user-installation": 0.0, "user-method-repair-design": 0.0, "user-quality": 0.0, "user-repair": 0.0, "user-review-only": 0.0} |  |
| `gate_decision_coverage` | 0.3415 | decided with evidence / decided |
| `approval_latency` | {"count": 21, "p50_seconds": 0.0, "p95_seconds": 1712.0, "mean_seconds": 443.476, "p50_hours": 0.0, "p95_hours": 0.476, "mean_hours": 0.123} |  |
| `task_cycle_time` | {"count": 27, "p50_days": 0.011, "p95_days": 0.369, "mean_days": 0.084, "basis": "created_at -> updated_at"} |  |
| `phase_dwell_time` | NOT_AVAILABLE | phase_transitions.jsonl absent (transition journal not yet wired — wave 2 item per B2 §2.2) |
| `task_rework_cycles` | {} | rejected gates per task (rejection -> fix -> re-audit) |
| `rework_cycles_from_transitions` | NOT_AVAILABLE | phase_transitions.jsonl absent |
| `guard_anomaly_rate` | 0.0 | FAIL events / total guard-check events (U8 guard-events.jsonl) |
| `guard_events_summary` | {"by_result": {"PASS": 299}, "by_check_type": {"health": 184, "death": 115}} |  |
| `guard_block_pass_error_rates` | NOT_AVAILABLE | guard_decisions.jsonl absent (hook decision log not yet wired — B2 §2.2) |
| `drift_events` | NOT_AVAILABLE | runtime-events.jsonl absent (drift source not yet wired) |
| `evidence_regeneration_events` | NOT_AVAILABLE | evidence freshness (C8) re-run events not yet recorded |
| `execution_cycle_time` | {"count": 6, "p50_seconds": 1203.132, "p95_seconds": 1217.614, "mean_seconds": 1008.031, "p50_hours": 0.334, "p95_hours": 0.338, "mean_hours": 0.28} |  |

## SLI / SLO evaluation

| SLI | Phase | Value | Target | Over target | Breach events | Consumed units | Severity |
|---|---|---|---|---|---|---|---|
| `req_gate_rejection_rate` | S1-requirements | 0.0000 | <= 0.35 | False | 0 | 0.0 | error-budget-slo |
| `design_review_rejection_rate` | S2-architecture | 0.0000 | <= 0.3 | False | 0 | 0.0 | error-budget-slo |
| `quality_gate_rejection_rate` | S5-quality | 0.0000 | <= 0.3 | False | 0 | 0.0 | error-budget-slo |
| `delivery_gate_rejection_rate` | S6-delivery | 0.0000 | <= 0.2 | False | 0 | 0.0 | error-budget-slo |
| `rework_cycle_rate` | S4-implementation | 0.0000 | <= 0.25 | False | 0 | 0.0 | error-budget-slo |
| `guard_block_rate` | S4-implementation | NOT_AVAILABLE | <= 0.05 | None | None | 0.0 | error-budget-slo |
| `guard_anomaly_rate` | S4-implementation | 0.0000 | <= 0.05 | False | 0 | 0.0 | error-budget-slo |
| `approval_latency_p95` | S6-delivery | 0.4760 | <= 24.0h | False | 0 | 0.0 | error-budget-slo |
| `gate_decision_coverage` | All | 0.3415 | >= 1.0 | True | 54 | 0.0 | hard-gate |
| `drift_event_rate` | S11-maintenance | NOT_AVAILABLE | <= 2 | None | None | 0.0 | informational |
| `delta_quality_pass_rate` | S4-implementation | NOT_AVAILABLE | >= 1.0 | None | None | 0.0 | hard-gate |
| `evidence_regeneration_rate` | S5-quality | NOT_AVAILABLE | <= 0.1 | None | None | 0.0 | error-budget-slo |
| `defect_fail_verdict_rate` | S5-quality | NOT_AVAILABLE | <= 0.2 | None | None | 0.0 | error-budget-slo |
| `ac_invest_rate` | S1-requirements | NOT_AVAILABLE | >= 1.0 | None | None | 0.0 | hard-gate |

## Notes

- wave 1 advisory: budget exhaustion is reported (FREEZE_RECOMMENDED); no release path is blocked by this module.
- read-only aggregation: data sources are never modified by this report.
- advisory only (wave 1): budget exhaustion is reported, no release path is blocked by this module
- release fee not assessed: no release ledger exists yet; pass --releases when a release record is available.
