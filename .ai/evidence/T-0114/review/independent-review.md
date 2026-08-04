# T-0114 独立审查报告 — B 组 4 死工具删除执行（用户确认）

- 审查者：independent-reviewer（fresh context，全部结论亲自复验：git diff / 读代码 / 独立跑测试）
- 审查日期：2026-08-03（工作区事件时间戳 2026-08-04 UTC）
- 审查对象：`.ai/tasks/T-0114.md`（6 项 AC）；developer 记录 `.ai/evidence/T-0114/commands.md`、`fixes/removal-execution.md`
- 实际改动基线：`git status` + `git diff`（HEAD=6e030e6 v3.12.49 → 当前工作区）
- 审查方式：只读 + 只写本报告；零生产文件修改

---

## 一、裁决

**GO（条件性）** — 删除执行本身完全通过独立复验：删除精确 4 项、注册表 26/26 双向零缺口、
零符号悬挂引用、hooks/ 零改动、run_* 保留、相关测试 200 passed 全绿、全量回归 0 失败
可归因于本次删除。条件：主会话完成收尾（版本 3.12.50 提交 + 生成
`.ai/evidence/T-0114/evidence-manifest.v1.yaml` + continuity 重投影）后 AC-05/AC-04 的
"版本与 git HEAD 一致 / 0 failed" 字面达标。

P1 发现数：**0** ｜ P2 发现数：**4**

---

## 二、删除精确性 / 保留保护专项（AC-01 / AC-06 前半）

### 2.1 删除清单：恰 4 项 ✅

`git diff --diff-filter=D --name-only HEAD` 独立复跑输出恰为 4 项（已 git rm 暂存）：

1. `tools/tool_task_queue.py`
2. `tools/tool_eval.py`
3. `tools/loop_vertical_slice.py`
4. `tools/loop_dispatch_role.py`

逐一从 HEAD 读取 4 文件原内容 spot-check：tool_task_queue.py 为薄壳 MCP handler
（`json/os/sys` + handle_analysis 存根），其余 3 个为独立 CLI 入口（docstring 用法
与 T-0111 final-audit 定性一致：0 代码调用方、核心实现分属 loop_core/task_queue.py、
loop_core/evals.py、loop_core/role_dispatch）。定性成立，无误删。

### 2.2 保留保护：run_* 2 个存在未动 ✅

- `agents/security-engineer/scripts/run_security_scan.py`、`agents/quality-engineer/scripts/run_quality_gates.py`
  均存在；`git diff HEAD -- agents/` 为空（零改动）。
- `tools/server.py` 子进程契约独立核对：`:38 _run_quality_gates` / `:41 script =
  run_quality_gates.py` / `:58 _run_security_scan` / `:61 script = run_security_scan.py` /
  `:506` / `:508` 分发点 —— 全部 LIVE（developer 声称的 41/61/506/508 与实际一致）。
- `tools/*.py` 其余 26 个零改动（diff-filter=D 仅 4 项实证 + manifest==disk 断言）。

### 2.3 hooks/ 与治理内核：零触碰 ✅

- `git diff HEAD -- hooks/` 为空（独立复跑，输出空、无 untracked hooks 文件）。
- 治理内核唯一触碰点：`loop_core/capability_registry.py` — 仅 TOOL_CAPABILITY_MANIFEST
  删 4 条目（loop_dispatch_role / loop_vertical_slice / tool_eval / tool_task_queue）+
  头注释 "30 个"→"26 个"。无任何逻辑/判定改动，fail-closed 语义不变。
- `.ai/gates.yaml`（+64 行）、`.ai/task_graph.yaml`（+13 行）改动经核对均为治理登记：
  `G-T-0114-REQUIREMENTS` gate（approval_text "B"、allowed_paths/forbidden_actions/evidence_required
  与任务卡一致）+ task_graph T-0114 节点。属主会话登记记录，非生产代码。
- 历史证据 `.ai/evidence/`：developer 仅新增 T-0114/ 下文件（approval-evidence.json、
  commands.md、compile-evidence.json、execution-evidence.json、fixes/removal-execution.md）。
  另有两个自动生成物 diff 需说明（见五、发现-4）：conformance-report.json（仅
  generated_at 时间戳，测试重生成）与 guard-events.jsonl（守护观测日志自动追加，
  含 check_type "death" 事件 —— 正是删除触发守护的运行时留痕），均为机制自产物，
  非手工改动。

## 三、引用同步核对（AC-02 / AC-03）

### 3.1 注册表 26/26 双向零缺口 ✅（独立断言）

独立执行（非复述 developer 输出）：

```
manifest: 26  disk: 26
missing (disk not in manifest): []
orphan  (manifest not on disk): []
```

TOOL_CAPABILITY_MANIFEST 键集与 `tools/*.py` 模块名集合完全相等，26=26，零缺口。

### 3.2 server.py 零引用 ✅

`grep -n -E "tool_task_queue|tool_eval|loop_vertical_slice|loop_dispatch_role" tools/server.py`
无匹配（exit 1）→ 4 工具 MCP 从未注册属实，server.py 零改动合理（任务卡 scope 中的
"server 注释清理"经 grep 实证无需执行，属预期偏差，T-0113 同款结论）。

### 3.3 全仓 grep（排除 .ai/evidence/ 历史证据）✅

独立复跑全仓 grep（*.py/*.md/*.yaml/*.yml/*.json/*.toml，排除 __pycache__/.git/evidence）：
剩余提及全部可归类为有意保留，**零 import / 零符号引用**：

| 位置 | 性质 |
|------|------|
| `.ai/gates.yaml`（G-T-0114 gate + 旧 gate 禁止动作记录）、`.ai/task_graph.yaml`、`.ai/tasks/T-0081/T-0099/T-0113/T-0114.md` | 治理登记/任务审计记录（T-0113 先例保留） |
| `tests/test_t0109_f5_tool_capability.py:13-14,175-183` | 文件头 docstring 说明 + 删除回归守卫（`importlib.util.find_spec(...) is None` 对 4 模块断言，有意引用） |
| `tests/deep_probe_v35.py:390` | 纯注释（计数来由说明） |

### 3.4 deep_probe_v35 计数更新 ✅

diff 核对：第 6 节 `tool_*.py` 门槛 `>= 19` → `>= 15`，附注释说明（T-0113 删 6 薄壳 +
T-0114 删 tool_task_queue/tool_eval 后剩 18 个；MCP 注册表 26 键为权威计数）。
独立跑探针：**248 passed, 13 failed** —— 与 developer 声明完全一致；13 项失败全部为
既有陈旧预期（EnforcementHub write 门禁、roles 计数、MCP total tools "Expected 20 got 26"
陈旧阈值、模块尺寸 x7、hook 尺寸、agent 契约 x2），tool_*.py 计数项已通过（18>=15），
**零 T-0114 新增失败**。

## 四、测试真实性与相关子集（AC-04 前置）

### 4.1 test_t0109_f5_tool_capability.py 更新核对 ✅

diff 逐项核对：注册表 30→26 共 4 处断言同步（manifest 全覆盖、all_tool_names、
registry_snapshot_sealed_26、audience 分组和）+ 注释/docstring 同步；删除回归守卫
`test_shell_modules_removed` 追加 4 模块（find_spec is None）；文件头 docstring 追加
T-0114 说明。改动均为计数/守卫维护，无断言语义弱化。

### 4.2 相关子集独立重跑 ✅

`pytest tests/test_t0109_f5_tool_capability.py tests/test_capability_registry.py
tests/test_task_queue.py tests/test_evals.py tests/test_t0109_f1_eval_model.py
tests/test_dispatcher.py tests/test_role_isolation.py
tests/test_runtime_dispatch_integration.py tests/test_mcp_capability.py -q`
→ **200 passed**（11.27s），与 developer 声明精确一致（含 26/26 断言 + 删除守卫 +
loop_core 实现直测）。

### 4.3 compile ✅

compile-evidence.json：87/87 编译通过（exit 0），独立抽查
`py_compile capability_registry/server/test_t0109_f5/test_deep_probe_v35` 对应 4 文件
为本次改动面，无语法问题。

## 五、全量回归独立结果（我的独立运行）

`C:/Python312/python.exe -m pytest tests/ -q`（独立运行，382s）：

```
5 failed, 4169 passed, 64 skipped, 12 xfailed
```

developer 执行窗口报告为 2 failed；我本次运行发现 5 failed。逐项独立归因（关键：
用干净 HEAD worktree（6e030e6）对照复跑同一批）：

| 失败测试 | 工作区 | 基线 HEAD worktree | 归因 |
|----------|--------|---------------------|------|
| test_deployment_quality_checker::test_runtime_report_is_simulated_and_fail_closed | FAIL | **FAIL** | 既有环境/模拟失败（T-0111/T-0113 同款），非本任务 |
| test_t0108_fixes::test_validate_state_still_passes_on_repo | FAIL | **FAIL** | 基线即失败（worktree 侧 drift .ai/ACCEPTANCE.md）；工作区侧 drift 源为 .ai/version-manifest.yaml（版本 bump 未重投影）→ 既有/收尾态，非删除引入 |
| test_t0108_fixes::test_existing_verdicts_unchanged_on_repo | FAIL | **FAIL** | 同上（PROJECT_CONTINUITY_SOURCE_DRIFT） |
| test_manifest_t0095::test_manifest_exists_and_handoff_reference_is_real | FAIL | PASS | 未提交 HANDOFF.md 引用尚不存在的 `.ai/evidence/T-0114/evidence-manifest.v1.yaml`（T-0113 manifest 存在故基线过）→ 主会话收尾生成后自愈（developer 已声明此遗留项） |
| test_release::test_pyproject_version_matches_git_head | FAIL | PASS | pyproject=3.12.50 vs git HEAD=3.12.49 —— 版本 bump 已写全部 8 载体但未提交（"先 bump 再提交"流程态）→ 提交后自愈 |

**结论：0 项失败可归因于 T-0114 删除本身。** 3 项基线即失败（含 developer 报告的 2 项
中可复现的 1 项），另 2 项为收尾态瞬态（bump 未提交、evidence-manifest 未生成），
与 developer 声明的差异源于其运行后主会话的 3 项工作区改动（版本载体写 3.12.50、
HANDOFF.md 指向 T-0114 manifest、continuity 未重投影），非删除引入。

## 六、AC 逐项裁决

| AC | 裁决 | 依据 |
|----|------|------|
| AC-01 删除恰 4 个（diff-filter=D） | **PASS** | 独立复跑恰 4 项，无误删无遗漏 |
| AC-02 capability_registry 26/26 双向零缺口 | **PASS** | 独立断言 missing=[] orphan=[]，26=26 |
| AC-03 全仓 grep 无被删工具符号引用（历史证据除外） | **PASS** | 剩余提及仅治理登记/删除守卫/注释，零 import/符号 |
| AC-04 全量回归 0 failed + compile + release check | **条件 PASS** | compile 87/87 ✅；回归 5 failed 全部归因基线/收尾态（0 删除归因）；release check 中版本同步项待提交后达标 |
| AC-05 版本 3.12.50 与 git HEAD 一致 | **条件 PASS** | 8 载体均已写 3.12.50（pyproject/CHANGELOG/README/docs/version-manifest/loop_core/src/plugin.json）；git HEAD 仍 6e030e6 v3.12.49，待主会话提交 |
| AC-06 独立审查 GO（hooks/ 零改动 + run_* 保留） | **PASS（条件 GO）** | hooks/ diff 空；run_* 存在未动 + server 契约 LIVE；GO 附带收尾条件见一 |

## 七、发现清单

**P1（阻断）：0 项**

**P2（4 项，均非删除缺陷，交主会话收尾）：**

1. **全量回归 delta**：developer 报告 2 failed，审查时工作区为 5 failed —— 差额 3 项
   （test_release 版本同步 + test_t0108 两 validate_state）由主会话运行后的版本 bump
   （未提交、continuity 未重投影）引入，提交/重投影后自愈。无删除归因失败。
2. **`.ai/evidence/T-0114/evidence-manifest.v1.yaml` 未生成**：HANDOFF.md:110 已引用，
   test_manifest_t0095 因此 FAIL；主会话收尾生成后自愈（T-0104~T-0113 同款模式）。
3. **版本 bump 3.12.50 未提交**：test_pyproject_version_matches_git_head FAIL；
   按项目"先 bump 再提交"约定，提交 v3.12.50 后自愈（AC-05 字面达标依赖此）。
4. **自动生成物 diff（信息项，非违规）**：`.ai/evidence/T-0087/contract-planes/
   conformance-report.json`（仅 generated_at 重生成）与 `.ai/evidence/observability/
   guard-events.jsonl`（守护事件自动追加，含删除触发的 check_type "death" 事件）——
   机制自产物，非手工修改；guard-events 追加恰是删除执行期间守护健康检查的实证。

## 八、总结论

T-0114 删除执行质量达标：**4 个 B 组死工具删除精确、注册表 26/26 双向零缺口、
零悬挂符号引用、hooks/ 零改动、run_* 2 个保留未动（server 子进程契约 LIVE）、
治理内核仅 manifest 数据面触碰、测试更新真实且相关子集 200 passed 独立复现、
全量回归 0 失败归因于本次删除**（4169 passed / 5 failed 全部归因基线既有或主会话
收尾态）。deep_probe 248/13 与声明一致，tool 计数更新消除新增失败。

**GO（条件性）**：主会话完成 ① 提交 v3.12.50（版本与 git HEAD 一致）② 生成
T-0114 evidence-manifest.v1.yaml ③ continuity 重投影（version-manifest drift 消除）
后，AC-04/AC-05 字面达标，T-0114 闭环。回滚点 6e030e6 完整保留（4 文件可
`git checkout 6e030e6 -- <file>` 恢复）。
