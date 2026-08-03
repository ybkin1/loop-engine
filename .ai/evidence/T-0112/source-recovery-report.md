# T-0112 会话源恢复阶段报告

## 已完成

1. 使用 Qoder 专用 Better Harness 适配器运行 `sources`。
2. 使用默认配置确认：5 个默认 enabled roots 中 1 个存在。
3. 使用 `--include-cache --include-global-capabilities` 重新探测：7 个可用配置项中 3 个存在且启用。
4. 运行 `facets`、`facts --selection all-eligible --debug`、`insights`。
5. 读取两个脱敏后的候选 session，生成 episode comparison。

## 关键证据

- 默认探测：`.ai/evidence/T-0112/source-probe-qoder-cn.json`
- 启用可选源探测：`.ai/evidence/T-0112/source-probe-enabled.json`
- Markdown 诊断：`.ai/evidence/T-0112/source-probe-enabled.md`
- 默认事实：`.ai/evidence/T-0112/session-facts-qoder-cn.json`
- 启用源事实：`.ai/evidence/T-0112/session-facts-enabled.json`
- 洞察：`.ai/evidence/T-0112/insights-enabled.json`
- Episode E1/E2：`.ai/evidence/T-0112/episode-E1.json`、`episode-E2-command.json`
- 对比结果：`.ai/evidence/T-0112/episode-comparison.json`

## 结论

### 机制缺陷已被复现并部分解除

默认配置下：

- `qoder-projects` 存在且启用。
- `qoder-audit`、`qoder-run-manifests`、`qoder-log-sessions`、`qoder-home-sessions` 不存在。
- `qoder-cache-projects` 和 `qoder-global-projects` 存在，但默认禁用。
- 因此原报告的 `disabled-source-root` / `missing-optional-root` 并非误报。

在本次只读探测中显式启用缓存和全局源后：

- `eligibleSessions = 131`
- `taskEpisodes = 158`
- `candidateEpisodes = 3`
- warning 从 `missing-optional-root + disabled-source-root` 降为 `missing-optional-root`

这证明：会话源并非完全不存在，真正问题是默认 source admission 配置过窄，且部分预期 root 缺失。

### 仍未满足完整验收

事实收集明确给出：

- `withChanges = 0`
- `withChecks = 0`
- `withReviewedRelevantCheck = 0`
- `withResultSignal = 0`
- `withStructuredCompletion = 0`
- `diagnosticFlags` 包含：
  - `no-change-evidence`
  - `no-reviewed-relevant-check-evidence`
  - `no-result-evidence`

两个候选 Episode 已有真实事件和 evidenceRefs，但当前结构化事实没有提供可靠的 edit→validation 或 rework/recovery 证据。因此只能标记为 `PARTIAL_ONLY`，不能据此声称“改动后验证机制已被验证”。

## 当前阻断

1. 默认配置仍会关闭两个实际存在的源：
   - cache-project-session
   - global-project-jsonl
2. 四个默认 enabled root 不存在：
   - audit-jsonl
   - run-manifest
   - logs-session
   - home-session
3. 当前候选 Episode 未观测到结构化编辑和验证事件。
4. 当前不能把四个维度的评分直接提升到 59 以上，也不能确认学习回路已经有效。

## 下一步

需要在新的、批准范围内的真实 governed session 中完成：

1. 一个批准范围内的实际编辑。
2. 编辑后的 `validate_state` 或专项验证命令。
3. 第二个相同生命周期的可比较会话，或明确的 rework/recovery 事件。
4. 再次运行 `facts`、`insights` 和 Better Harness 评审。

本阶段没有修改 Qoder 持久配置，没有伪造 Episode，也没有修改 Loop 治理内核。
