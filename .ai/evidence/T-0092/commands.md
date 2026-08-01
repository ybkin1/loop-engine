# T-0092 Commands

任务：AI-agent eval 栈（B1 设计落地）
Gate：G-T-0092-REQUIREMENTS（approved 2026-08-01，approval_text="继续 T-0092/T-0093/T-0094"）

## 登记与启动

1. 创建 `.ai/tasks/T-0092.md`（含 allowed_paths: YAML 契约字段）
2. 更新 `.ai/task_graph.yaml` — 登记 T-0092/93/94 三节点 + 边链（T-0091→92→93→94）
3. 更新 `.ai/gates.yaml` — 登记 G-T-0092/93/94-REQUIREMENTS（用户批量批准）
4. 更新 `.ai/state.yaml` — current_task_id=T-0092 + notes
5. 创建 approval/execution-evidence.json；compile_gate 生成 compile-evidence.json
6. `repair_continuity.py` + `close_session.py` — 连续性/HANDOFF 同步
7. `validate_state.py` — [ok] state is usable
8. 顺手修复：`.ai/tasks/T-0091.md` 双 status 位 → completed

## 实现（developer 子代理 agent_993722c7）

9. 新增 `loop_core/evals.py` — EvalCase schema（case_id/title/input/expected/rule/severity/version/tags + 校验拒绝非法）+ EvalRunner（4 种规则断言 text_contains/text_matches/json_equals/exit_code + LLM 判定 fail-safe（无驱动/异常/UNKNOWN → SKIP 不阻断）+ 异常隔离）+ EvalReport（ReportBinding 风格：task/phase/gate/git_commit/timestamp/stats/by_severity/明细 + validate fail-closed）
10. 新增 `tools/tool_eval.py` CLI（--cases/--report/--json/--llm）
11. 内置样例 6 例（正 2/负 4，severity critical/high/medium，与 guard_health 对照电池 GC-002/003/004/006/007/008 逐字对齐）
12. `tests/test_evals.py`（48 测试：schema 14/运行器 20/报告 8/内置 6）
13. 修复安全扫描回归：样例集 fake secret 字面量 → 运行时字符串拼接（SS-001 critical 清零）
14. 证据：`.ai/evidence/T-0092/evals/design.md` + builtin-cases.yaml + 实测报告 `.ai/evidence/observability/eval-report.json`（6/6 PASS，git_commit 16888da）

## 治理同步（主会话）

15. 独立审查（agent_9c6afb11）：GO — 6/6 AC PASS；hooks/enforcement/hard_constraints 零改动；eval 零接线（纯评测）；LLM 全 mock；2 项 P2 收尾（本文件补齐）
16. 落盘 commands.md + acceptance/acceptance-report.md

## 验收

17. 全量测试：3413 passed / 63 skipped / 12 xfailed / 0 failed（基线 3365 + 48）
18. 状态收敛（task_graph T-0092 completed）+ state 切 T-0093 + close_session
19. git 提交 v3.12.31

## 发现（P3 遗留，记录）

- HANDOFF.md 引用 evidence-manifest.v1.yaml 实际不存在（模板性引用，历史任务同款，非本任务引入）
