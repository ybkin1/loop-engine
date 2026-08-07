# Loop-DORA Metrics Report

- **Status**: PASS
- **Window**: 2026-07-06T15:12:38+00:00 → 2026-08-07T13:08:28.175904+00:00
- **Generated**: 2026-08-07T13:09:52.143102+00:00
- **Git commit**: 36d4ca671f446af1ecc81b56d2c8a4023463b8ba
- **Task**: T-0090 (phase S6-delivery)
- **Tool**: loop_metrics v1.0.0
- **SLO source**: .ai\slo.yaml

**Advisories (14 — 未接线数据源/未落盘项，不影响 computed 判定):**
- 数据源未接线（wave-2 项，不影响 computed 判定）: transitions (.ai/ledger/phase_transitions.jsonl)
- 数据源未接线（wave-2 项，不影响 computed 判定）: guard_decisions (.ai/ledger/guard_decisions.jsonl)
- 数据源未接线（wave-2 项，不影响 computed 判定）: runtime_events (.ai/ledger/runtime-events.jsonl)
- phase_dwell_time
- rework_cycles_from_transitions
- guard_block_pass_error_rates
- drift_events
- evidence_regeneration_events
- sli:guard_block_rate — guard_decisions.jsonl absent (hook decision log not yet wired — B2 §2.2 wave 1)
- sli:drift_event_rate — runtime-events.jsonl absent (drift source not yet wired)
- sli:delta_quality_pass_rate — delta gate results not yet recorded
- sli:evidence_regeneration_rate — evidence re-run tracking not yet recorded
- sli:defect_fail_verdict_rate — FAIL verdict store not yet recorded
- sli:ac_invest_rate — DoD gate acceptance-criteria check not yet recorded

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
| `gate_rejection_rate_by_gate_type` | {"real-project-delivery-architecture-governance-design": 0.0, "real-project-delivery-architecture-governance-review": 0.0, "real-project-governance-enforcement-architecture-design": 0.0, "real-project-governance-enforcement-architecture-review": 0.0, "user-approval": 0.0, "user-delivery": 0.0, "user-implementation": 0.0, "user-quality": 0.0} |  |
| `gate_decision_coverage` | 0.0396 | decided with evidence / decided |
| `approval_latency` | {"count": 63, "p50_seconds": 0.0, "p95_seconds": 1800.0, "mean_seconds": 274.429, "p50_hours": 0.0, "p95_hours": 0.5, "mean_hours": 0.076} |  |
| `task_cycle_time` | {"count": 27, "p50_days": 0.011, "p95_days": 0.369, "mean_days": 0.084, "basis": "created_at -> updated_at"} |  |
| `phase_dwell_time` | NOT_AVAILABLE | phase_transitions.jsonl absent (transition journal not yet wired — wave 2 item per B2 §2.2) |
| `task_rework_cycles` | {} | rejected gates per task (rejection -> fix -> re-audit) |
| `rework_cycles_from_transitions` | NOT_AVAILABLE | phase_transitions.jsonl absent |
| `guard_anomaly_rate` | 0.0 | FAIL events / total guard-check events (U8 guard-events.jsonl) |
| `guard_events_summary` | {"by_result": {"PASS": 7421, "REPORT": 6}, "by_check_type": {"health": 4408, "death": 2755, "missing": 6, "integrity": 207, "repair": 51}} |  |
| `guard_block_pass_error_rates` | NOT_AVAILABLE | guard_decisions.jsonl absent (hook decision log not yet wired — B2 §2.2) |
| `drift_events` | NOT_AVAILABLE | runtime-events.jsonl absent (drift source not yet wired) |
| `evidence_regeneration_events` | NOT_AVAILABLE | evidence freshness (C8) re-run events not yet recorded |
| `execution_cycle_time` | {"count": 6, "p50_seconds": 1203.132, "p95_seconds": 1217.614, "mean_seconds": 1008.031, "p50_hours": 0.334, "p95_hours": 0.338, "mean_hours": 0.28} |  |

## Repair Progress / Loop Effectiveness (T-0109 F1, advisory-only)

| Family | Metric | Value | Basis |
|---|---|---|---|
| repair_progress | `repair_triggers` | 0 |  |
| repair_progress | `fixed_gates` | 0 |  |
| repair_progress | `repair_progress` | None |  |
| loop_effectiveness | `gate_pass_rate` | 1.0 |  |
| loop_effectiveness | `rework_total` | 0 |  |
| loop_effectiveness | `task_cycle_time` | {'count': 27, 'p50_days': 0.011, 'p95_days': 0.369, 'mean_days': 0.084, 'basis': 'created_at -> updated_at'} |  |

| Score caps (state → cap) | Exercised=94 · Missing=59 · N-A=59 · Outcome-supported=100 · Present=74 · Unobserved=59 · Wired=84 | advisory: 评分仅呈现/度量，不进 gate 决策 |

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
| `approval_latency_p95` | S6-delivery | 0.5000 | <= 24.0h | False | 0 | 0.0 | error-budget-slo |
| `gate_decision_coverage` | All | 0.0396 | >= 1.0 | True | 97 | 0.0 | hard-gate |
| `drift_event_rate` | S11-maintenance | NOT_AVAILABLE | <= 2 | None | None | 0.0 | informational |
| `delta_quality_pass_rate` | S4-implementation | NOT_AVAILABLE | >= 1.0 | None | None | 0.0 | hard-gate |
| `evidence_regeneration_rate` | S5-quality | NOT_AVAILABLE | <= 0.1 | None | None | 0.0 | error-budget-slo |
| `defect_fail_verdict_rate` | S5-quality | NOT_AVAILABLE | <= 0.2 | None | None | 0.0 | error-budget-slo |
| `ac_invest_rate` | S1-requirements | NOT_AVAILABLE | >= 1.0 | None | None | 0.0 | hard-gate |

## Notes

- wave 1 advisory: budget exhaustion is reported (FREEZE_RECOMMENDED); no release path is blocked by this module.
- read-only aggregation: data sources are never modified by this report.
- advisory only (wave 1): budget exhaustion is reported, no release path is blocked by this module
- T-0109 F1 advisory: repair/loop metrics and score caps are presentation-only — they never enter gate decision paths.
- 部分数据源未接线（wave-2 ledger 项，共 3 个）：逐项 advisory 标注，computed 项正常判定，不因未接线源整体 NOT_VERIFIED
- release fee not assessed: no release ledger exists yet; pass --releases when a release record is available. 口径提示：release.py check 的 SLO 门禁按 releases=1 评估本次发布，metrics 报告用同一 releases 值即与 slo_gate 输出一致（同一 release_fee 函数）。
