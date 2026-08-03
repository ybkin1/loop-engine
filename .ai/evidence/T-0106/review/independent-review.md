# T-0106 独立审查报告（independent-review）

- 任务：T-0106 — Better Harness 融合与 LE 去臃肿升级：总设计 + 全仓库漏洞排查（candidate-only）
- 审查角色：independent-reviewer（fresh context，全部结论亲自复验）
- 基线：fb9d194（v3.12.43）；审查日期：2026-08-03
- 审查方式：git diff 核对 + 42 项发现逐文件行号复验（22 项深度抽查）+ 设计文档结构审查 + 全量 pytest 回归（含基线对照）

---

## 一、裁决：CONDITIONAL_GO

候选交付整体真实、高质量、零约束弱化；发现 0 项 P0/P1，1 项 P2（排布缺口/文档间不一致），3 项 P3（均为文档精度瑕疵，不影响本任务 AC 达成）。

**有条件放行的条件（T-0107 开工前落实，均为文档级修正，不涉及代码）**：
1. **P2-1 排布补齐**：audit-design-gaps.md §五 建议排布与 plan-task-roadmap.md 冲突——前者将"全部 P3"排入 T-0109，后者 T-0109 为"BH 融合·分层期"（F2-2/F3/F1/F5），30 项 P3 中约 18 项（D1-7、D3-3~8、D4-4~11、D5-5、D5-7 等）在 T-0107~T-0111 无任何任务归属。需显式补齐：并入 T-0109/T-0111 范围，或声明延后至 T-0112+ 并保持 KNOWN_ISSUES 追踪。
2. **F7 依赖引用修正**：design-bh-integration.md F7 依赖声称"T-0107（D5-5 contract_verifier 收窄）"，但 D5-5 为 P3，不在 T-0107 范围（T-0107 = P1+P2+D5-1/2）。两文档需对齐。
3. **F3 文件名修正**：design-bh-integration.md F3 目标文件写 `loop_core/schemas/gate.schema.yaml`，实际文件为 `loop_core/schemas/gate.schema.json`。

---

## 二、约束零弱化 + 改动范围核对（PASS）

`git diff fb9d194`（工作区未提交变更）全量核对：

| 变更文件 | 内容 | 判定 |
|---|---|---|
| `.ai/KNOWN_ISSUES.md`（+15） | Open 区新增 T-0106 修复项 12 条 + 小节头 | 允许路径内 ✓ |
| `.ai/evidence/observability/guard-events.jsonl`（+13） | 13 条 guard 健康/死亡检查 PASS 事件（2026-08-03T03:40Z，T-0106 会话期间的自动观测日志） | .ai/ 内自动写入 ✓ |
| `.ai/gates.yaml` | G-T-0106-REQUIREMENTS gate 状态 approved + execution in_progress；**新增 allowed_read_paths**（agents/skills/loop_core/hooks/tools/scripts/tests/docs/.zcode 等，只读） | 允许路径内 ✓；只读扩展为排查所需，forbidden_actions 与 allowed_paths（写）未变，**非约束弱化** |
| `.ai/tasks/T-0105.md`（+1） | Status in_progress → completed（T-0105 收尾记账，任务卡风险表明示"互不冲突"） | 允许路径内 ✓ |
| `.ai/evidence/T-0106/`（未跟踪） | design/ 4 文档 + commands.md + gate 自动证据 3 件 | 允许路径内 ✓ |

- **产品代码零改动**：`hooks/`、`loop_core/`、`tools/`、`scripts/`、`agents/`、`.zcode/`、`tests/` 均无 diff（git diff --stat 仅 4 个 .ai/ 文件，+50/-6）。
- **版本载体零改动**：pyproject.toml:7 与 loop_core/__init__.py:9 均为 3.12.43，未动。
- **约束语义**：gates.yaml forbidden_actions（modify hooks/ 等）原样保留；gate 只读路径扩展不改变写权限与 fail-closed 语义。
- **结论**：AC-06 达成，约束零弱化确认。

---

## 三、排查真实性抽查表（22/22 真实，准确率 100%，行号精确率 ~86%）

统计核对先行：42 项 = P1×1 + P2×11 + P3×30，与任务卡预期完全一致；每维度数量（D1:8、D2:8、D3:8、D4:11、D5:7）逐一复算正确。**域分布表有算术瑕疵（见 P3-1）**。

| # | 发现 | 文件:行号 存在 | 描述与代码一致 | 判定 |
|---|------|--------------|----------------|------|
| D1-1 | context_packager.py:42 任务卡 `[:1000]` 截断无标记（P1） | ✓ 精确 | ✓ T-0105.md 实测 4363 字符（报告称 4365，±2），AC-01 位于索引 3231，截断点（1000）落在业务范围中段，AC/验收节被切成立 | PASS |
| D1-2 | context_packager.py:62 max_content 截断无标记 | ✓ 精确 | ✓ | PASS |
| D1-3 | context_packager.py:68 extra_files `[:2000]` | ✓ 精确 | ✓ | PASS |
| D1-4 | context_packager.py:76 json.dumps[:3000] 截断 JSON | ✓ 精确 | ✓ | PASS |
| D1-5 | security_scanner.py:190,198,206,219 + design_reviewer.py:95,104 `[:100]` | ✓ 6 处全精确 | ✓ | PASS |
| D1-6 | executor.py:813 stderr[:500] | ✓ 精确 | ✓ | PASS |
| D1-7 | run_security_scan.py:137,142,143 raw[:500] 无标志 | ✓ 精确 | ✓ | PASS |
| D1-8 | loop_self_audit.py:81,138-139 4000/2000/800/400 | ✓ 精确 | ✓ | PASS |
| D2-1 | context_packager.py:42,68,76,65,74 字面量散落 | ✓ | ✓ | PASS |
| D2-2 | intent_router.py:558 `len(triggered_medium) >= 3` | ✓ 精确 | ✓ | PASS |
| D2-3 | intent_router.py:612 ≥4 且 ≤2 惩罚 | ✓ 精确 | ✓ | PASS |
| D2-4 | intent_router.py:637,790 `len(kw) > 3` | ✓ 精确 | ✓ 两处均核实 | PASS |
| D2-5 | veto_escalation.py:245 `len(distinct_roles) >= 3` | ✓ 精确 | ✓ | PASS |
| D2-6 | timeout=30 六文件散落（content_guard:71,76 / loop_enforcement:630 / rollback:207 / tool_evidence_chain:21,41 / tool_cost_tracker / upgrade）+ guard_health:247,258 timeout=20 | ✓ | ✓ 独立 grep 复现 6 文件 8 处；tool_cost_tracker 实际 :20（报告 :18）、upgrade 实际 :251（报告 :247），±3 | PASS |
| D2-7 | loop_self_audit 截断字面量 | ✓ 精确 | ✓ | PASS |
| D2-8 | context_packager.py:46,49,54 timeout=5/10/5 | ✓ 精确 | ✓ | PASS |
| D3-1 | audit_ledger.py:84 append 无轮转；observability 有 10k 行/10MB/3 档 | ✓ 精确 | ✓ observability.py:53-55 常量独立核实 | PASS |
| D3-2 | context_packager.py:37-38 MAX=15000 死护栏（total 从不递增） | ✓ 精确 | ✓ 全文核查 total 仅出现在 `total < MAX`，从未递增，死代码成立 | PASS |
| D3-3 | execution_ledger.py:184-192 归档无保留策略 + 链重置 | ✓ 精确 | ✓ | PASS |
| D3-4 | runtime_controller.py:120 journal_path，:489-492 append 无轮转 | ✓（:120 精确；append 实际 :490-491） | ✓ | PASS |
| D3-5 | async_jobs.py:504-523 落盘追加无轮转 | ✓ | ✓ | PASS |
| D3-6 | role_checkers git diff 无 timeout | 部分 | ✓ review_coverage_checker.py:8 精确；scope_drift_detector 实际 :15（报告 :14，±1）；"全仓库仅这两处 + loop_self_audit.git_commit"经独立 sweep 复现 | PASS |
| D3-7 | dev.py:391 open("a") 无轮转 | ✓ 精确 | ✓ | PASS |
| D3-8 | loop_self_audit.py:88-92 git_commit 无 timeout；evals.py:664 有 timeout=10 对照 | ✓ | ✓ evals.py:664 独立核实 | PASS |
| D4-1 | context_packager.py:57-58 `except Exception: pass` | ✓ 精确 | ✓ | PASS |
| D4-2 | loop_enforcement.py:214-219 is_loop_mode_enforced fail-open | ✓ | ✓ 异常→return False 成立；:1771-1777 RuntimeController 路径异常→EXIT_BLOCK 对照核实，不对称性成立 | PASS |
| D4-3 | tool_constraint_check.py:18,21 `except ValueError: pass` | ✓ 精确 | ✓ | PASS |
| D4-4 | context_packager.py:77-78 knowledge cases 静默丢弃 | ✓ 精确 | ✓ | PASS |
| D4-5 | audit_ledger.py:58-59 损坏行静默跳过 | ✓ 精确 | ✓ | PASS |
| D4-6 | observability.py:209-210 损坏行静默跳过 | ✓ 精确 | ✓ | PASS |
| D4-7 | loop_enforcement.py:94 OSError continue | ✓ 精确 | ✓ | PASS |
| D4-8 | transaction_registry.py:161 裸 except | ✓ 精确 | 基本一致；"try 内表达式本不会抛错"表述存疑（root 为 str 时 Path 除法会抛 TypeError，属双类型防御），但确为冗余双重计算 + 裸 except 吞 KeyboardInterrupt/SystemExit | PASS（表述微瑕入 P3-3） |
| D4-9 | scope_drift_detector.py:8、review_coverage_checker.py:13 裸 except | ✓ 均精确 | ✓ | PASS |
| D4-10 | analyze_dependencies.py:71 宽捕获冗余 Exception | ✓ 精确 | ✓ | PASS |
| D4-11 | validate_contract.py:279,342 冗余宽捕获 | ✓ 精确 | ✓ | PASS |
| D5-1 | context_controller.py:444-538 `_naive_yaml_parse` | ✓ 精确 | ✓ list_keys=["gates","tasks"] 实际 :472（报告 :473，±1）；全部值降字符串、静默产出部分 dict、`_load_state`/`_load_gates` :362/:376 消费、`_yaml_load` :429-442 fallback、governance_metrics load_guard_events :303-322 strict-parse 对照，全部独立核实 | PASS |
| D5-2 | loop_enforcement.py:259-295 vs context_controller.py:400-414 双解析器分歧 | ✓ | ✓ 独立验证：enforcement 版（load_task_contract :239-311）支持 mcp_allowed_tools 三种语法（含 `\|` markdown 表格行），context_controller 版完全不解析 mcp_allowed_tools——行为分歧成立 | PASS |
| D5-3 | context_loader.py:186-209 正则字段推断、:1283 Step 标题位置推断、:1299-1324 关键词节选择 | ✓ 均精确（:1283 逐字核对） | ✓ docstring 自认 "simple heuristic" | PASS |
| D5-4 | intent_router.py:626-646 / :649-738 / :1171-1183 | ✓（626/649 精确；_INTENT_SPLIT_RE 实际 :1171-1176） | ✓ 中文标点 lookbehind 独立核实 | PASS |
| D5-5 | contract_verifier.py:108-146 fallback 位置推断 | ✓（def 实际 :109，范围 ±1） | ✓ warning 实际 :117（报告 :116，±1）；"仅 function 行之后 test 行被收集"（顺序敏感）成立 | PASS |
| D5-6 | memory_service.py:52-70 正则族 | ✓ | ✓ _VERDICT_RE 实际 :62-63（报告 :63） | PASS |
| D5-7 | implementation_design_diff.py:13-14 反引号正则推断 | ✓ 精确 | ✓ | PASS |

**抽查结论**：22 项深度抽查全部真实存在、描述与代码一致，零误报；行号约 86% 精确，其余 ±1~4（不影响定位）。D5 两处核心新发现（双解析器分歧、naive YAML 降级）经独立阅读确认成立，且属真实行为差异而非文档臆测。

---

## 四、8 特性方案审查（AC-02，PASS，附 1 项 P3 修正）

| 特性 | 目标文件/模块真实 | 依赖/风险/验收齐备 | 必须保持（防篡改/fail-closed/审批闭环） |
|------|------------------|-------------------|----------------------------------------|
| F1 评估模型 | schemas/ 目录存在、gate_feedback.py/subagent_evidence_verifier.py/governance_metrics.py 存在、.ai/slo.yaml 存在 | ✓ | ①防篡改（evidence 哈希链不动）②fail-closed（Missing 不得自动通过）③审批闭环（can_approve_gate 不动）— 三项全覆盖 |
| F2 单一数据源 | state_machine.py:580 atomic_write_state、projection_engine.py:235 generate_projection、.zcode/tools/validate_state.py、governor_lib.py — 行号逐字核实 | ✓（依赖 T-0107 D5-2，两阶段过渡） | ①fail-closed ②审批闭环 ③防篡改 — 三项全覆盖 |
| F3 gates 分层 | .ai/gates.yaml、.ai/policies/（新增）、gate.schema —— **P3-2：报告写 gate.schema.yaml，实际为 gate.schema.json** | ✓ | ①fail-closed（_load_gates 异常语义保持）②审批闭环（归档不删 approval 记录）③防篡改（manifest 同步）— 三项全覆盖 |
| F4 文档路由 | context_loader.py:1299 _select_relevant_sections 精确 | ✓（依赖 F8 先行） | ①防篡改（repair_continuity 语义哈希永不自动重算）②审批闭环 ③fail-closed（路由缺失回退+告警）— 三项全覆盖 |
| F5 工具 capability 化 | dashboard 四层（status_dashboard/loop_dashboard/tool_dashboard/dashboard_views）、证据链三处（loop_core/tools/scripts）、安全扫描三处、缓存同步三处（_hook_sync.py/auto_sync_to_plugin_cache/sync_plugin_cache.py）——全部真实存在 | ✓ | ①防篡改（GOVERNANCE_TOOL_DIRS :356 与 :1884 白名单同步，不弱化）②fail-closed ③审批闭环 — 三项全覆盖 |
| F6 上下文打包 | context_packager.py 9 处缺陷计数与 audit 专项小结一致（D1-1~4/D2-1/D2-8/D3-2/D4-1/4 = 9） | ✓ | ①fail-closed（diff 失败告警+占位，不假装成功）②防篡改（只读）③审批闭环 — 三项全覆盖 |
| F7 finding 契约 | finding.schema.json 新增、design_reviewer/security_scanner/subagent_evidence_verifier/tool_evidence_submit 存在；**依赖引用瑕疵：声称 T-0107 做 D5-5，但 D5-5（P3）不在 T-0107 范围（见 P2-1）** | ✓ | ①fail-closed（schema 校验失败→INVALID 告警）②防篡改 ③审批闭环（建议性产物不触发 gate）— 三项全覆盖 |
| F8 契约测试 | tests/ 新增两模块（纯只读） | ✓ | ①测试只读不触发 repair ②fail-closed（失败即门禁失败）③防篡改（不改哈希/清单）— 覆盖到位（审批闭环对本特性不适用，已合理处理） |

- **治理内核/hook 触碰检查（PASS）**：全部 8 特性均在"必须保持"清单中显式声明治理内核语义不变；唯一 hook 行为改动为 T-0107 的 D4-2（fail-open→fail-closed，**增强而非弱化**，单列子项 + 独立门禁）；F5/F3 涉及 enforcement 白名单与 gates 解析路径的改动均为"同步/等价"性质并有行为等价测试兜底。方案层面未触碰 state_machine 决策语义、gate_guard/approval 审批闭环、fail-closed 阻断形态。

---

## 五、共同弱点方案审查（AC-03，PASS）

**1. 巨型单文件拆分（5 文件）**：
- 行数全部精确：loop_enforcement 2059、governance_metrics 1508、intent_router 1484、human_review_packet 1307、context_loader 1342（wc -l 逐一复验）。
- 拆分边界基于真实结构：governance_metrics 外提表（加载器 :215-370、聚合 :130-157/:808、SLO :663-1008、DORA :1012-1183、保留 MetricsReport :1206/classify_gate_phase :97/guard_anomaly_rates :499）逐项核实；intent_router 外提表（常量表 :35 起、检测辅助 :626-872、切分 :1127、保留 IntentRouter :314-620、route 主链 :1313-1484）核实；human_review_packet（模型 :34-254、resume :256-526、渲染 :570-682/1282-1307、builder :767-1281）核实；context_loader（正则 :186-209、摘要 :212-479、引用 :481-637、节选择 :1268-1324、保留主流程 :777-1188）核实。
- **"不拆主流程语义"明确**：loop_enforcement 保留 main() :1600 入口控制流与自愈 SHA+重执行机制（_hook_files_changed_since_load/_reexec_with_fresh_code/auto_sync_to_plugin_cache）在主文件——该机制依赖文件级闭包状态，评估保留原文件合理；路径裁决主链与 FULL 模式 fail-closed 语义显式保留。
- 行为等价验收完备：golden 快照（逐字节/逐字段）+ pytest 全量 + import_checker 防循环导入 + hook 自愈实测 + 每文件独立 gate。

**2. 魔法数字 M-1~17 清单**：抽查 M-1（loop_enforcement:158-159 EXIT_PASS/EXIT_BLOCK ✓、gate_guard:331/path_guard:200/content_guard:406 sys.exit(main()) ✓）、M-2（validate_state:333/336/339/455 返回 2、:450 返回 3 ✓；close_session 返回 2 ✓）、M-3/M-4/M-5（timeout 30/20/5-10-5 ✓）、M-6~9（intent_router/veto 阈值 ✓）、M-10/M-11（截断字面量 ✓）、M-12（MAX=15000 ✓）、M-13（max_content 表 :6-18 ✓）、M-14/M-15/M-17（observability 轮转、MAX_CONTRACT_AGE_DAYS=90 :44、MAX_CAPTURE_CHARS=64KB :65 ✓）；M-16 为 BH 新值落点。落点设计（loop_core/constants.py + hook 常量 + governor_lib + config/slo.yaml + 已有具名常量保持为模板）可落地，验收含"grep 零新散落"可测。

**3. 修复器治理**：repair_continuity.py 79 行精确；触发点 validate_state.py:383-402（REPAIR_MODE 分支）与 close_session.py:36-37（dynamic_only=True）核实；guard-events 事件落点（observability check_type 常量 :39-45 可扩展）可行；指标聚合（governance_metrics guard_anomaly_rates :499）真实；兜底边界明确（dynamic_only 不重算 semantic_sha256 — repair_continuity.py:53 `if not dynamic_only` 逐字核实；.tmp+os.replace :58-60；非 REPAIR_MODE SOURCE_DRIFT 仍阻断）。分类规则（over_strict/unstable_generation）与验收（PASS/FAIL 两分支计数、哈希未变断言、exit 2 断言）可测可落地。

---

## 六、排布可执行性审查（AC-04，条件 PASS — 见 P2-1）

**结构完整性（PASS）**：T-0107~T-0111 五任务均含 目标/范围/AC 草案（编号可测）/依赖/风险与缓解/验收门（pytest 0 failed + 专项 + 独立 gate）/预计变更文件清单，逐项核对无缺。

**依赖链（PASS）**：T-0107 ┬→ T-0108 → T-0109；T-0107 └→ T-0110 → T-0111。与 design-bh-integration.md 依赖图一致；T-0108 = F4/F6/F7/F8/F2-1、T-0109 = F2-2/F3/F1/F5，与批 2 文档一致。风险排序 LOW → LOW-MED → MED（F5 最大）→ MED（hook 拆分最高）→ LOW-MED（终态验证），满足"风险从低到高"。

**hook/内核不动（PASS）**：全程零 hook 语义改动，唯一例外 T-0107 D4-2（fail-open→fail-closed 增强性最小修复，单列子项 + 独立门禁）；T-0109 对 loop_enforcement.py 仅"白名单同步，仅常量表"；T-0110 hook 拆分限定纯外提 + 自愈回归实测；治理内核语义贯穿"必须保持"清单。

**覆盖缺口（FAIL 项 → P2-1）**：audit §五建议排布"T-0109：全部 P3（轮转补齐、常量集中、宽捕获收窄、无 timeout 补 timeout）+ D5-3~7 代码类修复"，但 roadmap T-0109 范围不含任何 P3 项（grep 验证：D3-3/D4-8/D5-5 等在 roadmap 出现次数为 0）。30 项 P3 中约 18 项（D1-7、D3-3~8、D4-4~11、D5-5、D5-7；D1-3/5/6/8 与 D2-3~8 可经 T-0110 常量集中 M-10/M-11/M-3/M-5/M-7/8/9 隐性覆盖）无显式任务归属。另 F7 依赖声称 T-0107 承担 D5-5（P3），与 T-0107 范围矛盾。修复项若失追踪，将随排布湮灭——需在 T-0107 开工前补齐归属（并入 T-0109/T-0111 或显式延后）。

---

## 七、KNOWN_ISSUES 登记核对（AC-05，PASS）

- 新增 12 条 = P1×1（D1-1）+ P2×11（D1-2/4、D2-1/2、D3-1/2、D4-1/2/3、D5-1/2），与 audit-design-gaps.md 的 P1/P2 全集**一一对应、编号引用一致**（diff 逐条对照）。
- 每条注明"→ T-0107 修复"；小节头声明"编号引用 .ai/evidence/T-0106/design/audit-design-gaps.md"——引用链完整可追踪。
- 说明：P3 修复项未登记（按 audit/roadmap 内追踪），严格读 AC-05 可接受；P2-1 修复后建议 P3 归属一并登记或显式声明延后。
- 既有 Open/Closed 项未被改动（diff 仅新增小节）。

---

## 八、回归结果（零回归确认）

- 全量：`C:/Python312/python.exe -m pytest tests/ -q` → **3867 passed / 1 failed / 64 skipped / 12 xfailed**（574s）。
- 唯一失败：`test_deployment_quality_checker.py::test_runtime_report_is_simulated_and_fail_closed`。**在干净基线 worktree（fb9d194，git worktree 独立检出）复跑同一测试同样失败**（1 failed, 3 passed）→ 该失败为基线预存问题（与 .zcode/tools/close_session 或 runtime_delivery_gate 环境相关），**与 T-0106 零代码改动无关**，非回归。
- 重点子集（任务卡指定）：test_version_consistency、test_governance_consistency、test_manifest_t0095 在 3867 通过中，全部绿。
- candidate-only 零代码改动的回归面成立：无任何由本任务引入的失败。

---

## 九、发现清单

**P0（阻断）：无。**

**P1（严重）：无。**
- 约束零弱化确认：仅 .ai/ 变更，产品代码零改动，版本载体未动，forbidden_actions 未改。
- 排查真实性：22/22 抽查真实（含 P1-1 与 D5 两项核心新发现），零误报。
- 方案质量：8 特性必须保持清单全覆盖，拆分边界真实，修复器治理可落地。

**P2（1 项）：**
- **P2-1 排布缺口/文档间不一致**：audit §五"P3→T-0109"与 roadmap T-0109 范围（BH 分层期）矛盾；约 18 项 P3 修复项（D1-7、D3-3~8、D4-4~11、D5-5、D5-7）在 T-0107~T-0111 无任务归属；F7 依赖引用 D5-5 未在 T-0107 排布。→ 条件：T-0107 开工前补齐归属并三文档对齐。

**P3（3 项，文档精度，不阻塞）：**
- **P3-1**：audit 域分布表算术不一致——表内合计 36 ≠ 总项 42；loop_core 应计 26 而非 20（按主文件域逐项复算：D1:6、D2:6、D3:5、D4:4、D5:5）。
- **P3-2**：F3 目标文件 `gate.schema.yaml` 不存在，实际为 `loop_core/schemas/gate.schema.json`。
- **P3-3**：个别行号 ±1~4（D2-6 tool_cost_tracker :20 vs :18、upgrade :251 vs :247；D3-6 scope_drift :15 vs :14；D5-1 list_keys :472 vs :473；D5-5 warning :117 vs :116；D1-1 T-0105 长度 4363 vs 4365；M-1 gate_guard :331 vs :330；D4-8"本不会抛错"表述存疑——str 型 root 下会抛 TypeError，属冗余双算而非纯死代码）。不影响定位与修复。

---

## 十、总结论

T-0106 候选交付达成 AC-01~AC-07 全部硬要求：42 项排查（P1×1/P2×11/P3×30）全部经独立复验真实（22 项深度抽查 100% 命中、行号高精度，D5 双解析器分歧与 naive YAML 降级两项核心新发现确凿成立）；8 特性方案每项含"必须保持"清单且不触碰治理内核语义；5 巨文件拆分边界基于真实代码结构且"不拆主流程语义"（自愈 SHA+重执行保留）明确；魔法数字 M-1~17 与修复器治理方案可落地可测；T-0107~T-0111 排布结构完整、依赖与风险排序合理、hook 全程不动（D4-2 例外为增强性修复且单列门禁）；KNOWN_ISSUES 12 条与 P1/P2 全集精确对应；全量回归零新增失败（唯一失败经基线对照确认为预存）。

**裁决：CONDITIONAL_GO**。条件（文档级，不涉代码）：补齐 P3 修复项任务归属并三文档对齐（P2-1）、修正 F7 依赖引用、修正 F3 文件名（P3-2）。条件落实后可转 GO。
