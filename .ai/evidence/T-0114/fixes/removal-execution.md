# T-0114 死工具删除执行 — 删除清单 / 引用同步 / 保留保护 / 测试 / 约束自查

日期：2026-08-03
任务卡：`.ai/tasks/T-0114.md`；复核依据：`.ai/evidence/T-0111/fixes/final-audit.md`
基线提交：6e030e6（v3.12.49，回滚点）

## 1. 删除清单（精确 4 项，AC-01）

`git diff --cached --name-status --diff-filter=D` 恰为 4 项：

| # | 文件 | 定性（T-0111 final-audit） |
|---|------|------------------------------|
| 1 | `tools/tool_task_queue.py` | 死壳确认（实现 = `loop_core/task_queue.py`，test_task_queue.py 覆盖）；MCP 未注册 |
| 2 | `tools/tool_eval.py` | 0 调用方独立 CLI（核心 = `loop_core/evals.py`，test_evals.py 覆盖） |
| 3 | `tools/loop_vertical_slice.py` | 0 调用方独立 CLI |
| 4 | `tools/loop_dispatch_role.py` | 0 调用方独立 CLI（role dispatch 实经 loop_core/role_dispatch + dispatcher） |

## 2. 引用同步表（删除后零悬挂引用，AC-03）

| 位置 | 动作 | 结果 |
|------|------|------|
| `loop_core/capability_registry.py` | manifest 删 4 条目（loop_dispatch_role / loop_vertical_slice / tool_eval / tool_task_queue）+ 头注释 30→26 | 26/26 双向零缺口 ✅ |
| `tools/server.py` | grep 实证 `_dispatch`/`TOOLS`/注释**零引用**（4 工具 MCP 从未注册）→ 零改动 | ✅（内联键仍 LIVE，测试断言） |
| `tests/test_t0109_f5_tool_capability.py` | 计数 30→26（4 处断言 + 4 处注释/docstring）；`test_shell_modules_removed` 追加 4 模块删除回归守卫（find_spec None）；文件头 docstring 追加 T-0114 说明 | 全绿 ✅ |
| `tests/deep_probe_v35.py` | 第 6 节 `tool_*.py` 计数门槛 19→15（删 2 个 tool_* 后 20→18；T-0113 同款探针维护先例）；MCP `expected_tools`/`TOOLS`（注册表键）保留不动 | 13 FAIL 与基线同级 ✅ |
| `tests/`（其余） | grep 零引用（test_task_queue/test_evals/test_dispatcher 等均为 loop_core 实现直测，不受影响） | ✅ |
| `docs/` | grep 零引用 → 无需改动 | ✅ |
| `.ai/README.md` | grep 零引用 → 无需改动 | ✅ |
| `pyproject.toml` | 检查：无入口引用 → 无需改动 | ✅ |
| `loop_core/server.py` | 不存在（server 实为 `tools/server.py`）→ 无操作 | ✅ |

**保留提及（约束保护区，均非 import/符号引用）**：
- `.ai/evidence/` 历史证据（T-0081~T-0113）：硬约束 3 保留不动 ✅
- `.ai/gates.yaml:1994,3925,3973-3974` / `.ai/task_graph.yaml:108,1289-1290` /
  `.ai/tasks/T-0081.md、T-0099.md、T-0113.md`：治理登记/任务审计记录（T-0113 先例保留）✅
- `CHANGELOG.md:165,171`（v3.12.26 历史条目，vertical_slice 契约平面化指
  tests/vertical_slice 平面，非本工具）：版本载体由主会话统一处理 ✅
- `tests/test_t0109_f5_tool_capability.py:175-184`：删除回归守卫（有意引用）✅

## 3. 保留保护断言（硬约束 2）

| 保留项 | 状态 |
|--------|------|
| `agents/security-engineer/scripts/run_security_scan.py` | ✅ 存在未动（server.py:61 子进程契约 + :508 分发点 LIVE；test_security_scan_whitelist 等全绿） |
| `agents/quality-engineer/scripts/run_quality_gates.py` | ✅ 存在未动（server.py:41 子进程契约 + :506 分发点 LIVE；test_quality_gates 全绿） |
| `tools/*.py` 其余 26 个 | ✅ 未动（diff-filter=D 仅 4 项实证） |

## 4. 任务卡偏差说明（重要）

任务卡/gate scope 写「TOOLS/注释清理」——**实际 grep 实证 server.py 对 4 个被删
工具零引用**（T-0111 定性「MCP 未注册」成立），故 server.py 零改动。这与
T-0113 的「_dispatch 不引用被删模块」结论一致，属预期内。

`tests/deep_probe_v35.py` 第 6 节新增 1 项 FAIL（`MCP tools >= 20 — Found 18`，
门槛 `>= 19`，删 2 个 tool_* 后 20→18）：按 T-0113 同款探针维护先例将门槛
同步为 `>= 15` 并注释计数来由，恢复与 HEAD 基线同级（13 FAIL，全为既有陈旧
预期）。**没有改动任何断言语义/注册表键/测试门槛语义**，仅同步陈旧数字。

## 5. 测试结果

| 项 | 结果 |
|----|------|
| 双向零缺口断言（manifest 26 = tools/*.py 26） | ✅ missing=[] orphan=[] |
| 相关测试子集（f5 + capability_registry + task_queue + evals + f1_eval + dispatcher + role_isolation + runtime_dispatch + mcp_capability） | ✅ **200 passed** |
| server MCP 执行路径（test_live_acceptance + test_mcp_agent_runtime） | ✅ **44 passed, 3 skipped** |
| compileall（4 个改动文件：capability_registry / server / f5 / deep_probe） | ✅ COMPILE OK |
| deep_probe_v35 探针 | 248 passed / 13 FAIL，与 T-0113 基线（13 FAIL）同级；13 项全部为既有陈旧预期（MCP total tools Expected 20 got 26、模块尺寸、hook 尺寸、agent 契约等），零新增 |
| 全量 pytest | 4172 passed / 64 skipped / 12 xfailed；**2 failed 均经 HEAD worktree(6e030e6) 对照为既有/环境失败**：① `test_deployment_quality_checker::test_runtime_report_is_simulated_and_fail_closed`（HEAD 即失败，T-0113 同款）；② `test_manifest_t0095::test_manifest_exists_and_handoff_reference_is_real`（主会话 HANDOFF.md 预存改动引用尚未生成的 T-0114 evidence-manifest，主会话收尾生成后自愈） |
| hooks/ 变更 | `git diff HEAD -- hooks/` = 空（零改动实证）✅ |

## 6. 约束自查（硬约束 1-5）

| 约束 | 自查 |
|------|------|
| 1. hooks/ 零改动；治理内核判定零触碰 | ✅ hooks/ diff 为空；gates.yaml/task_graph.yaml 审计记录未动（保留提及） |
| 2. 删除清单精确 4 项；run_* 保护 | ✅ diff-filter=D 恰 4；§3 保留断言全过（run_security_scan/run_quality_gates 存在 + server.py:41/61/506/508 契约 LIVE） |
| 3. 历史证据 `.ai/evidence/` 零改动 | ✅ 本任务仅新增 T-0114/ 下 2 个证据文件（commands.md、fixes/removal-execution.md） |
| 4. 写路径仅限任务卡 allowed_paths | ✅ 写路径：tools/（4 删）、loop_core/capability_registry.py、tests/（2 文件）、.ai/evidence/T-0114/ |
| 5. 版本文件不改（bump 主会话执行） | ✅ pyproject.toml / CHANGELOG.md / 版本载体零改动（CHANGELOG 历史条目未动） |

## 7. 遗留事项（交主会话/后续）

1. **版本 bump 3.12.50**（8 载体原子写，先 bump 再提交）——硬约束 5，主会话执行。
2. **生成 `.ai/evidence/T-0114/evidence-manifest.v1.yaml`**（HANDOFF.md:110 已引用；
   T-0104~T-0113 模式为主会话收尾生成）——生成后
   `test_manifest_t0095::test_manifest_exists_and_handoff_reference_is_real` 自愈。
3. 全量回归 2 项既有失败（§5）与 T-0111/T-0113 基线一致，非本任务范围；其中
   `test_runtime_report_is_simulated_and_fail_closed` 建议后续任务评估修复。
4. 回滚：`git checkout 6e030e6 -- <4 个文件>` 可恢复（删除前提交点完整）。
