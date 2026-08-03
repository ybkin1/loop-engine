# T-0109 F2-2 写入收敛 / F3 gates 分层 / F1 评估模型 / F5 工具 capability 化 — 实施命令记录

日期：2026-08-03（工作树基线：HEAD v3.12.45 + 主会话 T-0109 启动改动）

## F2-2 状态写入收敛

### 落地
1. `.zcode/tools/governor_lib.py`（保护区，纯新增）
   - `write_state_files(root, changes, *, refresh_projection=True, **kwargs)`：
     F2-2 收敛写入入口——state 相关路径（state.yaml/task_graph.yaml/
     HANDOFF.md/PROGRESS.md/tasks/*.md）统一经既有 `transactional_write_texts`
     事务写；非 state 路径 / `.ai` 外路径 → `SCOPE_VIOLATION`（fail-closed）；
     写后默认触发 projection 刷新。默认（非 idempotent）模式返回
     `TransactionResult(written=[...])`（兼容底层 None 语义）。
   - `refresh_state_view(root)`：复用 T-0108 `loop_core/projection_engine.write_state_view`
     刷新 `.ai/views/state-view.yaml`；独立运行环境（loop_core 不可导入）显式告警
     返回 False——刷新失败不阻断权威写，但绝不静默吞错。
   - `STATE_RELATED_FILES`：静态检查「仅 governor_lib 写 state 相关路径」覆盖清单。
2. `loop_core/state_machine.py`（唯一权威入口保持 + 仅加刷新调用）
   - `atomic_write_state` 保持 .tmp+os.replace 原子写语义（design F2-2「:580 保持」）；
     写入后新增 `_refresh_state_view_after_transition(root_p)` 调用——转换后触发
     projection 刷新（best-effort + `STATE_VIEW_REFRESH_FAILED` 显式告警，不回滚
     已提交的权威写）。判定逻辑零改动（diff 实证见下）。
3. `.zcode/tools/validate_state.py`：**零改动**——F2-1 既有 `check_state_view_freshness`
   即双写检测器（`[warn] stale view`），F2-2 通过收敛写路径使告警清零，无需新增检测。

### 收敛路径总览
- state.yaml：`state_machine.atomic_write_state`（唯一权威入口）+ `governor_lib.write_state_files`
  （工具层）+ close_session（既有 transactional_write_texts）→ 写后刷新派生视图
- task_graph.yaml / 任务卡 Status / HANDOFF / PROGRESS：任务卡 Status 与视图字段
  为派生（权威源 state.yaml + task_graph.yaml），HANDOFF 经 close_session 事务写
- 遗留写路径（不在 T-0109 allowed_paths，未改动，静态检查以「文档化遗留例外」登记）：
  loop_core/executor.py（PhaseExecutor 持久化，T-0110 拆分目标）、
  loop_core/runtime_controller.py（S0-init onboard 引导 ensure-file）、
  loop_engine/adapters/zcode_adapter.py（host adapter save_state）、
  hooks/scripts/loop_auto_activate.py（SessionStart 自动激活；hooks 零改动约束）

### 测试
- `tests/test_t0109_f2_write_convergence.py`（13 passed）
  - TestStaticWriteConvergence：AC-02 静态检查（仓库级 AST 扫描，state 路径引用 +
    写操作文件必须登记在 收敛/遗留/manifest 修复/非状态写 四类白名单；
    .zcode/tools 与 scripts 收敛入口必须引用 governor_lib 事务写；
    loop_core state.yaml 写路径集合 == 登记名单（state_machine 唯一权威入口））
  - TestProjectionRefreshOnStateWrite：atomic_write_state / write_state_files 写后
    视图自动刷新（内容 + mtime）；刷新失败非致命 + 显式告警；write_state_files
    SCOPE_VIOLATION（gates.yaml 非 state 路径、.ai 外路径）；idempotent kwargs 透传
  - TestDualWriteWarningZeroed：裸写不刷新 → `[warn] stale view` 仍在（检测器有效）；
    收敛写 → 告警清零；validate_state 集成无 stale 输出

## F3 gates.yaml 分层

### 落地
1. `.ai/gates.yaml`：102 → 66 条 active 域（当前治理纪元 T-0081+ 29 条 +
   内核判定消费的 phase 相关历史 gate 37 条）；头部注释说明分层与归档指针
2. `.ai/archive/gates-archive.yaml`（新增）：36 条历史记录，**逐字段 verbatim**
   （快照核对 0 差异）；仅移域不删记录（union==原记录集、无删无重）
3. `.ai/policies/forbidden-actions.yaml`（新增）：7 个命名 policy（standard-v1/
   standard-core-v1/agents-md-only-v1/agents-md-deploy-v1/agents-md-business-v1/
   agents-md-external-v1/agents-md-acceptance-v1）；仅 active 域**精确重复 >=2**
   的 forbidden 集合外提为引用（26 条 gate），唯一列表保持内联（记录零丢失）
4. `loop_core/schemas/gate.schema.json`：gate_type 枚举化（覆盖 active+archive
   全部 29 个既有取值 + user-plan-approval）；新增 forbidden_policy 属性；
   approval_source 枚举补历史值（legacy_pre_field/explicit_user_plan_approval/
   explicit_user_directive）；notes/allowed_actions items 兼容历史 inline-map 条目

### 归档规则（内核判定等价保持，纯函数可复算）
gate 满足以下任一 → 必须留在 active 域：
- 任务编号 >= 81（当前治理纪元）；status == pending；id == state.current_gate_id
- 含 phase 字段；id 含阶段模式（check_phase_constraints 消费）；gate_type 命中
  任一 phase heuristic（enforcement_hub._has_approved_user_gate 消费）

### 测试
- `tests/test_t0109_f3_gates_layering.py`（18 passed）
  - TestGateSchemaValidation：active + archive 全部记录过 jsonschema 校验；
    gate_type 枚举覆盖全部记录取值
  - TestActiveDomainEquivalence：AC-01——规则(完整记录集) == 归档后 active 文件
    （逐记录等价）；union==102 无删无重；归档记录字段完整；current_gate_id/pending 留 active
  - TestKernelBehaviorEquivalence：12 phase 的 enforcement heuristic 逐 phase
    完整集 == active 域；check_phase_constraints gate-id 前缀匹配逐 phase 等价；
    resolve_gate_status(current_gate_id) 在 active 域恰一条且 approved
  - TestForbiddenPolicyReferences：policy 引用全部可解析；policy 展开 == 迁移前
    原列表（记录零丢失）；外提 gate 无残留内联；唯一列表保持内联

### 消费方核对（先 grep 后改，归档不影响）
- hooks（gate_guard/_hook_state/hook_common/loop_enforcement/session_brief/
  role_isolation/loop_auto_activate）：读 .ai/gates.yaml；所需（current task gate、
  current_gate_id、pending、phase heuristic）全部留在 active 域 → 行为不变
- validate_state/audit_handoff/continuity_producer：pending（无）+ 当前任务 gate +
  current_gate_id 均在 active → 不变；governance_metrics/dashboard 等 advisory
  读方改为 active 域视图（分层语义本意，非判定路径）
- 内核判定（enforcement_hub/check_phase_constraints/resolve_gate_status）：
  归档规则按消费语义逐项排除，等价性测试逐 phase 实证

## 回归结果

| 套件 | 结果 |
|------|------|
| test_t0109_f2_write_convergence + f3 + projection_freshness | 39 passed |
| state_machine_enhanced/projection_engine/projection_freshness/reliable_delivery/t0108_fixes/executor | 171 passed，2 failed（预期 drift，见遗留） |
| gates 消费方（gate_guard/governance_metrics/slo/status_dashboard/dashboard/approval_ledger/context_controller/governance_consistency） | 257 passed |
| enforcement/hooks/operations/cross_layer_safety/idle_semantics | 248 passed |
| doc_links/quality_gates/t0107_fixes/loop_core/learning_loop | 200 passed，1 failed（预存，见遗留） |
| human_review_packet/resume_payload/guard_health/hard_constraints/role_isolation/gate_feedback/verdicts/veto/evals/certification | 407 passed |
| live_acceptance/version_consistency/release/release_bump/loop_core_coverage | 72 passed，4 skipped |
| py_compile（governor_lib/validate_state/state_machine/projection_engine/新测试） | OK |

## 约束自查
- hooks/ diff：`git diff HEAD -- hooks/` = 0 行（零改动）
- 内核判定零触碰：state_machine.py diff 仅 atomic_write_state 加刷新调用 +
  `_refresh_state_view_after_transition` 新增函数（判定逻辑零改动）；validate_state.py
  diff = 0 行；gate_guard/enforcement/hard_constraints/guard_health 未触碰
- fail-closed 不变：write_state_files 非 state 路径 SCOPE_VIOLATION 拒绝；
  schema 校验失败即测试失败；视图刷新失败不回滚权威写但显式告警
- 写路径仅限任务卡 allowed_paths：governor_lib.py/state_machine.py/schemas/.ai/tests/
  新测试文件
- 版本文件未改（bump 主会话执行）

## 遗留（主会话收尾处理）
1. **continuity drift（预期）**：`.ai/gates.yaml` 是 continuity source 文件，F3 改动后
   validate_state 报唯一错误 `PROJECT_CONTINUITY_SOURCE_DRIFT: Continuity source
   drift: .ai/gates.yaml`（exit 2）——需 repair_continuity + manifest 同步（按 design F3
   必须保持③：gates.yaml/archive/policies 路径变更须入 manifest）。HEAD 基线
   （v3.12.45）上两个 validate_state 回归测试全过，证明 drift 完全由 F3 引起。
2. **test_t0108_fixes 两项**（TestValidateStateRegression::test_existing_verdicts_unchanged_on_repo、
   TestArchiveAndContinuity::test_validate_state_still_passes_on_repo）：仅因上述 drift
   exit 2；主会话 repair 后恢复（已在 HEAD 基线验证全过）。
3. **test_manifest_t0095 一项**（test_manifest_exists_and_handoff_reference_is_real）：
   主会话 HANDOFF 编辑新增 `Evidence manifest: .ai/evidence/T-0109/evidence-manifest.v1.yaml`
   引用，文件未生成（T-0109 closeout 时产出）——预存状态，与 F2-2/F3 无关
   （HEAD 基线该测试过是因为 HEAD HANDOFF 无此引用）。
4. `.ai/views/state-view.yaml` 现由 atomic_write_state/write_state_files 自动刷新
   （F2-2 落盘）；主会话可运行 close_session 收敛 HANDOFF 并重新生成 continuity。

---

## F1 评估模型（AC-03）

### 落地
1. `loop_core/schemas/evidence_state.py`（新增）：EvidenceState 七态枚举
   （Present/Wired/Exercised/Outcome-supported/Missing/Unobserved/N-A）+
   `coerce`（fail-closed 规整）+ 评分上限表代码默认
   `DEFAULT_SCORE_CAPS`/`SCORE_BANDS=(59,74,84,94,100)` +
   `apply_score_cap`/`score_cap_for_state`（可注入 slo.yaml 显式化配置）。
   模块无任何 gate 判定函数（advisory-only 设计约束）。
2. `loop_core/gate_feedback.py`：GateLesson 新增 `evidence_state` 字段
   （默认 N-A；to_dict/from_dict round-trip；旧记录缺字段 → N-A 向后兼容；
   schema_version 保持 1）；`record_gate_lesson` 新增关键字参数。
3. `loop_core/governance_metrics.py`：`load_slo_config` 解析 `.ai/slo.yaml`
   `score_caps` 节（fail-closed 校验）；新增分离指标族
   `build_repair_progress`（repair 触发次数/修复 GO 数）与
   `build_loop_effectiveness`（gate 通过率/cycle time/rework）+ 纯呈现
   `evidence_score_advisory`；MetricsReport 新增 repair_progress/
   loop_effectiveness/score_caps 字段；render_markdown 新增节。
4. `.ai/slo.yaml`：`score_caps:` 节显式化（对齐配置外置模式）。
5. `subagent_evidence_verifier.py` 零改动（不在 allowed_paths；映射消费留待
   后续任务，`coerce` 为统一入口）。

### 测试
- `tests/test_t0109_f1_eval_model.py`（29 passed）：七态映射 + GateLesson
  evidence 字段 round-trip/向后兼容/非法拒绝 + **分档边界等值断言
  （59/74/84/94/100 各档 parametrize）** + slo.yaml score_caps 解析/
  覆盖/fail-closed + Repair/Loop 分离计数 + **advisory 静态断言**
  （AST 扫描 7 个 gate 判定模块零评分符号；can_approve_gate/
  can_transition_phase 函数级断言；hooks/ 零符号）。

## F5 工具 capability 化（AC-04 / AC-05）

### 落地
1. `loop_core/capability_registry.py`：`ToolCapability` + `TOOL_CAPABILITY_MANIFEST`
   **36 工具全覆盖**（域分组 14 域 + audience 三级 workflow/advanced/
   maintainer）+ `build_tool_registry`（sealed、content-addressed）。
2. 薄壳消除（6 个）：先 grep 调用方（唯一代码 import 方 = tools/server.py
   `_dispatch`）→ 委托逻辑内联进 server.py 注册表（`_run_quality_gates`/
   `_run_security_scan`/`_run_dependency_analysis`/`_run_contract_validate`/
   `_run_cost_report`，行为逐字节等价；`_run_evidence_verify`/`_run_evidence_freeze`
   直调 loop_core.evidence_chain）。薄壳文件保留未删 → 删除候选
   （design/tool-removal-candidates.md，待用户独立 gate）。
3. 重复合并：
   - dashboard 四层 → `loop_core/dashboard_views.py` 单一实现（Dashboard/
     ProjectStatus 逻辑零改动迁移；status_dashboard.py 降级 re-export shim，
     session_brief/tool_dashboard/test 无感兼容）
   - 证据链三处 → loop_core.evidence_chain（`verify_chain_yaml`/
     `freeze_file_yaml` verbatim 收敛 scripts/evidence_chain.py 逻辑；
     工具壳消除；scripts/evidence_chain.py 未动——不在 allowed_paths）
   - 安全扫描三处：工具壳 → 注册表内联（MCP 输出契约 security_report/v1
     保持；重定向 loop_core 会破契约，不做）；scripts/security_scan.py 未动
   - 缓存同步三处：勘察确认不构成可合并重复组（context_packager D4-4 diff
     缓存 / role_orchestrator B-4-4 配置缓存 / hooks auto_sync_to_plugin_cache
     三类不同机制），不合并，记录在案
4. hook 白名单门禁：`hooks/scripts/loop_enforcement.py` **仅**
   GOVERNANCE_TOOL_DIRS 常量表注释同步（6 目录逐项原样；功能零改动）
   ——见 fixes/hook-whitelist.md（单独门禁）。

### 测试
- `tests/test_t0109_f5_tool_capability.py`（25 passed）：注册表 36 全覆盖/
  分组/audience + 薄壳消除调用测试（subprocess 注入等价 5 组 + server 不再
  import 实证 + 文件仍可导入）+ 证据链收敛等价（verify/freeze 逐字段 ==
  scripts 实现）+ dashboard 合并等价（shim is 单一实现）+ **白名单一致性
  （AC-05）**：36 工具路径全在白名单内、常量表 6 目录稳定、hooks/ 仅
  loop_enforcement.py 一处改动（AC-08 实证）。
- 死工具证据：`design/tool-removal-candidates.md`（候选 A 6 薄壳 0 代码
  importers；候选 B 4 弱引用；候选 C 3 legacy；每项附调用图 grep 证据 +
  一个 gate 周期无引用实证说明；删除动作待用户独立 gate，本任务零删除）。

### 回归
| 套件 | 结果 |
|------|------|
| F1/F2/F3 专测 + governance_metrics/gate_feedback/slo_consistency/evidence_chain/capability_registry/status_dashboard/dashboard | 282 passed |
| F2/F3 + product_layer_integration/tool_executor/slo_consistency/plugin_cache_sync | 81 passed |
| enforcement/hooks/hook_guards/mcp_client/tool_executor/loop_core | 187 passed |
| tool_registry_status/self_audit_llm/t0105_batch3/evals | 85 passed |
| mcp_capability/role_capability | 41 passed |
| compileall（loop_core/tools/hooks/scripts/新测试） | OK |

### F1/F5 约束自查
- hooks/ 仅 loop_enforcement.py 一处（git diff 实证 + 测试断言）；diff 为
  注释级白名单同步
- 内核判定零触碰：gate_guard/enforcement/hard_constraints/guard_health
  diff = 0 行；state_machine.py 仅 F2-2 刷新调用（f2 证据）
- 评分 advisory-only：静态断言全绿（7 判定模块零符号 + 函数级断言）
- 零工具删除：6 薄壳 + 4 弱引用 + 3 legacy 全部保留，仅证据清单
- fail-closed 不变：薄壳内联逐字节等价；evidence 不可读节点显式 BLOCKED；
  MCP 输出契约零变化
- 写路径限 allowed_paths：schemas/、gate_feedback、governance_metrics、
  capability_registry、status_dashboard、dashboard_views、evidence_chain、
  tools/server.py、tests/、.ai/、loop_enforcement.py（白名单门禁）
- 版本文件未改（bump 主会话执行）

### F1/F5 遗留
1. subagent_evidence_verifier 七态映射消费（不在 allowed_paths，coerce 入口
   已就绪）——T-0110/T-0111
2. 候选 A/B/C 删除/收敛决策：待用户独立 gate（tool-removal-candidates.md）
3. 安全扫描双实现收敛（输出契约变更）——需独立 gate 的后续任务
4. scripts/evidence_chain.py legacy CLI 壳化/删除——后续任务
5. F2 静态检查钉集更新：dashboard_views 因 F5 合并进入 state.yaml 只读消费
   （NON_STATE_WRITERS 已登记；test_state_machine_is_single_authoritative_entry
   钉集同步，state_machine 仍为唯一权威写入口）

---

## P1 修复记录（独立审查放行项，2026-08-03）

审查：T-0109 独立审查（independent-review.md）五-1 P1 + 五-2 P3-1。
裁决 CONDITIONAL_GO：修复 P1（loop_core/evidence_chain.py DR-002 host leak）
+ P3-1（test_t0108_fixes.py 任务 ID 断言去耦合）。

### 修复内容

**P1（DR-002 宿主无关，loop_core/evidence_chain.py 单文件）**
- `CHAIN_YAML_CANDIDATES` 移除 `.zcode/` 前缀项，改为纯仓库相对路径：
  `("skills/loop-governance/chain.yaml",)`。
- 宿主安装副本改注入式（T-0105 安装副本优先语义保持）：
  - 参数：`load_chain_yaml(project_root, host_candidates=...)` /
    `verify_chain_yaml(project_root, strict=..., host_candidates=...)`；
  - 环境变量：`LOOP_GOVERNANCE_CHAIN_YAML_HOST`（相对 project_root 路径）。
  - 注入候选优先于仓库源；注入缺失 → 仓库源回退（原语义保持）。
- 行为保持：仓库两处 chain.yaml 逐字节相同 → 实仓加载配置与修复前一致；
  scripts/evidence_chain.py、tools/* 未改动（不在修复写路径）；
  freeze_file_yaml 零改动。

**P3-1（test_t0108_fixes.py 测试任务 ID 去耦合）**
- `test_existing_verdicts_unchanged_on_repo` 末断言由
  `"current_task_id: T-0108" or "current_task_id: none"` 改为
  `"current_task_id:" in out`（仅前缀存在，不绑定具体任务 ID；
  参照同文件 test_validate_state_still_passes_on_repo 风格）。

### 测试结果

| 套件 | 结果 |
|------|------|
| test_code_quality::test_loop_core_has_no_host_leaks | **PASS**（修复前 FAIL） |
| test_t0109_f5_tool_capability.py（+TestEvidenceChainHostInjection 4 项宿主无关回归防护） | 29 passed |
| test_t0108_fixes.py | 31 passed |
| test_evidence_chain.py + test_code_quality.py 全量 | 73 passed |
| 四套件合并 | 136 passed |
| 全量回归 tests/ | 见下（仅 3 项预登记瞬态） |

### 约束自查（修复期）
- hooks/ 零改动（`git diff HEAD --name-only -- hooks/` 维持仅
  loop_enforcement.py 白名单注释同步——本修复未触碰）
- 治理内核零触碰（gate_guard/enforcement/enforcement_hub/hard_constraints/
  guard_health 不在本修复 diff）
- 写路径仅：loop_core/evidence_chain.py、tests/test_t0108_fixes.py、
  tests/test_t0109_f5_tool_capability.py、.ai/evidence/T-0109/（记录）
- 零删除；修复仅消除宿主路径耦合，行为保持（配置加载结果与修复前一致）
