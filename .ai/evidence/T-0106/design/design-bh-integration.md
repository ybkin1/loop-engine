# T-0106 批 2 — BH 融合详细方案（8 特性，模块级）

- 任务：T-0106（candidate-only 设计任务，零产品代码变更）
- 依据：BH 逐行调研结论（T-0106 调研批次）"BH 优于 LE 的 8 项" + 批 1 漏洞排查（audit-design-gaps.md）
- 日期：2026-08-03
- 总原则：每特性显式标注"必须保持"清单（防篡改 / fail-closed / 审批闭环）；实施经 T-0108/T-0109 独立 gate；hook 强制层与治理内核不改语义，仅允许最小行为修复（D4-2 fail-open→fail-closed）与纯外提（不改变控制流）

---

## F0 会话证据边界说明（外部项，不属 LE 融合范围）——2026-08-03 修正

> **修正记录**（用户决策 + HANDOFF Scope Correction）：原 F0"启用 Qoder source roots + 可观测性解锁"
> 为**错误 scope 表述**——Qoder 是外部会话宿主/适配器，其 transcripts 不能作为当前 ZCode 会话证据；
> 不得恢复/修改外部 Qoder 项目配置。Qoder 相关探针与 Episode 仅保留为**外部诊断证据**，
> 不得用于声称当前 ZCode 会话执行了编辑/验证/恢复/可靠交付。原 T-0112 候选已撤销（2026-08-03）。

- **问题编号**：`session-source-disabled`（Medium，KNOWN_ISSUES 保留为记录，不立项修复）
- **影响维度**：BH/Qoder 评估侧的会话证据可读性（任务理解/可控执行/改动验证/可靠交付在评估侧呈 Unobserved）
- **修正后目标**：定义 **ZCode 原生会话证据路径**（当前 ZCode 会话内产生 edit→validation Episode 的可验证路径），作为后续候选设计（排布外独立立项，需用户单独 gate）
- **改动边界**：不修改任何外部 Qoder/BH 项目；LE 治理内核零触碰
- **必须保持**：证据真实性（仅接受当前会话内可溯源证据）、隐私脱敏、fail-closed 安全裁决、用户 gate 审批边界；源不可用时洞察必须标记 `NO_EVIDENCE/INSUFFICIENT_SAMPLE`，不得生成行为性确定结论。

## F1 评估模型升级：证据七态 + gate evidence + 评分上限表 + Repair/Loop 分离

- **目标文件/新增模块**：`loop_core/schemas/evidence_state.py`（新增，EvidenceState 枚举七态 Present/Wired/Exercised/Outcome-supported/Missing/Unobserved/N-A）；`loop_core/subagent_evidence_verifier.py`（修改，验证结果映射七态）；`loop_core/gate_feedback.py`（修改，GateLesson 增加 evidence 状态字段）；`loop_core/governance_metrics.py`（修改，MetricsReport 增加评分档位与 Repair/Loop 两族指标）；`.ai/slo.yaml`（修改，评分上限表 59/74/84/94/100 显式化，对齐 slo.yaml 既有配置外置模式）
- **改动方式**：新增枚举模块 + 修改三处消费方；评分只做**呈现/度量**，不进入 gate 决策
- **依赖**：无外部依赖；内部依赖 gate_lesson 记录（`record_gate_lesson`）与 guard-events 数据
- **风险**：七态语义被误当决策输入（MEDIUM）→ 设计约束：评分与证据状态为 advisory，gate 决策仍走 `state_machine.can_approve_gate` 审批闭环
- **验收**：单测覆盖七态映射 + 评分分档边界（59/74/84/94/100 各档取等值断言）；指标输出含 Repair Progress（repair 触发次数/修复 GO 数）与 Loop Effectiveness（gate 通过率/cycle time，来自 `rework_cycles_from_gates`/`task_cycle_time_stats`）分离字段；门禁：无新增评分字段不进任何 gate 判定路径（静态检查）
- **必须保持**：①防篡改：evidence 哈希链（evidence_chain/execution_ledger root_hash）不动，七态仅描述验证结果不替代哈希校验；②fail-closed：证据 Missing/Unobserved 不得"自动通过"任何门禁；③审批闭环：用户 gate 批准流程（approval_ledger）零改动

## F2 单一数据源：状态五写收敛 + projection_engine + validate_state 新鲜度

- **目标文件**：`loop_core/state_machine.py`（修改，`atomic_write_state` :580 为唯一权威写入入口，保持）；`loop_core/projection_engine.py`（修改，`generate_projection` :235 增加任务卡 Status / HANDOFF / PROGRESS 投影视图）；`.zcode/tools/validate_state.py`（修改，新增新鲜度检查函数，检查 state.yaml mtime 与派生视图 mtime 差，超龄 flag `[warn] stale view`）；`.zcode/tools/governor_lib.py`（修改，`transactional_write_texts` 已有事务写，作为收敛写入 helper）
- **改动方式**：分两阶段——阶段 1 只读（validate_state 加新鲜度检查 + 投影视图生成，双写告警）；阶段 2 收敛（写路径统一经 governor_lib 事务写 + projection 刷新）。任务卡 Status / HANDOFF / PROGRESS 成为派生视图，不直接手改
- **依赖**：T-0107（D5-2 契约解析收敛）先行，保证 task_graph/任务卡解析一致
- **风险**：收敛过渡期双写不一致（MEDIUM）→ 阶段 1 告警不阻断，阶段 2 逐写入点切换
- **验收**：投影一致性测试（视图 = state.yaml 派生，同一输入逐字段一致）；新鲜度测试（伪造旧 mtime → validate_state 报 `[warn] stale view` 仅告警，exit code 与既有判定一致——T-0116 措辞修正：T-0108 实现为 warn-only，任务卡 AC-04 口径为准）
- **必须保持**：①fail-closed：loop_enforcement 的 FULL 模式写入阻断闸门不变（收敛写入不得绕过 enforcement 路径检查）；②审批闭环：状态推进仍须先经 gate 批准（`can_transition_phase`/`can_approve_gate` 语义不变）；③防篡改：project_continuity.yaml 源清单仍覆盖 state.yaml（`repair_continuity` dynamic_only 三件套不变）

## F3 gates.yaml 分层瘦身：active/archive + forbidden 模板外提 + gate_type 枚举

- **目标文件**：`.ai/gates.yaml`（修改，保留 active 域 gate，归档 gate 移 `.ai/archive/gates-archive.yaml` 或标 `archived: true` + 单独小节）；`.ai/policies/forbidden-actions.yaml`（新增，forbidden_actions 标准模板外提，gate 记录 `forbidden_policy: standard-v1` 引用 id）；`loop_core/schemas/gate.schema.json`（修改，gate_type 枚举化：user-approval/state-sync/user-activation/approval-record 等，对齐 `hard_constraints.py` 既有 gate 类型消费方）
- **改动方式**：归档迁移脚本（.ai 内，一次性）+ gate_type 校验接入解析路径
- **依赖**：T-0107（D5-1 解析 schema 校验）；gates 消费方（context_controller `_load_gates`、governance_metrics `load_gates`、gate_guard）须先统一解析入口
- **风险**：归档后旧 gate 引用断裂（evidence/registry 路径）→ 归档仅移域不删记录，引用路径保持；enforcement 读取路径变更引入回归 → 行为等价测试
- **验收**：gates.yaml schema 校验测试；归档前后 `load_gates` 输出等价（active 域一致）；enforcement 路径裁决回归全绿
- **必须保持**：①fail-closed：gate 文件缺失/解析失败 → 阻断（`_load_gates` 异常语义保持，不得静默空列表放行）；②审批闭环：归档 gate 的 approval 记录不可删（历史可审计）；③防篡改：continuity 源清单同步（gates.yaml/archive 路径变更须入 manifest）

## F4 按需加载与文档路由：.ai/README Switchboard + 目录四态 + 文档活/死归类

- **目标文件**：`.ai/README.md`（新增，Switchboard 三节 Owns / Does Not Own / Read Next）；`.ai/` 顶层文档归类表（新增，20+ 文档活/死分类：活 = state/gates/PROGRESS/HANDOFF/DECISIONS/KNOWN_ISSUES/DECISIONS/README；死/归档 = 历史文档移 `.ai/archive/`）；`loop_core/context_loader.py`（修改，`_select_relevant_sections` :1299 改读 Switchboard 路由表，替代关键词启发式——消解 D5-3）；`docs/02-architecture.md`（修改，front-matter 增加 `designed_files:` 显式声明区——消解 D5-7）
- **改动方式**：新增 README + 归类表；context_loader 节选择改路由驱动；死文档移动（归档，不删除）
- **依赖**：T-0108 内部 F8（文档链接完整性测试）先行建立基线，再动文档
- **风险**：文档移动破坏既有引用（链接/continuity 哈希）→ 移动与链接测试同批；context_loader 节选择行为变化影响子代理上下文 → 黄金快照对比
- **验收**：doc-link 测试覆盖 README 全部链接（F8）；路由表 schema 校验；节选择黄金快照（相同 doc 输入，输出节集一致）
- **必须保持**：①防篡改：continuity 源清单随归档路径更新，语义哈希不自动修复（`repair_continuity` 语义哈希永不自动重算，:54-56）；②审批闭环：归档决策经任务 gate 批准，不静默移动；③fail-closed：路由表缺失时回退旧关键词行为并告警，不静默返回空上下文

## F5 工具层 capability 化：36 工具分组 / 薄壳消除 / 死工具删除 / 重复合并 / audience 分级

- **目标文件**：`tools/` 36 个工具 + `tools/server.py`（MCP 注册表）；`loop_core/capability_registry.py`（修改，注册表补充 capability/domain/audience 元数据）；`loop_core/status_dashboard.py`、`tools/loop_dashboard.py`、`tools/tool_dashboard.py`、`loop_core/dashboard_views.py`（dashboard 四层重复 → 合并为 dashboard_views 单一实现）；`loop_core/evidence_chain.py`、`tools/tool_evidence_chain.py`、`scripts/evidence_chain.py`（证据链三处 → 收敛至 loop_core）；安全扫描三处（`security_scanner.py`/`tool_security_scan.py`/`scripts/security_scan.py`）与缓存同步三处同理
- **改动方式**：分组元数据先行（只读标注）；薄壳消除（工具模块保留 entry point，逻辑下放 loop_core）；死工具删除（先调用图/引用确认 + 一个 gate 周期无引用，再删）；audience 分级 workflow/advanced/maintainer 入注册表
- **依赖**：T-0107（解析/常量收敛）后工具行为稳定再动
- **风险**：工具改名/删除破坏 enforcement 白名单（`loop_enforcement.py:356` GOVERNANCE_TOOL_DIRS 与 :1884 治理工具清单）→ 删除与改名必须同步白名单，防篡改语义不弱化；MCP 注册表断连 → 合并期双注册过渡
- **验收**：注册表一致性测试（每个已安装工具在注册表有元数据）；行为等价测试（合并前后同一输入输出一致）；死工具确认报告（调用图 + 引用 grep 证据）
- **必须保持**：①防篡改：enforcement 的治理工具白名单/路径豁免表不变或同步更新（不允许工具绕过）；②fail-closed：工具 PASS/BLOCK 返回语义不变（`tool_constraint_check` 的 D4-3 修复先行）；③审批闭环：治理工具（close_session/validate_state）权限语义不变

## F6 上下文打包升级：token 预算 / AC 节解析 / git diff 缓存 / subprocess 超时

- **目标文件**：`loop_core/context_packager.py`（修改/重写主体，修复 D1-1~4/D2-1/D2-8/D3-2/D4-1/4 共 9 处缺陷）；`loop_core/context_budget.py`（新增，token 预算计算器：字符→token 估算 + 按节优先级分配，AC/验收节优先保留 + truncated 标记）
- **改动方式**：`build_context` 签名与返回结构不变（调用方零改动）；内部：`[:1000]` → token 预算 + AC 节优先；`MAX=15000` 死护栏（D3-2）改为真实递增预算；git diff 按 `git rev-parse HEAD` 哈希做磁盘缓存；timeout 常量集中（5/10/5 → 命名常量）；git diff 段异常 → warning + "diff unavailable" 占位（D4-1）
- **依赖**：无外部依赖；与 F4（节选择）正交
- **风险**：预算分配改变子代理实际收到的上下文 → 黄金快照 + 子代理回归；token 估算偏差 → 常量可调（config）
- **验收**：专项测试（AC 节保留断言、截断标记断言、diff 缓存命中断言、timeout 注入断言）；原 9 处缺陷逐项回归
- **必须保持**：①fail-closed：git diff/记忆召回失败不得静默吞错（D4-1 修复方向为告警+占位，不假装成功）；②防篡改：context 打包不写任何治理文件（只读）；③审批闭环：不引入任何跳过 gate 的上下文指令

## F7 评估产物契约化：finding 结构化修复契约（对齐 BH harness-findings.input.json）

- **目标文件**：`loop_core/schemas/finding.schema.json`（新增，字段：finding_id/source/severity/expectedOutput/修复边界/验证命令/acceptance checks，对齐 BH `harness-findings.input.json` 字段映射表）；`loop_core/design_reviewer.py`、`loop_core/security_scanner.py`、`loop_core/subagent_evidence_verifier.py`、`agents/*/scripts/*.py`（修改，输出收敛到 finding schema）；`tools/tool_evidence_submit.py`（修改，提交校验）
- **改动方式**：先加 schema + 校验器（只读），再逐扫描器适配（加字段不删字段，保持消费方兼容）
- **依赖**：T-0107（D5-5 contract_verifier fallback 收窄——P3 归属经 plan-task-roadmap.md『P3 项归属总表』明确：D5-5 由 T-0107 解析器收敛族同批承担，本引用与 T-0107 范围一致）防同类静默裁剪
- **风险**：既有 finding 消费方（review 流程/gate 证据）字段漂移 → 兼容层（老字段映射新 schema）；agent 脚本改动面大 → 分批
- **验收**：schema 校验单测（合法/非法 finding 用例）；现有扫描器输出转换测试（老输出 → schema 化输出，字段无损）；BH 映射表对照测试（LE finding 字段 → BH harness-findings.input.json 字段）
- **必须保持**：①fail-closed：finding schema 校验失败 → 标记 INVALID 并告警，不静默丢弃（对齐 `load_guard_events` strict-parse 风格）；②防篡改：finding 证据哈希引用不变；③审批闭环：修复契约是建议性产物，不自动触发任何 gate 状态变更

## F8 治理契约测试：文档链接完整性 + 投影新鲜度测试

- **目标文件**：`tests/test_ai_doc_links.py`（新增，仿 BH doc-link-graph：遍历 `.ai/` 文档引用链接（含 README Switchboard/evidence 路径），校验目标存在；断链 → FAIL）；`tests/test_projection_freshness.py`（新增，state.yaml 权威 vs 投影视图一致性 + mtime 新鲜度）；`.ai/checkers/`（可选挂接，进入 validate_state/CI 门禁）
- **改动方式**：新增测试模块（纯只读）；可接入既有 CI/门禁入口
- **依赖**：F4（README 落地后链接测试方有意义）；F2（投影生成后新鲜度测试方有意义）——同一任务批次
- **风险**：测试误报（合法外链/动态路径）→ 白名单机制；门禁误伤正常流程 → 先报告后门禁
- **验收**：测试套件运行绿；人为断链用例 → FAIL 断言；投影陈旧用例 → FAIL 断言
- **必须保持**：①测试只读，不写 `.ai/`（不得触发 repair/自愈路径）；②fail-closed：测试失败即门禁失败，不降级为 warning；③防篡改：链接测试不修改任何哈希/清单

---

## 特性依赖关系与实施顺序

```
T-0107（正确性修复：D1/D2/D3/D4 P1+P2 + D5-1/2 收敛 + P3 追加 D3-4/5、D4-5/7/8、D5-5）
  └─> T-0108（BH 融合·收敛期）：F4 文档路由、F6 上下文打包、F7 finding 契约、
      F8 契约测试、F2 阶段 1（只读新鲜度）
        └─> T-0109（BH 融合·分层期）：F2 阶段 2（写入收敛）、F3 gates 分层、
            F1 评估模型、F5 工具 capability 化
```

风险从低到高：T-0107（LOW）→ T-0108（LOW-MED）→ T-0109（MED，F5 影响面最大）。
每个特性独立 AC + 独立 gate 批准；F5 工具删除类子项单独列 gate。
