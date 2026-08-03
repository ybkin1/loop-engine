# T-0106 批 3 — 双方共同弱点优化方案（LE × BH）

- 任务：T-0106（candidate-only 设计任务，零产品代码变更）
- 依据：批 1 漏洞排查（audit-design-gaps.md）+ BH 调研对比 + 本批函数级抽查
- 日期：2026-08-03
- 范围：① 巨型单文件拆分（5 个 >50KB）② 魔法数字集中化 ③ "修复器"现象治理
- 总原则：拆分只外提、不改语义；每文件拆分后做**行为等价验收**（黄金快照）；hook 自愈与 fail-closed 语义零变化

---

## 一、巨型单文件拆分

### 1.1 hooks/scripts/loop_enforcement.py（2059 行）

**拆分边界（外提，均为纯函数/常量表，不改变控制流）**

| 外提内容 | 原位置（行号） | 目标新模块 |
|---|---|---|
| 自愈/重执行辅助（SHA 快照、hook 变更检测、重执行）——**评估后建议保留原文件**，因与 main 入口耦合（详见"不拆的主流程"） | :83-125 | （保留） |
| 任务卡契约解析（`load_task_contract` + `_task_mcp_allowed_tools`） | :239-311 | `hooks/scripts/loop_contract_parser.py`（与 context_controller 共享——消解 D5-2 双解析器） |
| 路径/命令判定辅助（`_is_python_interpreter`/`_msys_to_windows`/`_split_command_segments`/`_is_governance_tool_segment`/`_is_safe_cd_segment`/`_is_safe_display_segment`） | :378-529 | `hooks/scripts/loop_command_utils.py` |
| 约束常量表（EXIT_PASS/EXIT_BLOCK :158-159、`_REEXEC_MAX` :80、治理目录白名单 :356、max_files 默认值等） | :80,158-159,356,673 等 | `hooks/scripts/loop_enforcement_constants.py` |
| 各类 gate 证据检查（`check_quality_gate_evidence`/`check_delivery_gate_evidence`/`check_runtime_quality_gate`/`check_slo_gate_evidence`/`check_second_failure_gate_evidence`/`check_security_gate_evidence`/`check_phase_gate_enforcement`） | :742-1569 | `hooks/scripts/gate_evidence_checks.py`（纯函数，返回 (bool, str)） |

**保留在主文件的（不拆的主流程语义）**：`main()` :1600 入口控制流；**自愈 SHA+重执行机制**（`_hook_files_changed_since_load` :119 + `_reexec_with_fresh_code` :125 + `auto_sync_to_plugin_cache`，:1602-1613 调用链）——该机制依赖主文件级闭包状态与 env 计数器，拆分即破坏；路径裁决主链 `is_governance_write`/`is_governance_tool_command`/`is_in_task_scope`/`check_diff_scope`（:313-673）与 FULL 模式 fail-closed 语义。

**行为等价验收**：
1. 黄金快照：构造固定 hook_input 语料（PASS 放行 / 外部路径 BLOCK / 治理工具放行 / 任务范围外写入 BLOCK / loop 模式开关各态），拆分前后 stdout+exit code 逐字节一致；
2. 自愈回归：改本地 hook 文件 → 触发 re-exec，仍只执行 1 次（`_REEXEC_MAX=1`），判定一致；
3. 既有测试套件（tests/ 下 enforcement/绕过矩阵相关）全绿。

### 1.2 loop_core/governance_metrics.py（1508 行）

**拆分边界**

| 外提内容 | 原位置 | 目标新模块 |
|---|---|---|
| 数据加载器（`_load_jsonl`/`load_gates`/`load_tasks`/`load_guard_events`/`load_phase_transitions`/`load_executions`/`load_runtime_events`） | :215-370 | `loop_core/governance_loaders.py` |
| 统计聚合辅助（`_percentile`/`_seconds_stats`/`_over_target` 等） | :130-157,808 | `loop_core/governance_aggregations.py` |
| SLI/SLO 评估（`load_slo_config`/`evaluate_sli`/`compute_error_budget`/`_metric`/`_not_available`） | :663-1008 | `loop_core/slo_evaluator.py` |
| DORA 指标构建（`build_dora_metrics`/`_sha256`/`git_commit`） | :1012-1183 | `loop_core/dora_metrics.py` |

**保留**：数据类（GateMetric/TaskRecord/PhaseTransition/SliContext/GuardCheckEvent :159-213）、MetricsReport :1206+、`classify_gate_phase` :97、`guard_anomaly_rates` :499 等度量面入口。**必须保持**：`load_guard_events` 的 strict-parse fail-closed（:303-322，损坏行 → NOT_AVAILABLE 而非静默跳过）；SLO 评估的 DataSourceUnavailableError 语义（`slo_gate.py` 依赖）。

**行为等价验收**：固定 .ai 夹具（gates.yaml/guard-events.jsonl/executions.jsonl 快照）→ 拆分前后 MetricsReport 输出逐字段一致（golden JSON diff）；`governance_metrics` 相关既有测试全绿。

### 1.3 loop_core/intent_router.py（1484 行）

**拆分边界**

| 外提内容 | 原位置 | 目标新模块 |
|---|---|---|
| 关键词常量表（`DOMAIN_KEYWORDS` 等大表） | :35 起 | `loop_core/intent_keywords.py`（纯数据常量表） |
| 检测/评分辅助（`_detect_domains`/`_extract_risk_factors`/`_is_negated`/`_set_if_match`/`_compute_complexity`/`_build_reasoning`） | :626-872 | `loop_core/intent_detection.py` |
| 意图切分/切换辅助（`split_intents`/`_INTENT_SPLIT_RE`/`detect_intent_switch`/`_other_task_refs`/`_active_task_completion_signal`） | :1127-1235 | `loop_core/intent_split.py` |

**保留**：`IntentRouter` 类 :314-620、`IntentAnalysis`/`ProjectProfile` 转换 :934、`route_user_input`/`_route_internal` :1313-1484（路由主流程与 LoopMode 决策语义）。

**行为等价验收**：固定描述语料集 → 拆分前后 `analyse_intent`/`route_user_input` 输出（mode/domains/risk/complexity）逐字段一致（golden JSON）；既有 intent_router 测试全绿。

### 1.4 loop_core/human_review_packet.py（1307 行）

**拆分边界**

| 外提内容 | 原位置 | 目标新模块 |
|---|---|---|
| 数据模型（PacketType/KeyChoice/RiskItem/DecisionRequired/DecisionPoint/ResumeSnapshot/ResumePayload/ResumeContext 及 to/from_dict 序列化） | :34-254 | `loop_core/review_models.py` |
| Resume 载荷逻辑（`_load_authoritative_yaml`/`_find_task`/`_find_gate`/`build_resume_payload`/`resume_from_payload` + 恢复字段常量） | :256-526 | `loop_core/resume_payload.py` |
| 渲染器（`HumanReviewPacket.to_markdown`/`to_plain_text` + `_phase_label`/`_format_ts`） | :570-682,1282-1307 | `loop_core/review_renderer.py` |

**保留**：`HumanReviewPacketBuilder` :767-1281（`from_phase_completion`/`from_veto_escalation`/`_extract_key_choices`/`translate_technical_risk`）——builder 主流程与 veto/phase 语义。

**行为等价验收**：固定 gate/phase/veto 输入 → 拆分前后 `to_markdown` 输出逐字节一致（golden text diff）；`resume_from_payload` 往返（build→resume→state 一致）测试；既有 review_packet 相关测试全绿。

### 1.5 loop_core/context_loader.py（1342 行）

**拆分边界**

| 外提内容 | 原位置 | 目标新模块 |
|---|---|---|
| 正则常量族 + key 字段提取（`_TASK_ID_RE` 等 :186-209、`extract_key_fields`/`_format_key_fields`） | :186-209,318-363 | `loop_core/loader_fields.py` |
| 摘要级别/行选择（`_level_line_params`/`_level_body_cap`/`_select_body_lines`/`_split_sentences`/`_truncate_line`/`summarize_text`/`estimate_tokens`） | :212-479 | `loop_core/loader_summary.py` |
| 引用解析（`CitationResolver`/`repair_truncated_references`/`_find_citation_tokens`） | :254-264,481-637 | `loop_core/citation_resolver.py` |
| 文档节选择/框架标题（`_extract_framework_titles`/`_select_relevant_sections`） | :1268-1324 | `loop_core/loader_sections.py` |

**保留**：`LoadLevel`/`LoadedContext`/`DocumentIndex`/`CompressionResult`/`ContextCompressor`、`ContextLoader` 主加载流程 :777-1188、`_parse_yaml` :1194、`_extract_fixed_stance`/`_extract_contract_extras` :1219-1266、记忆注入语义（fail-closed：store 损坏抛异常不猜）。

**行为等价验收**：固定文档语料 × 各 LoadLevel → 拆分前后 `load()` 输出文本逐字节一致（golden diff）；既有 context_loader 测试（tests/test_context_loader.py）全绿。

### 1.6 拆分通用验收门（每文件共用）

1. 行为等价：golden 快照逐字节/逐字段一致（上述每文件专项）；
2. 全量回归：`pytest tests/` 0 failed（T-0106 基线）；
3. 静态引用：拆分后 `grep -rn "from X import"` 全部解析成功，无循环导入（lint + import_checker）；
4. hook 强制层专项：loop_enforcement 拆分后自愈路径实测（改文件→re-exec→判定一致）；
5. 门禁：每文件拆分独立 gate 批准，拆一个验一个，不批量合入。

---

## 二、魔法数字集中化清单

### 2.1 现状清单（来源：批 1 D2 发现 + 本批抽查）

| # | 魔法值 | 位置（现状） | 语义 |
|---|--------|--------------|------|
| M-1 | exit code 0/2 | `loop_enforcement.py:158-159`（EXIT_PASS=0/EXIT_BLOCK=2，已命名但仅本文件）、`gate_guard.py:330`、`path_guard.py:200`、`content_guard.py:406`（均 `sys.exit(main())`，各 hook 各自定义） | hook 裁决返回码，多文件重复定义，值未集中 |
| M-2 | exit code 0/2/3 | `validate_state.py:333-463`（2=校验失败、3=版本不匹配）、`close_session.py:64-71`（2=未稳定） | 治理工具返回码，分散 |
| M-3 | timeout=30 | `content_guard.py:71,76`、`loop_enforcement.py:630`、`rollback.py:207`、`tool_evidence_chain.py:21,41`、`tool_cost_tracker.py:18`、`upgrade.py:247`（6 文件） | 工具/命令超时 |
| M-4 | timeout=20 | `guard_health.py:247,258` | guard 健康探测超时 |
| M-5 | timeout=5/10/5 | `context_packager.py:46,49,54`（D2-8） | git 命令超时 |
| M-6 | 升级阈值 ≥3 | `intent_router.py:558`（D2-2，MEDIUM_RISK_ESCALATION_MIN） | loop_mode 升级 |
| M-7 | 置信惩罚 ≥4 且 ≤2 | `intent_router.py:612`（D2-3） | 置信度惩罚 |
| M-8 | 关键词长度 >3 | `intent_router.py:637,790`（D2-4） | 词边界策略 |
| M-9 | USER_GATE 升级 ≥3 | `veto_escalation.py:245`（D2-5） | 角色数阈值 |
| M-10 | 截断 1000/2000/3000/500/100 | `context_packager.py:42,62,68,76`、`executor.py:813`、`security_scanner.py:190-219`、`design_reviewer.py:95,104`（D1-2~6） | 上下文/输出截断 |
| M-11 | 截断 4000/2000/800/400 | `loop_self_audit.py:81,138-139`（D1-8/D2-7） | 审计输出尾部 |
| M-12 | MAX=15000 死护栏 | `context_packager.py:38`（D3-2） | 全局护栏（死代码） |
| M-13 | max_content 2000-8000 | `context_packager.py:6-18`（D2-1） | 角色文件上限表 |
| M-14 | 文件轮转 10k 行/10MB/3 档 | `observability.py`（已命名 DEFAULT_MAX_LINES/BYTES/ARCHIVES） | 已有集中先例（**对齐模板**） |
| M-15 | MAX_CONTRACT_AGE_DAYS=90 | `validate_state.py:44`（已命名） | 契约新鲜度阈值 |
| M-16 | 评分上限 59/74/84/94/100 | （LE 尚无数值评分天花板；BH 有） | BH 上限表显式化落点 |
| M-17 | MAX_CAPTURE_CHARS=64KB | `evals.py:65`（已命名，D3 排除项） | 捕获上限（已有先例） |

### 2.2 落点设计

| 落点 | 承载内容 | 消费方 |
|------|----------|--------|
| `loop_core/constants.py`（新增） | LE 内核共享常量：截断上限、token 预算、超时族、阈值族（M-6~11 迁移） | loop_core 各模块 |
| `hooks/scripts/loop_enforcement_constants.py`（新增，拆分 1.1 同源） | hook 共享：EXIT_PASS/BLOCK 统一值（M-1）、timeout 族（M-3/4）、路径白名单 | 各 hook 脚本 |
| `.zcode/tools/` 共享（`governor_lib.py` 或新增 `tool_constants.py`） | 治理工具 exit code（M-2）、MAX_CONTRACT_AGE_DAYS（M-15，validate_state 保留具名值，注册为共享引用） | validate_state/close_session |
| `config.yaml` / `.ai/slo.yaml` | 环境级可调值：token 预算、评分上限表（M-16，对齐 BH 上限表显式化，F1 消费）、阈值族 | context_packager/evals/governance_metrics |
| 已有具名常量（M-14/15/17） | 保持，作为集中化模板，不重复迁移 | — |

**集中化验收**：`grep -rn "timeout *=\|\[: *[0-9]"` 扫描零新散落（迁移后仅常量表出现）；常量表单测（取值/语义注释）；behavior 等价（golden 复用拆分验收）。

---

## 三、"修复器"现象治理

### 3.1 现象定位

修复器 = `repair_continuity.py`（79 行，SHA256 重算 + 原子写）。触发点：
- `validate_state.py:383-402`：`--repair` 或 `LOOP_REPAIR_CONTINUITY=1` 时，SOURCE_DRIFT 错误自动调用 `repair_continuity(root)`（全量模式，重算 source_sha256/semantic_sha256 :53-56）；
- `close_session.py:36-37`：会话收尾 `repair_continuity(root, dynamic_only=True)`（仅修 state/gates/task_graph 三个动态条目 :39-41）。

风险：自动修复会掩盖"生成路径不更新 manifest"或"校验过严误报"两类根因——修复 GO 不等于长期有效（与 F1 Repair Progress / Loop Effectiveness 分离同源）。

### 3.2 触发率度量方案（guard-events 加计数）

- **事件落点**：`observability.py` 事件层（GuardCheckEvent，check_type 常量 :39-45）新增 `check_type="repair"` 事件类型，由两个触发点写入：
  - `validate_state.py:391-402` 每次 REPAIR_MODE 触发写一条：`guard_id="repair_continuity"`、result=PASS（fixed>0）/FAIL（auto-repair 失败）、failure_reason 带漂移类型（SOURCE_DRIFT/SEMANTIC_DRIFT）与 fixed 计数；
  - `close_session.py:36-37` 每次收尾修复写一条：result=PASS/FAIL、failure_reason=dynamic drift 计数。
- **指标聚合**：`governance_metrics.py` 扩展 `guard_anomaly_rates`（:499）或新增 `repair_trigger_rate` = 周期内 repair 事件数 / guard 检查总数；Repair Progress 指标族（F1 消费）。
- **可观测性**：guard-events.jsonl 已有只读消费者（`load_guard_events` strict-parse），新事件类型向后兼容（check_type 枚举扩展，旧消费者不感知）。

### 3.3 生成路径缺陷归类（校验过严 vs 生成不稳）

判定规则（落到 repair 事件的 failure_reason 分类，由 metrics 聚合报告）：
- **校验过严**：repair 后重新校验仍 FAIL/REPORT，且被修文件 mtime 无外部人工修改窗口（连续多次 repair 事件 fixed=0）→ 证据：规则/白名单与真实写入路径不匹配（如 CONTINUITY 源清单含非动态文件却被正常流程写改）；
- **生成不稳**：repair 事件 fixed>0 且 mtime 落在正常写操作窗口（allowed_paths 内工具写入后未同步 manifest）→ 证据：生成器（continuity_producer 或写入工具）漏更新清单；
- **输出**：metrics 报告含 `repair_classification: {over_strict: n, unstable_generation: n, benign: n}`，超阈值（如 over_strict ≥3/周期）触发 gate 提示人工检视规则（不改自动语义）。

### 3.4 修复器保留为确定性兜底的边界（必须保持）

- `repair_continuity.py` 原子写语义（.tmp + os.replace :58-60）不动；SHA256 重算逻辑不动；
- `dynamic_only=True` 仅修三个动态条目（state/gates/task_graph :39-41）不动；
- **语义哈希（semantic_sha256）永不自动修复**（:54-56 仅全量模式重算、非动态修复；`dynamic_only` 下不重算）——防篡改边界不变；
- 非 REPAIR_MODE 时 validate_state 对 SOURCE_DRIFT 仍硬阻断（fail-closed :403-404）不动；
- 修复器只修清单哈希，不触碰 gate/审批/状态推进任何决策——审批闭环不变。

### 3.5 验收

- 计数测试：构造 REPAIR_MODE 运行 → guard-events.jsonl 出现 check_type=repair 事件（PASS/FAIL 两分支）；
- 分类测试：fixed=0 连续场景归类 over_strict、fixed>0 场景归类 unstable_generation；
- 兜底边界测试：dynamic_only 不重算 semantic_sha256（断言哈希未变）；非 repair 模式 SOURCE_DRIFT 仍 exit 2。
