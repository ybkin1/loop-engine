# T-0108 独立审查报告（independent review）

- 审查者：independent-reviewer 子代理（fresh context，全部结论亲自复验）
- 日期：2026-08-03
- 基线：`3e766ec`（v3.12.44）→ 当前工作区（未提交，bump 3.12.45 在树）
- 审查对象：`.ai/tasks/T-0108.md`（9 AC）、design-bh-integration.md F2/F4/F6/F7/F8、plan-task-roadmap.md T-0108 节、`.ai/evidence/T-0108/commands.md` + fixes/*.md、`git diff HEAD`
- 复验方式：读代码、git diff 逐文件核对、目标测试独立重跑、全量回归独立重跑、基线 worktree 对照、validate_state 手工 A/B 实证

---

## 一、裁决

# **CONDITIONAL_GO**

实施内容全部通过独立复验；唯一阻塞项为**主会话 bump 未提交产生的 continuity 漂移瞬态**（version-manifest.yaml 3.12.45 已改、project_continuity.yaml 未重算哈希 → validate_state exit 2），导致 2 项新增仓库态测试当前失败。该漂移由主会话 AC-08 bump 引入（非 developer 改动），closeout 时经 render_handoff/continuity 重生成自愈。**放行条件**（见第五节 P2-1）：主会话 closeout 序列须在**最终全量回归前**完成：①提交 bump（3.12.45 == HEAD）；②重生成 project_continuity.yaml（validate_state 复归 exit 0）；③创建 `.ai/evidence/T-0108/evidence-manifest.v1.yaml`。三条件满足后 AC-07 的"0 failed"可达。

---

## 二、改动范围核对 + 约束零弱化专项

### 2.1 全量 diff 清单（git diff HEAD，28 文件 + 2 staged 归档 + 9 untracked）

| 类别 | 文件 | 判定 |
|------|------|------|
| 允许路径内（.ai/） | HANDOFF/continuity/state/task_graph/gates/version-manifest + README.md（新）+ archive/plans×2（git mv） | PASS |
| 允许路径内（loop_core/） | context_loader / context_packager / design_reviewer / security_scanner / subagent_evidence_verifier / memory_service / projection_engine + context_budget.py / schemas/finding.schema.json / finding_contract.py（新） | PASS |
| 允许路径内 | validate_state.py、agents×3、implementation_design_diff.py、docs/02-architecture.md、pyproject.toml、CHANGELOG.md、tests/×3（新） | PASS |
| **allowed_paths 未枚举（版本载体）** | README.md、docs/06-delivery.md、loop_core/__init__.py、src/loop_engine/__init__.py、.zcode-plugin/plugin.json | **P3-2**：均为纯 3.12.44→3.12.45 版本字面量替换（AC-08 必需），机械性无害，但任务卡 allowed_paths 未枚举 |

### 2.2 约束零弱化专项（最高优先，全部亲自实证）

| 约束 | 实证方式 | 结果 |
|------|----------|------|
| **hooks/ 零改动** | `git diff HEAD -- hooks/` 输出为空 | **PASS**（零 diff） |
| **治理内核零触碰** | `git diff HEAD -- loop_core/gate_guard.py loop_core/enforcement.py loop_core/hard_constraints.py loop_core/guard_health.py loop_core/state_machine.py` 输出为空 | **PASS**（零 diff） |
| **context_loader 默认值不变** | 签名 `_select_relevant_sections(role_id, doc_index, project_root=None)` 默认 None → 旧启发式路径逐字节保留；`load_for_role` 调用点显式透传 `self._project_root`（该属性既有） | **PASS** |
| **validate_state 纯新增** | `git diff`：37 insertions / **0 deletions**（`grep "^-"` 为空）；新增 `check_state_view_freshness` + main() 一处 `errors.extend(...)` | **PASS**（纯新增） |
| **validate_state 既有判定/exit code 不变** | 代码核对：`[warn]` 前缀条目被既有分类逻辑分流至 warn_errors，**不进 blocker_errors**、不改变 exit 判定；手工 A/B 实证（伪造旧 mtime 视图 vs 无视图）：`[warn] stale view` 出现且 **error 集合逐条一致、exit code 一致（均为 2，当前唯一漂移错误）** | **PASS** |
| **fail-closed 语义不变** | 路由表缺失 → 回退旧启发式 + warning（不静默空上下文）；finding 校验失败/`jsonschema` 缺失/schema 不可读 → INVALID（不静默放行）；D4-10/11 失败原因区分上报（不再静默 None/空）；D5-6 未命中行计数 + warning | **PASS** |
| **不实施 T-0109+** | 无 state_machine 写入收敛、无 gates 分层、无 evidence_state、无 capability_registry、无工具合并/删除改动 | **PASS** |

---

## 三、五线逐线真实性（抽查表）

### 线 1 — F6 上下文打包（PASS）

- `loop_core/context_budget.py`（新增）与 HEAD 内联实现**逐字节等价**：`estimate_tokens`/`slice_with_marker`/`split_sections`/`is_ac_section` 函数体与删除的 `_estimate_tokens` 等逐一比对一致；`format_task_card` 与旧 `_format_task_card` 仅 budget 变为参数（默认值=原常量），标记字符串 `…[task card truncated: `、`…[truncated N chars]` 与 HEAD 字面量一致
- context_packager：5 常量 re-export + 5 别名，既有导入方/测试属性访问零改动；`build_context` 内部调用别名（L178/186/210/233/243）
- P3 覆盖：D1-3 extra_files `_slice_with_marker(c, EXTRA_FILE_MAX_CHARS)`（L243 带标记）；D2-8 `GIT_TIMEOUT_DIFF_STAT/CODE/NAME/REV_PARSE`=5/10/5/5（L41-44）且 diff 调用点引用；D4-4 knowledge cases 失败 `logger.warning`（L253，T-0107 落地、回归确认）
- 测试：`test_t0107_fixes.py` + `test_context_compression.py` 独立重跑 **79 passed**；TestContextBudget 6 passed

### 线 2 — F4 文档路由（PASS）

- `.ai/README.md`：Owns / Does Not Own / Read Next 三节、目录四态（active/generated/target/candidate/archived）、20+ 文档活/死归类表、front-matter `section_routing`（机器可读）
- **路由表 keyword 与旧启发式 panel 逐项一致**（quality-engineer…release-engineer 11 角色逐条比对相同；default=[] 与旧 `get(role_id, [])`→`available[:3]` 语义等价）→ golden 一致性在语义层成立（TestRoutingTable 4 用例含 routed==legacy 实证）
- 归档：`git mv` 确认（diff 显示 `{ => archive}/plans/` 100% rename 0 内容变更）；continuity source_manifest 移除 2 条目 + source_sha256 重算（C0D2AF9B→4FA31FC1，semantic_sha256 未动）；HANDOFF 重生成且嵌入 source_sha256 与 manifest 一致
- D5-7：docs/02-architecture.md front-matter `designed_files:`（flow 风格，含 content_guard 兼容注释）；implementation_design_diff 重写——DRIFT 判定仅依声明区，正则推断进 `hint_regex_inferred`（不参与判定），无声明回退 `regex-fallback`。**独立运行 checker 实证**：`designed_but_missing=[]`，evidence_chain.py/hook_common.py/server.py/validate_state.py 全部移入 hint（误报消除声明成立）；剩余 `actual_but_undesigned`（loop_enforcement/content_guard 等非 v1.0 声明 hook）= 声明驱动的正确行为（P3-4）
- 归档链路测试：test_archived_plans_moved_not_deleted / test_continuity_manifest_synced PASS；test_validate_state_still_passes_on_repo 受 bump 漂移影响（见 P2-1）

### 线 3 — F7 finding 结构化契约（PASS）

- `finding.schema.json`：draft-07、9 必填字段、severity 枚举、`additionalProperties: true`（加字段不删字段）。**对照 .qoder/better-harness/.../findings.json 实样独立核对**：BH 侧字段 id/title/severity(首字母大写)/reason/expectedOutput[]/expectedArtifact/aiFixPrompt/dimensionRefs 与 `to_bh_finding` 映射逐项吻合
- `finding_contract.py` fail-closed：`validate_finding` 永不抛出；schema 不可读/jsonschema 缺失 → (False, 原因)；`mark_schema_status` 附加 VALID/INVALID
- 三扫描器收敛（加字段不删字段）：design_reviewer `DesignFinding.to_finding()`（severity error→high 映射）+ schema_valid/invalid 计数；security_scanner `SecFinding.to_finding()`（truncated 标志）+ `findings_contract` 视图；subagent_evidence_verifier `verify_review_evidence` 结果增 findings（valid/reason/checks 旧语义保留：reason 取首个失败、checks 逐项布尔不变——重构后逐分支核对等价）
- agents 三脚本：D1-7 `_slice_raw`/RAW_OUTPUT_MAX_CHARS=500/raw_truncated/raw_length/raw_max + finding_id/severity/truncated/snippet + `_finding_contract`/`_attach_contract`；D4-10 run_madge 五态失败原因（unavailable/timeout/error/non-zero-exit/invalid-json + reason/stderr|stdout_tail）+ dependency_source；D4-11 双处宽捕获收窄 + `_PARSE_ERRORS`/parse_errors 上报
- D5-6 memory_service：`acceptance_meta` 结构化块优先，正则族回退保留（meta_skip 后旧循环逐行等价核对），`_count_unmatched_meta_lines` + warning 上报
- 测试：TestFindingContract 6 / TestAgentsScripts 5 / TestMemoryReportMeta 4 全绿

### 线 4 — F8 治理契约测试（PASS，2 项仓库态用例除外见 P2-1）

- `tests/test_ai_doc_links.py` 8 用例：三节/四态/归类表存在性、全链接可解析（markdown + 反引号路径，已知根前缀+白名单机制）、归档无悬挂、**断链夹具×2 断言 FAIL（monkeypatch REPO_ROOT 隔离临时仓库）**——独立重跑 8 passed
- `tests/test_projection_freshness.py` 8 用例：视图=state.yaml 派生逐字段/确定性/task_status 权威源/缺 state 抛错；mtime 新鲜度（无视图不 stale/新视图不 stale/伪造旧 mtime→stale+age 断言）；validate_state 集成（`[warn] stale view` + error 集合/exit code 一致性断言）——独立重跑 8 passed
- `tests/test_t0108_fixes.py` 34 用例（9 类）：独立重跑 32 passed / **2 failed（仓库态 validate_state 断言，bump 漂移所致，见 P2-1）**

### 线 5 — F2 阶段 1（PASS）

- `projection_engine.py`：`generate_state_view`（state.yaml 派生 + `task_status` 取自 task_graph 权威源）、`write_state_view`（显式落盘 `.ai/views/state-view.yaml`，仅显式调用才写）、`is_state_view_stale`（mtime 对比，缺失→(False,None)）；既有 ProjectionEngine 类零改动（纯追加模块级函数）
- `validate_state.py`：`check_state_view_freshness` 只读（1s 容差），接入 main() 第 8 步；`[warn]` 前缀分流不阻断（见 2.2 实证）
- 手工实证（独立执行）：伪造旧 mtime 视图 → `[warn] stale view` 输出 + exit 2（与无视图一致，漂移错误为唯一错误）；error 集合逐条相同

---

## 四、测试真实性 + 全量回归独立结果

### 4.1 全量回归（独立重跑，192.89s）

```
= 5 failed, 3957 passed, 64 skipped, 12 xfailed in 192.89s =
```

| # | 失败项 | 原因定性 | 是否预期 |
|---|--------|----------|----------|
| 1 | test_deployment_quality_checker::test_runtime_report_is_simulated_and_fail_closed | 本机 localhost:3000/8000 占用（service.startup=PASS）——**基线 worktree（3e766ec）独立重跑同样 FAIL**，KNOWN_ISSUES 已登记 | 预期（环境依赖，预存在） |
| 2 | test_manifest_t0095::test_manifest_exists_and_handoff_reference_is_real | HANDOFF 引用 `.ai/evidence/T-0108/evidence-manifest.v1.yaml` 未创建（closeout 产物） | 预期（closeout 瞬态） |
| 3 | test_release::TestAC01VersionSync::test_pyproject_version_matches_git_head | pyproject=3.12.45 vs HEAD=3.12.44（提交前瞬态） | 预期（bump 瞬态） |
| 4 | test_t0108_fixes::TestArchiveAndContinuity::test_validate_state_still_passes_on_repo | validate_state exit 2：唯一错误 = `.ai/version-manifest.yaml` continuity 漂移（bump 后 manifest 未重算） | **未预期**（P2-1） |
| 5 | test_t0108_fixes::TestValidateStateRegression::test_existing_verdicts_unchanged_on_repo | 同上 | **未预期**（P2-1） |

> 基线对照（worktree 3e766ec）：唯一真实失败为 #1；#2/#3/#4/#5 均为 T-0108 期间新状态（T-0108 HANDOFF 引用、bump、bump 所致漂移）。基线 #2 指纹用例的 worktree 失败为 CRLF 检出差异伪影（327 vs 316 bytes），非真实失败。

### 4.2 其它验收相关

- compileall（loop_core/.zcode/tools/agents/scripts/tools/src）：**exit 0**
- release.py check 6 步：compile / guard_health（5 guard 存活）/ slo_gate（消耗 5.0/100.0）/ key_tests **PASS**；version_sync + validate_state 仅因 bump 瞬态 FAIL（closeout 提交后自愈）
- 目标测试独立重跑：test_t0107_fixes + test_context_compression **79 passed**；test_ai_doc_links **8 passed**；test_projection_freshness **8 passed**；test_t0108_fixes **32/34**（2 项为 P2-1）

---

## 五、发现清单

### P0（无）
### P1（0 项）
### P2（1 项）

- **P2-1**：主会话 bump（3.12.45）未同步重算 `project_continuity.yaml` 中 version-manifest.yaml 的 sha256 → 当前 validate_state exit 2（`PROJECT_CONTINUITY_SOURCE_DRIFT`），2 项新增仓库态测试（test_validate_state_still_passes_on_repo / test_existing_verdicts_unchanged_on_repo）失败。developer 的 continuity 同步（F4-3）在其运行时刻是正确的（bump 前版本哈希匹配），漂移由 bump 后引入；commands.md 遗留事项已登记 #2/#3 瞬态但**未登记本项**。
  **放行条件**：closeout 序列须为 ①提交 bump（3.12.45==HEAD）→ ②重生成 continuity（validate_state 复归 exit 0）→ ③创建 T-0108 evidence-manifest；随后重跑全量回归确认 0 failed（剔除 #1 环境项）。

### P3（4 项，记录不阻塞）

- **P3-1**：设计文档与任务卡口径不一致——design-bh-integration.md F2 验收写"伪造旧 mtime → validate_state 报 stale，**exit code 非 0**"、roadmap AC-04 草案写"exit 非 0 仅告警阶段"，而任务卡 AC-04 + 禁止动作明确"仅告警、既有判定不变"。实现遵循任务卡（warn-only，与硬约束一致），建议后续修订设计文档措辞。
- **P3-2**：任务卡 allowed_paths 未枚举版本载体（README.md / docs/06-delivery.md / loop_core/__init__.py / src/loop_engine/__init__.py / .zcode-plugin/plugin.json），改动为纯版本字面量（AC-08 必需），建议后续任务卡显式枚举。
- **P3-3**：agents 脚本 `_finding_contract` 的 schema_status 为构造保证的静态 VALID（独立 subprocess 不加载 loop_core schema），已在 fixes/f7-finding.md 遗留声明——符合设计，运行时对真实 schema 校验留待需要时接入。
- **P3-4**：implementation_design_diff 对 hooks/scripts 非 v1.0 声明文件（loop_enforcement/content_guard 等）仍报 actual_but_undesigned（DRIFT）。属声明驱动的正确行为（designed_files 未声明它们），系统架构师可在架构文档演进时扩充；建议 T-0109+ 排布内处理。

---

## 六、总结论

五线实施（F6 外提逐字节等价 / F4 路由+归档+声明区 / F7 schema 契约+BH 映射 / F8 三测试文件 / F2-1 只读告警）全部经独立复验**真实且达标**；约束零弱化四项（hooks/ 零 diff、内核零 diff、validate_state 纯新增 0 删除、fail-closed 语义不变）均有 diff/运行实证。全量回归 5 failed 中 3 项为预期瞬态/环境项、2 项为 bump 漂移致仓库态测试失败（非代码缺陷，closeout 自愈）。

**裁决：CONDITIONAL_GO**——前提是主会话按 P2-1 放行条件完成 closeout 序列（提交 bump → 重生成 continuity → 创建 evidence-manifest）后重跑全量回归确认 0 failed。
