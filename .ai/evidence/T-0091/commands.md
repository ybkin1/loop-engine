# T-0091 Commands

任务：B5 自举审计回路接线 — LLM 驱动 self-audit + ZCode 模型配置适配
Gate：G-T-0091-REQUIREMENTS（approved 2026-08-01，approval_text="继续 T-0091，模型配置可以用 Z Code 的模型配置"）

## 登记与启动

1. 创建 `.ai/tasks/T-0091.md`（含 allowed_paths: YAML 契约字段）
2. 更新 `.ai/task_graph.yaml` — 登记 T-0091（in_progress）+ edge T-0090→T-0091
3. 更新 `.ai/gates.yaml` — 登记 G-T-0091-REQUIREMENTS（用户消息即批准）
4. 更新 `.ai/state.yaml` — current_task_id=T-0091, current_gate_id=G-T-0091-REQUIREMENTS + notes
5. 创建 approval/execution-evidence.json；compile_gate 生成 compile-evidence.json
6. `repair_continuity.py` + `close_session.py` — 连续性/HANDOFF 同步
7. `validate_state.py` — [ok] state is usable
8. 顺手修复：`.ai/tasks/T-0090.md` 双 status 位 → completed（历史遗留 warn）
9. 前置调研（子代理）：ZCode 模型配置机制（~/.zcode/v2/config.json provider 结构 + env 优先链 + anthropic kind 协议要点 + 内网 baseURL 风险）

## 实现（developer 子代理 × 3）

### AC-01 Anthropic Messages 驱动（agent_40bd4852）
10. 新增 `loop_core/llm/anthropic_driver.py`（~530 行）— AnthropicMessagesDriver 实现 ProtocolDriver（complete/complete_json/stream/cancel）；POST {base_url}/v1/messages；x-api-key + anthropic-version: 2023-06-01；SSE 事件分发（message_start/delta/stop/error/ping）；错误映射（401/403/404/408/429/5xx → ErrorCode + retryable）；复用 retry/redaction/output_policy；httpx 懒加载 + MockTransport 注入
11. 修改 `loop_core/llm/__init__.py`（+2 行导出）
12. `tests/test_anthropic_driver.py`（38 测试：头断言/SSE/错误映射/空响应/脱敏/钳制/cancel/网络守卫）
13. 证据：`.ai/evidence/T-0091/anthropic-driver/design.md`

### AC-02 ZCode 配置解析（agent_dd0499e3）
14. 新增 `loop_core/llm/zcode_config.py`（~250 行）— ENV_TIERS 链（LLM→ANTHROPIC→OPENAI→ZCODE，key/base_url 成对）/resolve_zcode_provider（解析 ~/.zcode/v2/config.json，损坏 → CONFIGURATION_ERROR）/select_provider（preferred 优先，否则 anthropic kind 先）/resolve_model_config（env 优先 → 文件兜底 → KEY_MISSING）；to_dict 掩码 api_key
15. `tests/test_zcode_config.py`（36 测试：fixture 隔离/选择/env 链/脱敏/损坏文件）
16. 证据：`.ai/evidence/T-0091/zcode-config/design.md`

### AC-03 self-audit 接线（agent_584f295c）
17. 修改 `tools/loop_self_audit.py`（+256/-8 纯增量）— --llm/--provider/--model；build_llm_summary（脱敏摘要）+ run_llm_stage（resolve_model_config → 按 protocol 选驱动 → complete_json(operation="audit")）+ normalize_findings + 报告落盘 .ai/evidence/observability/self-audit-llm.json；fail-safe 三态（KEY_MISSING→SKIPPED / 调用失败→DEGRADED / 兜底 INTERNAL_ERROR，规则式永不阻断）
18. `tests/test_self_audit_llm.py`（10 测试：双协议接线/SKIPPED/DEGRADED/无 --llm 逐字节兼容/机密零泄漏）
19. 证据：`.ai/evidence/T-0091/self-audit-llm/design.md`

## 治理同步（主会话）

20. 独立审查（agent_1f422e1c）：GO — 5/5 AC PASS；约束零弱化；key 与内网地址零泄漏（10.213.196.114 仅禁令文本 2 处）；全量 3365 passed；1 项 P2（acceptance 待补）+ 1 项 P3
21. 落盘 commands.md + acceptance/acceptance-report.md

## 验收

22. 全量测试：3365 passed / 63 skipped / 12 xfailed / 0 failed（基线 3281 + 84 = 38+36+10）
23. 状态收敛（task_graph T-0091 completed + state idle）+ close_session 重建 HANDOFF
24. git 提交 v3.12.30

## 发现（P3 遗留，记录）

- AnthropicMessagesDriver._resolve_key() 的 env 链（LLM→DEEPSEEK→OPENAI→ANTHROPIC，T-0090 keys.py）与 zcode_config.ENV_TIERS（LLM→ANTHROPIC→OPENAI→ZCODE）次序不一致 —— 兜底路径极少触发（self-audit 显式传 key），留待后续统一
- 真机冒烟（非 mock）：--quick --llm 在无模型配置时 SKIPPED、假 key 时 3 次重试后 DEGRADED，报告无泄漏
