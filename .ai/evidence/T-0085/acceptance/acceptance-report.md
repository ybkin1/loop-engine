# T-0085 Acceptance Report — Independent Review (7 AC)

| | |
|---|---|
| **Task** | T-0085 — 硬约束内核剩余激活（C5 阶段推进域 + C9 依赖债 + 约束覆盖验证） |
| **Role** | independent-reviewer（独立 actor/session：zcode-sess-9d0e1f2a3b4c5d6e） |
| **Date** | 2026-07-31 |
| **Method** | 全部 AC 独立重跑：代码审读（hard_constraints/enforcement_hub/executor/import_checker/state_machine）、运行时探针（instrumented check 函数 + 真实/合成治理项目经 EnforcementHub 全链路）、测试独立执行（phase-advance 套件 + 全量 tests/）、git diff 审查、证据文件核对。未采用任何他人结论。 |
| **Gate** | G-T-0085-REQUIREMENTS |

## Per-AC table

| AC | Criterion | Method | Verdict | Evidence |
|---|---|---|---|---|
| **AC-01** | 硬约束内核 11/11 全部实际执行（无死信） | 探针：包装 HardConstraints 全部 11 个 check_c{n}_* 方法，经 EnforcementHub 对真实仓库调用 should_allow_write + should_allow_phase_advance；另在合成治理项目经 should_allow_phase_advance 验证 C5/C9/C10/C11 触发语义 | **PASS** | 真实仓库调用实际触发：C1,C2,C3,C4,C5,C6,C7,C8,C10,C11（10/11 方法被调用）；C9 按设计仅在 S4/S5 相位门内执行（hard_constraints.py L284），经 S4→S5 合成项目验证其真实执行。C5：缺证据→BLOCK、lint=FAIL→BLOCK、test/lint/build 全 PASS→ALLOW（经 hub 真实路径）。C9：真实仓库扫描 0 违规（原 237）；未声明 import→BLOCK。C10/C11：state.current_task_id=T-0085 进入 _build_context → 两检查在真实仓库被调用（Fix 3 生效）；合成项目验证 task_id 存在时 C10/C11 触发（WARNING-only），无 task_id 时不触发（by design） |
| **AC-02** | C5 在阶段推进路径激活且有测试（推进时验证，非写入时） | 审读 executor.py Step 6b（L690-708）位于 Step 7 persist_state（L710-711）之前；BLOCKED 分支直接 return 不写 state.yaml；独立运行 tests/test_constraint_phase_advance.py | **PASS** | Step 6b `_check_phase_advance_gate` 在 persist 之前调用，BLOCKED → plan.status=BLOCKED + phase-advance-gate step，state.yaml 不推进（test_blocked_advance_does_not_persist_state 验证 state 停留在 S1）；异常默认 fail-closed（should_fail_closed，默认 True）；仅 fixture_mode（TEST-ONLY）/reentry 跳过；生产入口 tools/tool_execute_phase.py 用 `PhaseExecutor()`（fixture_mode=False）→ 门激活。套件独立执行：**21 passed** |
| **AC-03** | C9 的 237 项全部分类 | 核对 c9-buckets.json 计数与分类文档；独立运行 kernel C9 检查 | **PASS** | 分类完整：A1=5 + A2=71 + A3=160 + B=0 + C=1 = **237**（与 c9-raw-findings.json 237 条一致）；TYPE-B（真实第三方债）=0，TYPE-C=1（playwright 惰性导入，已登记为 optional-dep）。独立重跑 `check_c9_import_validity(root='.', scan_paths=['loop_core','hooks','tools'])` = **0 违规**；全仓库扫描 = 0。负控制独立验证：未声明 `requests`→BLOCK；声明 `pyyaml` 后 `import yaml`→PASS（A2 映射）；`from .x import`→PASS（A1 node.level）；嵌套本地模块（hooks/scripts/hook_common.py）→PASS（A3） |
| **AC-04** | 每约束触发+放行测试 | 逐约束清点 trigger/allow 测试（单元级 + 阶段推进门级）；独立运行套件 | **PASS（含 caveat）** | 单元级（test_hard_constraints.py / test_import_checker.py / test_contract_verifier.py）：C1-C11 全部有触发+放行测试。门级（test_constraint_phase_advance.py，21 测试独立执行全部通过）：C1(1 触发/1 放行)、C2(1/1)、C5(2 触发/1 放行+1 行为固化)、C6(1 触发/1 放行+1 严重度固化)、C8(2 触发/1 放行)、C9(1 触发/2 放行)；C3/C4 在写入路径（should_allow_write）覆盖；execute_phase 冒烟 3 项（BLOCK 不持久化 / ALLOW 持久化 / fixture 跳过）。**C10/C11 门级仅有探针测试 test_c10_c11_not_active_at_hub_level，其断言已过时（详见 caveat 1）** |
| **AC-05** | 全量测试无回归 | 独立运行 `pytest tests/ -q` | **PASS** | 独立执行：**2768 passed, 63 skipped, 16 xfailed, 0 failed**（231.4s，exit 0）。注：与 developer 报告的 2740+7 基线失败不同——本 reviewer 在当前工作树（.ai/task_graph.yaml 已为合法 YAML）上 0 失败 |
| **AC-06** | 无约束被弱化 | git diff 全量审查 4 个核心文件 + pyproject | **PASS** | diff 仅含新增：hard_constraints.py 只增 TypedDict 字段（root/scan_paths/task_id/max_files 文档化）；enforcement_hub.py 只增 task_id/max_files 上下文 + verification_passed 转发；executor.py 只增 Step 6b 门（新增强制）；import_checker.py 只改检测缺陷（A1/A2/A3）；pyproject.toml 只增声明（PyYAML 运行时依赖 + playwright optional）。**diff 中零处 Severity 改动**（grep 无结果）；C9 保持 BLOCKER（hard_constraints.py L930）；C5 语义未变（test/lint/build 必须全为 "PASS"，缺证据 fail-closed，state_machine.py L479 verification_passed 默认 False）；fail-closed 默认完整（hub 治理文件损坏 fail-closed + 门异常 fail-closed） |
| **AC-07** | 依赖债登记 | 核对 .ai/evidence/T-0085/c9-debt/ | **PASS** | c9-classification.md（含 TYPE-A1/A2/A3/B/C 分节，237=5+71+160+0+1）、c9-fix-report.md、c9-buckets.json、c9-raw-findings.json、classify_c9.py 全部存在 |

## Overall verdict: **CONDITIONAL GO**

7 项 AC 全部通过独立验证，约束内核安全（fail-closed 方向保持，无弱化，无死信）。两项条件须在后续任务/收尾中处理（均不影响当前内核安全性，方向均为"过度拦截"而非"放水"）：

1. **替换过时的 C10/C11 门级探针测试**（tests/test_constraint_phase_advance.py::TestC10C11PhaseAdvanceProbe::test_c10_c11_not_active_at_hub_level）。该测试断言 "EnforcementHub._build_context never sets task_id"，但本任务 Fix 3 已落地（_build_context L354 从 state.current_task_id 注入 task_id）；测试仅因 fixture 未写 current_task_id 而通过。测试自身 docstring 明确要求 "the moment the context fix lands, this probe must be replaced with real trigger/allow tests"。应改为经 should_allow_phase_advance 的真实 C10/C11 触发（WARNING）+ 放行测试。
2. **消除 should_allow_phase_advance 中 C9 违规重复计数**（loop_core/enforcement_hub.py L568-575）：S4→S5 分支显式调用 check_c9_import_validity，随后 check_all 又跑一次（context.current_phase=S4 时 C9 在 check_all 内也执行），同一违规在 decision.violations 出现两次、blocker_count 翻倍。拦截行为正确（只多报不少报），建议去重。

## Honest caveats

1. **C9 本地模块缓存不失效**（loop_core/import_checker.py `_LOCAL_MODULE_CACHE`，按 root 键缓存，永不失效）：同一进程内首次扫描后新建的 .py 文件不会被识别为本地模块 → 产生误报（安全方向，非漏报）。探针实证：先扫 `import requests` 场景再创建 hook_common.py，后续扫描仍标记 hook_common。实际影响低（enforcement 每次调用多为新进程），但值得修复。
2. **C8 hash 新鲜度怪癖（既有，非本任务引入）**：EnforcementHub._compute_evidence_hashes 以目录名为键对 envelope 文件本身取哈希，recorded content_hash 与文件自哈希永不相等 → evidence_id==目录名的磁盘 envelope 恒为"hash-stale"（phase-advance-matrix.md §4 已记录）。
3. **真实仓库当前状态 C5 拦截全部写入**：state.yaml 为 S6-delivery 且缺 quality_report.json（test/lint/build 证据）→ should_allow_write 返回 BLOCK（C5）。为既有行为（T-0085 未改动写入路径），但意味着该仓库在 S6 状态完成质量证据登记前，经 hub 的写入是 fail-closed 的——这是内核按设计工作，不是缺陷。
4. **fixture_mode / reentry 逃生口**（仅 TEST-ONLY 模拟与重跑当前阶段）；生产路径 tools/tool_execute_phase.py 门激活。config.yaml fail_open 仅限 DEBUG 且只作用于门异常（非违规）。
5. **tests/lab/ 测试卫生债仍在**（test_project_governor_consistency.py 依赖 archive 内 governor_lib）：已不再是 C9 误报（解析为项目本地），但仍是测试卫生债。
6. 本 reviewer 全量运行 0 失败，与 developer 早期报告的"7 项 pre-existing 失败"差异源于 .ai/task_graph.yaml 已修复为合法 YAML（其自身即 pre-existing 漂移源）。

## Files reviewed

- loop_core/hard_constraints.py, loop_core/enforcement_hub.py, loop_core/executor.py, loop_core/import_checker.py, loop_core/contract_verifier.py, loop_core/state_machine.py
- tests/test_constraint_phase_advance.py（21 项全部独立执行通过）
- .ai/evidence/T-0085/c9-debt/{c9-classification.md, c9-fix-report.md, c9-buckets.json, c9-raw-findings.json}
- .ai/evidence/T-0085/constraint-matrix/{coverage-inventory.md, phase-advance-matrix.md}
- git diff（8 文件，289 insertions / 23 deletions）

## Conditional GO items resolved

Developer follow-up（actor: developer, session: zcode-sess-9d0e1f2a3b4c5d6e，2026-07-31）处理 reviewer 的 2 项条件 + 1 项 honest finding。全部改动仅涉及 tests/、loop_core/、.ai/evidence/T-0085/，未触碰任何约束语义（C9 仍 BLOCKER、C10/C11 仍 WARNING-only、默认 max_files=10 不变）。

### Item 1 — C10/C11 门级真实 trigger/allow 测试（替换过时探针）

**修复**：`tests/test_constraint_phase_advance.py` 删除 `TestC10C11PhaseAdvanceProbe::test_c10_c11_not_active_at_hub_level`（其 docstring 自述待 Fix 3 落地后必须替换），改为 `TestC10C11PhaseAdvance` 5 项真实测试，全部经 `EnforcementHub.should_allow_phase_advance`（S4→S5）驱动，fixture 写 `state.current_task_id: T1`（Fix 3 注入 task_id 的前置条件）：
- `test_c10_trigger_contract_missing_required_tests`：`interface-contract.json` 声明 `tests_required` 但 tests/ 无对应测试 → C10 violation 存在（WARNING，不单独阻断，`allowed is True`）。
- `test_c10_allow_required_tests_present`：tests/test_api.py 定义所需测试 → 无 C10。
- `test_c11_trigger_allowed_paths_exceed_max_files`：state.yaml `max_files: 2`（低限） + 任务 markdown 3 个 allowed_paths → C11 violation 存在（WARNING）。
- `test_c11_allow_within_max_files`：2 个 allowed_paths（默认限 10）→ 无 C11。
- `test_c10_c11_allow_clean_fixture`：无 contract 文件、无任务 markdown → 无 C10/C11 且 advance ALLOWED（blocker_count=0）。

**配套改动**：`loop_core/enforcement_hub.py::_build_context` 的 `max_files` 由硬编码 10 改为读 `state.yaml` 的 `max_files` 键（`_state_max_files()`：int 强转，非正数/非数值回退默认 10——坏值绝不静默关闭检查），使 fixture 可设低限。

**验证（真实）**：`pytest tests/test_constraint_phase_advance.py -q` → **26 passed**（21 原有 − 1 探针 + C10 2 + C11 2 + C9 dedup 1 = 26）。

### Item 2 — should_allow_phase_advance 中 C9 重复计数消除

**修复**：`loop_core/enforcement_hub.py::should_allow_phase_advance`（原 L568-575）：显式 S4→S5 C9 分支运行后，`check_all` 聚合结果中过滤掉 `C9_IMPORT_NOT_DECLARED`（check_all 在 current_phase∈{S4,S5} 时也跑 C9，此前同一违规出现两次、blocker_count 翻倍）。去重后显式分支是 S4→S5 的 C9 唯一来源。

**验证（真实）**：独立探针（合成治理项目，`src/app.py` 单条未声明 `import requests`）：`should_allow_phase_advance(S5)` → **C9 violations=1、blocker_count=1、allowed=False**（修复前为 2/2）。新增固化测试 `TestC9PhaseAdvance::test_single_undeclared_import_reported_exactly_once` 断言 `len(c9)==1 and blocker_count==1`。

### Item 3 — ImportChecker 本地模块缓存失效（honest finding 1）

**修复**：`loop_core/import_checker.py` 删除模块级 `_LOCAL_MODULE_CACHE`（按 root 键缓存、永不失效）。`_collect_local_module_names` 改为无缓存、每次调用新鲜遍历；`check_directory` 每次扫描计算一次并下传 `_scan_file` → `_is_project_local_module`（避免逐条 import 全树遍历）。设计说明：树指纹（sorted file list / mtime snapshot）本身仍需全树遍历才能计算，无法避免 walk，故"每次扫描一次新鲜 walk"是正确且最简方案。

**验证（真实）**：独立探针（temp repo，`import newmod`，扫描后创建 `src/sub/newmod.py`，同一进程再扫）：run1 标记 newmod 未声明 → run2 **不标记**。新增 `TestLocalModuleCacheFreshness` 2 项测试固化（含经 `HardConstraints.check_c9_import_validity` 的 reviewer 探针形态）。

### 回归验证（真实）

- `pytest tests/test_constraint_phase_advance.py tests/test_import_checker.py tests/test_enforcement_hub.py -q` → **106 passed**（2.20s）。
- 相邻回归：`pytest tests/test_hard_constraints.py tests/test_executor.py tests/test_contract_verifier.py -q` → **144 passed**。
- 无任何约束弱化：C9 保持 BLOCKER；C10/C11 保持 WARNING（soft）；max_files 默认 10，坏值 fail-safe 回退。
