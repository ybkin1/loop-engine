# T-0154: loop x 对比研究报告（合并版）

> 交付物：T-0154（AC-01~AC-06）
> 日期：2026-08-07
> 性质：candidate-only 只读研究（零产品代码改动，保 loop 稳定）
> 研究对象：两个 GitHub loopx 项目（subagent 深读实证）

## 1. 项目定位

| 项目 | 仓库 | 定位 | 版本/commit | 规模 |
|------|------|------|------------|------|
| loopx A | huangruiteng/loopx | 跨 runtime 本地控制面：目标/门禁/待办/证据/配额/handoff 状态内核 | v0.4.2，深读时点 commit `db19e9b`（2026-08-07 22:25 +0800，"docs: tighten public evidence boundaries (#2853)"） | 4019 commits，Python 纯标准库 |
| loopx B | rye567/loopx | 单次需求 17 阶段可审计流程状态机（Codex/Claude 双宿主） | v0.1.0 首发，深读时点 commit `a8f3201`（2026-08-07 发布） | 110 文件，8.4k 行 |
| loop-engine | 本地 | 全工程多角色治理运行时（ZCode 插件，阶段机+gate+委托链） | v3.12.67，commit 见 git HEAD | 146 commits，4359 测试 |

> **可复现性说明**：外部项目事实（commit/规模/提交数）由 subagent 深读时
> 克隆实证记录（见 .ai/evidence/T-0154/review/ 深读留档）；本环境 github.com
> 网络不可达时无法再验证，以深读时点快照为准。

**核心判断**：loopx 是「状态内核 + 调度器 + 单流程状态机」，loop-engine 是
「人机治理门禁 + 全工程运行时」；两者互补。loopx 提供 loop-engine 缺少的
**审计可追溯性**、**配额决策机制**、**风险分级**、**收口声明纪律**；
loop-engine 的 gate 审批、反伪造证据、SLO/认证/委托链全面领先。

## 2. 对比差距表（合并两报告）

| 维度 | loopx 独有（可借鉴） | loop-engine 现状 | 价值 |
|------|---------------------|------------------|------|
| 状态内核 | 事件溯源（追加事件链，可审计回放） | YAML 最后一拍快照（transaction_registry 有雏形） | **P0** |
| 配额决策 | quota should-run 5 路决策（deliver/ask/wait/repair/quiet） | cost_tracker 记账无调度决策 | **P0** |
| 风险分级 | risk.yml：critical_triggers→FULL；score_rules 打分→LIGHT/STANDARD/FULL + ACCEPTED_RISK + SKIPPED 白名单 | loop_mode=FULL 一刀切 | **P0** |
| 收口声明 | git-gate（git diff 摘要入证据）+ ci_coverage: LOCAL_ONLY 显式声明 | release check 纯本地，无远端 CI | **P1** |
| 阶段快照 | 阶段结果内嵌全局 tracking_snapshot | 证据链哈希（更强）但阶段证据不自包含全局状态 | P1 |
| todo 元数据 | claimed_by/blocks_agent/successor/resume_when 可路由 | 任务卡 AC 文档 + task_graph 依赖 | P1 |
| 证据隐私 | 三档隐私分级 + 自动脱敏 | evidence_chain 哈希校验（更强）无隐私分级 | P2 |
| handoff 预算 | ≤16 行/1800 字符硬约束 + successor 链接验证 | HANDOFF 投影 + 审计（无预算约束） | P2 |
| CI | GitHub Actions（lint/test/cov/制品 attestation） | **无 CI**（本地 release 全链） | P0（工程风险） |
| 非侵入接入 | 不写用户 AGENTS.md，profiles 语言模板 | loop_onboard 写 AGENTS.md（侵入强） | P2 |

## 3. 提升建议（分级 + 采纳风险评估）

### P0-1 事件溯源影子层（loopx A 借鉴）
- **内容**：`.zcode/tools/event_log.py`，对现有事务写追加 JSONL 事件
  （todo/gate/evidence 生命周期），state.yaml 仍为权威投影
- **风险**：低（只增只读审计流，validate_state 语义不变；写入失败吞掉）
- **稳定性**：事件写入绝不阻断业务；加「投影=事件回放」一致性测试

### P0-2 配额决策路由（loopx A 借鉴）
- **内容**：cost_tracker 之上加 `quota_decision.py`：输入成本账本+gate 状态
  +悬空轮次 → 输出 deliver/ask/wait/repair/quiet + reason；**只建议不执行**
  （`/loop-quota` 命令），与用户 gate 驱动哲学兼容
- **风险**：中（自动唤醒与用户批准边界冲突）→ 必须"配额只建议、gate 才放行"
- **稳定性**：默认 quiet/wait（fail-safe）；异常降级 ask；5 态决策单测矩阵

### P0-3 风险驱动执行分级（loopx B 借鉴）
- **内容**：critical_triggers（auth/permission/db/external）→ FULL；
  score_rules 打分 → LIGHT/STANDARD/FULL；降级需 ACCEPTED_RISK + 理由；
  SKIPPED 白名单单一事实源
- **风险**：中（分级被用来跳过质量门）→ LIGHT 仅跳审核/审计门，
  输入/开发/验证/健康门保留；超界立即升级回 FULL
- **稳定性**：candidate-only 设计 gate + 决策包（T-0132/T-0136 惯例）；
  hooks/ 内核零改动；分级仅 advisory，不改 gate 批准语义

### P1-1 收口契约显式化（loopx B 借鉴）
- **内容**：release/close 前采集 git 变更摘要入证据 + `ci_coverage: LOCAL_ONLY`
  显式声明（本地通过/本地阻塞/未覆盖需 CI 三分类）
- **风险**：低（纯增量证据要求，不改判定语义）

### P1-2 阶段结果内嵌全局快照（loopx B 借鉴）
- **内容**：每阶段证据自带当时 state 快照（审计不回溯多文件，可检测
  事后改状态漂移）
- **风险**：低（只读增强，校验单测先行）

### P1-3 CI 接入评估（两项目共同缺口）
- **内容**：评估 GitHub Actions（ruff + pytest 子集 + validate_state +
  release check check 段），路径过滤避免全量耗时
- **风险**：低-中（测试时长需并行化评估）

### P2 候选（记录观望）
- 证据隐私分级+自动脱敏（未来公开复盘）
- handoff 预算硬约束（≤16 行）
- todo 元数据升级（blocks/successor/resume）
- 非侵入接入模式（不写 AGENTS.md 的轻量模式）

## 4. 采纳路径建议（保 loop 稳定）

1. **全部 candidate-only**：P0-1~P0-3 先出设计文档 + 决策包（沿用
   T-0132/T-0136 惯例），交用户裁决，不直接落地
2. **零 hooks/内核改动**：所有建议均在 .zcode/tools/ 或 loop_engine/ 新增
   模块（影子层/配额/分级均 advisory），不改现有 gate 语义
3. **测试先行**：每项带单测 + 变异测试接线 + golden 保护
4. **分批采纳**：P1-1（收口声明）成本最低可先行；P0 项需设计 gate

## 5. 边界确认

- 零产品代码改动（研究只读）；hooks/ 内核零触碰
- 未安装/启用任何新 skill/MCP/agent
- 版本保持 3.12.67

## 6. 结论

loop-engine 在治理深度上领先 loopx；最值得借鉴 3 项：
1. **事件溯源影子层**（审计可追溯性，P0）
2. **配额决策路由**（cost-gated auto-wake 雏形，P0）
3. **风险驱动执行分级**（LIGHT/STANDARD/FULL + ACCEPTED_RISK，P0）

三项均以 candidate-only 决策包方式吸收，不改 hooks/内核，保整体稳定。
