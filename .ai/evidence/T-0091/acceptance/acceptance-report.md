# T-0091 验收报告（acceptance-report）

> **T-0091: B5 自举审计回路接线 — LLM 驱动 self-audit + ZCode 模型配置适配 | 2026-08-01**
> Gate: G-T-0091-REQUIREMENTS（user 批准，approval_text="继续 T-0091，模型配置可以用 Z Code 的模型配置"）
> 独立审查：GO（5/5 AC，约束零弱化、key 与内网地址零泄漏，1 项 P2 已补）

## AC 验收矩阵

| AC | 标准 | 结果 | 证据 |
|---|---|---|---|
| AC-01 | Anthropic Messages 驱动（complete/stream/头/SSE/错误映射） | ✅ PASS | anthropic_driver.py ~530 行；x-api-key + anthropic-version 头断言；SSE 事件分发；错误映射 retryable；全 mock（网络守卫 + transport 审计）；38 测试 |
| AC-02 | ZCode 配置解析（env 优先链 + provider fixture；key 不落日志） | ✅ PASS | zcode_config.py ~250 行；ENV_TIERS 链；fixture 隔离（真实配置不可达）；to_dict 掩码；KEY_MISSING 消息无 key；36 测试 |
| AC-03 | self-audit 接线（--llm 分析报告 + SKIPPED/DEGRADED 降级） | ✅ PASS | loop_self_audit.py +256/-8；三态 fail-safe；规则式永不阻断；无 --llm 逐字节兼容；合成机密零泄漏；10 测试 |
| AC-04 | 全量测试无回归 | ✅ PASS | 3365 passed / 63 skipped / 12 xfailed / 0 failed（基线 3281 +84 = 38+36+10） |
| AC-05 | 无约束弱化 + 无真实调用 + 无硬编码密钥 + 无内网泄漏 | ✅ PASS | hooks/enforcement 零改动；三层 mock 证明；sk- 仅脱敏正则与测试假 key；10.213.196.114 仅禁令文本 2 处 |

## 交付物清单

1. `loop_core/llm/anthropic_driver.py`（新，~530 行）+ `__init__.py` 导出
2. `loop_core/llm/zcode_config.py`（新，~250 行）
3. `tools/loop_self_audit.py`（+256/-8 纯增量：--llm/--provider/--model + run_llm_stage）
4. `tests/`：test_anthropic_driver（38）+ test_zcode_config（36）+ test_self_audit_llm（10）= 84 新测试
5. `.ai/evidence/T-0091/`：approval/execution/compile-evidence + 3 份 design.md + commands + acceptance

## 治理记录

- 任务登记：task_graph T-0091 + edge T-0090→T-0091；gates G-T-0091-REQUIREMENTS（用户消息批准）；state current_task_id=T-0091
- 前置调研：ZCode 模型配置机制（v2/config.json + env 链 + anthropic kind）
- 启动证据：approval/execution/compile 全就位；T-0090 双 status 位遗留修复
- 派发记录：developer ×3（驱动/配置/接线）、independent-reviewer ×1（GO）
- 全程零越界写入（diff 审查）；key 用后即弃；内网 baseURL 零写入

## 最终裁决

**GO**（独立审查 GO，5/5 AC 全 PASS）

## 已知遗留（P3，记录）

- AnthropicMessagesDriver._resolve_key() env 链（T-0090 keys.py 次序）与 zcode_config.ENV_TIERS 不一致 —— 兜底路径极少触发，留待后续统一
- 运行时 LLM 分析默认关闭（--llm 显式启用）；真实模型接入需用户环境就绪（v2/config.json provider）
