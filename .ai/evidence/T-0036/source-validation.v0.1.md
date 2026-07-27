# T-0036 来源核验记录 v0.1

日期：2026-07-22

## 方法

- 使用 PowerShell `Invoke-WebRequest` 对候选官方来源执行 HEAD/GET。
- 对可访问页面读取 HTTP 状态、最终 URL、HTML title 和前若干级标题。
- 只把页面内容确实读取到的来源标记为 `content_read`；标准入口、超时、区域不可用和仅登记入口分别保留原状态。
- 不复制受版权保护的标准正文；只保存元数据、短摘要、适用边界和 Loop 适配说明。

## 结果

- 目录材料：46 条。
- `content_read`：核心来源包括 MCP、Anthropic Context Engineering/Building Effective Agents、Inspect、NIST AI RMF、NIST SSDF、OWASP ASVS/LLM、SLSA、OpenAPI、JSON Schema、AsyncAPI、C4、arc42、Google Code Review、Testing Library、Stryker、k6、OpenTelemetry、Twelve-Factor、DORA、Agile Manifesto、Scrum Guide、Kanban Guide、Diátaxis。
- `url_verified_only`：ISO/IEC/IEEE 29148、12207、NIST GenAI Profile、RFC 2119 等；入口可访问，但本轮未读取完整正文。
- `access_blocked`：OpenAI Prompt Engineering 超时、Anthropic 文档区域不可用、Google Prompting Strategies 超时、Google SRE 入口超时。
- `not_yet_checked`：Pact、ISTQB、PMI、ADR/MADR、若干论文和 API 指南，已登记但不能视为本轮已核验。

## 结论

本轮完成的是可追溯研究基线，不是标准合规结论，不是 Loop 运行时能力证明，也不是用户对后续 Loop 实现的 Gate 批准。
