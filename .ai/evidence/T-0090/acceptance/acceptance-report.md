# T-0090 验收报告（acceptance-report）

> **T-0090: 新能力引入 — D1 LLM 抽象层 + D5 工具执行器/MCP + D7 异步队列 + D2 SLO/指标 | 2026-08-01**
> Gate: G-T-0090-REQUIREMENTS（user 批准，approval_text="批准 T-0090 需求"）
> 独立审查：GO（6/6 AC，约束零弱化、无网络面、无硬编码凭据，3 项 P3）

## AC 验收矩阵

| AC | 标准 | 结果 | 证据 |
|---|---|---|---|
| AC-01 | LLM 抽象层（驱动/错误码/重试/JSON 修复/脱敏/钳制，全 mock，key 环境变量） | ✅ PASS | loop_core/llm/ 9 模块 1471 行；11 错误码 + retryable；9 候选 JSON 修复；Redactor 三路脱敏；操作级钳制表；网络守卫 + 无硬编码扫描测试；52 测试 |
| AC-02 | 工具执行器 + MCP（白名单/超时/错误码/stdio 全流程） | ✅ PASS | ToolExecutor fail-closed 流水线（双重白名单）；MCPSession stdio JSON-RPC 全握手；本地 mock server 零网络；50 测试 |
| AC-03 | 异步任务队列（状态跟踪 + 租约防重复） | ✅ PASS | AsyncJobQueue 状态机 + 8 线程并发同 job_id 仅执行 1 次 + 协作式取消 + BaseException 隔离；26 测试 |
| AC-04 | SLO/指标（SLI + error budget + DORA ≥3） | ✅ PASS | governance_metrics.py 1321 行（7 路只读 loader/14 SLI/budget 核算/FREEZE_RECOMMENDED advisory）；27 测试；真实报告落盘 |
| AC-05 | 全量测试无回归 | ✅ PASS | 3281 passed / 63 skipped / 12 xfailed / 0 failed（基线 3126 +155 = 52+50+26+27） |
| AC-06 | 无约束弱化 + 测试隔离 + 无真实凭据 | ✅ PASS | enforcement/hooks 零改动；D2 不接线阻断（advisory 仅报告）；socket 阻断 + MockTransport 强制；sk- 扫描 0 命中；155 测试零跳过 |

## 交付物清单

1. `loop_core/llm/` 包（errors/protocol_driver/openai_driver/retry/json_repair/redaction/output_policy/keys）
2. `loop_core/tool_executor.py` + `loop_core/mcp_client.py`
3. `loop_core/async_jobs.py`
4. `loop_core/governance_metrics.py` + `tools/loop_metrics.py`
5. `tests/`：test_llm_layer（52）+ test_tool_executor（28）+ test_mcp_client（22）+ test_async_jobs（26）+ test_governance_metrics（27）+ mcp_mock_server
6. `.ai/evidence/T-0090/`：approval/execution/compile-evidence + 4 份 design.md + commands + acceptance
7. `.ai/evidence/observability/metrics-report.json`（真实数据报告）

## 治理记录

- 任务登记：task_graph T-0090 + edge T-0089→T-0090；gates G-T-0090-REQUIREMENTS（用户消息批准）；state current_task_id=T-0090
- 启动证据：approval/execution/compile 全就位；T-0089 双 status 位遗留修复
- 派发记录：developer ×4 并行（D1/D5/D7/D2）、independent-reviewer ×1（GO）
- 全程零越界写入（diff 审查）；约束层零改动；B1/B2/B3 设计落地

## 最终裁决

**GO**（独立审查 GO，6/6 AC 全 PASS）

## 已知遗留（P3，记录）

- metrics-report status=NOT_VERIFIED（wave-2 数据源未接线，fail-closed 设计行为）
- httpx 懒加载可选依赖（pyproject 声明留待自举审计接线任务）
- LLM 层默认不连接外部服务（能力就绪，连接由后续任务按需启用）
