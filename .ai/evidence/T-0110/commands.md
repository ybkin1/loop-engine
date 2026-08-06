# T-0110 批 A — 魔法数字集中化（M-1~17）+ P3 消解 — 实施命令记录

日期：2026-08-03（工作树基线：HEAD v3.12.46 + 主会话 T-0110 启动改动；
本批为 developer 子代理批 A 执行，版本 bump 由主会话负责）

## 落地清单

### 新增文件（2 个常量表 + 1 个测试文件）
1. `loop_core/constants.py`（新增，24 常量 + 2 截断辅助函数）
   - exit code 族（M-2）：`EXIT_OK=0` / `EXIT_VALIDATION_FAILED=2` /
     `EXIT_IDLE_BLOCKED=3`（validate_state/close_session 返回码共享登记；
     消费方接线受限时保留原字面量——显式豁免表见 fixes/batch-a-constants.md）
   - 截断族（M-10/M-11）：`SNIPPET_MAX_CHARS=100`（D1-5）、
     `FAILED_STDERR_MAX_CHARS=500`（D1-6）、`AUDIT_STDOUT_TAIL_CHARS=4000`/
     `AUDIT_STDERR_TAIL_CHARS=2000`/`AUDIT_SUMMARY_STDOUT_TAIL_CHARS=800`/
     `AUDIT_SUMMARY_STDERR_TAIL_CHARS=400`（D1-8/D2-7）、`TRUNCATION_ELLIPSIS="…"`
   - 超时族（D3-6/D3-8）：`GIT_DIFF_NAME_ONLY_TIMEOUT_SECONDS=10`、
     `GIT_SHORT_SHA_TIMEOUT_SECONDS=10`（对齐 evals.py git_commit 同款 timeout=10）、
     `AUDIT_RUN_TIMEOUT_SECONDS=300`
   - 阈值族（M-7/M-8/M-9）：`CONFIDENCE_CONFLICT_MIN_DOMAINS=4`/
     `CONFIDENCE_CONFLICT_MAX_RISK_FACTORS=2`（D2-3）、
     `KEYWORD_BOUNDARY_MAX_LEN=3`（D2-4）、`USER_GATE_MIN_DISTINCT_ROLES=3`（D2-5）
   - 辅助：`truncate_with_marker`（D1-5/6 前截断+`…`标记）、
     `tail_with_marker`（D1-8 尾部保留+标记）；均为纯函数、导入零副作用
2. `hooks/scripts/loop_enforcement_constants.py`（新增，M 清单 hook 部分）
   - M-1：`EXIT_PASS=0`/`EXIT_BLOCK=2`（与 loop_enforcement.py:172-173 现值一致，
     gate_guard/path_guard/content_guard 同值——批 C 统一接线）
   - M-3/M-4：`COMMAND_TIMEOUT_SECONDS=30`（六文件七处同值）、
     `GUARD_HEALTH_PROBE_TIMEOUT_SECONDS=20`
   - 阈值/默认：`REEXEC_MAX=1`（自愈重执行上限）、`MAX_DIFF_FILES=15`、
     `DEFAULT_MAX_FILES=10`
   - 治理路径白名单：`GOVERNANCE_EXEMPT`/`MINIMAL_METADATA_READ`/
     `MAIN_THREAD_ALLOWED`/`GOVERNANCE_TOOL_DIRS`（loop_enforcement.py 现值
     逐字拷贝，脚本比对 ALL MATCH；批 C 接线后唯一来源）
   - 本文件零依赖纯常量表；批 A 不触碰任何既有 hook 文件
3. `tests/test_t0110_batch_a.py`（新增，41 passed）
   - 常量表单测（两表逐值断言）+ 截断辅助纯函数
   - P3 消解行为测试（D2-3/4/5 边界、D1-5/6/8 标记、D3-6/8 兜底、D4-9 收窄）
   - AC-01 grep 零散落断言（touched 文件扫描 + 显式豁免）
   - M-16 slo.yaml score_caps 与 DEFAULT_SCORE_CAPS 一致性

### 改动文件（P3 消解 + 常量接线，全部行为等价）
| 文件 | 改动 | 对应项 |
|------|------|--------|
| loop_core/executor.py | 失败 stderr 截断 → `truncate_with_marker(stderr, FAILED_STDERR_MAX_CHARS)` | D1-6/M-10 |
| loop_core/security_scanner.py | 4 处 snippet `[:100]` → `truncate_with_marker(..., SNIPPET_MAX_CHARS)`；`truncated` 标志 `>= SNIPPET_MAX_CHARS` | D1-5/M-10 |
| loop_core/design_reviewer.py | 2 处 snippet `[:100]` → 同上 | D1-5/M-10 |
| loop_core/intent_router.py | `>= 4 且 <= 2` → `CONFIDENCE_CONFLICT_MIN_DOMAINS/MAX_RISK_FACTORS`；`len(kw) > 3` ×2 → `KEYWORD_BOUNDARY_MAX_LEN` | D2-3/D2-4/M-7/M-8 |
| loop_core/veto_escalation.py | `>= 3` → `USER_GATE_MIN_DISTINCT_ROLES` | D2-5/M-9 |
| tools/loop_self_audit.py | 尾部 `[-4000:]/[-2000:]/[-800:]/[-400:]` → `tail_with_marker` 命名常量；`timeout=300` → `AUDIT_RUN_TIMEOUT_SECONDS`；git_commit 补 timeout + 异常兜底返回 ""；validate_state rc 0/2/3 与 guard rc=2 → EXIT_* 常量 | D1-8/D2-7/D3-8/M-2/M-11 |
| scripts/role_checkers/scope_drift_detector.py | git diff 补 timeout + 异常兜底（error dict）；裸 `except:` → `ImportError` + 记原因；repo root sys.path 引导 | D3-6/D4-9 |
| scripts/role_checkers/review_coverage_checker.py | git diff 补 timeout + 异常兜底（status=ERROR）；裸 `except:` → `(ValueError, OSError)` + 记原因 | D3-6/D4-9 |

### M-16 核对
`.ai/slo.yaml` score_caps 节（T-0109 已加）与 `loop_core/schemas/evidence_state.py`
`DEFAULT_SCORE_CAPS` 逐项一致（Missing/Unobserved/N-A=59、Present=74、Wired=84、
Exercised=94、Outcome-supported=100），M-16 已覆盖，无需补充；测试
`test_slo_yaml_matches_default_score_caps` 锁定。

## 测试

- 新增 `tests/test_t0110_batch_a.py`：**41 passed**
- 相关既有套件（executor/intent_router(+upgrade)/veto_escalation/self_audit_llm/
  verdicts/code_quality/t0108_fixes/security_scan×2/evals/governance_metrics/
  enforcement/hooks/import_checker）：**493 passed**
- 全量回归 `pytest tests/`：**4090 passed, 64 skipped, 12 xfailed, 2 failed**
  - 两项失败均为**批 A 启动前预存**（与批 A 改动无关，见下节）

## 预存失败（2 项，非批 A 引入，基准已证）

1. `tests/test_manifest_t0095.py::test_manifest_exists_and_handoff_reference_is_real`
   — 主会话启动 T-0110 时编辑 `.ai/HANDOFF.md` 新增
   `Evidence manifest: .ai/evidence/T-0110/evidence-manifest.v1.yaml` 引用，
   清单文件在 T-0110 closeout 时产出（与 T-0109 同款预存记录，
   见 .ai/evidence/T-0109/commands.md 第 3 项）。批 A 未触碰 HANDOFF。
2. `tests/test_t0109_f5_tool_capability.py::TestWhitelistConsistency::test_hooks_only_whitelist_file_changed`
   — 硬编码断言 `git diff HEAD -- hooks/ == ["hooks/scripts/loop_enforcement.py"]`，
   仅在 T-0109 工作树（loop_enforcement.py 未提交改动）成立；T-0109 提交后
   干净树 diff 为空 → 必红。批 C 改动 loop_enforcement.py 后该测试将自然恢复
   绿灯（批 A 无既有 hook 文件改动，`git diff HEAD -- hooks/` 为空为基线状态）。

## 约束自查

- hooks/ 仅新建 loop_enforcement_constants.py；其余 hook 文件零改动 ✓
- 治理内核判定零触碰（gate_guard/enforcement 判定语义/hard_constraints/
  guard_health/state_machine 均未改；guard_health timeout=20 字面量保留并
  登记为共享引用）✓
- 行为等价：常量替换只改字面量为命名引用，数值/逻辑零变化；截断标记为
  P3 消解本意（显示层），阈值/超时/兜底边界均有测试锁定 ✓
- 零删除 ✓；写路径全部在任务卡 allowed_paths 内（.ai/、loop_core/、
  hooks/scripts/loop_enforcement_constants.py、tools/loop_self_audit.py、
  scripts/role_checkers/、tests/）✓
- 版本文件零改动（bump 3.12.47 由主会话执行）✓
- AC-01 grep `timeout=[0-9]`：touched 文件仅 executor.py 两处既有
  timeout=120（显式豁免，非 M 清单/D2-6 项）；常量表仅注释提及 ✓

---

# T-0110 批 B-1 — governance_metrics / intent_router 行为等价拆分（developer 子代理）

日期：2026-08-03（工作树基线：批 A 已合入的同一工作树）

## 落地清单

### 新增文件（7 个 loop_core 模块 + 3 个测试/证据文件）
1. `loop_core/governance_aggregations.py`（367 行，依赖图叶子）
   - 记录数据类 GateMetric/TaskRecord/PhaseTransition/SliContext、相位分类
     GATE_PHASE_TOKENS/classify_gate_phase、时间/统计辅助 _parse_dt/_percentile/
     _seconds_stats、纯度量聚合 12 函数（gate_rejection_rate/gate_decision_coverage/
     approval_latencies(_stats)/task_cycle_seconds(_stats)/phase_dwell_stats/
     rework_cycles_from_gates(_transitions)/guard_anomaly_rates/
     execution_cycle_stats/drift_event_counts）、_over_target、_DECIDED_STATUSES
   - design "保留"清单中的共享基础设施按"叶子先拆"落此（避免壳↔评估循环导入），
     壳 re-export 保持公开面逐名一致
2. `loop_core/governance_loaders.py`（200 行）
   - DataSourceUnavailableError、_load_jsonl、load_gates（since 过滤）/
     load_tasks/load_guard_events（strict-parse fail-closed）/load_phase_transitions/
     load_executions/load_runtime_events
3. `loop_core/slo_evaluator.py`（529 行）
   - 哨兵常量族（NOT_AVAILABLE/BUDGET_*/REPORT_*/SEVERITY_*）、DEFAULT_SLOS、
     DEFAULT_BUDGET_TOTAL_UNITS/DEFAULT_RELEASE_FEE_UNITS、WAVE2_UNWIRED_SOURCES/
     UNWIRED_SLI_IDS、release_fee_consumption（T-0100 F-05 单一共享实现）、
     load_slo_config（T-0095 fail-closed 校验）、evaluate_sli、compute_error_budget、
     _metric/_not_available
4. `loop_core/dora_metrics.py`（215 行）
   - build_dora_metrics（NOT_AVAILABLE/advisory 逐项标注）、_sha256、git_commit
5. `loop_core/intent_keywords.py`（188 行，纯数据零依赖）——D5-4 词表/正则外提
   - DOMAIN_KEYWORDS/LIGHTWEIGHT_KEYWORDS/HIGH_RISK_KEYWORDS/MEDIUM_RISK_KEYWORDS/
     SCALE_INDICATORS/MAX_COMPLEXITY/MIN_COMPLEXITY/变更类型五词表/_NEGATION_PATTERNS
6. `loop_core/intent_detection.py`（313 行）
   - _detect_domains/_extract_risk_factors/_is_negated/_set_if_match/
     _compute_complexity/_build_reasoning（批 A 接线保持：KEYWORD_BOUNDARY_MAX_LEN）
7. `loop_core/intent_split.py`（152 行）
   - split_intents/_INTENT_SPLIT_RE/detect_intent_switch/_other_task_refs/
     _active_task_completion_signal + _MAX_TASK_FRAMES/INTENT_SWITCH_KEYWORDS/
     _TASK_ID_RE/_COMPLETION_VERBS
8. `tests/t0110_b1_golden.py`（819 行，非测试收集）+ `tests/test_t0110_batch_b1.py`
   （275 行，17 passed）+ `.ai/evidence/T-0110/golden/generate_golden.py` +
   `golden-before.json`/`golden-after.json`（各 425,977 B）

### 瘦身壳（re-export，行为不变）
| 文件 | 原行数 | 现行数 | 保留实体 |
|---|---|---|---|
| loop_core/governance_metrics.py | 1508 | 612 | Repair/Loop 指标族、evidence_score_advisory、MetricsReport、build_report、render_markdown + 全量 re-export |
| loop_core/intent_router.py | 1484 | 965 | ChangeType 族、IntentAnalysis、IntentRouter、U5 路由主流程（sticky/多帧/fail-safe）、analyse_intent/route_user_input + 全量 re-export |

### golden 等价证据（硬门槛 1）
同一捕获器拆分前后各跑一次 → `golden-before.json` 与 `golden-after.json`
sha256 均 = `a55433f2…3ffe`，**逐字节一致（425,977 bytes）**。
捕获面：governance_metrics 常量/加载器（含失败路径 9 例）/度量 17 项/SLO 配置
11 例无效/评估 14 条/budget 4 例/DORA/报告 to_dict+markdown；intent_router
词表/检测 7+7 例/analyze 192 例/route_upgrade 11 例/切分 12 例/切换信号 12 例；
两模块 dir() 快照（97+69 名）。

### re-export 完整性断言（硬门槛 2）
- dir() 全量 == 拆分前基线（含私有名）；import * 公开面一致；22 项对象同一性
  （壳绑定即新模块定义对象）；slo_gate.py `_parse_dt` 等私有导入路径不变。
- pyproject.toml 新增 `[tool.ruff.lint.per-file-ignores]`：两壳文件 F401 豁免
  （re-export 设计意图）；其余文件照常。

### 测试与检查
- 新增 17 passed（golden ×2 + re-export ×5 + 循环导入静态防线 ×7 + 抽查 ×2…）
- 直接相关套件 327 passed；消费方套件 631 passed/60 skipped
- 全量回归 1039 passed + 12 xfailed（`-x` 遇 1 既有环境依赖失败：
  test_deployment_quality_checker::test_runtime_report_is_simulated_and_fail_closed，
  **纯净 HEAD 工作树复现**、scripts 零 loop_core 依赖，非本批引入；完整统计见
  fixes/batch-b1-metrics-intent.md）
- compileall PASS；loop_core 77 模块全量导入零循环；ruff 11 文件 All checks passed
- 消费方端到端：tools/loop_metrics.py --report rc=0（报告 PASS）；slo_gate/
  inbox/planner/runtime_controller/tool_route_intent 冒烟通过

### 约束自查（hooks 零改动 / 治理内核零触碰 / 零删除 / 版本文件不改）全过
详见 fixes/batch-b1-metrics-intent.md §六。

# T-0110 批 B-2 — human_review_packet / context_loader 行为等价拆分（developer 子代理）

日期：2026-08-03（基线：HEAD v3.12.46 + 批 A + 批 B-1 + 本批）
验收：golden 快照先行（拆分前捕获 → 拆分后重放 → 逐字节对比），
完整证据见 fixes/batch-b2-review-loader.md

## 拆分边界（按 design-common-weakness.md 1.4 / 1.5）

1. `loop_core/human_review_packet.py`（1307 → 643 行壳）
   - `review_models.py`（236 行，叶子）：PacketType/KeyChoice/RiskItem/
     DecisionRequired/DecisionPoint/ResumeSnapshot/ResumePayload/ResumeContext +
     to/from_dict、to_json/from_json + ResumePayloadError/StateDriftError +
     RESUME_PAYLOAD_* 常量
   - `resume_payload.py`（293 行）：_load_authoritative_yaml/_find_task/_find_gate/
     _TASK_RECOVERY_FIELDS/_GATE_RECOVERY_FIELDS/_task_recovery_record/
     _gate_recovery_record/_pending_tasks/build_resume_payload/resume_from_payload
     （U6 fail-closed 与 StateDrift 语义保持）
   - `review_renderer.py`（237 行，叶子）：render_markdown/render_plain_text/
     _phase_label/_format_ts；壳方法 to_markdown/to_plain_text 改薄委托
     （方法级局部导入，壳命名空间零新绑定）
   - 壳保留：HumanReviewPacket / HumanReviewPacketBuilder 主流程 + 全量 re-export
2. `loop_core/context_loader.py`（1432 → 839 行壳；T-0108 接入后行数）
   - `loader_fields.py`（86 行，叶子）：正则常量族 9 条 + extract_key_fields/
     _format_key_fields
   - `citation_resolver.py`（229 行）：CitationResolution/CitationResolver/
     repair_truncated_references/_find_citation_tokens/_truncate_citation +
     CITATION_MAX_CHARS/UNRESOLVED_MARKER
   - `loader_summary.py`（226 行）：_level_line_params/_level_body_cap/
     _select_body_lines/CITATION_LINE_CAP/_split_sentences/_truncate_line/
     summarize_text/estimate_tokens
   - `loader_sections.py`（184 行，叶子）：_extract_framework_titles/
     _select_relevant_sections + T-0108 F4 路由表逻辑（_ROUTING_CACHE/
     _parse_front_matter_yaml/_load_section_routing，D5-3 接入保持）
   - 壳保留：LoadLevel/LoadedContext/DocumentIndex/CompressionResult/
     ContextCompressor/ContextLoader 全流程（D3 记忆注入默认 False 语义）+
     _parse_yaml/_extract_fixed_stance/_extract_contract_extras + 全量 re-export

依赖 DAG（无环）：review_models ← resume_payload；loader_fields ←
citation_resolver ← loader_summary；loader_sections（叶）；壳 import 全部叶子。

## 新模块清单与壳规模

| 文件 | 行数 | 角色 |
|---|---|---|
| loop_core/review_models.py | 236 | 数据模型/序列化/异常族（叶子） |
| loop_core/resume_payload.py | 293 | U6 resume 载荷 |
| loop_core/review_renderer.py | 237 | 渲染器（叶子） |
| loop_core/loader_fields.py | 86 | 正则族+字段提取（叶子） |
| loop_core/loader_summary.py | 226 | 摘要/行选择 |
| loop_core/citation_resolver.py | 229 | 引用解析 |
| loop_core/loader_sections.py | 184 | 节选择+T-0108 路由表（叶子） |
| loop_core/human_review_packet.py | 643（原 1307） | 瘦身壳 |
| loop_core/context_loader.py | 839（原 1432） | 瘦身壳 |
| tests/t0110_b2_golden.py | 1209 | golden 捕获助手（非测试收集） |
| tests/test_t0110_batch_b2.py | 404 | 验收测试 20 条 |
| .ai/evidence/T-0110/golden/generate_golden_b2.py | 62 | golden 生成器 |
| golden-b2-before/after.json | 各 66,082 B | 拆分前后快照 |

## golden 等价证据（硬门槛 1）

同一捕获器拆分前后各跑一次 → `golden-b2-before.json` 与 `golden-b2-after.json`
sha256 均 = `c372a466f9967c804b0a77312579807031fa35c14cd1d4175b40b3752b017431`，
**逐字节一致（66,082 bytes）**。捕获面：hrp 模型/序列化+失败 15 例/build 成功+
11 fail-closed/resume 成功+9 drift/渲染全文 3 包/builder 三路；cl 正则 9 条/
摘要辅助/summarize 5 例/CitationResolver 10 例/repair 3 例/Compressor 8 例/
load 3 级+3 失败/记忆注入 6 例（含损坏存储 fail-closed）/文档索引/节选择 7 例/
路由缓存；两模块 dir() 快照（43+67 名）。

## re-export 完整性断言（硬门槛 2）

- dir() 全量 == 拆分前基线（含私有名；`__annotations__` 模块属性经
  `DEFAULT_BUDGET_TOKENS: int` 注解赋值保持）；import * 公开面一致；
- 对象同一性 30 项（壳绑定即新模块定义对象；`cl._ROUTING_CACHE is
  loader_sections._ROUTING_CACHE` 同一 dict——test_t0108_fixes `.clear()`
  语义保持）；
- pyproject.toml per-file-ignores 新增两壳 F401（与批 B-1 同模式）。

## include_memories 默认 False 保持（T-0104 硬约束）

kwdefaults 断言（load_role_context/load_for_role 均 False，memory_limit=5）+
行为断言（默认=显式 False 逐字节一致；损坏知识库默认关闭不报错、开启时
fail-closed 抛 KnowledgeStoreError）——golden 与专项测试双覆盖。

## 测试与检查

- 新增验收 tests/test_t0110_batch_b2.py：**20 passed**
- 直接相关套件 13 个：**441 passed**
- 消费方套件 12 个（roles 族/t0104/t0105/t0107/t0109/t0110 批 A/
  context_controller）：**747 passed, 60 skipped**
- 全量回归：**4126 passed + 64 skipped + 12 xfailed + 1 deselected**
  （deselect 为批 B-1 已登记环境项）；2 项失败均为工作树状态型、非本批引入：
  - test_manifest_t0095（HANDOFF 引用的 T-0110 evidence-manifest 于 closeout
    生成，HANDOFF.md 先行修改非本批）
  - test_t0109_f5::test_hooks_only_whitelist_file_changed（断言 hooks diff 恰为
    loop_enforcement.py；T-0110 hooks 零触碰下必然为空，陈旧期望）
- compileall PASS；loop_core 74 模块全量导入零循环；ruff 12 触及文件
  All checks passed（顺带修复原文件遗留 UP045/F541/E702，运行时零差异，
  golden 重跑仍一致）
- 消费方端到端：真实仓库 load_for_role（路由表 7 节）与 builder 生成
  markdown rc=0

### 约束自查（hooks 零改动 / 治理内核零触碰 / 零删除 / 版本文件不改）全过
详见 fixes/batch-b2-review-loader.md §六。

---

# T-0110 批 C — hooks/scripts/loop_enforcement.py 行为等价拆分（developer 子代理，最高风险最后执行）

日期：2026-08-03（工作树基线：批 A/B 已合入的同一工作树；loop_enforcement.py 拆分前 2115 行）

## 落地清单

### 新增文件（3 个 hooks 拆分模块 + 1 个 golden 捕获助手 + 1 个验收测试 + 1 个 golden 生成器）
1. `hooks/scripts/loop_contract_parser.py`（新增 155 行）——任务卡契约解析接线
   （T-0107 D5-2 共享解析器 loop_core/front_matter.py 的 hooks 侧封装）：
   `_SHARED_FRONT_MATTER_PARSER`/`_front_matter_parser`/`_parse_task_front_matter_legacy`/
   `load_task_contract`/`_task_mcp_allowed_tools`/`_read_task_max_files`
2. `hooks/scripts/loop_command_utils.py`（新增 339 行）——命令/路径判定与子进程
   执行辅助（任务卡"subprocess timeout 等，接入批 A 常量"）：
   `_PYTHON_INTERPRETER_RE`/`_SIDE_EFFECT_CAPABLE`/`_is_python_interpreter`/
   `_msys_to_windows`/`_script_in_governance_dirs`/`_split_command_segments`/
   `_is_governance_tool_segment`/`_is_safe_cd_segment`/`_is_safe_display_segment`/
   `is_in_task_scope`/`check_diff_scope`（git diff timeout 接线
   COMMAND_TIMEOUT_SECONDS，max_diff_files 接线 MAX_DIFF_FILES）/
   `_command_references_outside`
3. `hooks/scripts/gate_evidence_checks.py`（新增 709 行）——gate 证据检查
   （T-0056/T-0067 相关证据校验外提）：`check_quality_gate_evidence`/
   `_self_review_block_enabled`/`trace_review_evidence_isolation`（T-0067
   verify_review_evidence 接线）/`check_delivery_gate_evidence`/
   `check_runtime_quality_gate`/`_import_loop_core_gate`/`check_slo_gate_evidence`/
   `check_second_failure_gate_evidence`/`_PHASE_EVIDENCE_FILES`/
   `_check_phase_evidence_file`/`check_security_gate_evidence`/
   `check_phase_gate_enforcement`
4. `tests/t0110_c_golden.py`（新增，golden 捕获助手）——hook 入口判定矩阵
   48 场景（子进程实跑）+ 关键函数直调 204 项 + dir/公开面快照
5. `tests/test_t0110_batch_c.py`（新增，14 项验收）——golden 逐字节等价 /
   re-export 完整性 / 自愈 re-exec 实测（AC-03）/ 循环导入防线 / AC-01 零散落
6. `.ai/evidence/T-0110/golden/generate_golden_c.py` + `golden-c-before.json`
   （49858 B）+ `golden-c-after.json`（49858 B）——拆分前后 golden 快照

### 接线既有文件（行为等价）
- `hooks/scripts/loop_enforcement_constants.py`（批 A 已建）——EXIT_PASS/EXIT_BLOCK
  （M-1）、REEXEC_MAX→_REEXEC_MAX、GOVERNANCE_EXEMPT/MINIMAL_METADATA_READ/
  MAIN_THREAD_ALLOWED 改引常量表（唯一来源）；**GOVERNANCE_TOOL_DIRS 保留壳内
  tuple 字面量双登记**（T-0109 AC-05 门禁要求源文件 AST 字面量，一致性测试锁定）
- `hooks/scripts/loop_enforcement.py`（2115 → 1052 行壳）——自愈 SHA+重执行机制
  与 main() fail-closed 裁决链逐字保留；扫描集扩展 4 个拆分模块（机制语义零变化）；
  全量 re-export（dir() 104 名与拆分前逐名一致，含私有名）
- `tests/test_hook_integration.py`——隔离运行夹具复制集加入 4 个拆分模块
  （`_copy_hook_set`，夹具语义不变：仍验证 loop_core 缺失降级）
- `pyproject.toml`——per-file-ignores 登记壳 F401（批 B 同模式）

## golden 等价证据（硬门槛 1/2）

- 捕获器：`tests/t0110_c_golden.py`（48 场景矩阵子进程实跑 + 204 直调 + dir 快照），
  归一化规则：fixture 根路径（含 root.parent 形态）→ `<ROOT>`、ISO 时间戳 →
  `<TS>`、hook 自家 logger 名前缀 → `[HOOK_LOGGER]`（消息文本不变，随模块迁移
  的仅前缀）、`\` → `/`；运行两次自证确定性（byte-identical）
- **拆分前后逐字节一致**：
  `golden-c-before.json sha256 = 47e105ce5d23bbf3eaa56e130f13ba64134fa68f2653e64dc4c457e87270ca61`
  `golden-c-after.json  sha256 = 47e105ce5d23bbf3eaa56e130f13ba64134fa68f2653e64dc4c457e87270ca61`
  （after 在 lint 修复后再跑一次仍 byte-identical）
- re-export：dir() 104/104 零缺失零新增；import * 公开面 55 名一致；
  对象同一性 12 项（壳绑定 is 新模块定义对象）；常量接线 identity 一致

## 自愈 re-exec 实测（AC-03）

缓存旧代码 + 本地新代码（常量表 GOVERNANCE_EXEMPT 追加 extra/）场景：
- call-1（写 extra/x.txt）：**re-exec 恰好 1 次**，rc=0（新代码判定；旧代码
  本应 SETUP_INCOMPLETE rc=2）——"本次仍按旧代码拦截"竞态消除
- call-2（写 docs/y.txt）：文件无变化 → 0 次 re-exec，rc=2（范围外 fail-closed）
- call-3（写 extra/z.txt）：新代码已加载 → 0 次 re-exec，rc=0
- 同步后缓存 == 本地（extra/ 已入缓存常量表）；无修改对照场景 rc=2 且 0 次 re-exec
- 已固化为 tests/test_t0110_batch_c.py::TestSelfHealReexec（2 项）

## 测试与检查

- hook 全套件（拆分前基线 → 拆分后）：**1229 passed + 60 skipped + 1 预存失败
  → 1273 passed + 60 skipped + 0 failed**（+44 = 批 C 14 项 + import_checker 等；
  T-0109 AC-08 陈旧期望测试因本批恰改 loop_enforcement.py 一处而恢复绿色）
- 全量回归 tests/：见 fixes/batch-c-enforcement.md §五（AC-04 记录）
- compileall 触及文件 0 错误；ruff 我的 6 个文件 All checks passed
  （test_hook_integration.py 余 4 项 N806 为 git HEAD 预存，未触碰）
- 循环导入：4 拆分模块零反向引用壳（静态断言 + 独立导入通过）

## 约束自查

| 约束 | 状态 |
|------|------|
| hooks/ 仅批 C 5 文件（壳 + 4 模块） | ✓ 其余 hook 文件零改动（git diff 实证） |
| 治理内核判定零触碰 | ✓ 壳/模块均未改判定语义；golden 逐字节实证 |
| 不改变任何行为 | ✓ golden byte-identical；自愈 re-exec 一次且判定一致 |
| 零删除 | ✓ dir() 104/104 全量保留（含私有名） |
| 写路径仅限 hooks/scripts 指定文件 + tests/ + .ai/evidence/T-0110/ + pyproject.toml | ✓ |
| 版本文件不改 | ✓ |

详见 fixes/batch-c-enforcement.md。

## T-0116 P3 措辞修正记录

- **P3-1（golden 场景数）**：51→48 已修正（本文件 + fixes/batch-c-enforcement.md）；
  `tests/t0110_c_golden.py` 文档串不在本任务 allowed_paths（tests/ 零改动），
  行为等价结论不受影响（before/after 同源同捕获器逐字节一致）。
- **P3-2（test_t0108_fixes 登记）**：批 C 期间 2 项 test_t0108_fixes 失败为
  continuity 漂移（.ai/ 写路径后未 repair）所致，`validate_state --repair`
  后通过；登记于本小节，非任务缺陷。
- **P3-3（.bak 口径）**：`hooks/scripts/loop_enforcement.py.bak` 为前序遗留的
  已跟踪文件（非本任务引入），任务卡"15 个 hook 文件"口径不含它（实 16 个
  零改动）；拆分后壳文件与 .bak 共存属历史状态，留待清理评估。
- **P3-4（guard-events）**：`.ai/evidence/observability/guard-events.jsonl`
  +307 行为运行事件追加（既有行为，轮转机制 10k 行生效），非本任务写入。
