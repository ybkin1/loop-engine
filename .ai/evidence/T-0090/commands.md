# T-0090 Commands

任务：新能力引入 — D1 LLM 接入抽象层 + D5 工具执行器/MCP + D7 异步任务队列 + D2 SLO/指标子系统
Gate：G-T-0090-REQUIREMENTS（approved 2026-08-01，approval_text="批准 T-0090 需求"）

## 登记与启动

1. 创建 `.ai/tasks/T-0090.md`（含 allowed_paths: YAML 契约字段）
2. 更新 `.ai/task_graph.yaml` — 登记 T-0090（in_progress）+ edge T-0089→T-0090
3. 更新 `.ai/gates.yaml` — 登记 G-T-0090-REQUIREMENTS（用户消息即批准）
4. 更新 `.ai/state.yaml` — current_task_id=T-0090, current_gate_id=G-T-0090-REQUIREMENTS + notes
5. 创建 approval/execution-evidence.json；compile_gate 生成 compile-evidence.json
6. `repair_continuity.py` + `close_session.py` — 连续性/HANDOFF 同步
7. `validate_state.py` — [ok] state is usable
8. 顺手修复：`.ai/tasks/T-0089.md` 双 status 位 → completed（历史遗留 warn）

## 实现（developer 子代理 × 4 并行）

### D1 LLM 接入抽象层（agent_0fdafe1f）
9. 新增 `loop_core/llm/` 包（9 模块 1471 行）— errors.py（11 错误码 + retryable + HTTP 映射）/protocol_driver.py（complete/stream/complete_json/cancel）/openai_driver.py（Chat Completions + httpx 懒加载 + MockTransport 注入 + SSE）/retry.py（指数退避 + jitter + sleep_fn 注入）/json_repair.py（9 候选修复管线）/redaction.py（Redactor 三路脱敏）/output_policy.py（操作级钳制表）/keys.py（环境变量 LLM_API_KEY→DEEPSEEK→OPENAI→ANTHROPIC，缺失显式报错）
10. `tests/test_llm_layer.py`（52 测试）— 网络守卫（socket/httpx 全 mock 断言）+ 无硬编码密钥扫描 + 全 AC-01 覆盖
11. 证据：`.ai/evidence/T-0090/llm-layer/design.md`

### D5 工具执行器 + MCP（agent_96136e36）
12. 新增 `loop_core/tool_executor.py`（~430 行）— ToolSpec/ErrorCode/ToolExecutor fail-closed 流水线（存在→enabled→双重白名单→类型→超时→执行）；subprocess 无 shell 插值 + 输出截断 20KB
13. 新增 `loop_core/mcp_client.py`（~410 行）— MCPSession/_StdioSession（JSON-RPC 2.0：initialize→initialized→tools/list→tools/call；id→Future；stderr 排空；EOF fail-closed）
14. 新增 `tests/mcp_mock_server.py`（本地 mock stdio server：echo/add/fail/sleep + 故障模式，零网络）+ test_tool_executor.py（28）+ test_mcp_client.py（22）
15. 证据：`.ai/evidence/T-0090/tool-executor/design.md`

### D7 异步任务队列（agent_6a715e67）
16. 新增 `loop_core/async_jobs.py`（559 行）— AsyncJobQueue（ThreadPoolExecutor 4 worker + 状态机 queued→running→succeeded/failed/cancelled + 租约防重复（同 job_id 并发只执行一次）+ 自动确定性 job_id + 协作式取消 + BaseException 隔离 + 历史裁剪 500 + 可选 JSONL 持久化）
17. `tests/test_async_jobs.py`（26 测试，含 8 线程并发防重）
18. 证据：`.ai/evidence/T-0090/async-jobs/design.md`

### D2 SLO/指标（agent_9ed839e8）
19. 新增 `loop_core/governance_metrics.py`（1321 行）— 7 路只读 loader + 纯函数指标（拒绝率/驻留/返工/guard 异常率等 14 SLI）+ error budget 核算（FREEZE_RECOMMENDED advisory，不接线阻断）+ MetricsReport（ReportBinding 风格）+ markdown 渲染
20. 新增 `tools/loop_metrics.py` CLI（--report/--window/--slo）
21. `tests/test_governance_metrics.py`（27 测试）+ 真实报告 `.ai/evidence/observability/metrics-report.json`（8/14 SLI computed，budget HEALTHY，NOT_VERIFIED 为 wave-2 数据源缺省设计行为）
22. 证据：`.ai/evidence/T-0090/slo-metrics/design.md`

## 治理同步（主会话）

23. 独立审查（agent_c133ed24）：GO — 6/6 AC PASS；约束零弱化（enforcement/hooks 零改动）；D2 advisory 不接线；D1/MCP 无真实网络面；无硬编码凭据；3 项 P3
24. 落盘 commands.md + acceptance/acceptance-report.md

## 验收

25. 全量测试：3281 passed / 63 skipped / 12 xfailed / 0 failed（基线 3126 + 155 = 52+50+26+27）
26. 状态收敛（task_graph T-0090 completed + state idle）+ close_session 重建 HANDOFF
27. git 提交 v3.12.29

## 发现（P3 遗留，记录）

- metrics-report.json status=NOT_VERIFIED（wave-2 数据源 guard_decisions.jsonl 等未接线，fail-closed 设计行为）
- D7 全量中 2 个瞬时失败为并行 D5 子代理 in-flight 文件竞态（单独重跑通过）
- httpx 为懒加载可选依赖（pyproject 声明留待自举审计接线任务）
- loop-engine LLM 层默认不连接任何外部服务（能力提供，连接由后续任务按需启用）
