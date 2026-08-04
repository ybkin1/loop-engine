# T-0111 终态审计：死工具复核 + 注册表终态（AC-04，不执行删除）

日期：2026-08-03
依据：T-0109 `.ai/evidence/T-0109/design/tool-removal-candidates.md`（A/B/C 三组）
方法：对每个候选在当前仓库状态执行调用图 grep（--include="*.py"，排除
__pycache__/tests/.ai 证据目录；另查 docs/、server.py 注册表、capability
manifest）。**本任务只复核 + 建议，不执行任何删除**——删除动作待用户
独立 gate 批准。

## 1. 候选 A：6 个薄壳 —— 复核确认 0 代码 importers（删除建议：高）

| 候选 | 当前引用面（grep 实证） | 复核定性 |
|------|------------------------|----------|
| `tools/tool_quality_gates.py` | server.py 仅注释提及（"原 ...run()"）；capability manifest 元数据；tests/test_t0109_f5 行为等价冒烟 import；tests/deep_probe_v35 字符串表；docs/06-delivery.md 工具目录 | **0 代码 importers 确认**（MCP 行为已内联 `quality_gates_run`） |
| `tools/tool_security_scan.py` | 同上（server.py 内联 `security_scan_run`；agents 脚本路径排除表提及） | **0 代码 importers 确认** |
| `tools/tool_dependency_analysis.py` | 同上（内联 `dependency_analysis`） | **0 代码 importers 确认** |
| `tools/tool_contract_validate.py` | 同上（内联 `contract_validate`） | **0 代码 importers 确认** |
| `tools/tool_cost_tracker.py` | 同上（内联 `cost_report`；constants 注释提及） | **0 代码 importers 确认** |
| `tools/tool_evidence_chain.py` | 同上（server.py 内联 `evidence_verify/evidence_freeze`；loop_core.evidence_chain 注释历史） | **0 代码 importers 确认** |

门禁周期实证（T-0109 → T-0111 间 0 引用）已满足：一个完整 gate 周期内
无任何代码 import。删除影响评估：MCP 注册表（server.py TOOLS）不含这 6
个模块（内联键替代）；删除需同步调整：capability manifest 6 条目、
`tests/test_t0109_f5_tool_capability.py` 冒烟用例、`tests/deep_probe_v35.py`
字符串表、`docs/06-delivery.md` 目录。

## 2. 候选 B：静态弱引用 —— 复核确认（删除建议：中，逐项 gate）

| 候选 | 当前引用面 | 复核定性 |
|------|-----------|----------|
| `tools/tool_task_queue.py` | 仅 capability manifest 元数据；无 tests/docs 引用；MCP 未注册（server.py TOOLS 无 loop_task_queue）；实际实现 = `loop_core/task_queue.py`（test_task_queue.py 覆盖） | **死壳确认**，删除建议最高（B 组内） |
| `tools/tool_eval.py` | manifest + 自身 docstring；tests/docs 零引用；核心 = `loop_core/evals.py`（test_evals.py） | 独立 CLI 运行器（可能被 CI/人工调用）→ 需用户确认无外部调用后删 |
| `tools/loop_vertical_slice.py` | manifest + 自身；tests/docs 零引用 | 独立 CLI → 需用户确认后删 |
| `tools/loop_dispatch_role.py` | manifest + 自身；tests/docs 零引用（role dispatch 实经 loop_core/role_dispatch + dispatcher） | 独立 CLI → 需用户确认后删 |

## 3. 候选 C：legacy 脚本 —— 复核确认（建议分级）

| 候选 | 当前引用面 | 复核定性 |
|------|-----------|----------|
| `scripts/evidence_chain.py` | 0 importers（仅 loop_core.evidence_chain 注释历史 + constants 注释）；逻辑已收敛至 `loop_core.evidence_chain`（verify_chain_yaml/freeze_file_yaml） | legacy CLI → 删除/收敛建议（同 T-0109 结论，待 gate） |
| `scripts/security_scan.py` | 0 importers（自标 DEPRECATED；run_security_scan.py 的排除表提及非调用）；核心 = `loop_core.security_scanner` | legacy CLI → 删除/收敛建议（输出 schema 契约变更需独立 gate） |
| `agents/security-engineer/scripts/run_security_scan.py` | **LIVE**：server.py:58 `_run_security_scan` 子进程目标 + test_security_scan_whitelist/test_security_dependency_scan 加载 | **保留**（MCP 契约 security_report/v1 输出形态依赖） |
| `agents/quality-engineer/scripts/run_quality_gates.py` | **LIVE**：server.py:38 `_run_quality_gates` 子进程目标 + test_quality_gates.py + check_thresholds.py 导入 | **保留**（quality_report.json 为 enforcement 消费链唯一入口） |

## 4. 注册表终态审计（AC-04）

- **36 工具全覆盖**：`tools/*.py` 36 个模块 ↔ `TOOL_CAPABILITY_MANIFEST`
  36 条目，双向零缺口（`all_tool_names()` 实测 36 = 36，无未登记工具
  静默存在、无 manifest 孤儿条目）——`test_t0109_f5::TestToolRegistryCoverage`
  持续断言。
- **候选工具均已复核定性**（上述 A/B/C 全表）：无"未定性"残留。
- **无重复实现（合并清单闭环）**：薄壳消除（A 组 6 项 → server.py 内联/
  loop_core 收敛）、dashboard 四层合并（`status_dashboard.Dashboard is
  dashboard_views.Dashboard`）、证据链三处收敛——均由
  `test_t0109_f5_tool_capability.py`（行为等价 + 单一实现断言）与
  `test_t0110_batch_c` 覆盖，本次复核未见新的重复实现。
- **非候选活引用确认**（保留）：tool_inbox/tool_planner/tool_registry_status/
  tool_dashboard/loop_metrics/loop_guard_health/loop_self_audit/loop_onboard/
  mcp_agent_runtime/loop_execute_phase 均有代码/测试/MCP 注册活引用。

## 5. 删除建议汇总（交用户独立 gate）

| 组 | 候选 | 建议 | 删除时同步调整 |
|----|------|------|----------------|
| A | 6 薄壳 | **删除**（0 importers 实证 + 门禁周期完成；MCP 行为已内联等价） | manifest 6 条目 + f5 冒烟用例 + deep_probe_v35 字符串表 + docs/06-delivery.md |
| B | tool_task_queue | **删除**（死壳，实现在 loop_core.task_queue） | manifest 1 条目 |
| B | tool_eval / loop_vertical_slice / loop_dispatch_role | **删除**（0 调用方；如外部 CI/人工有调用需先声明保留） | manifest 3 条目 |
| C | scripts/evidence_chain.py / scripts/security_scan.py | **删除或收敛为 loop_core CLI 壳**（security_scan 输出契约变更另需 gate） | 文档/注释清理 |
| C | run_security_scan.py / run_quality_gates.py | **保留**（MCP 子进程契约依赖） | 无 |

gate 建议：与 T-0109 gate 2 合并执行（候选 A 删除 + 候选 B 逐项确认 +
候选 C 收敛决策）。
