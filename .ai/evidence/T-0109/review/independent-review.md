# T-0109 独立审查报告（BH 融合·分层期：F2-2 / F3 / F1 / F5）

- 审查者：independent-reviewer 子代理（fresh context，未参与实施）
- 日期：2026-08-03
- 基线：1f02409 v3.12.45 → 当前工作区
- 方法：全部结论独立复验（git diff 逐行 / 数据脚本复算 / HEAD worktree 对照 / 独立重跑全量回归），不复述 developer 证据
- 审查对象：`.ai/tasks/T-0109.md`（8 AC + 硬约束）、design-bh-integration.md（F1/F2/F3/F5）、`.ai/evidence/T-0109/`（commands/fixes/design）、实际 diff

---

## 一、裁决

**CONDITIONAL_GO**（条件：修复 1 项 P1 后重跑全量回归至 0 failed，详见五-1）

四线判定：**F2-2 PASS / F3 PASS / F1 PASS / F5 PASS**；约束零弱化专项 **PASS（hooks 单文件注释级 + 内核零触碰 + validate_state 零改动 + 零删除）**；
发现清单：**P1×1（新增测试失败，AC-06 未达）、P3×2（测试耦合/理由差异）**；无 P0/P2。

---

## 二、改动范围核对 + 约束零弱化专项

### 2.1 全量改动文件（git diff --name-only + untracked）

**修改（27）**：.ai/HANDOFF.md、.ai/evidence/observability/guard-events.jsonl（hook 观测事件，全 PASS）、.ai/gates.yaml、.ai/project_continuity.yaml、.ai/slo.yaml、.ai/state.yaml、.ai/task_graph.yaml、.ai/tasks/T-0108.md（Status → completed）、.ai/version-manifest.yaml、.zcode-plugin/plugin.json、.zcode/tools/governor_lib.py、CHANGELOG.md、README.md、docs/06-delivery.md、hooks/scripts/loop_enforcement.py、loop_core/__init__.py、loop_core/capability_registry.py、loop_core/dashboard_views.py、loop_core/evidence_chain.py、loop_core/gate_feedback.py、loop_core/governance_metrics.py、loop_core/schemas/gate.schema.json、loop_core/state_machine.py、loop_core/status_dashboard.py、pyproject.toml、src/loop_engine/__init__.py、tools/server.py
**新增（7）**：.ai/archive/gates-archive.yaml、.ai/policies/forbidden-actions.yaml、.ai/tasks/T-0109.md、.ai/evidence/T-0109/、loop_core/schemas/evidence_state.py、tests/test_t0109_{f1,f2,f3,f5}*.py（4 文件）

allowed_paths 对照：全部代码改动落在 allowed_paths 内。任务卡允许路径之外的改动为**纯版本同步**（README/docs/06-delivery/plugin.json/loop_core.__init__/src/loop_engine.__init__ 均为 3.12.45→3.12.46 单行；version-manifest 全量 3.12.46；CHANGELOG 新增 v3.12.46 条目；pyproject 3.12.46——AC-07 所需，bump 由主会话执行，developer 记录与实证一致）。project_continuity.yaml 为 repair_continuity 再生成（gates.yaml 新哈希入 manifest，drift 已修复——见四）。

### 2.2 hooks/ 专项（最高优先）

- `git diff -- hooks/` = **仅 hooks/scripts/loop_enforcement.py 一个文件**（git status porcelain 实证：仅 ` M hooks/scripts/loop_enforcement.py`；预存在跟踪文件 loop_enforcement.py.bak 未被改动）。
- diff 逐行核对：**+6/-2 行，全部为 GOVERNANCE_TOOL_DIRS 块内注释行**；6 个目录常量值（`.zcode/tools/`、`.ai/checkers/`、`.ai/guards/`、`scripts/`、`hooks/`、`tools/`）逐项原样；判定逻辑（`_script_in_governance_dirs` 等）零触碰。与任务卡「仅白名单常量表注释同步」完全一致。

### 2.3 治理内核零触碰

- gate_guard（hooks/scripts/gate_guard.py）、loop_core/enforcement.py、enforcement_hub.py、hard_constraints.py、guard_health.py：**diff = 0 行**（均不在 diff 名单）。
- state_machine.py：diff 仅 3 处——docstring 增补、`atomic_write_state` 在 `os.replace` 之后新增一行 `_refresh_state_view_after_transition(root_p)`、新增该 helper 函数（try/except + warnings.warn，失败不回滚权威写）。**判定逻辑零改动**（逐 diff 核对：约束检查、can_approve_gate、check_phase_constraints 等函数体无任何变化）。
- validate_state.py：`git diff -- .zcode/tools/validate_state.py` = **0 行**（F2-2 声明实证成立；F2-1 check_state_view_freshness 即双写检测器）。
- fail-closed 语义不变：write_state_files 非 state 路径 → `SCOPE_VIOLATION`（代码实证）；schema 校验失败即测试失败；视图刷新失败显式告警不回滚；证据链不可读节点显式 BLOCKED。

### 2.4 零删除

- `git status --porcelain` 无任何 D 条目；tools/ 仍为 36 个模块（与注册表一一对应）；6 薄壳 + 4 弱引用 + 3 legacy 文件全部保留。tool-removal-candidates.md 仅为证据清单（A 组 6 薄壳 0 代码 importers 独立 grep 实证：仅 capability_registry 元数据、tests/deep_probe_v35.py 字符串清单、docstring 注释、测试自身引用；server.py 不再 import）。

---

## 三、四线逐线真实性（独立复验）

### 3.1 F2-2 写入收敛 — PASS（13 测试独立重跑全绿）

| 项 | 独立复验 |
|---|---|
| write_state_files 收敛入口 | governor_lib.py diff 为纯追加（+94 行）：`write_state_files` 内部调既有 `transactional_write_texts`；路径必须 resolve 于 `.ai/` 且属 STATE_RELATED_FILES（state.yaml/task_graph.yaml/HANDOFF.md/PROGRESS.md/tasks/*）否则 GovernanceError SCOPE_VIOLATION；写后默认 `refresh_state_view`（复用 projection_engine.write_state_view，失败 logging.warning + 返回 False） |
| state_machine 仅加刷新调用 | diff 实证（见 2.3），判定零改动 |
| validate_state 零改动 | diff = 0 行；实仓运行 validate_state → `[ok] state is usable` 无 stale 告警（双写告警清零实证） |
| 静态检查真实性 | test_t0109_f2_write_convergence.py 为仓库级 AST/正则扫描：写候选须登记 SANCTIONED/LEGACY/MANIFEST_REPAIR/NON_STATE 四类互斥白名单；loop_core state.yaml 写路径集合 == 登记名单（state_machine 唯一权威入口）——真实断言，非摆设 |

### 3.2 F3 gates 分层 — PASS（18 测试独立重跑全绿）

| 项 | 独立复验（脚本对 git HEAD 原文件复算） |
|---|---|
| 66 active + 36 archive | 实证：active=66、archive=36、union=102 唯一；**union == HEAD 原 101 条 + 唯一新增 G-T-0109-REQUIREMENTS**（当前任务 gate，approved）；无删、无重、互斥 |
| 归档逐字段 verbatim | archive 36 条 vs HEAD 原记录：**字段级 diff = 0**（含 G-T-0055-BASELINE-AUDIT 缺 recorded_at 的历史原样保留） |
| active 域等价 | active 66 条非 forbidden 字段 vs HEAD：**0 diff**；forbidden_actions→forbidden_policy 外提 26 条 + 内联 40 条，**policy 展开 == 原列表 0 mismatch**；7 个 policy id 全部可解析 |
| gate_type 枚举化 | schema enum 30 值覆盖 active+archive 全部 29 个取值（0 未入枚举）；forbidden_policy 属性存在；approval_source 5 值（补 3 个历史值） |
| 消费方读取路径 | 全仓 grep：gate_guard/_hook_state/hook_common/loop_enforcement/session_brief/role_isolation/loop_auto_activate/enforcement_hub/approval_ledger 全部只读 `.ai/gates.yaml`（active 域）；state.current_gate_id=G-T-0109-REQUIREMENTS 在 active 域恰一条且 approved；无任何生产代码引用 archive/policies 文件（仅测试） |
| 内核等价测试真实性 | 测试中 gate_matches_phase_heuristic 与 enforcement_hub._has_approved_user_gate 实现（loop_core/enforcement_hub.py:247-300，enforcement_hub 本身 0 改动）语义逐行一致；check_phase_constraints 前缀匹配为 state_machine.py 既有函数（未改动） |

### 3.3 F1 评估模型 — PASS（29 测试独立重跑全绿）

| 项 | 独立复验 |
|---|---|
| 七态枚举 | evidence_state.py：Present/Wired/Exercised/Outcome-supported/Missing/Unobserved/N-A；coerce 大小写/连字符/空值规整、未知值 ValueError（fail-closed）；模块无任何 gate 判定函数 |
| 评分上限表 | DEFAULT_SCORE_CAPS = {Missing/Unobserved/N-A:59, Present:74, Wired:84, Exercised:94, Outcome-supported:100}；SCORE_BANDS=(59,74,84,94,100)；apply_score_cap=min(round(raw),cap)；边界测试 parametrize 5 档实证存在 |
| slo.yaml score_caps | 显式化节与代码默认一致；governance_metrics.load_slo_config 校验 fail-closed（非 mapping/非法状态/负数 → DataSourceUnavailableError） |
| Repair/Loop 分离 | build_repair_progress（triggers=rejected、fixed=同任务先 rejected 后 approved）/ build_loop_effectiveness（pass_rate/cycle time/rework 同源）；MetricsReport 三新字段 + render_markdown 新节 |
| **advisory-only 静态断言** | 独立 grep 7 个判定模块（state_machine/gate_guard/enforcement/hard_constraints/guard_health/slo_gate/approval_ledger）+ hooks/ 全仓 + validate_state/audit_handoff：**0 个评分符号**；符号仅存在于 gate_feedback.py（字段，advisory）与 governance_metrics.py（advisory 度量）；测试为真实 AST 扫描 + 函数级断言 |
| GateLesson 兼容 | evidence_state 缺省 N-A；from_dict 缺字段 → N-A（schema_version 保持 1）；非法值 InvalidLessonError |

### 3.4 F5 工具 capability 化 — PASS（25 测试独立重跑全绿）

| 项 | 独立复验 |
|---|---|
| 注册表 36/36 | tools/*.py = 36 文件，TOOL_CAPABILITY_MANIFEST = 36 项，一一对应（name 集合逐项相等）；audience 三档互斥覆盖；未知工具 LookupError；build_tool_registry sealed |
| 6 薄壳消除行为等价 | server.py 新增 `_run_quality_gates/_run_security_scan/_run_dependency_analysis/_run_contract_validate/_run_cost_report` 与 HEAD 原薄壳 run() **逐字节等价**（逐函数对照实证：命令/超时/回退分支一致；plugin_root == PROJECT_ROOT）；evidence_verify/freeze 直调 loop_core.evidence_chain；`_dispatch` 不再 import 6 薄壳（grep 实证）；顺带移除 contract_validate 死重复 return |
| dashboard 四层合并 | status_dashboard.py 降级 re-export shim；dashboard_views.py 新增 ProjectStatus/Dashboard 与 HEAD 原 status_dashboard 实现 **AST 规范化后字节一致**（仅 import 别名差异，函数体 0 diff） |
| 证据链三处收敛 | verify_chain_yaml/freeze_file_yaml 与 scripts/evidence_chain.py 实现逐行对照一致（含候选路径顺序、strict 语义、输出结构；另加 OSError 防御 → 不可读节点显式 BLOCKED，fail-closed 增强） |
| 缓存三处不合并理由 | 勘察成立：context_packager 进程内 git diff 缓存 / role_orchestrator mtime 缓存 / hooks auto_sync_to_plugin_cache 三类不同机制，无 tools/ 内重复实现——不合并合理，记录在案 |
| 白名单一致性（AC-05） | 测试 AST 提取 GOVERNANCE_TOOL_DIRS：36 工具路径全部落白名单目录；6 目录稳定；`git diff HEAD --name-only -- hooks/` 断言 == 仅 loop_enforcement.py（AC-08 实证） |

---

## 四、测试真实性 + 全量回归独立结果

- 4 个新测试文件全部为真实断言（非空转）：F2 仓库级静态扫描、F3 对 HEAD 原文件等价复算（独立脚本同结果）、F1 AST 扫描 + 分档边界、F5 注入式等价 + git 断言。
- 新增测试独立重跑：**85 passed**（13+18+29+25）。
- 全量回归独立重跑（`pytest tests/ -q`，3 分 23 秒）：**4042 passed / 5 failed / 64 skipped / 12 xfailed**。
  1. test_code_quality::test_loop_core_has_no_host_leaks — **新增失败（P1）**，详见五-1。
  2. test_deployment_quality_checker::test_runtime_report_is_simulated_and_fail_closed — **预登记环境依赖**（KNOWN_ISSUES：localhost:3000/8000 占用；HEAD worktree 独立重跑同样 FAIL，非本任务引入）。
  3. test_manifest_t0095::test_manifest_exists_and_handoff_reference_is_real — **closeout 瞬态**（HANDOFF 引用 .ai/evidence/T-0109/evidence-manifest.v1.yaml，closeout 时产出；T-0108 同款先例）。
  4. test_release::test_pyproject_version_matches_git_head — **提交前瞬态**（工作区 3.12.46 vs HEAD 3.12.45，AC-07 提交后自愈；6 个版本载体已全量 3.12.46）。
  5. test_t0108_fixes::test_existing_verdicts_unchanged_on_repo — **P3**（详见五-3）。
- compileall 独立通过（governor_lib/state_machine/gate_feedback/governance_metrics/capability_registry/dashboard_views/status_dashboard/evidence_chain/evidence_state/server/loop_enforcement）；validate_state 实仓运行 `[ok] state is usable`（F3 continuity drift 已由主会话 repair 修复）。

---

## 五、发现清单

### P1（1 项，修复后放行）

1. **test_loop_core_has_no_host_leaks 新增失败（DR-002 host leak）**
   - 现象：全量回归新增失败项；`review_design` 对 loop_core 报 error 级 DR-002：`loop_core/evidence_chain.py:480` 含宿主特定路径字面量 `.zcode/skills/loop-governance/chain.yaml`（CHAIN_YAML_CANDIDATES，F5 证据链收敛引入）。
   - 基线对照：HEAD worktree 独立重跑该测试 **PASS** ⇒ 确认由 T-0109 引入，非预存。
   - 影响：违反 loop_core 宿主无关原则（模块 docstring 明示 "does NOT depend on any specific host"）+ AC-06「全量回归 0 failed」未达。无行为/安全影响（路径仅为候选查找表，且与既有 scripts/evidence_chain.py 语义一致）。
   - 建议修复方向：将 chain.yaml 候选路径参数化/注入（如经配置或调用方传入），使 loop_core 不含 `.zcode` 字面量；修复后重跑全量回归至 0 failed（排除 2-4 三项登记瞬态）。
   - developer 记录（commands.md 回归表）未覆盖该测试文件（test_code_quality），属其回归盲区。

### P3（2 项，不阻断）

2. **test_existing_verdicts_unchanged_on_repo 失败理由与记录不符**：developer 记录为「continuity drift exit 2 所致，repair 后恢复」；实际当前失败原因为测试硬编码 `current_task_id: T-0108` 断言（state 已推进至 T-0109）——同属任务态耦合瞬态类（closeout 后 state 复位即自愈），但记录的理由与实测不符，建议修正记录或在 closeout 时同步该测试断言。
3. **dashboard_views.py 中段 import（:832-834）**：模块中部追加别名 import（`dataclass as _dataclass` 等）风格上略欠整洁（功能正确，行为等价已实证），可作 P3 记录。

---

## 六、总结论

T-0109 四线（F2-2/F3/F1/F5）实施真实、数据可复算、约束零弱化：hooks/ 仅 loop_enforcement.py 白名单常量表注释级同步（+6/-2，逐行核对）；治理内核（gate_guard/enforcement/enforcement_hub/hard_constraints/guard_health）diff=0；state_machine.py 仅 F2-2 刷新调用（判定零改动）；validate_state.py 零改动；零工具删除；F1 评分 advisory-only 静态断言与独立 grep 双证。F3 归档/外提/枚举全部对 HEAD 原数据复算 0 差异。全量回归 4042 passed / 5 failed（3 项预登记瞬态 + 1 项 P3 耦合 + **1 项 P1 新增 host-leak 测试失败**）。

**裁决：CONDITIONAL_GO**——修复 P1（loop_core/evidence_chain.py 去宿主特定路径，消除 DR-002）并重跑全量回归确认 0 failed（排除登记瞬态）后，可转 GO 进入 closeout。
