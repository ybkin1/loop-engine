# T-0106 批 4 — 整合任务排布 T-0107~T-0111

- 任务：T-0106（candidate-only 设计任务，零产品代码变更；本排布自 T-0107 起实施）
- 依据：audit-design-gaps.md（批 1+D5 共 42 项）、design-bh-integration.md（8 特性）、design-common-weakness.md（3 项）
- 日期：2026-08-03
- 排布原则（任务卡要求）：**风险从低到高**、**先收敛后分层**、**hook 强制层与治理内核全程不动**（仅 T-0107 对 D4-2 做最小 fail-closed 行为修复，单列子项 + 独立门禁）、**每任务独立 gate**、每任务独立验收门（测试/门禁）。

## 依赖图

```
T-0107 漏洞修复（LOW）─┬─> T-0108 BH 融合·收敛期（LOW-MED）─> T-0109 BH 融合·分层期（MED）
                      └─> T-0110 共同弱点·常量与拆分（MED）─> T-0111 共同弱点·修复器与全景验证（LOW-MED）
```

---

## T-0107 漏洞修复（正确性）

- **目标**：修复批 1 全部 P1/P2 + D5 P2 解析器收敛；context_packager 专项 9 处缺陷清零
- **范围**：
  - P1：D1-1（任务卡 1000 字符截断无标记，AC 节被切）
  - P2 全部：D1-2/4、D2-1/2、D3-1/2、D4-1/2/3
  - D5-1（`_naive_yaml_parse` fallback 告警 + schema 校验）、D5-2（任务卡 front-matter 双解析器统一为共享 `loop_contract_parser`）
  - **P3 追加（P2-1 排布补齐，见『P3 项归属总表』）**：
    - D3-4（`runtime_controller` journal 轮转，与 D3-1 轮转族同批，复用 observability 轮转方案）
    - D3-5（`async_jobs` 落盘持久化轮转，同批）
    - D4-5（`audit_ledger` 损坏行计数，与 D3-1 同文件同批）
    - D4-7（`loop_enforcement:94` OSError 记录被跳过文件，与 D4-2 同文件同批最小 diff）
    - D4-8（`transaction_registry:161` 裸 except 收窄 + 日志，吞 KeyboardInterrupt/SystemExit 属正确性缺陷）
    - D5-5（`contract_verifier` fallback 收窄 + 产出去向标注，与 D5-1/2 解析器收敛同族，F7 依赖项）
- **AC 草案（可测）**：
  1. context_packager 输出含 truncated 标记（截断发生时），任务卡截断后 AC/验收节仍在（token 预算优先保留）；golden 对比测试
  2. `MAX=15000` 死护栏修复：total 真实递增或删除护栏，无恒真条件（静态断言）
  3. git diff 段失败时上下文含 "diff unavailable" 占位 + warning 日志（无静默吞错）
  4. `intent_router:558` 阈值命名常量（MEDIUM_RISK_ESCALATION_MIN），行为不变（golden）
  5. audit_ledger 有轮转/归档策略（对齐 observability）
  6. D4-2：loop_enforcement `is_loop_mode_enforced` 异常路径 fail-closed（BLOCK）——**最小 diff 子项，单列 gate**
  7. D5-2：enforcement 与 context_controller 解析同一契约模块，双路径行为一致（含 mcp_allowed_tools 表格格式）
  8. D4-3：tool_constraint_check 非法 phase 告警字段，不再静默 PASS
  9. 追加 P3 项回归断言：journal/persist 轮转生效（D3-4/5）、audit_ledger 损坏行计数（D4-5）、loop_enforcement 跳过文件记录（D4-7）、transaction_registry 无裸 except（D4-8）、contract_verifier fallback 仅 ImportError 触发（D5-5）
- **依赖**：无（T-0106 设计已批准）
- **风险与缓解**：
  - D4-2 改动 hook（HIGH 敏感）→ 仅改异常分支、fail-closed 对齐、全量回归 + 自愈路径实测；**hook 其他逻辑零改动**
  - context_packager 重写影响子代理上下文 → 黄金快照 + 调用方（role_dispatch）回归
  - D5-2 共享解析器引入回归 → 解析输出等价测试（新旧解析器对同一任务卡逐字段一致）
- **验收门**：`pytest tests/` 0 failed；context_packager 专项 9 处缺陷逐项回归；hook 自愈路径实测；独立 gate（D4-2 子项单独批准）
- **预计变更文件**：`loop_core/context_packager.py`（重写主体）、`loop_core/context_budget.py`（新增）、`loop_core/intent_router.py`（常量命名）、`loop_core/veto_escalation.py`（常量）、`loop_core/audit_ledger.py`（轮转 + 损坏行计数 D4-5）、`hooks/scripts/loop_enforcement.py`（D4-2 最小修复 + D4-7 + 契约解析接入）、`hooks/scripts/loop_contract_parser.py`（新增）、`loop_core/context_controller.py`（解析统一）、`loop_core/contract_verifier.py`（D5-5 fallback 收窄）、`loop_core/runtime_controller.py`（D3-4 轮转）、`loop_core/async_jobs.py`（D3-5 轮转）、`.zcode/tools/transaction_registry.py`（D4-8）、`tools/tool_constraint_check.py`（D4-3）、`.ai/KNOWN_ISSUES.md`（关闭登记项）

## T-0108 BH 融合·收敛期（F4/F6/F7/F8/F2-阶段1）

- **目标**：低风险收敛型 BH 特性落地：文档路由、上下文打包、finding 契约、契约测试、单源阶段 1（只读）
- **范围**：
  - F6 上下文打包升级（token 预算/AC 节/git diff 缓存/timeout 常量——接续 T-0107 context_packager 改造；显式覆盖 P3：D1-3 截断标记、D2-8 timeout 常量、D4-4 knowledge cases 记 warning）
  - F4 文档路由（.ai/README Switchboard + 目录四态 + 死文档归档 + context_loader 节选择改路由表，消解 D5-3；并落 docs/02-architecture.md front-matter designed_files: 显式声明区，消解 D5-7）
  - F7 finding 结构化契约（finding.schema.json + 扫描器输出收敛，消解 D5-6 报告 front-matter 契约化；agents 脚本输出收敛同批落地 P3：D1-7 截断标志结构化、D4-10/D4-11 失败原因区分上报）
  - F8 治理契约测试（.ai 文档链接完整性 + 投影新鲜度测试）
  - F2 阶段 1：validate_state 新鲜度检查（只读告警）+ projection_engine 视图生成
- **AC 草案（可测）**：
  1. README Switchboard 三节存在且 doc-link 测试全绿（断链用例 FAIL）
  2. context_loader 节选择读路由表，golden 快照一致；路由表缺失回退旧行为 + 告警
  3. finding 输出通过 schema 校验；BH harness-findings.input.json 字段映射对照测试
  4. validate_state 对伪造旧 mtime 视图报 `[warn] stale view`（T-0116 措辞修正：仅告警，exit code 与既有判定一致）
  5. 投影视图 = state.yaml 派生（一致性测试）
- **依赖**：T-0107
- **风险与缓解**：文档归档破坏既有链接/continuity → 归档与链接测试同批、continuity 源清单同步；context_loader 行为变化 → 黄金快照
- **验收门**：`pytest tests/` 0 failed + 新增 F8 测试全绿；独立 gate
- **预计变更文件**：`.ai/README.md`（新增）、`.ai/archive/`（迁移）、`loop_core/context_loader.py`、`loop_core/context_packager.py`、`loop_core/context_budget.py`、`loop_core/schemas/finding.schema.json`（新增）、`loop_core/design_reviewer.py`、`loop_core/security_scanner.py`、`loop_core/subagent_evidence_verifier.py`、`loop_core/projection_engine.py`、`.zcode/tools/validate_state.py`、`agents/security-engineer/scripts/run_security_scan.py`（D1-7）、`agents/system-architect/scripts/analyze_dependencies.py`（D4-10）、`agents/module-architect/scripts/validate_contract.py`（D4-11）、`scripts/role_checkers/implementation_design_diff.py`（D5-7）、`docs/02-architecture.md`（front-matter designed_files:，D5-7 契约区）、`tests/test_ai_doc_links.py`（新增）、`tests/test_projection_freshness.py`（新增）

## T-0109 BH 融合·分层期（F2-阶段2/F3/F1/F5）

- **目标**：结构性分层与能力化：写入收敛、gates 分层、评估模型、工具 capability 化
- **范围**：
  - F2 阶段 2：状态写入统一经 governor_lib 事务写 + projection 刷新（任务卡 Status/HANDOFF/PROGRESS 派生）
  - F3 gates.yaml 分层（active/archive + forbidden 模板外提 + gate_type 枚举）
  - F1 评估模型（证据七态 + 评分上限表 59/74/84/94/100 + Repair/Loop 分离指标）
  - F5 工具 capability 化（分组元数据 → 薄壳消除 → 死工具确认删除 → 重复合并：dashboard 四层/证据链三处/安全扫描三处/缓存同步三处 → audience 分级）
- **AC 草案（可测）**：
  1. gates.yaml schema 校验 + 归档前后 load_gates active 域等价
  2. 写入收敛后仅 governor_lib 写 state 相关路径（静态检查 + 双写告警清零）
  3. F1 评分分档边界单测（59/74/84/94/100）+ 评分不进 gate 决策（静态断言）
  4. F5：注册表元数据完整（36 工具全覆盖）；合并后行为等价测试；死工具删除有调用图证据 + 一个 gate 周期无引用
  5. enforcement 白名单与工具变更同步（GOVERNANCE_TOOL_DIRS 一致性测试）
- **依赖**：T-0108
- **风险与缓解**：F5 影响面最大（MCP 注册表/白名单）→ 合并期双注册过渡、删除类子项独立 gate；F1 评分语义新增 → advisory-only 约束；F3 归档引用断裂 → 仅移域不删
- **验收门**：`pytest tests/` 0 failed + 专项测试全绿 + 全量回归；F5 删除类子项单独 gate；独立 gate
- **预计变更文件**：`loop_core/state_machine.py`、`.zcode/tools/governor_lib.py`、`.zcode/tools/validate_state.py`、`.ai/gates.yaml`、`.ai/archive/gates-archive.yaml`（新增）、`.ai/policies/forbidden-actions.yaml`（新增）、`loop_core/schemas/gate.schema.json`、`loop_core/gate_feedback.py`、`loop_core/governance_metrics.py`、`loop_core/schemas/evidence_state.py`（新增）、`.ai/slo.yaml`、`tools/*`（36 工具分组/合并/删除）、`tools/server.py`、`loop_core/capability_registry.py`、`loop_core/status_dashboard.py`、`loop_core/dashboard_views.py`、`loop_core/evidence_chain.py`、`hooks/scripts/loop_enforcement.py`（白名单同步，仅常量表）

## T-0110 共同弱点·常量集中与巨型文件拆分

- **目标**：魔法数字集中化落地（M-1~17 清单）+ 5 个巨型文件行为等价拆分
- **范围**：
  - 常量集中：`loop_core/constants.py` + `loop_enforcement_constants.py` + tool 共享常量 + slo.yaml 上限表（M-16）（显式覆盖 P3：D2-3/4/5/6/7、D1-5/6/8 —— M-7/8/9/3/4/10/11 清单项，含截断统一标记；D3-6/8 补 timeout=10 + 异常兜底接入常量表；D4-9 role_checkers 裸 except 收窄，与 D3-6 同文件同批）
  - 拆分：loop_enforcement.py（外提契约解析/命令工具/常量表/gate 证据检查）→ governance_metrics.py → intent_router.py → human_review_packet.py → context_loader.py（各按 design-common-weakness.md 边界；D5-4 词表/正则外提 intent_keywords.py/intent_detection.py/intent_split.py 随 intent_router 拆分落地）
- **AC 草案（可测）**：
  1. 常量表单测 + `grep timeout=[0-9]` 零新散落
  2. 每文件拆分后 golden 快照逐字节/逐字段一致（该文件专项验收）
  3. loop_enforcement 自愈路径实测（re-exec 一次、判定一致）
  4. `pytest tests/` 0 failed（全量回归基线）
- **依赖**：T-0109（拆分前先常量集中，外提引用常量表）
- **风险与缓解**：拆分散落行为漂移 → 逐文件独立 gate、golden 先行；循环导入 → import_checker + lint；hook 拆分风险最高 → loop_enforcement 最后拆、golden 语料最全
- **验收门**：每文件拆分独立 gate；全量回归；hook 自愈实测
- **预计变更文件**：`loop_core/constants.py`（新增）、`hooks/scripts/loop_enforcement_constants.py`（新增）、`hooks/scripts/loop_contract_parser.py`（T-0107 已有）、`hooks/scripts/loop_command_utils.py`（新增）、`hooks/scripts/gate_evidence_checks.py`（新增）、`loop_core/governance_loaders.py`/`governance_aggregations.py`/`slo_evaluator.py`/`dora_metrics.py`（新增）、`loop_core/intent_keywords.py`/`intent_detection.py`/`intent_split.py`（新增，D5-4）、`loop_core/review_models.py`/`resume_payload.py`/`review_renderer.py`（新增）、`loop_core/loader_fields.py`/`loader_summary.py`/`citation_resolver.py`/`loader_sections.py`（新增）、`loop_core/executor.py`（D1-6）、`loop_core/security_scanner.py`/`loop_core/design_reviewer.py`（D1-5）、`tools/loop_self_audit.py`（D1-8/D2-7/D3-8）、`scripts/role_checkers/scope_drift_detector.py`/`review_coverage_checker.py`（D3-6/D4-9）、各原巨文件（瘦身为壳）

## T-0111 共同弱点·修复器治理与臃肿全景清理

- **目标**：修复器触发率度量与缺陷归类落地；臃肿全景清理收尾验证（死工具/死文档/重复合并确认）
- **范围**：
  - 修复器度量：guard-events 新增 check_type="repair" 事件（validate_state/close_session 触发点写入）+ `repair_trigger_rate`/`repair_classification` 指标（design-common-weakness.md 3.2-3.4）
  - 生成路径缺陷归类报告（over_strict / unstable_generation / benign）
  - 臃肿清理确认：死工具删除复核、归档文档核对、36 工具注册表终态审计
  - **P3 追加（P2-1 排布补齐）**：D3-3（execution_ledger 归档保留 N 份 + 跨归档链延续，清理/防篡改链主题）、D4-6（observability 读侧损坏行计数，随 check_type 扩展同文件同批）
  - **不实施（记录留档）**：D3-7（dev.py 日志轮转——audit 已分类"文档化即可"，dev 内部工具影响低，仅终态审计留档）
  - 全量回归 + 性能基线（perf_runner）
- **AC 草案（可测）**：
  1. REPAIR_MODE 运行产生 guard-events repair 事件（PASS/FAIL 两分支断言）
  2. fixed=0 连续场景归类 over_strict；fixed>0 归类 unstable_generation
  3. dynamic_only 不重算 semantic_sha256；非 repair 模式 SOURCE_DRIFT 仍 exit 2（兜底边界测试）
  4. 注册表终态：无死工具残留（调用图证据）、无重复实现（合并清单闭环）
- **依赖**：T-0110
- **风险与缓解**：度量事件污染既有 guard-events 消费者 → check_type 枚举向后兼容；归类阈值误判 → 报告制不自动阻断
- **验收门**：`pytest tests/` 0 failed + 专项测试 + perf 基线无回退；独立 gate
- **预计变更文件**：`loop_core/observability.py`（check_type 扩展 + D4-6 读侧计数）、`loop_core/governance_metrics.py`（指标）、`loop_core/execution_ledger.py`（D3-3 归档保留 + 跨归档链）、`.zcode/tools/validate_state.py`、`.zcode/tools/close_session.py`、`.zcode/tools/repair_continuity.py`（只读不动，边界验证测试）、`tests/test_repair_governance.py`（新增）、`.ai/README.md`（终态）、`.ai/KNOWN_ISSUES.md`（闭环）

---

## 汇总表

| 任务 | 名称 | 依赖 | 风险等级 | 核心产出 |
|------|------|------|----------|----------|
| T-0107 | 漏洞修复（正确性，P1+P2+D5-P2） | T-0106 | LOW（D4-2 子项 HIGH 敏感，单列门禁） | context_packager 专项 9 处清零、双解析器收敛、P2×11、P3×6（D3-4/5、D4-5/7/8、D5-5） |
| T-0108 | BH 融合·收敛期（F4/F6/F7/F8/F2-1） | T-0107 | LOW-MED | Switchboard/路由、上下文打包、finding 契约、契约测试、新鲜度检查、P3×9 |
| T-0109 | BH 融合·分层期（F2-2/F3/F1/F5） | T-0108 | MED（F5 影响面最大） | 写入收敛、gates 分层、评估模型、工具 capability 化 |
| T-0110 | 共同弱点·常量集中与巨型文件拆分 | T-0109 | MED（hook 拆分最高） | constants 落点、5 文件行为等价拆分、P3×12（M 清单显式化） |
| T-0111 | 共同弱点·修复器治理与全景清理 | T-0110 | LOW-MED | repair 度量/归类、臃肿终态审计、全量回归+perf 基线、P3×2 |

**全程约束**：hook 强制层零改动（T-0107 D4-2 最小修复除外，独立 gate）；治理内核（gate_guard/enforcement/hard_constraints/guard_health/state_machine/validate_state 默认值）语义不变；每任务独立 gate 批准后实施；防篡改/fail-closed/审批闭环三机制贯穿（逐特性见 design-bh-integration.md 必须保持清单）。

---

## 新增前置机制项：session-source-disabled（已撤销——2026-08-03 用户决策，见下）

> 撤销记录：原 T-0112 候选（恢复/启用 Qoder 工作区会话证据源）已撤销——Qoder 为外部会话宿主，
> 其会话数据不能作为 ZCode 验收证据（HANDOFF Scope Correction）。本问题保留为
> KNOWN_ISSUES 记录，不立项修复；如后续需要，改走 ZCode 原生会话证据路径独立立项。

### 问题定性

Better Harness 会话分析报告同时出现 `disabled-source-root` 与 `missing-optional-root`，仅 `1/5` 个 enabled source roots 存在，`eligibleSessions=0`。这不是普通的“当前证据边界”，而是 Qoder 工作区会话源被禁用、缺失或不可读的机制缺陷：即使工作区存在会话，分析器也读不到，导致任务理解、可控执行、改动验证、可靠交付持续处于 Unobserved，评分被证据上限锁死；经验沉淀因没有 Task Episode 证据同样无法验证。

### 修复目标

1. 恢复/启用 Qoder 工作区会话证据源，修复 source-root 配置、路径解析和导入权限。
2. 对 5 个 enabled root 逐一输出 configured/resolved/exists/readable/sessionCount/eligibleCount/reason，禁止只报告 `1/5`。
3. 重新运行会话事实收集，确认 `eligibleSessions > 0`，且无未解释的 `disabled-source-root`。
4. 导入至少两个可比较的 Task Episode，事件至少覆盖 session start、task identification、edit、validation、close/recovery，并保留非空 evidenceRefs。
5. 在源恢复前，所有洞察保持 `NO_EVIDENCE` 或 `INSUFFICIENT_SAMPLE`，不得把“不可观察”解释为“未执行”。

### 任务边界与排布

- **候选任务**：T-0112（Qoder 会话源恢复与可比较观察窗口）。
- **依赖**：需要 Better Harness/Qoder 工作区配置与事实收集入口可用；不依赖 T-0107 的代码修复。
- **与现有任务关系**：T-0107 继续只处理设计漏洞正确性修复；T-0108 的 BH 融合验收必须把 T-0112 作为可观测性前置条件或明确记录未满足，不得用静态文件存在替代会话证据。
- **禁止合并**：不得在 T-0107 中直接修改 Qoder 外部配置、伪造 Episode、放宽评分上限或绕过用户 gate。

### 可测验收标准

- [ ] 五个 source root 均有逐项诊断状态；不可用 root 有明确错误码和修复建议。
- [ ] `eligibleSessions > 0`，且 `disabled-source-root` 不再出现；`sourceGaps` 为空或逐项有可接受解释。
- [ ] 至少两个可比较 Task Episode 成功导入，至少覆盖一次 edit→validation 和一次 rework/recovery。
- [ ] Episode 与 task/session/gate 可关联，evidenceRefs 非空、可追溯、已脱敏。
- [ ] 重新评审后，任务理解、可控执行、改动验证、可靠交付四维不再因会话源缺失被锁定；经验沉淀具备可比较窗口。
- [ ] 未满足上述条件时，报告明确为“无可用观察证据”，不输出确定性行为结论。

---

## P3 项归属总表（T-0106 P2-1 排布补齐）

> 全部 30 项 P3（audit-design-gaps.md 编号）显式任务归属；编号引用以 audit-design-gaps.md 为准。T-0109（BH 分层期）不承接 P3。

| P3 编号 | 内容（一行） | 归属任务 | 理由（一行） |
|---------|--------------|----------|--------------|
| D1-3 | context_packager:68 extra_files `[:2000]` 截断无标记 | T-0108（F6） | F6 上下文打包重写已含 D1-1~4 九处缺陷族，截断标记统一落地 |
| D1-5 | security_scanner/design_reviewer snippet `[:100]` 无省略号 | T-0110（M-10） | 截断字面量集中（M-10 含 500/100）+ 统一 `…` 标记 |
| D1-6 | executor:813 失败 stderr `[:500]` 截断无标记 | T-0110（M-10） | 同上，字面量入常量表 + 尾部/长度提示 |
| D1-7 | run_security_scan raw `[:500]` 无 truncated 标志 | T-0108（F7） | agents/*/scripts 输出收敛入 finding schema，截断标志结构化（F7 改造名单内） |
| D1-8 | loop_self_audit 尾部截断 4000/2000/800/400 字面量 | T-0110（M-11） | 与 D2-7 同源，M-11 截断字面量集中 + 标记 |
| D2-3 | intent_router:612 置信度惩罚阈值（≥4 且 ≤2） | T-0110（M-7） | 阈值族集中（M-7 落点 loop_core/constants.py） |
| D2-4 | intent_router:637,790 `len(kw) > 3` 两处重复 | T-0110（M-8） | 阈值族集中（M-8） |
| D2-5 | veto_escalation:245 USER_GATE 升级阈值 ≥3 | T-0110（M-9） | 阈值族集中（M-9） |
| D2-6 | timeout=30 六文件 + timeout=20 两处散落 | T-0110（M-3/M-4） | timeout 族集中（hook 工具共享常量） |
| D2-7 | loop_self_audit 截断字面量未命名 | T-0110（M-11） | 与 D1-8 同源集中 |
| D2-8 | context_packager git timeout 5/10/5 字面量 | T-0108（F6） | F6 已含"timeout 常量集中（5/10/5 → 命名常量）" |
| D3-3 | execution_ledger 归档无保留策略 + 归档即重置链 | T-0111 | 清理/防篡改链主题：保留 N 份归档 + 跨归档链延续，随全景清理同批 |
| D3-4 | runtime_controller `runtime-events.jsonl` 无轮转 | T-0107 | 与 D3-1 轮转族同批（复用 observability 轮转方案），风险 LOW |
| D3-5 | async_jobs 落盘 JSONL 追加无轮转 | T-0107 | 同上，与 D3-1 同批 |
| D3-6 | role_checkers `git diff` subprocess 无 timeout | T-0110 | timeout 常量落点（M-3 族，默认 10s）+ 异常处理 |
| D3-7 | dev.py:391 `open("a")` 日志无轮转 | **不实施（记录留档）** | audit 已分类"文档化即可"：dev 内部工具影响低；T-0111 终态审计留档 |
| D3-8 | loop_self_audit `git rev-parse` 无 timeout 无兜底 | T-0110 | timeout 常量落点 + try/except 返回空串（与 D3-6 同族） |
| D4-4 | context_packager knowledge cases 损坏静默丢弃 | T-0108（F6） | F6 已含 D4-1/4（捕获后记 warning） |
| D4-5 | audit_ledger:58-59 损坏行静默跳过 | T-0107 | 与 D3-1 同文件（audit_ledger）同批：记录损坏行号/计数 |
| D4-6 | observability:209-210 损坏行静默跳过 | T-0111 | 与 check_type="repair" 扩展同文件同批：读侧 warning/计数对称 |
| D4-7 | loop_enforcement:94 哈希读取 OSError continue | T-0107 | 与 D4-2 同文件同批：记录被跳过文件，最小 diff |
| D4-8 | transaction_registry:161 裸 except 吞中断 | T-0107 | 正确性缺陷：吞 KeyboardInterrupt/SystemExit，收窄 + 日志 |
| D4-9 | role_checkers 裸 except（yaml 降级 / INVALID） | T-0110 | 与 D3-6 同文件同批：收窄 + 记原因 |
| D4-10 | analyze_dependencies:71 宽捕获静默返回 None | T-0108（F7） | agents 脚本输出收敛同批：失败原因区分上报 |
| D4-11 | validate_contract:279,342 冗余宽捕获 | T-0108（F7） | 同上：收窄 + 记录失败文件 |
| D5-3 | context_loader 正则/标题位置/关键词节推断 | T-0108（F4） | F4 节选择改读 Switchboard 路由表（既有声明） |
| D5-4 | intent_router 词表/正则启发式推断 | T-0110 | 词表/正则外提 intent_keywords.py 等（拆分 1.3 既有变更文件） |
| D5-5 | contract_verifier fallback 位置推断重建 | T-0107 | 与 D5-1/2 解析器收敛同族：收窄触发条件 + 产出去向标注（F7 依赖项） |
| D5-6 | memory_service 验收报告正则族 | T-0108（F7） | F7 报告 front-matter 契约化（既有声明）+ 未命中行计数 |
| D5-7 | implementation_design_diff 反引号正则推断 | T-0108（F4） | 架构文档 front-matter designed_files: 显式声明区随 F4 文档结构规范化落地 |

**归属统计**：T-0107 ×6（D3-4/5、D4-5/7/8、D5-5）｜T-0108 ×9（D1-3/7、D2-8、D4-4/10/11、D5-3/6/7）｜T-0110 ×12（D1-5/6/8、D2-3~7、D3-6/8、D4-9、D5-4）｜T-0111 ×2（D3-3、D4-6）｜不实施（记录留档）×1（D3-7）＝ 30 项全覆盖。
