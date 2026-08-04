# T-0113 死工具删除执行 — 删除清单 / 引用同步 / 保留保护 / 测试 / 约束自查

日期：2026-08-03
任务卡：`.ai/tasks/T-0113.md`；复核依据：`.ai/evidence/T-0111/fixes/final-audit.md`
基线提交：3623584（v3.12.48，回滚点）

## 1. 删除清单（精确 8 项，AC-01）

`git diff --cached --name-status --diff-filter=D` 恰为 8 项：

| # | 文件 | 组 | 定性（T-0111 final-audit） |
|---|------|----|------------------------------|
| 1 | `tools/tool_quality_gates.py` | A 薄壳 | 0 importers；MCP 内联 `quality_gates_run` |
| 2 | `tools/tool_security_scan.py` | A 薄壳 | 0 importers；内联 `security_scan_run` |
| 3 | `tools/tool_dependency_analysis.py` | A 薄壳 | 0 importers；内联 `dependency_analysis` |
| 4 | `tools/tool_contract_validate.py` | A 薄壳 | 0 importers；内联 `contract_validate` |
| 5 | `tools/tool_cost_tracker.py` | A 薄壳 | 0 importers；内联 `cost_report` |
| 6 | `tools/tool_evidence_chain.py` | A 薄壳 | 0 importers；内联 `evidence_verify/freeze` |
| 7 | `scripts/evidence_chain.py` | C legacy | 逻辑收敛 `loop_core.evidence_chain` |
| 8 | `scripts/security_scan.py` | C legacy | 自标 DEPRECATED；核心 `loop_core.security_scanner` |

## 2. 引用同步表（删除后零悬挂引用，AC-03）

| 位置 | 动作 | 结果 |
|------|------|------|
| `loop_core/capability_registry.py` | manifest 删 6 条目（tool_contract_validate / tool_cost_tracker / tool_dependency_analysis / tool_evidence_chain / tool_quality_gates / tool_security_scan）+ 头注释 36→30 | 30/30 双向零缺口 ✅ |
| `tools/server.py` | `_dispatch`/`TOOLS` 检查：**不引用被删模块**（7 个键全部内联 `_run_*` helper）；仅清理 6 处 docstring + 2 处块注释中的已删文件名提及 | 内联键仍 LIVE（测试断言）✅ |
| `tests/test_t0109_f5_tool_capability.py` | 36→30 计数（4 处）；`TestThinShellElimination`→`TestInlineDispatchLive`（5 个等价测试改为 LIVE 断言 + `test_shell_modules_removed` 删除回归守卫）；`TestEvidenceChainConvergence` 3 个等价测试改为 loop_core 直测；域抽查 security→dashboard；hooks 断言语义化 | 全绿 ✅ |
| `tests/deep_probe_v35.py` | `TOOL_MODULES` 删 6 项（第 6 节 MCP `expected_tools` 为**内联注册表键**，保留不动） | ✅ |
| `docs/06-delivery.md` | 2.3 删 6 行 + server.py 行注明内联；2.7 删 `scripts/evidence_chain.py` 行 | ✅ |
| `docs/ops-handoff.md` | 安全监控命令 `scripts/security_scan.py` → `agents/security-engineer/scripts/run_security_scan.py --json` | ✅ |
| `.ai/README.md` | 检查：仅目录级列举，无被删工具名 → 无需改动 | ✅ |
| `pyproject.toml` | 检查：无入口引用 → 无需改动 | ✅ |
| `loop_core/server.py` | 不存在（server 实为 `tools/server.py`，由 tools/ 覆盖）→ 无操作 | ✅ |

**保留提及（约束保护区，均非 import/符号引用）**：
- `.ai/evidence/` 历史证据（T-0082~T-0111）：硬约束 3 保留不动 ✅
- `hooks/scripts/loop_enforcement_constants.py:33-34` 注释（M-3 历史登记）：硬约束 1 hooks/ 零改动 ✅
- `loop_core/evidence_chain.py:472-475,520,560,587` 收敛溯源注释：不在 allowed_paths，注释非符号 ✅
- `agents/security-engineer/scripts/run_security_scan.py:390-392` scanner_self 排除表字符串（tools/tool_security_scan.py、scripts/security_scan.py）：路径允许清单非调用，且 agents/ 不在 allowed_paths；对不存在文件是 no-op ✅
- `.ai/gates.yaml:458`（T-0025 历史 gate 记录）与 `:3914-3915`（T-0113 gate 记录 allowed_paths）：审计记录保留 ✅
- `tests/test_t0109_f5_tool_capability.py:165-176`：删除回归守卫（`find_spec(...) is None`），有意引用 ✅

## 3. 保留保护断言（硬约束 2）

| 保留项 | 状态 |
|--------|------|
| `agents/security-engineer/scripts/run_security_scan.py` | ✅ 存在未动（server.py:58 子进程契约 LIVE；test_security_scan_whitelist / test_security_dependency_scan 全绿） |
| `agents/quality-engineer/scripts/run_quality_gates.py` | ✅ 存在未动（server.py:38 子进程契约 LIVE；test_quality_gates 全绿） |
| B 组 `tools/tool_task_queue.py` | ✅ 未动（待用户确认） |
| B 组 `tools/tool_eval.py` | ✅ 未动（待用户确认） |
| B 组 `tools/loop_vertical_slice.py` | ✅ 未动（待用户确认） |
| B 组 `tools/loop_dispatch_role.py` | ✅ 未动（待用户确认） |

## 4. 任务卡偏差说明（重要）

任务卡/gate scope 写「TOOL_CAPABILITY_MANIFEST 删除 8 条目（36 → 28）」。
**实际：manifest 仅覆盖 tools/*.py 模块**（36 条目 ↔ 36 模块，含 server），
C 组 2 个 scripts 从无 manifest 条目；A 组仅 6 条可删。
故最终态为 **36 → 30（30/30 双向零缺口）**——与复核依据
final-audit「capability manifest 6 条目」一致；AC-02 的不变式是**双向零缺口**，
数字以实测 30/30 为准（`test_t0109_f5::TestToolRegistryCoverage` 持续断言）。

## 5. 测试结果

| 项 | 结果 |
|----|------|
| 双向零缺口断言（manifest 30 = tools/*.py 30） | ✅ missing=[] orphan=[] |
| 相关测试子集（f5 + evidence_chain + quality_gates + security 两文件） | ✅ **131 passed** |
| compileall（4 个改动文件） | ✅ COMPILE OK |
| deep_probe_v35 探针 | 13 FAIL，与 HEAD(3623584) 基线**逐项一致**（陈旧预期：MCP total tools Expected 20 got 26 等），零新增 |
| 全量 pytest | 4172 passed / 64 skipped / 12 xfailed；**2 failed 均经 HEAD worktree 对照为既有失败**：① `test_deployment_quality_checker::test_runtime_report_is_simulated_and_fail_closed`（HEAD 即失败）；② `test_manifest_t0095::test_manifest_exists_and_handoff_reference_is_real`（主会话 HANDOFF.md 预存改动引用尚未生成的 T-0113 evidence-manifest —— 与本任务删除无关，主会话收尾生成 manifest 后自愈） |
| hooks/ 变更 | `git diff HEAD -- hooks/` = 空（零改动实证）✅ |

## 6. 约束自查（硬约束 1-5）

| 约束 | 自查 |
|------|------|
| 1. hooks/ 零改动；治理内核判定零触碰 | ✅ hooks/ diff 为空；loop_enforcement/constants 未动 |
| 2. 删除清单精确 8 项；B 组与 run_* 保护 | ✅ diff-filter=D 恰 8；§3 六项保留断言全过 |
| 3. 历史证据 `.ai/evidence/` 零改动 | ✅ 本任务仅新增 T-0113/ 下 2 个证据文件（commands.md、fixes/removal-execution.md） |
| 4. 写路径仅限任务卡 allowed_paths | ✅ 写路径：tools/（6 删 + server.py）、scripts/（2 删）、loop_core/capability_registry.py、tests/（2 文件）、docs/（2 文件）、.ai/evidence/T-0113/ |
| 5. 版本文件不改（bump 主会话执行） | ✅ pyproject.toml / CHANGELOG.md / 版本载体零改动 |

## 7. 遗留事项（交主会话/后续）

1. **版本 bump 3.12.49**（8 载体原子写，先 bump 再提交）——硬约束 5，主会话执行。
2. **生成 `.ai/evidence/T-0113/evidence-manifest.v1.yaml`**（HANDOFF.md:128 已引用；
   T-0104~T-0111 模式为主会话收尾生成）——生成后
   `test_manifest_t0095::test_manifest_exists_and_handoff_reference_is_real` 自愈。
3. 全量回归 2 项既有失败（§5）与 T-0111 基线一致，非本任务范围；其中
   `test_runtime_report_is_simulated_and_fail_closed` 建议后续任务评估修复。
4. B 组 4 个工具（tool_task_queue/tool_eval/loop_vertical_slice/loop_dispatch_role）
   待用户确认无外部调用后单独删除（每项含 manifest 1 条目同步）。
5. `agents/security-engineer/scripts/run_security_scan.py:390-392` 排除表含已删
   文件路径（scanner_self 允许清单，无功能影响）；如需清理需 agents/ 路径授权。
6. 回滚：`git checkout 3623584 -- <8 个文件>` 可恢复（删除前提交点完整）。
