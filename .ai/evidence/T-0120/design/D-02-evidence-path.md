# D-02 ZCode 原生会话证据路径方案（T-0120）

> candidate-only 设计：不落地。三个方案 + 推荐 + 影响面 + 与 T-0112 撤销理由
> 的一致性论证。

## 1. 方案选项

### 方案 A（推荐）：会话存在性核验（呈现层，轻量）

- **内容**：`subagent_evidence_verifier.has_valid_session_id()` 增强——当
  `reviewer_session_id` 形如 `sess_<uuid>` 时，校验
  `~/.zcode/cli/exec/sess_<uuid>/` 目录存在（本地可核验）；找不到时在 reason
  中标注 `session source unverified (zcode)`（**不改变 verdict 判定**——既有
  非空/独立性校验语义不变，仅增加呈现层提示）。
- **影响面**：`loop_core/subagent_evidence_verifier.py` 1 处 + 测试 +
  文档（映射表/KNOWN_ISSUES 更新）。证据链、gate 判定、manifest 零改动。
- **价值**：审查证据的"会话存在性"从不可核验（外部转录）变为本地可核验；
  与 T-0112 撤销理由（外部性/不可控）直接互补。
- **局限**：只证明会话目录存在，不证明审查内容真实（verdict/findings 仍由
  evidence-manifest 哈希与独立审查流程保证）。

### 方案 B：会话活动佐证（执行日志哈希入链）

- **内容**：把 `call_*.log` 哈希纳入 evidence-manifest 或 AiDecisionLedger
  佐证条目。
- **评估**：**低价值高成本**——5.1G 日志含大量工具输出噪音、无结构化审查
  内容、文件持续追加（哈希不稳定）；收益（活动佐证）与 evidence-manifest
  既有的不可变清单能力重叠。**不推荐**。

### 方案 C：不落地（维持现状）

- 保留 KNOWN_ISSUES `session-source-disabled` 记录；会话数据仅作本地排障。
- **适用**：若用户判定"会话存在性核验"不值得引入。

## 2. 与 T-0112 撤销理由的一致性论证

T-0112 撤销理由（HANDOFF Scope Correction）：**Qoder 为外部会话宿主，其会话
数据不能作为 ZCode 验收证据**——外部性（transcripts 外部生成、不在本仓库
控制内）与不可控性（无法核验、无法纳入证据链）是撤销核心。

方案 A 不违背该理由：
- **本地性**：ZCode 会话为本地原生数据（同一 harness、文件系统内）——非
  "外部宿主"。
- **边界保持**：方案 A 只做"会话存在性核验"（呈现层提示），**不把日志内容
  作为验收/审查裁决证据**——验收证据仍是 evidence-manifest 不可变清单 +
  独立审查流程；撤销理由的实质（外部数据不作验收证据）不受影响。
- **方向一致**：方案 A 强化的是"本地可核验性"，正是 T-0112 撤销所缺的。

## 3. 影响面评估（若落地，需独立 gate）

| 项 | 影响 |
|----|------|
| loop_core/subagent_evidence_verifier.py | has_valid_session_id + 1 个路径核验 helper（呈现层，verdict 判定零变更） |
| tests/ | 3-4 个用例（存在/不存在/非 sess_ 格式/边界） |
| 文档 | evidence_state 映射表说明 + KNOWN_ISSUES session-source-disabled 更新 |
| 证据链/gate 判定/manifest | 零改动 |
| 版本 | 需独立任务 bump（本次 candidate-only 不 bump） |

## 4. 风险

- 误用风险：若未来把"会话目录存在"误当"审查内容可信"→ 需在文档与测试中
  明确边界（存在性 ≠ 真实性）。
- 路径耦合：`~/.zcode/` 是 harness 安装位置，换机/换用户路径不同 → 方案 A
  需做成可配置/可探测（找不到路径时静默降级为现状，fail-safe）。
