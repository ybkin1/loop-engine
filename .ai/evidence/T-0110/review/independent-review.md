# T-0110 独立审查（independent-review）

- 审查人：independent-reviewer 子代理（fresh context，未参与实施）
- 日期：2026-08-03
- 基线：git HEAD 70ca674（v3.12.46）→ 当前工作树（含主会话版本 bump 3.12.47）
- 审查对象：`.ai/tasks/T-0110.md`（6 AC + 硬约束）、`.ai/evidence/T-0106/design/design-common-weakness.md`、
  `.ai/evidence/T-0110/commands.md`、`fixes/{batch-a-constants,batch-b1-metrics-intent,batch-b2-review-loader,batch-c-enforcement}.md`、
  `golden/`（6 快照 + 3 生成器）、实际 git diff
- 方法：全部结论亲自复验（读代码 / 独立重跑 golden / AST 交叉核对 / 独立全量回归），不复述他人证据

---

## 一、裁决

**GO**（无 P0/P1/P2；4 项 P3 见 §六，其中 3 项为文档口径/登记类，1 项为预存运行时噪声）

核心证据链（全部独立复验）：
1. 三个批次的 golden 快照**独立重跑逐字节一致**（B-1/B-2/C，sha256 与提交的 before/after 双快照完全相同）；
2. "before" 快照经 **AST 交叉核对确系拆分前源码**（HEAD 版本顶层名 vs 快照 dir()，仅运行时注入属性差异）；
3. 自愈 re-exec 机制**逐字保留**（函数体与 main() 调用链 diff 为空；仅扫描集 +4 文件名）；
4. 自愈路径实测 2/2 通过（真子进程端到端）；
5. 全量回归 4138 passed，5 failed 全部归类为预登记/瞬态项（§五），无 T-0110 代码引入的失败。

---

## 二、改动范围核对 + 约束零弱化专项

### 2.1 全量 diff 与 allowed_paths

`git diff HEAD --stat`（29 文件，+991/-4388）+ untracked 新增 20 文件。对照任务卡 allowed_paths：

| 类别 | 文件 | 判定 |
|---|---|---|
| 产品代码（allowed） | loop_core/ 9 个（5 壳 + 4 批 A 接线）、hooks/scripts/loop_enforcement.py、tools/loop_self_audit.py、scripts/role_checkers/ ×2 | ✅ |
| 新增（allowed） | loop_core/constants.py + 12 拆分模块、hooks/scripts 4 模块、tests/ 4 个新文件、.ai/evidence/T-0110/、.ai/tasks/T-0110.md | ✅ |
| 测试/配置 | tests/test_hook_integration.py（复制集改造）、pyproject.toml（per-file-ignores 6 行）、CHANGELOG.md | ✅ |
| 版本 bump 文件 | pyproject.toml/README.md/docs/06-delivery.md/loop_core/__init__.py/src/loop_engine/__init__.py/.zcode-plugin/plugin.json/.ai/version-manifest.yaml（3.12.46→47） | ✅ AC-05 主会话职责，commands.md 明示 |
| .ai/ 治理态 | gates.yaml（G-T-0110-REQUIREMENTS 登记）、state.yaml/task_graph.yaml/HANDOFF.md（T-0110 状态）、guard-events.jsonl（+307 运行时事件）、conformance-report.json、T-0109.md | ✅ 运行时/治理流，非代码改动 |

### 2.2 hooks/ 专项（逐文件核对）

`git diff HEAD --numstat -- hooks/` 仅 1 行：`98 1161 hooks/scripts/loop_enforcement.py`。
`git status --short -- hooks/`：壳 M + 4 untracked 新增（gate_evidence_checks.py / loop_command_utils.py / loop_contract_parser.py / loop_enforcement_constants.py）。

hooks/scripts/ 17 个已跟踪文件逐一核对：**16 个零改动**（_hook_bash/_hook_config/_hook_path/_hook_state/_hook_sync/bash_content_guard/content_guard/gate_guard/hook_common/ledger_guard/loop_auto_activate/loop_enforcement.py.bak/path_guard/role_isolation/session_brief/template_injector），仅 loop_enforcement.py 改动。任务卡"其余 15 个"为不含 .bak 的口径，实际 16 个，零改动事实成立。

### 2.3 治理内核零触碰

- 内核实体定位：loop_core/enforcement_hub.py、loop_core/guard_health.py、loop_core/hard_constraints.py、loop_core/state_machine.py、hooks/scripts/gate_guard.py
- `git diff HEAD --` 上述文件：**diff = 0**（空输出）
- guard_health timeout=20 字面量保留（零触碰豁免，常量表仅登记）

### 2.4 零删除

`git diff HEAD --diff-filter=D --name-only`：**空**。5 壳 dir() 全量 re-export（104/97/69/43/67 名）零符号消失。

### 2.5 fail-closed 语义

- golden-c 51→48 场景矩阵（PASS/BLOCK 全谱）+ 204 直调逐字节一致 ⇒ 裁决链输出不变
- 壳 main() 与自愈调用链逐字保留（§三）
- check_diff_scope/quality gate 等证据检查函数体逐字迁移（golden 覆盖越界/超时/git 失败路径）

---

## 三、行为等价专项（硬门槛）

### 3.1 golden 独立复跑（本审查人亲自执行）

用 golden 目录捕获器在当前工作树独立重跑，与提交的 before/after 快照 sha256 对比：

| 批次 | 捕获器 | 独立复跑 sha256 | before | after | 结果 |
|---|---|---|---|---|---|
| B-1 | generate_golden.py | `a55433f2…3ffe`（425,977 B） | 同 | 同 | **byte-identical** |
| B-2 | generate_golden_b2.py | `c372a466…7431`（66,082 B） | 同 | 同 | **byte-identical** |
| C | generate_golden_c.py | `47e105ce…0ca61`（49,858 B） | 同 | 同 | **byte-identical** |

### 3.2 "before" 快照真实性（防"before 也是拆分后产物"的怀疑）

AST 交叉核对：对 5 个拆分前文件取 `git show HEAD:<file>`，解析顶层名字（含 if/try 嵌套、import 别名、TYPE_CHECKING 块），与 before 快照的 dir() 基线对比：

- governance_metrics（97）、context_loader（67）、human_review_packet（43）、loop_enforcement（104）：**零缺失**；多余项仅为运行时注入（`annotations`=__future__ feature 绑定、`__warningregistry__`）或拆批工作树增量（intent_router 快照多出批 A 的 CONFIDENCE_CONFLICT_* ×2 + KEYWORD_BOUNDARY_MAX_LEN 3 名——与 commands.md 批 A 基线声明精确吻合）
- 结论：before 快照确系拆分前代码捕获，before==after 的逐字节一致是真实的行为等价证据，非同源重放

### 3.3 自愈 re-exec 实测（AC-03）

- 机制保留：`_snapshot_hook_file_shas`（仅 +4 扫描集文件名与注释）、`_hook_files_changed_since_load`、`_reexec_with_fresh_code`（含 os.execv 主体）与 main() 内 re-exec 调用链（count < _REEXEC_MAX → env 计数 → re-exec）**与 HEAD 逐字节 diff 为空**；`_REEXEC_MAX` 别名接线自常量表（值 1）
- 实测：`tests/test_t0110_batch_c.py::TestSelfHealReexec` 独立重跑 **2/2 passed**。测试为真端到端：缓存旧代码 + 本地新代码（常量表 GOVERNANCE_EXEMPT 追加 extra/）→ 子进程实跑 hook → 断言 re-exec 恰一次、rc=0（新代码判定）、缓存同步 == 本地、后续调用 0 次 re-exec、无修改对照 rc=2 且 0 次 re-exec
- 判定：**AC-03 PASS**

### 3.4 re-export 完整性（五壳抽查）

- 对象同一性 15 项独立断言全 OK（壳绑定 is 新模块定义对象）：gm.load_gates is governance_loaders.load_gates、ir._detect_domains is intent_detection._detect_domains、hrp.build_resume_payload is resume_payload.build_resume_payload、cl.summarize_text is loader_summary.summarize_text、**cl._ROUTING_CACHE is loader_sections._ROUTING_CACHE（同一 dict，T-0108 clear 语义保持）** 等
- dir() 基线断言真实：test_t0110_batch_c.py 以 golden-c-before.json 的 dir_snapshot（104 名）为基线运行时比对，非硬编码抄袭
- kwdefaults 保持：ContextLoader.load_role_context/load_for_role 的 include_memories=False、memory_limit=5、memory_task_id=None（独立 inspect 复验）

---

## 四、逐批真实性（抽查表）

### 批 A：常量集中
| 项 | 复验 |
|---|---|
| loop_core/constants.py | 22 常量 + 2 纯函数，值核对（100/500/4000/2000/800/400/10/300/4/2/3/3）✅ |
| hook 常量表 | EXIT_PASS=0/EXIT_BLOCK=2/REEXEC_MAX=1/COMMAND_TIMEOUT=30/PROBE=20/MAX_DIFF_FILES=15/DEFAULT_MAX_FILES=10 + 白名单 4 组 ✅ |
| 接线 diff | executor/security_scanner/design_reviewer 字面量→常量（值逐一相同，diff 目检）✅ |
| grep 零散落 | 独立 grep touched 文件：仅 executor.py 既有 timeout=120 ×2（显式豁免）；TestGrepZeroScatter 双断言真实（timeout= 与 `[:N]`/`[-N:]` 双模式）✅ |
| M-16 | .ai/slo.yaml score_caps（59/74/84/94/100）== evidence_state.DEFAULT_SCORE_CAPS（独立导入比对一致）✅ |
| P3 消解 | D3-6/D3-8 补 timeout+兜底、D4-9 裸 except 收窄（role_checkers diff 目检 + 兜底行为测试在册）✅ |

### 批 B-1/B-2：拆分边界
- 新模块 15 个与 design-common-weakness.md §1.2~1.5 边界一致（governance_loaders/aggregations/slo_evaluator/dora_metrics；intent_keywords/detection/split；review_models/resume_payload/review_renderer；loader_fields/summary/citation_resolver/sections）
- 壳规模与声明一致：governance_metrics 612（原 1508）、intent_router 965（1484）、human_review_packet 643（1307）、context_loader 839（1432）
- 依赖 DAG 无环（test_leaf_modules_never_import_shell 等静态防线在册并通过）
- T-0108 路由表逻辑随 loader_sections 外提且同一性保持（§3.4）

### 批 C：hook 拆分
- 壳 1052 行（声明 1052，原 2115）✅；外提 3 新模块 + 接线常量表
- GOVERNANCE_TOOL_DIRS 双登记属实（壳源内 tuple 字面量 + 常量表，AST 断言测试 test_governance_tool_dirs_ast_literal_kept 在册通过）
- hook 全套件独立重跑（enforcement/hooks/role_isolation/enforcement_hub/hook_guards/hook_integration/guard_health/gate_guard_lifecycle/path_guard）：**225 passed**

---

## 五、测试真实性 + 全量回归独立结果

### 5.1 新增验收测试（独立重跑）
| 套件 | 结果 |
|---|---|
| tests/test_t0110_batch_a.py | 41 passed |
| tests/test_t0110_batch_b1.py | 17 passed |
| tests/test_t0110_batch_b2.py | 20 passed |
| tests/test_t0110_batch_c.py（含 TestSelfHealReexec 2 项） | 14 passed |
| 编译 compileall（全部触及文件） | exit 0，0 错误 |

### 5.2 全量回归（本审查人独立执行）
`C:/Python312/python.exe -m pytest tests/ -q` → **4138 passed, 64 skipped, 12 xfailed, 5 failed**（3 分 14 秒）

5 项失败逐一独立判定：

| 失败 | 归类 | 独立证据 |
|---|---|---|
| test_deployment_quality_checker::test_runtime_report_is_simulated_and_fail_closed | 预登记环境依赖（T-0108 closeout 已登记；批 B-1/B-2/C 文档一致） | 断言环境模拟态 status 判定，零 loop_core 依赖 |
| test_manifest_t0095::test_manifest_exists_and_handoff_reference_is_real | closeout 瞬态（预登记） | HANDOFF.md 引用 `.ai/evidence/T-0110/evidence-manifest.v1.yaml`，closeout 时生成（T-0109 同款） |
| test_release.py::test_pyproject_version_matches_git_head | bump 瞬态（预登记类别） | pyproject=3.12.47 vs git HEAD=3.12.46（提交后自然恢复） |
| test_t0108_fixes::test_validate_state_still_passes_on_repo | **bump 瞬态（新出现，非预登记明细）** | validate_state rc=2，`PROJECT_CONTINUITY_SOURCE_DRIFT: .ai/version-manifest.yaml`；独立重算 source_manifest 哈希：**仅 version-manifest.yaml 1 项漂移**，且其 diff 纯版本号（1619→1619 字节） |
| test_t0108_fixes::test_existing_verdicts_unchanged_on_repo | 同上（同一根因） | 同一条 PROJECT_CONTINUITY_SOURCE_DRIFT |

两项 test_t0108_fixes 失败根因为主会话版本 bump 3.12.47 未提交（version-manifest.yaml 内容变更 → continuity 源漂移 → rc=2），与 T-0110 拆分散落的任何文件无关（拆分散落文件不在 continuity source_manifest 中），提交 bump 后自然恢复。属审查指令中"bump 后 version sync 提交前瞬态——标注即可"类别。

**无任何 T-0110 代码改动引入的失败。**

---

## 六、发现清单

**P0：无**
**P1：无**
**P2：无**

**P3（4 项）：**
1. **文档口径：golden C 场景数"51"与实 48 不符**。commands.md / fixes/batch-c-enforcement.md / test_t0110_batch_c.py 文档串均称"51 场景"，golden-c-before.json 实际 48 个矩阵条目。不影响行为等价结论（before/after 同源同捕获器逐字节一致），但文档计数应更正。
2. **两项 test_t0108_fixes 失败未在 fixes/ 文档中单独登记**（仅批 C 记录"2 failed = manifest + deployment"）。根因是主会话在批 C 回归之后才执行版本 bump（AC-05），时间线解释成立；建议 closeout 时登记，避免后续审查误判。
3. **hooks/scripts/loop_enforcement.py.bak 为已跟踪文件**（前序遗留，非本任务引入），零改动；任务卡"其余 15 个 hook 文件"口径不含它（实际 16 个零改动）。仅提示，无需动作。
4. **.ai/evidence/observability/guard-events.jsonl +307 行**为 hook 测试运行期追加的运行时事件（既有行为），非批 C 代码改动；与 T-0109 提交模式一致。

---

## 七、总结论

- **裁决：GO**
- 行为等价硬门槛全部独立复验通过：三批 golden 独立重跑逐字节一致（且 before 快照经 AST 交叉核对确系拆分前源码）；自愈 re-exec 机制逐字保留且实测 2/2；五壳 re-export 面（104/97/69/43/67 名）零缺失零新增
- 约束零弱化：hooks/ 仅 loop_enforcement.py 改动 + 4 新增模块（其余 16 个 hook 文件零改动）；治理内核 5 文件 diff=0；零删除（diff-filter=D 为空）；fail-closed 语义不变
- 全量回归 4138 passed / 5 failed 全部归类（2 预登记 + 3 bump 瞬态，其中 2 项为同一 version-manifest 漂移根因），无 T-0110 引入失败
- AC 对照：AC-01 ✅（grep 零散落双断言真实）、AC-02 ✅（golden 逐字节）、AC-03 ✅（自愈实测 2/2 + hook 套件 225 passed）、AC-04 基本 ✅（compileall 0 错误；0 failed 待提交后达成，5 项失败均为瞬态/预登记）、AC-05 ✅（版本 3.12.47 全文件一致，git HEAD 同步待主会话提交）、AC-06 ✅（本审查）
- 遗留：4 项 P3 建议在 closeout 时登记/更正文档口径
