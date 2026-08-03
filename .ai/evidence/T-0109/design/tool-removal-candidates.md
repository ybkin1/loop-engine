# T-0109 F5 死工具候选清单 — 调用图证据（只收集证据，删除待用户独立 gate）

日期：2026-08-03
状态：**仅证据收集，零删除**。删除动作由用户独立 gate 批准后执行
（T-0109 硬约束④：不执行任何工具删除；删除建议落入 T-0111 终态审计）。

## 方法

对每个候选工具执行全仓调用图 grep（代码 import / 引用 / MCP 注册 /
文档引用），范围：`--include="*.py"`（排除 `__pycache__`/`tests/`/`.ai/` 证据
目录）加 docs/、skills/、server.py 注册表核对。

## 候选 A：6 个薄壳（本轮已消除委托链，0 代码 importers —— 最高优先删除候选）

T-0109 薄壳消除：`tools/server.py` `_dispatch` 不再 import 这 6 个模块
（委托逻辑内联进注册表 / evidence 收敛至 loop_core），模块文件保留未删。

| 候选 | 消除方式 | 调用图证据（grep 实证） | 删除后影响 |
|------|----------|--------------------------|------------|
| `tools/tool_quality_gates.py` | server.py `_run_quality_gates` 内联（子进程目标不变，输出逐字节等价） | 唯一代码 import 方 `tools/server.py:365` 已移除；其余：docs/06-delivery.md（文档）、tests/deep_probe_v35.py（字符串 import 冒烟）、T-0082/T-0085 历史证据 | 零（MCP 行为等价，测试覆盖） |
| `tools/tool_security_scan.py` | server.py `_run_security_scan` 内联 | 同上（原 server.py:367）；T-0082 已标记 DEPRECATED | 零 |
| `tools/tool_dependency_analysis.py` | server.py `_run_dependency_analysis` 内联 | 同上（原 server.py:370） | 零 |
| `tools/tool_contract_validate.py` | server.py `_run_contract_validate` 内联 | 同上（原 server.py:373；顺带移除原文件 376 行死 return 重复行） | 零 |
| `tools/tool_cost_tracker.py` | server.py `_run_cost_report` 内联 | 同上（原 server.py:383） | 零 |
| `tools/tool_evidence_chain.py` | 证据链三处收敛：server.py `_run_evidence_verify/_run_evidence_freeze` 直调 `loop_core.evidence_chain`（verify_chain_yaml/freeze_file_yaml，行为等价测试） | 唯一代码 import 方 `tools/server.py:377-382` 已移除；T-0105 证据（q4 双副本） | 零（输出为完整校验 dict，overall/issues 键保持） |

**一个 gate 周期无引用实证说明**：T-0109 本任务内 grep 已确认 0 代码
importers；"一个完整 gate 周期无引用"需 T-0109 gate 批准 → T-0110/T-0111
期间（下一 gate 周期）复核仍 0 引用后，删除动作才具备完整实证。建议删除
动作随 T-0111「注册表终态审计：无死工具残留」gate 一并批准。

## 候选 B：仅静态弱引用（manifest/文档/自身，建议 gate 周期实证后删）

| 候选 | 引用面（grep 实证） | 判断 |
|------|---------------------|------|
| `tools/tool_task_queue.py` | 仅 `loop_core/capability_registry.py` manifest（本任务新增）+ 历史文档；无代码调用方；实际实现为 `loop_core/task_queue.py`（Dashboard/executor 消费） | MCP 未注册（server.py TOOLS 无 loop_task_queue）；CLI/HANDLERS 无消费方 → 死壳候选 |
| `tools/tool_eval.py` | manifest + 自身 + T-0092 历史证据；tests/ 无引用 | CLI 独立运行器（eval 套件），可能被 CI/人工调用 → 需 gate 周期实证 |
| `tools/loop_vertical_slice.py` | manifest + 自身 + T-0083 历史证据；无代码调用方 | 独立 CLI → 需 gate 周期实证 |
| `tools/loop_dispatch_role.py` | manifest + 自身；无代码调用方（role dispatch 实际经 loop_core/role_dispatch + dispatcher） | 独立 CLI → 需 gate 周期实证 |

## 候选 C：legacy 脚本（不在本任务 allowed_paths，未动；收敛方向记录）

| 候选 | 引用面 | 判断 |
|------|--------|------|
| `scripts/evidence_chain.py` | 原唯一调用方 tools/tool_evidence_chain.py 已消除；逻辑已收敛至 `loop_core.evidence_chain`（verify_chain_yaml/freeze_file_yaml 行为等价）；仅 loop_core 注释/历史证据引用 | legacy CLI；建议后续任务（T-0110+）收敛为 loop_core CLI 壳或删除（需 gate） |
| `scripts/security_scan.py` | 自标 DEPRECATED（"Use loop_core.security_scanner.scan_security()"）；仅 run_security_scan.py 规则表注释提及 | legacy CLI；三处（loop_core/agent 脚本/tools 壳）合并的收敛方向 = loop_core；输出 schema 契约变更需独立 gate（见 f5-tool-capability.md 遗留②） |
| `agents/security-engineer/scripts/run_security_scan.py` | DEPRECATED 头（"Use loop_core.security_scanner"）；但仍被 server.py `_run_security_scan` 子进程调用（输出 schema security_report/v1 负载性，enforcement 消费方无） | 保留（当前 MCP 契约依赖其输出形态）；收敛需契约变更 gate |
| `agents/quality-engineer/scripts/run_quality_gates.py` | LEGACY WRAPPER（B4 已收敛：内部调 loop_core.static_analyzer + security_scanner 折入 quality_report.json）；server.py `_run_quality_gates` 子进程调用 | 保留（quality_report.json 为 enforcement hook 消费链）；薄壳消除后仍为唯一入口 |

## 非候选（有活引用，明确保留）

tool_inbox / tool_planner（test_t0105_batch3 覆盖）、tool_registry_status
（test_tool_registry_status.py）、tool_dashboard（test_dashboard.py）、
loop_metrics（governance_metrics tool_name + test_governance_metrics）、
loop_guard_health（loop_self_audit.py:276 子进程调用）、loop_self_audit
（test_self_audit_llm.py import）、loop_onboard（CLI 安装流程 +
docs/06-delivery）、mcp_agent_runtime（server.py loop_dispatch_agents）、
loop_execute_phase（server.py:572 注册 + 自身 CLI）。

## 独立 gate 建议

1. **gate 1（随 T-0109 closeout）**：批准候选 A 6 薄壳的"注册表去引用"事实
   （本轮已完成，无行为变化）；文件删除动作与 gate 2 合并执行。
2. **gate 2（随 T-0111 终态审计）**：候选 A 删除 + 候选 B 逐项确认
   （gate 周期实证：T-0109→T-0111 间 0 引用）+ 候选 C 收敛决策
   （contract 变更需独立批准）。
