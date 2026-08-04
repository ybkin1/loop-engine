# T-0113 独立审查报告 — 死工具删除执行（A 组 6 薄壳 + C 组 2 legacy）

- 审查者：independent-reviewer（fresh context 子代理）
- 日期：2026-08-03（会话时区）/ 证据文件时间 2026-08-04
- 基线提交：`3623584`（v3.12.48，T-0111 closeout）
- 审查对象：任务卡 `.ai/tasks/T-0113.md`；developer 证据 `commands.md`、`fixes/removal-execution.md`
- 审查方式：全部结论独立复验（git diff / 读代码 / python 断言 / grep / 全量 pytest / HEAD worktree 对照），不复述 developer 证据
- 审查范围：只读 + 仅写本文件

---

## 一、裁决

**裁决：GO（通过，附条件说明见下）**

- AC-01（8 文件删除）：**PASS**（独立复验）
- AC-02（manifest 30/30 双向零缺口）：**PASS**（独立复验）
- AC-03（全仓无被删符号引用）：**PASS**（独立复验）
- AC-04（全量回归 0 failed）：**条件 PASS** — 独立全量回归 5 failed，其中 2 项 HEAD 基线即失败（既有）、3 项为工作区在途状态（主会话版本 bump 未提交 + 预存 HANDOFF 改动）引发，**0 项与删除相关**（逐项 HEAD worktree 对照，见 §四）
- AC-05（版本 3.12.49 == git HEAD）：**待提交** — 工作区 8 载体已全部 3.12.49，HEAD 仍 3.12.48（bump-先于-提交为任务卡既定流程，提交后自愈）
- AC-06（独立审查 GO + hooks/ 零改动 + 保留保护）：**PASS**

---

## 二、删除精确性 / 保留保护专项（AC-01，最高优先）

### 2.1 删除清单：恰 8 项 ✅

独立执行 `git diff --diff-filter=D HEAD --name-only`，恰为 8 个文件：

| # | 文件 | 组 |
|---|------|-----|
| 1 | `tools/tool_quality_gates.py` | A |
| 2 | `tools/tool_security_scan.py` | A |
| 3 | `tools/tool_dependency_analysis.py` | A |
| 4 | `tools/tool_contract_validate.py` | A |
| 5 | `tools/tool_cost_tracker.py` | A |
| 6 | `tools/tool_evidence_chain.py` | A |
| 7 | `scripts/evidence_chain.py` | C |
| 8 | `scripts/security_scan.py` | C |

删除总计 522 行。删除内容复核（`git show HEAD:<file>`）：A 组均为自标 DEPRECATED 的纯 subprocess 委托薄壳；C 组 `scripts/security_scan.py` 头部自标 DEPRECATED（"Use loop_core.security_scanner"）。无任何唯一逻辑随删除丢失（委托目标均为保留的 agent 脚本 / loop_core 实现，且 server.py 内联 helper 与薄壳 era 输出形态等价——测试断言覆盖）。

### 2.2 保留保护：6 项全部存在未动 ✅

独立 `ls` 验证（全部存在，且不在任何 git diff 中）：

- `agents/security-engineer/scripts/run_security_scan.py` ✅（未动）
- `agents/quality-engineer/scripts/run_quality_gates.py` ✅（未动）
- B 组 `tools/tool_task_queue.py` / `tools/tool_eval.py` / `tools/loop_vertical_slice.py` / `tools/loop_dispatch_role.py` ✅（4 个全部未动）

**server.py 子进程契约 LIVE**：`_run_quality_gates` 引用 `agents/quality-engineer/scripts/run_quality_gates.py`（**server.py:41**）、`_run_security_scan` 引用 `agents/security-engineer/scripts/run_security_scan.py`（**server.py:61**）。任务卡写 38/58——行号因头部注释块扩展 +3 而偏移，契约本身完整存在，无功能差异。

### 2.3 hooks/ 零改动、治理内核零触碰 ✅

- `git diff HEAD -- hooks/` 输出为空（独立复验，exit 0 无内容）。
- 治理内核：`loop_core/` 仅 `capability_registry.py` 修改（manifest 条目 + 头注释），其余零改动；fail-closed 语义未触碰。
- hooks 白名单一致性：更新后 `tests/test_t0109_f5_tool_capability.py::test_hooks_zero_changes` 断言 hooks diff == []，随 131 子集通过。

### 2.4 历史证据 `.ai/evidence/` 零改动（附注）⚠️ 轻微

`git status .ai/evidence/`：除新增 `T-0113/`（untracked）外，另有 2 个**自动生成物**在途修改（均未暂存、非 T-0113 写路径产物）：
- `.ai/evidence/T-0087/contract-planes/conformance-report.json`：仅 `generated_at` 时间戳再生成（1 行）。
- `.ai/evidence/observability/guard-events.jsonl`：追加 69 行 guard 事件日志（append-only 可观测日志）。

两者均为环境/钩子自动产物、非实质证据改动。developer 自查 §3「仅新增 T-0113/ 下 2 个证据文件」措辞不精确（未提及上述 2 个自动产物），但无实质影响。记 P3-1。

---

## 三、引用同步核对（AC-02 / AC-03）

### 3.1 capability_registry 30/30 双向零缺口 ✅（独立 python 断言）

```
manifest count: 30    disk count: 30
missing (disk 有 manifest 无): []     orphan (manifest 有 disk 无): []
```

- HEAD 基线 manifest 独立计数 = **36**（`git show HEAD:... | grep -c`）；当前 30 → 恰删 6 条目（tool_contract_validate / tool_cost_tracker / tool_dependency_analysis / tool_evidence_chain / tool_quality_gates / tool_security_scan），头注释 36→30。
- 任务卡/gate 文字写「36 → 28（8 条目）」，实际 36 → 30：C 组 2 个 scripts 从无 manifest 条目（manifest 仅覆盖 tools/*.py）。developer 已在 removal-execution.md §4 明示偏差；**AC-02 不变式（双向零缺口）在 30/30 下成立**。记 P3-2（仅措辞层面）。

### 3.2 server.py：零被删模块引用，7 个内联键 LIVE ✅

- `grep tool_quality_gates|...|tool_evidence_chain tools/server.py` → **0 命中**（无 import、无符号引用）。
- 7 个 MCP 内联键抽查：TOOLS 注册表 `tools/server.py:162-229`（quality_gates_run / security_scan_run / dependency_analysis / contract_validate / evidence_verify / evidence_freeze / cost_report）全部存在；`_dispatch` 分派分支 `:505-519` 全部存在；_run_* helper 全部存在。server.py 的 diff 仅为 docstring/注释清理，零功能代码改动。
- `test_server_no_longer_imports_shell_modules` 断言 server.py 源码无 6 薄壳 import——随子集通过。

### 3.3 全仓 grep：剩余提及全部在约束保护区 ✅

被删符号（6 工具 + 2 scripts 路径）全仓扫描（排除 .git/），非证据区命中逐条核查：

| 位置 | 性质 | 判定 |
|------|------|------|
| `tests/test_t0109_f5_tool_capability.py:165-176` | `test_shell_modules_removed` 删除回归守卫（`find_spec(...) is None` ×8） | 有意引用 ✅ |
| `hooks/scripts/loop_enforcement_constants.py:33-34` | M-3 历史登记注释（`tool_evidence_chain.py:21,41` 等） | 注释，hooks/ 零改动 ✅ |
| `loop_core/evidence_chain.py:472-475,520,560,587` | T-0109 收敛溯源注释（`scripts/evidence_chain.py` 提及） | 注释非符号，不在 allowed_paths ✅ |
| `agents/security-engineer/scripts/run_security_scan.py:390,392` | scanner_self 排除表路径字符串（`scripts/security_scan.py`、`tools/tool_security_scan.py`） | 允许清单字符串，对不存在文件 no-op ✅ |
| `.ai/gates.yaml:458`（T-0025 历史记录）、`:3914-3915`（T-0113 gate allowed_paths） | 审计记录 | ✅ |
| `.ai/evidence/`、`.ai/tasks/`、`.ai/evidence/T-0113/` | 历史证据 + 任务卡 | 硬约束保留区 ✅ |

**import/符号引用专项**：全仓 `(import|from) (tool_*|scripts.*)` 正则扫描（排除 .ai/evidence、.ai/tasks）→ **0 命中**。无任何可执行代码引用被删模块。

### 3.4 测试与探针同步 ✅

- `tests/deep_probe_v35.py`：`TOOL_MODULES` 删 6 项；第 6 节 MCP `expected_tools` 保留 7 个**内联注册表键**（quality_gates_run 等）——正确（这些是 LIVE 键，非被删模块）。
- `tests/test_t0109_f5_tool_capability.py`：36→30 共 4 处（manifest 覆盖 / all_tool_names / snapshot sealed / audience 分组）；`TestThinShellElimination`→`TestInlineDispatchLive`（5 个等价测试改 LIVE 断言，注入 fake subprocess 输出断言 `{"fake":"payload","overall":"PASS","n":1}`）；`TestEvidenceChainConvergence` 3 个测试改 loop_core 直测；域抽查 security→dashboard（tool_security_scan 已删，域内无替代）；`test_hooks_zero_changes` 断言 hooks diff 为空。diff 复核与声明一致。

### 3.5 文档同步 ✅

- `docs/06-delivery.md`：2.3 表删 6 行 → 单行 `tools/server.py`（注明含 6 内联键、T-0113 薄壳已删）；2.7 删 `scripts/evidence_chain.py` 行。
- `docs/ops-handoff.md`：安全监控命令改为 `python agents/security-engineer/scripts/run_security_scan.py --project-root . --json`——已独立验证该脚本支持 `--json` 参数（`run_security_scan.py:938`）✅。
- `README.md` / `.ai/README.md` / `docs/` 其余：grep 无被删工具名（0 命中）✅；`pyproject.toml` 无入口引用（0 命中）✅。

---

## 四、测试与全量回归独立结果

### 4.1 相关子集（developer 声称 131 passed）✅ 独立复验

```
C:/Python312/python.exe -m pytest tests/test_t0109_f5_tool_capability.py \
  tests/test_evidence_chain.py tests/test_quality_gates.py \
  tests/test_security_scan_whitelist.py tests/test_security_dependency_scan.py -q
→ 131 passed in 1.49s（与 developer 记录一致）
```

### 4.2 compileall ✅

`compileall loop_core/capability_registry.py tools/server.py tests/test_t0109_f5_tool_capability.py tests/deep_probe_v35.py` → COMPILE OK。

### 4.3 全量回归独立重跑（约 4.8 分钟）

```
C:/Python312/python.exe -m pytest tests/ -q
→ 4169 passed, 64 skipped, 12 xfailed; 5 failed（0 删除引入）
```

developer 声称「2 failed 均既有」；独立重跑出现 **5 failed**（3 项为 developer 运行后的工作区在途状态变化引入，非删除引入）。逐项归因（全部经 `git worktree add` 于基线 3623584 的干净 HEAD 对照）：

| # | 失败测试 | 当前工作区原因 | HEAD 基线复验 | 归因 |
|---|---------|---------------|--------------|------|
| 1 | `test_deployment_quality_checker::test_runtime_report_is_simulated_and_fail_closed` | — | **HEAD 即失败** | 既有失败（与 developer 判断一致），非 T-0113 |
| 2 | `test_manifest_t0095::...::test_manifest_exists_and_handoff_reference_is_real` | 主会话预存 HANDOFF.md 改动引用尚未生成的 T-0113 evidence-manifest | **HEAD 通过** | 在途主会话状态，非 T-0113 删除 |
| 3 | `test_release::TestAC01VersionSync::test_pyproject_version_matches_git_head` | pyproject=3.12.49 vs git HEAD=3.12.48（版本 bump 未提交） | **HEAD 通过** | 在途 bump（任务卡既定「先 bump 再提交」流程），提交后自愈 |
| 4 | `test_t0108_fixes::TestArchiveAndContinuity::test_validate_state_still_passes_on_repo` | `PROJECT_CONTINUITY_SOURCE_DRIFT: .ai/version-manifest.yaml`（在途 bump 使连续性源漂移） | **HEAD 亦失败**（drift: .ai/ACCEPTANCE.md，环境敏感） | 状态敏感既有项，非 T-0113 |
| 5 | `test_t0108_fixes::TestValidateStateRegression::test_existing_verdicts_unchanged_on_repo` | 同上 | **HEAD 亦失败** | 同上 |

附加证据：`.ai/project_continuity.yaml` 与 `.ai/version-manifest.yaml` 的连续性源清单 **0 处提及被删文件**（grep 独立复验），删除在机制上不可能引发连续性漂移；漂移源（.ai/version-manifest.yaml / .ai/ACCEPTANCE.md）与删除无关。

**结论：0 failed 由 T-0113 删除引入**。收集总数 4174 与 developer 运行一致（4172 passed + 2 failed / 4169 passed + 5 failed），差值恰为 3 个在途状态项。AC-04 硬门槛「0 failed」在提交 bump + 生成 evidence-manifest 后可达成，属主会话收尾动作。

---

## 五、发现清单

### P1（阻断）— 0 项

### P2（重要）— 0 项

### P3（轻微/观察，不阻断）— 6 项

1. **P3-1 证据区零改动断言措辞不精确**：`.ai/evidence/` 工作区另有 2 个自动产物在途修改（conformance-report.json 时间戳、guard-events.jsonl 追加 69 行），developer 自查「仅新增 T-0113/ 下 2 个证据文件」未提及；均为自动生成、非实质改动。
2. **P3-2 任务卡/gate 措辞「36→28」与实际「36→30」**：C 组 scripts 从无 manifest 条目；deviation 已由 developer 在 removal-execution.md §4 记录，AC-02 不变式（零缺口）成立，`execution-evidence.json` workstream 文字仍写「36→28」，建议主会话收尾时修正措辞。
3. **P3-3 AC-05 版本一致性待提交**：工作区 8 载体全部 3.12.49（pyproject / README / loop_core、src `__init__.py` / plugin.json / version-manifest / CHANGELOG / 06-delivery），HEAD 仍 3.12.48；`test_release::test_pyproject_version_matches_git_head` 提交后自愈。
4. **P3-4 t0108 两项 validate_state 测试状态敏感**：HEAD 干净 worktree 亦失败（连续性漂移），建议后续任务评估（developer 遗留事项 3 同款）。
5. **P3-5 run_security_scan.py:390-392 排除表含已删文件路径字符串**：no-op 允许清单，清理需 agents/ 授权（developer 遗留事项 5 同款）。
6. **P3-6 server.py 契约行号偏移**：任务卡写 38/58，实际 41/61（注释块扩展 +3），契约本体完整，无功能影响。

---

## 六、总结论

T-0113 死工具删除执行**通过独立审查（GO）**：

- 删除精确性：`diff-filter=D` 恰 8 项（A 组 6 + C 组 2），删除文件均为自标 DEPRECATED 薄壳/legacy，无唯一逻辑丢失；B 组 4 个 + run_* 2 个全部存在未动；server.py:41/61 子进程契约 LIVE；hooks/ diff 为空；治理内核仅 capability_registry 一处。
- 引用同步：manifest 30/30 双向零缺口（HEAD 基线 36，恰删 6）；server.py 零被删模块引用、7 个 MCP 内联键 LIVE；全仓 import/符号级引用 0 命中；docs/deep_probe/测试同步一致。
- 测试：131 子集独立重跑通过；compileall 通过；全量回归 4169 passed / 5 failed——5 项经 HEAD worktree 对照**均非删除引入**（2 项 HEAD 即失败、3 项在途主会话状态），0 failed 硬门槛待主会话提交 bump + 生成 evidence-manifest 后达成。
- 无 P1/P2；P3 观察 6 项均不阻断。
