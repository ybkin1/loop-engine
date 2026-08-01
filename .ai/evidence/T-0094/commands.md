# T-0094 Commands

任务：前端产品层 — AutoPlan dashboard 升级（D4）
Gate：G-T-0094-REQUIREMENTS（approved 2026-08-01，approval_text="继续 T-0092/T-0093/T-0094"）

## 登记与启动

1. 批量登记批次第 3 项；state 串行指向 T-0094
2. 创建 approval/execution-evidence.json；compile_gate 生成 compile-evidence.json
3. `repair_continuity.py` + `close_session.py` + `validate_state.py` — [ok] state is usable
4. 顺手修复：`.ai/tasks/T-0093.md` 双 status 位 → completed

## 实现（developer 子代理 agent_c364c842）

5. 新增 `loop_core/dashboard_views.py`（~700 行）— DashboardViews 四视图：task_graph_view（Kahn 拓扑排序/环 unresolved/状态汇总）/ gate_view（pending/approved/rejected + 86 决策记录降序）/ metrics_view（budget + DORA 关键项 + NOT_AVAILABLE 透传）/ guard_health_view（guard-events 重算统计）+ build_snapshot/render_text/render_html（自包含 HTML：内联 CSS 无外链）+ write_snapshot_files（source_hashes 只读证明）
6. 修改 `tools/tool_dashboard.py`（+50/-1）— 新增 4 个 MCP handler（dashboard_task_graph/dashboard_gates/dashboard_guard_health/dashboard_snapshot），原 dashboard_status 不变
7. 新增 `tools/loop_dashboard.py` CLI（--text/--html/--json/--snapshot）
8. `tests/test_dashboard.py`（23 测试：AC-01 任务图 6/AC-02 gate 4/AC-03 指标+健康 4/AC-04 快照 5 + CLI/MCP）
9. 证据：`.ai/evidence/T-0094/dashboard/design.md` + 真实快照 `.ai/evidence/observability/dashboard-snapshot.{md,html}`（Status PASS）

## 治理同步（主会话）

10. 独立审查（agent_25990ff9）：GO — 6/6 AC PASS；约束零改动；数据源零修改（task_graph/gates/metrics 全 clean；guard-events.jsonl modified 为测试套件 U8 append-only 行为，审查判定与 T-0094 无关）；3 项 P3 观察
11. 落盘 commands.md + acceptance/acceptance-report.md

## 验收

12. 全量测试：3476 passed / 63 skipped / 12 xfailed / 0 failed（基线 3453 + 23）
13. 状态收敛（task_graph T-0094 completed + state idle）+ close_session 重建 HANDOFF
14. git 提交 v3.12.33

## 发现（P3 遗留，记录）

- metrics_view 顶层非对象 JSON 返回 available 而非 NOT_AVAILABLE（边缘场景，影响可忽略）
- _topological_order 中指向未知任务 id 的边展示但不参与排序（设计语义已文档化）
- guard-events.jsonl 提交说明需注明测试套件 append 行为
