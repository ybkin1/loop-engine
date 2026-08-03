# T-0110 批 B-1 — governance_metrics / intent_router 行为等价拆分验收

日期：2026-08-03
执行：developer 子代理（批 B-1）
基线：工作树 = HEAD v3.12.46 + 批 A（constants.py 已接线 intent_router）+ 本批
验收方法：**golden 快照先行**（拆分前捕获 → 拆分后重放 → 逐字节对比）

---

## 一、拆分边界表（按 design-common-weakness.md 1.2 / 1.3）

### 1.1 loop_core/governance_metrics.py（1508 → 612 行壳）

| 外提内容 | 原位置 | 目标新模块 | 实现 |
|---|---|---|---|
| 数据加载器（`_load_jsonl`/`load_gates`/`load_tasks`/`load_guard_events`/`load_phase_transitions`/`load_executions`/`load_runtime_events`）+ 同节 `DataSourceUnavailableError` | :215-370（含 :216-218） | `governance_loaders.py`（200 行） | 逐字迁移 |
| 统计聚合辅助（`_percentile`/`_seconds_stats`/`_over_target`）**及共享基础设施**（记录数据类 GateMetric/TaskRecord/PhaseTransition/SliContext、相位分类 GATE_PHASE_TOKENS/classify_gate_phase、时间辅助 _parse_dt、纯度量函数 gate_rejection_rate/gate_decision_coverage/approval_latencies(_stats)/task_cycle_seconds(_stats)/phase_dwell_stats/rework_cycles_from_gates(_transitions)/guard_anomaly_rates/execution_cycle_stats/drift_event_counts、_DECIDED_STATUSES） | :97-159, :161-213, :381-560, :808 | `governance_aggregations.py`（367 行，**依赖图叶子**） | 逐字迁移 |
| SLI/SLO 评估（`load_slo_config`/`evaluate_sli`/`compute_error_budget`/`_metric`/`_not_available`）+ SLO 域常量（哨兵 NOT_AVAILABLE/BUDGET_*/REPORT_*/SEVERITY_*、DEFAULT_SLOS、DEFAULT_BUDGET_TOTAL_UNITS、DEFAULT_RELEASE_FEE_UNITS、WAVE2_UNWIRED_SOURCES、UNWIRED_SLI_IDS、release_fee_consumption） | :64-79, :563-654, :657-1043 | `slo_evaluator.py`（529 行） | 逐字迁移 |
| DORA 指标构建（`build_dora_metrics`/`_sha256`/`git_commit`） | :1012-1183 | `dora_metrics.py`（215 行） | 逐字迁移 |
| **保留在壳**：`_TASK_COMPLETED_STATUS`、Repair Progress 族（repair_trigger_count/fixed_gate_count/build_repair_progress）、Loop Effectiveness（build_loop_effectiveness）、evidence_score_advisory、REPORT_SOURCE_FILES、MetricsReport、_data_window、build_report、_fmt、render_markdown | :1206-1692 | `governance_metrics.py`（612 行壳） | 保留 + 全量 re-export |

**设计说明（保留项物理位置）**：design 表格"保留"清单中的记录数据类/度量函数等
与聚合/评估模块存在强依赖（evaluate_sli 用 guard_anomaly_rates，build_dora_metrics
用十余个度量函数），物理保留在壳将产生循环导入（壳→评估→壳）。按 design 自身的
循环导入缓解（"叶子先拆：聚合/评估后建"），共享基础设施物理落在叶子
`governance_aggregations.py`，壳 **re-export 保持公开面逐名一致**（含私有名，
见 §三 re-export 断言）——`from loop_core.governance_metrics import *` 与全部
直接导入路径（含 slo_gate.py 的 `_parse_dt` 私有导入）行为不变。

依赖 DAG（无环）：`aggregations` ← `loaders` ← `slo_evaluator` ← `dora_metrics`；
壳 import 全部四个叶子。静态断言见 tests/test_t0110_batch_b1.py
`test_metrics_leaves_do_not_import_shell` / `test_dependency_dag_order`。

### 1.2 loop_core/intent_router.py（1484 → 965 行壳）

| 外提内容 | 原位置 | 目标新模块 | 实现 |
|---|---|---|---|
| 关键词常量表（`DOMAIN_KEYWORDS`/`LIGHTWEIGHT_KEYWORDS`/`HIGH_RISK_KEYWORDS`/`MEDIUM_RISK_KEYWORDS`/`SCALE_INDICATORS`/`MAX_COMPLEXITY`/`MIN_COMPLEXITY`/变更类型词表五张/`_NEGATION_PATTERNS`）——D5-4 词表/正则外提 | :35-161, :202-228, :769-775 | `intent_keywords.py`（188 行，纯数据零依赖） | 逐字迁移 |
| 检测/评分辅助（`_detect_domains`/`_extract_risk_factors`/`_is_negated`/`_set_if_match`/`_compute_complexity`/`_build_reasoning`） | :626-872 | `intent_detection.py`（313 行） | 逐字迁移 |
| 意图切分/切换辅助（`split_intents`/`_INTENT_SPLIT_RE`/`detect_intent_switch`/`_other_task_refs`/`_active_task_completion_signal` + 专属常量 `_MAX_TASK_FRAMES`/`INTENT_SWITCH_KEYWORDS`/`_TASK_ID_RE`/`_COMPLETION_VERBS`） | :991-1013, :1127-1246 | `intent_split.py`（152 行） | 逐字迁移 |
| **保留在壳**：ChangeType/CHANGE_TYPE_TO_ENTRY_PHASE/CHANGE_TYPE_MIN_PHASES/_detect_change_type、IntentAnalysis、IntentRouter（analyze/route/route_upgrade/should_escalate/置信度）、_phases_for_mode/_analysis_to_profile、ActiveTaskSnapshot/TaskFrame/RoutedIntent/_status_quo_route_result/_degraded_result/_route_internal、IntentBrief/analyse_intent/route_user_input | :169-313, :314-624, :926-963, :1016-1484 | `intent_router.py`（965 行壳） | 保留 + 全量 re-export |

依赖 DAG（无环）：`intent_keywords`（叶子）← `intent_detection`；`intent_split`
（叶子）；壳 import 三个叶子。批 A 接线保持：intent_detection 从
`loop_core.constants` 导入 `KEYWORD_BOUNDARY_MAX_LEN`（D2-4），壳保留
`CONFIDENCE_CONFLICT_*`（D2-3）用法。静态断言见
`test_intent_leaves_do_not_import_shell`。

## 二、新模块清单与壳规模

| 文件 | 角色 | 行数 |
|---|---|---|
| loop_core/governance_aggregations.py | 新增（叶子：记录/分类/统计/纯度量） | 367 |
| loop_core/governance_loaders.py | 新增（数据加载 + DataSourceUnavailableError） | 200 |
| loop_core/slo_evaluator.py | 新增（SLI/SLO/预算 + 常量族） | 529 |
| loop_core/dora_metrics.py | 新增（DORA 构建 + _sha256/git_commit） | 215 |
| loop_core/governance_metrics.py | 瘦身壳（1508 → 612，re-export + 报告主流程） | 612 |
| loop_core/intent_keywords.py | 新增（D5-4 词表/正则，纯数据） | 188 |
| loop_core/intent_detection.py | 新增（检测/评分辅助） | 313 |
| loop_core/intent_split.py | 新增（切分/切换辅助） | 152 |
| loop_core/intent_router.py | 瘦身壳（1484 → 965，re-export + 路由主流程） | 965 |
| tests/t0110_b1_golden.py | 新增（golden 语料共享助手，非测试收集） | 819 |
| tests/test_t0110_batch_b1.py | 新增（验收测试 17 条） | 275 |
| .ai/evidence/T-0110/golden/generate_golden.py | 新增（golden 生成器） | 58 |
| .ai/evidence/T-0110/golden/golden-before.json | 新增（拆分前基线快照） | 425,977 B |
| .ai/evidence/T-0110/golden/golden-after.json | 新增（拆分后重放快照） | 425,977 B |

## 三、golden 等价证据（硬门槛 1）

**对比方法**：同一确定性捕获器（tests/t0110_b1_golden.py）在拆分前后各运行一次，
产物为 sort_keys JSON 文本；`sha256` 逐字节对比。

- 捕获范围（governance_metrics）：模块常量值快照、classify_gate_phase/_parse_dt/
  _percentile/_seconds_stats/_over_target 边界、全部加载器（含 since 过滤）、
  加载器失败路径 9 例（缺失/损坏行/未知 result/缺 key/无 gates 列表，fail-closed
  异常类型+message）、纯度量函数 17 项（含空输入）、load_slo_config 缺省/覆盖/
  无效配置 11 例（T-0095 fail-closed）、evaluate_sli × 默认表 14 条、
  compute_error_budget 4 例、release_fee_consumption 3 例、build_dora_metrics、
  build_repair_progress/build_loop_effectiveness/evidence_score_advisory、
  build_report 显式窗口 + 数据窗口（to_dict 全量，generated_at/git_commit 归一化）、
  render_markdown 全文。
- 捕获范围（intent_router）：全部词表/常量/正则 pattern、_detect_change_type 7 例、
  _detect_domains 7 例、_extract_risk_factors 7 例、_is_negated/_set_if_match、
  _compute_complexity 5 例、_build_reasoning、analyze × 48 条语料 × 4 上下文
  = 192 例（含自定义阈值路由实例）、should_escalate 6 例、route 3 例、
  _phases_for_mode/_analysis_to_profile、split_intents 12 例（含 max_frames 截断、
  非法输入、时态引用不切分）、detect_intent_switch 6 例、_other_task_refs/
  _active_task_completion_signal 6 例、route_user_input 11 例（sticky/switch/
  completion/other-task-ref/degraded/多帧/from_task 变体）、analyse_intent 3 例。
- 两模块 dir() 全量快照（97 + 69 名）同步入基线。

**结果**：
```
golden-before.json sha256 = a55433f2504031e079ca7fb154cf83fb9e2c75421ea85cd7ae13025e3ccc3ffe
golden-after.json  sha256 = a55433f2504031e079ca7fb154cf83fb9e2c75421ea85cd7ae13025e3ccc3ffe
byte-identical: True（425,977 bytes）
```
（golden-after 在 governance_metrics 拆分后与 intent_router 拆分后各跑一次，
两次均 byte-identical；UP037 引号注解修复后第三次重跑仍一致。）

## 四、re-export 完整性断言（硬门槛 2）

- `sorted(dir(壳)) == 拆分前 dir 基线`（governance_metrics 97 名 / intent_router
  69 名，含私有名——覆盖 `import *` 公开面与 slo_gate.py `_parse_dt` 等直接私有导入）；
- `from loop_core.governance_metrics import *` / `from loop_core.intent_router import *`
  可执行且公开名集合与 dir() 非下划线名一致；
- 对象同一性：壳绑定即新模块定义对象（`gm.GateMetric is agg.GateMetric`、
  `gm.load_gates is ld.load_gates`、`ir._detect_domains is det._detect_domains`、
  `ir.split_intents is sp.split_intents` 等 22 项，非拷贝）；
- 原文件 import 面逐名保留：`hashlib/json/math/statistics/subprocess/Counter/
  Sequence/timedelta/yaml/GuardCheckEvent` 等以 `# noqa: F401` 保留绑定
  （命名空间保持），壳文件在 pyproject.toml `per-file-ignores` 登记 F401
  （re-export 是设计意图；其余文件 F401 照常生效）。

## 五、测试结果

- 新增验收 tests/test_t0110_batch_b1.py：**17 passed**（golden 两文件逐字节等价 ×2、
  re-export 面 ×2、对象同一性 ×2、star import ×1、循环导入静态防线 ×7、
  内嵌抽查 ×2）。
- 直接相关套件：test_governance_metrics / test_intent_router /
  test_intent_router_upgrade / test_slo_gate / test_slo_consistency /
  test_t0107_fixes / test_t0109_f1_eval_model / test_t0110_batch_a /
  test_t0110_batch_b1 → **327 passed**。
- 消费方套件：planner / inbox / dashboard / status_dashboard / runtime_controller /
  management_roles / remaining_roles / technical_roles / quality_engineer_role /
  role_capability / role_isolation → **631 passed, 60 skipped**。
- 全量回归 tests/：**1039 passed + 12 xfailed**（`-x` 模式先遇
  test_deployment_quality_checker::test_runtime_report_is_simulated_and_fail_closed
  失败）。该失败**在纯净 HEAD 工作树同样复现**（scripts/runtime_delivery_gate 与
  deployment_quality_checker 均零 loop_core 依赖；环境相关既有项，T-0108 closeout
  已登记"1 已登记环境依赖项"）——非本批引入。全量（deselect 该项）统计见最终命令记录。
- 编译：`python -m compileall loop_core/` PASS；全量导入 loop_core 77 个模块
  零循环导入/零导入错误。
- lint：`ruff check` 11 个触及文件 All checks passed（新文件零违规；壳文件按
  per-file-ignores 豁免 F401；另修复原文件遗留 UP037 引号注解——`from __future__
  import annotations` 下注解恒为字符串，运行时零差异）。
- 消费方端到端：`tools/loop_metrics.py --report`（真实仓库根）rc=0，报告
  PASS；`tools/tool_route_intent`、`loop_core.slo_gate`（含 `_parse_dt` 私有
  导入）、`.ai/checkers/slo_gate_checker.py`（load_slo_config 路径）冒烟通过。

## 六、约束自查（任务卡硬约束）

| 约束 | 自查 |
|---|---|
| hooks/ 零改动 | ✅ 本批未触碰 hooks/ 任何文件 |
| 治理内核判定零触碰（gate_guard/enforcement 判定/hard_constraints/guard_health/state_machine） | ✅ 未触碰；golden 判定语义逐字节一致 |
| 不改变任何行为 | ✅ golden 逐字节等价（sha256 相同）；数值/逻辑/输出格式零变化；UP037 为运行时零差异的注解去引号 |
| 零删除 | ✅ 全部公开+私有符号 re-export；无任何符号消失 |
| 写路径仅限 loop_core/ + tests/ + .ai/evidence/T-0110/ + pyproject.toml | ✅ 新增 7 模块 + 2 测试文件 + golden 3 文件；pyproject.toml 仅加 per-file-ignores 段（allowed_paths 内） |
| 版本文件不改 | ✅ 未触碰 |
| 批 A 接线保持 | ✅ constants.KEYWORD_BOUNDARY_MAX_LEN 由 intent_detection 继续消费；CONFIDENCE_CONFLICT_* 壳内继续使用 |

## 七、遗留事项（批 B-2/C 依赖）

1. 批 B-2/B-3/B-4 沿用本批的壳+re-export 模式与 per-file-ignores 登记
   （human_review_packet / context_loader / review 拆分时，若保留项与
   外提项有强依赖，同样按"叶子先拆"处理并文档化）。
2. golden 基线（golden-before.json）已入库；后续批沿用
   `generate_golden.py` 生成器模式时建议复用 tests/t0110_b1_golden.py 的
   to_jsonable/norm_paths/try_exc 工具。
3. 全量回归中的既有环境依赖失败项（test_deployment_quality_checker::…）
   非本批引入（HEAD 复现），留给主会话登记/处置。
4. 批 C（hooks/scripts/loop_enforcement.py 2059 行）拆分时，本批的
   `loop_enforcement_constants.py`（批 A）已就绪；需按 design 1.1 的
   "不拆主流程语义"清单执行，自愈路径实测另行记录。
