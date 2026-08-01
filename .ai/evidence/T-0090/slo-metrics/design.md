# D2 SLO / Error Budget + Loop-DORA Metrics — 设计证据 (T-0090 AC-04)

| | |
|---|---|
| **Task** | T-0090 — 新能力引入（D2 工作包子任务） |
| **Role** | developer |
| **Date** | 2026-08-01 |
| **Design source** | docs/designs/loop-v4-slo-metrics-learning.md（B2）§1（SLO 子系统）/ §2（Loop-DORA 指标） |
| **Wave** | 1 advisory — 只核算与报告，**不接线发布阻断**（B2 §1.6：wave 1 无阻断；S6 `slo_budget_available` 为 wave 2） |
| **Data sources (read-only)** | .ai/gates.yaml、.ai/task_graph.yaml、.ai/evidence/observability/guard-events.jsonl（U8）、.ai/ledger/executions.jsonl、.ai/slo.yaml（可选覆盖） |
| **Implementation** | loop_core/governance_metrics.py、tools/loop_metrics.py、tests/test_governance_metrics.py |
| **Report artifact** | .ai/evidence/observability/metrics-report.json + .md（本任务生成；B2 §2.4 的 .ai/metrics/ 落点在 D2 范围内等效于 evidence 目录） |

---

## 1. 设计原则（继承 B1/B2）

1. **纯函数可复现**：每个指标都是 ledger/register 输入的纯函数（B2 §2.3），报告绑定 `git_commit` + window + generated_at（ReportBinding 风格，verdicts.py:37）。
2. **只读聚合**：聚合模块从不写数据源（B2 §2.3 "aggregation never writes to the ledger"）；报告落盘仅由 CLI 写入 evidence 目录。
3. **缺数据 fail-closed**：数据源缺失/不可解析 → 明确 `NOT_AVAILABLE`（绝不猜零，B2 §2.5/AC-MET "never a silent zero"）；报告状态随之 `NOT_VERIFIED`。
4. **wave 1 advisory**：error budget 耗尽只报告 `FREEZE_RECOMMENDED`，不接任何 gate/发布阻断（B2 §1.6 wave 1）。

## 2. SLI 采集（B2 §1.2 表 → 现有数据源映射）

| SLI (B2 §1.2) | 数据源 | 计算方式 | 真实数据结果（2026-07-06→08-01） |
|---|---|---|---|
| req_gate_rejection_rate | gates.yaml | S1 gate 拒绝/(批准+拒绝) | computed 0.0 |
| design_review_rejection_rate | gates.yaml | S2 同上 | computed 0.0 |
| quality_gate_rejection_rate | gates.yaml | S5 同上 | computed 0.0 |
| delivery_gate_rejection_rate | gates.yaml | S6 同上 | computed 0.0 |
| rework_cycle_rate | gates.yaml（拒绝 gate 数）；transitions 可用时优先 | 返工周期/完成任务数 | computed 0.0 |
| guard_block_rate | ledger/guard_decisions.jsonl | blocks/(blocks+passes) | **NOT_AVAILABLE**（hook 决策日志未接线，B2 §2.2 wave 1） |
| **guard_anomaly_rate**（本工作包新增，B2 §1.2 无此项） | **guard-events.jsonl（U8）** | FAIL 事件/总 guard 检查事件（guard_block_rate 的 wave-1 可计算代理） | computed 0.0（195 事件 0 FAIL） |
| approval_latency_p95 | gates.yaml | requested_at→recorded_at p95（小时） | computed 0.476 h（21 个样本） |
| gate_decision_coverage | gates.yaml evidence 字段 | 有证据 dossier 的决策/总决策 | computed 0.3415（28/82） |
| drift_event_rate | ledger/runtime-events.jsonl | 漂移事件数 | **NOT_AVAILABLE**（源未接线） |
| delta_quality_pass_rate | —（delta gate 结果未记录） | — | **NOT_AVAILABLE** |
| evidence_regeneration_rate | —（C8 freshness 重跑未记录） | — | **NOT_AVAILABLE** |
| defect_fail_verdict_rate | —（FAIL verdict 库未记录） | — | **NOT_AVAILABLE** |
| ac_invest_rate | —（DoD gate T-0089 范围） | — | **NOT_AVAILABLE** |

要点：
- **gate→phase 分类**：gates.yaml 无 phase 字段；按仓库 gate id 命名约定
  `G-<scope>-<TASK>-<TOKEN>` 的 token 表确定性分类（`classify_gate_phase`：
  REQUIREMENTS→S1 / ARCHITECTURE|DESIGN→S2 / INTERFACE→S3 /
  IMPLEMENTATION|IMPLEMENT|IMPL→S4 / QUALITY→S5 / DELIVERY→S6）。无 token
  匹配 → 归入 `unmapped` 桶（真实数据 50/82），**不猜测**。
- **守卫事件严格解析**：guard-events.jsonl 逐行 `json.loads` + schema 校验
  （guard_id/check_type/result 必备，result ∈ PASS|FAIL|REPORT）；损坏行 →
  整个源 NOT_AVAILABLE（不复用 observability.read_events 的容错前缀语义，
  避免静默产生伪造事件）。
- **时间解析**：ISO-8601（含时区/'Z'/纯日期）；naive 视为 UTC；不可解析字段
  仅影响该 gate 的时序指标（排除），不猜测。

## 3. SLO / error budget 核算（B2 §1.4 v1 规则）

- **默认 SLO 表**：B2 §1.2 的 13 项 + `guard_anomaly_rate`（budget 消耗类默认
  budget_share=1.0）；`.ai/slo.yaml` 存在时按 sli_id 合并覆盖
  （target/severity/budget_share）并可设 `budget_total_units` /
  `release_fee_units`（B2 §1.3 schema 兼容）。
- **预算**：默认 100 units/窗口（quarterly）。
- **消耗**：每个 budget-consuming SLO 的 breach event（=该 SLI 的违规实例：
  拒绝的 gate 数、guard FAIL 数、>24h 的审批数、无证据决策数）消耗
  `breach_events × budget_share` units。
- **release fee**：`releases × release_fee_units`（默认 5）；无 release ledger
  时默认不评估（releases=0，报告注明）——**不猜释放数**。
- **状态机**：remaining ≤ 0 → `FREEZE_RECOMMENDED`（仅报告）；消耗 >0 →
  `CONSUMING`；消耗 0 → `HEALTHY`。
- **红线**：本模块不 import 任何 gate/enforcement 路径，不产生 BLOCK——
  冻结留给 wave 2 的 `slo_budget_available` 条件（B2 §1.5）。

## 4. DORA 指标报告（B2 §2.2/§2.3/§2.4）

指标目录（≥3 项，真实数据 12 项 computed + 5 项 NOT_AVAILABLE）：

| 指标 | 真实数据结果 | 数据源 |
|---|---|---|
| gate_rejection_rate（总/分 phase/分 gate_type） | 0.0（0/82 拒绝） | gates.yaml |
| gate_decision_coverage | 0.3415 | gates.yaml evidence |
| approval_latency（p50/p95/mean） | p95 0.476 h（21 样本） | gates.yaml |
| task_cycle_time（created_at→updated_at，basis 显式标注） | p50 0.011 d（27 任务） | task_graph.yaml |
| phase_dwell_time | **NOT_AVAILABLE**（无 phase_transitions.jsonl） | ledger（wave 2） |
| task_rework_cycles | 0（无拒绝 gate） | gates.yaml |
| rework_cycles_from_transitions | **NOT_AVAILABLE** | ledger（wave 2） |
| guard_anomaly_rate（总体/每 guard） | 0.0（195 事件 0 FAIL） | guard-events.jsonl（U8） |
| guard_block_pass_error_rates | **NOT_AVAILABLE** | ledger（wave 2） |
| drift_events | **NOT_AVAILABLE** | ledger（wave 2） |
| evidence_regeneration_events | **NOT_AVAILABLE** | — |
| execution_cycle_time（launched→completed） | p50 1203 s（6 执行） | executions.jsonl |

报告结构（ReportBinding 风格）：
- `binding`: task_id/phase/git_commit/timestamp/tool_name/tool_version
- `window`、`status`（PASS | NOT_VERIFIED）、`missing`（缺项清单）
- `dora_metrics`、`slo_evaluation`（逐 SLI：value/target/over_target/
  breach_events/consumed_units/severity）、`error_budget`
- `sources`（每源 path/status/sha256/lines —— 可复现性 + 只读证明）
- 任一指标 NOT_AVAILABLE → 报告 `NOT_VERIFIED`（B2 §2.5 fail-closed）。

## 5. 与 U8 衔接（AC-04 数据源之一）

- 读取 `.ai/evidence/observability/guard-events.jsonl` 统计 guard 异常
  （check_type 分布 + result 分布 + 每 guard 异常率），**不修改事件文件**
  （AC-04d 前后 sha256 一致）；事件 schema 复用 `loop_core.observability.
  GuardCheckEvent`（from_dict + 严格字段校验）。
- 观测文件损坏 → guard 相关指标 NOT_AVAILABLE（不静默吞错）。

## 6. 验收映射（AC-04）

| 验收 | 证据（tests/test_governance_metrics.py，27 passed） |
|---|---|
| AC-04a SLI 计算（fixture→正确指标；缺失→NOT_AVAILABLE） | TestSliComputation：拒绝率 2/6、返工 2/2、guard 异常 1/3、审批 p95=1h、dwell/bounce=1、纯函数、全缺/部分缺/损坏源→NOT_AVAILABLE、phase 分类 |
| AC-04b SLO/error budget（超预算状态正确；预算内正常） | TestErrorBudget：60 拒绝→120>100→FREEZE_RECOMMENDED、clean→HEALTHY、5 units→CONSUMING、budget_share 0.5×10→5 units、release fee 3×5=15、slo.yaml 覆盖（total 50/share 0.25/target 0.99） |
| AC-04c DORA 报告（≥3 项指标+结构化输出） | TestDoraReport：≥3 computed（真实 fixture 10+）、JSON round-trip + binding 字段、markdown 渲染、缺数据→NOT_VERIFIED、window 绑定 |
| AC-04d 不修改数据源 | TestReadOnly：4 个源文件报告前后 sha256 一致（×3 次构建）；空仓库构建不创建任何源文件 |

## 7. 实现文件

| 文件 | 说明 |
|---|---|
| loop_core/governance_metrics.py（新增） | loaders（只读）+ 纯函数指标 + SLI/SLO/budget + MetricsReport/build_report/render_markdown |
| tools/loop_metrics.py（新增） | CLI：`python tools/loop_metrics.py --report [--window ..] [--slo ..] [--releases N] [--json-out ..]` |
| tests/test_governance_metrics.py（新增） | AC-04a/b/c/d + 单元测试，27 passed |
| .ai/evidence/observability/metrics-report.json / .md | 真实数据报告（本任务生成） |

## 8. 约束合规

- 只读数据源：gates.yaml / task_graph.yaml / guard-events.jsonl /
  executions.jsonl 在本模块中只有读路径（AC-04d 证明）。
- 未接线发布阻断：预算状态仅为报告字段，无任何 BLOCK/enforcement 依赖。
- 未修改业务源码：新增文件均在允许路径（loop_core/、tools/、tests/、.ai/evidence/T-0090/）。
- ruff 全绿；全量回归 3281 passed / 63 skipped / 12 xfailed（无失败）。
