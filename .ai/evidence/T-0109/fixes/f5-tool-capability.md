# T-0109 F5 工具 capability 化 — 修复证据（AC-04）

日期：2026-08-03
范围：36 工具分组元数据 / audience 分级 / 薄壳消除 / 重复合并（dashboard 四层、
证据链三处、安全扫描三处、缓存同步按实际确认）/ 死工具证据（见
design/tool-removal-candidates.md）

## 改动

### 1. `loop_core/capability_registry.py`（修改，新增工具层注册表）
- 新增 `ToolCapability(name, domain, audience, description)` + 常量
  `AUDIENCE_WORKFLOW/ADVANCED/MAINTAINER` + 14 个 DOMAIN_*。
- `TOOL_CAPABILITY_MANIFEST`：**36 个工具模块全覆盖**（与 tools/*.py
  一一对应；新增工具未登记 → 完整性测试失败，fail-closed）。
- 查询 API：`tool_capability()`（未知 → LookupError）、`tools_by_domain()`、
  `tools_by_audience()`（非法 audience → ValueError）、`all_tool_names()`。
- `build_tool_registry(project_root, seal)`：复用既有 CapabilityRegistry
  （provider_id="tool"，content-addressed version/hash，seal 后不可变）。

### 2. 薄壳消除（6 个纯委托薄壳 → MCP server 注册表）
先 grep 调用方（实证：6 模块唯一代码级 import 方均为 `tools/server.py`
`_dispatch`；其余为 docs 文档 / tests/deep_probe_v35.py 字符串 import 冒烟 /
历史证据文档）→ 再改：
- `tools/server.py` 新增 `_run_quality_gates` / `_run_security_scan` /
  `_run_dependency_analysis` / `_run_contract_validate` / `_run_cost_report`
  （子进程委托目标、超时、错误分支与原薄壳模块 run() **逐字节等价**）；
  `_dispatch` 相应分支改调 helper，不再 import 薄壳模块。
- `evidence_verify` / `evidence_freeze`：`_run_evidence_verify` /
  `_run_evidence_freeze` 直调 `loop_core.evidence_chain`
  `verify_chain_yaml` / `freeze_file_yaml`（证据链三处收敛，见下）。
- 薄壳模块文件**保留未删**（硬约束④：不执行任何工具删除）→ 列入
  tool-removal-candidates.md 候选 A（0 代码 importers，删除待用户独立 gate）。
- 顺带移除原 `_dispatch` contract_validate 分支的死重复 return 行。

### 3. 重复合并
**a. dashboard 四层 → `loop_core/dashboard_views.py` 单一实现**
- 原四层：dashboard_views（DashboardViews）、status_dashboard
  （Dashboard 健康快照）、tools/tool_dashboard.py（MCP 处理器壳）、
  tools/loop_dashboard.py（CLI 壳）。
- `ProjectStatus` / `Dashboard` 逻辑零改动迁移进 dashboard_views.py
  （Dashboard 只读 state.yaml 作呈现；快照写为既有行为）；
  `loop_core/status_dashboard.py` 降级为 **re-export shim**
  （`from loop_core.dashboard_views import Dashboard, ProjectStatus`）——
  消费方（hooks/scripts/session_brief.py、tools/tool_dashboard.py、
  tests/test_status_dashboard.py）import 路径无感兼容。
- 等价实证：`status_dashboard.Dashboard is dashboard_views.Dashboard`；
  test_status_dashboard + test_dashboard 全绿（32 passed）。

**b. 证据链三处 → loop_core.evidence_chain 收敛**
- 原三处：loop_core.evidence_chain（chain_index 信封链）、
  tools/tool_evidence_chain.py（subprocess 壳）、scripts/evidence_chain.py
  （chain.yaml 校验 CLI）。
- `loop_core/evidence_chain.py` 新增 `load_chain_yaml` /
  `verify_chain_yaml` / `freeze_file_yaml`（**verbatim 移植**
  scripts/evidence_chain.py 逻辑：.zcode 安装副本优先的候选路径顺序、
  strict 语义、输出 dict 结构逐字段一致；不可读节点显式 ERROR + BLOCKED，
  fail-closed 不静默跳过）。
- tools/tool_evidence_chain.py 子进程壳消除 → server.py 直调 loop_core。
- `scripts/evidence_chain.py` 不在本任务 allowed_paths，未改动（legacy CLI，
  其逻辑已有 loop_core 单一实现，删除/收敛建议入 tool-removal-candidates
  候选 C）。

**c. 安全扫描三处（按实际确认）**
- 三处 = loop_core/security_scanner.py（canonical）、tools/tool_security_scan.py
  （薄壳）、scripts/security_scan.py（DEPRECATED CLI）。工具壳 → server.py
  注册表内联（子进程目标 run_security_scan.py 不变，输出 schema
  security_report/v1 负载性保持——**重定向 loop_core 会破坏 MCP 输出契约**，
  不做）；scripts/security_scan.py 不在 allowed_paths 未动。
- loop_core 与 agent 脚本双实现的收敛（输出契约变更）列为遗留②，需独立
  gate（T-0110+）。

**d. 缓存同步三处（按实际确认：不构成可合并重复组）**
- 全仓勘察：缓存相关实现为三类**不同机制**——context_packager 进程内 git
  diff 缓存（D4-4）、role_orchestrator 配置 mtime 缓存（B-4-4）、hooks
  auto_sync_to_plugin_cache（hook 零触碰区）。无 tools/ 内"缓存同步三处"
  重复实现，无合并目标；结论记录在案（不制造无意义合并）。

### 4. enforcement 白名单同步（AC-05）→ 见 hook-whitelist.md（单独门禁）

## 测试（tests/test_t0109_f5_tool_capability.py，25 passed）

- **TestToolRegistryCoverage（AC-04）**：tools/*.py（36）== 注册表（36），
  无遗漏无多余；all_tool_names 稳定排序；build_tool_registry sealed 快照
  36 条；未知工具 LookupError。
- **TestToolRegistryGrouping**：36 工具 audience ∈ 三档、domain 非空；
  workflow/advanced/maintainer 三档均非空且互斥覆盖 36；域分组抽查。
- **TestThinShellElimination（薄壳消除后调用测试，行为等价）**：
  注入相同 subprocess.run 假输出 → server._dispatch 与旧薄壳模块 run()
  输出逐字段一致（quality/security/dependency/contract/cost 5 组）；
  server.py 源码不再 import 6 薄壳（消除实证）；薄壳文件仍可独立导入
  （deep_probe 兼容）。
- **TestEvidenceChainConvergence（合并行为等价）**：
  verify_chain_yaml == scripts.evidence_chain.verify_chain（PASS 场景 +
  required 节点缺失 strict/非 strict 两场景，逐字段相等）；freeze_file_yaml
  == scripts freeze_file（记录逐字段相等 + sha256 断言）；server dispatch
  evidence_verify/freeze 集成。
- **TestDashboardMerge（合并行为等价）**：shim is 单一实现；generate()
  to_dict 关键字段一致。
- **TestWhitelistConsistency（AC-05）**：见 hook-whitelist.md。

## 约束自查

| 硬约束 | 实证 |
|--------|------|
| hooks/ 仅白名单一处 | `git diff HEAD --name-only -- hooks/` == 仅 `hooks/scripts/loop_enforcement.py`（测试断言）；该 diff 为注释级白名单同步（见 hook-whitelist.md） |
| 内核判定零触碰 | gate_guard/enforcement/hard_constraints/guard_health diff = 0 行；state_machine.py 仅 F2-2 刷新调用（f2 证据）；判定语义零改动 |
| 不执行任何工具删除 | 6 薄壳 + 4 弱引用 + 3 legacy：文件全部保留；仅收集证据（tool-removal-candidates.md），删除待用户独立 gate |
| fail-closed 不变 | 薄壳内联行为逐字节等价；evidence 校验不可读节点显式 BLOCKED；未知工具 LookupError；MCP 输出契约零变化 |
| 写路径限 allowed_paths | capability_registry.py / evidence_chain.py / status_dashboard.py / dashboard_views.py / tools/server.py / tests/ / .ai/ |
| 版本文件不改 | pyproject/CHANGELOG 未触碰 |

## 回归（相关既有测试全绿）

- F1/F2/F3 专测 + governance_metrics/gate_feedback/slo_consistency/
  evidence_chain/capability_registry/status_dashboard/dashboard：282 passed
- F2/F3 + product_layer_integration/tool_executor/slo_consistency/
  plugin_cache_sync：81 passed
- enforcement/hooks/hook_guards/mcp_client/tool_executor/loop_core：
  187 passed
- tool_registry_status/self_audit_llm/t0105_batch3/evals：85 passed
- mcp_capability/role_capability：41 passed
- compileall（loop_core/tools/hooks/scripts/新测试）：OK

## 遗留

1. 候选 A 6 薄壳删除 + 候选 B 4 弱引用确认 + 候选 C legacy 收敛决策：
   待用户独立 gate（tool-removal-candidates.md 附调用图证据 + 一个 gate
   周期无引用实证说明）。
2. 安全扫描双实现收敛（loop_core.security_scanner vs agent 脚本
   security_report/v1 契约）：输出 schema 变更影响 MCP 契约，需独立
   gate 批准后在后续任务执行（scripts/security_scan.py 已 DEPRECATED，
   收敛方向 = loop_core）。
3. scripts/evidence_chain.py legacy CLI：逻辑已收敛 loop_core，删除/壳化
   待后续任务（不在本任务 allowed_paths）。
4. 缓存同步"三处"经勘察不构成重复组（三类不同机制），未合并——记录在案。

---

## P1 修复记录（独立审查放行项，2026-08-03）

来源：T-0109 独立审查（independent-review.md 五-1）——`test_loop_core_has_no_host_leaks`
新增失败（DR-002 宿主无关违反）：`loop_core/evidence_chain.py:480` 的
`CHAIN_YAML_CANDIDATES` 含宿主特定路径字面量 `.zcode/skills/loop-governance/chain.yaml`
（F5 证据链收敛 verbatim 移植引入）。

### 根因
- F5 收敛时按 scripts/evidence_chain.py 原样移植了候选路径顺序
  （`.zcode` 安装副本优先 → `skills/` 仓库源回退），把宿主特定路径
  字面量带进 loop_core，违反 DR-002 宿主无关原则（模块 docstring 明示
  "does NOT depend on any specific host"）+ AC-06 全量回归 0 failed 未达。

### 修复方式（loop_core/evidence_chain.py，单文件）
- `CHAIN_YAML_CANDIDATES` 改为纯仓库相对路径：`("skills/loop-governance/chain.yaml",)`
  ——不再含任何 `.zcode` 字面量（DR-002 消除）。
- 宿主特定安装副本改为**注入式**（保持 T-0105「安装副本优先」语义）：
  - 参数注入：`load_chain_yaml(project_root, host_candidates=...)` /
    `verify_chain_yaml(project_root, strict=..., host_candidates=...)`——调用方
    （如 tools/server.py）可显式传入宿主安装路径；
  - 配置注入：环境变量 `LOOP_GOVERNANCE_CHAIN_YAML_HOST`（相对 project_root
    的 chain.yaml 路径）——宿主部署时经配置注入安装副本。
  - 注入候选优先于仓库源回退（原 `.zcode` 副本优先语义保持）；注入候选
    缺失 → 回退仓库源（原回退语义保持）。
- 注释/docstring 同步更新（不含带引号的 `.zcode` 字面量）。
- 未改动：scripts/evidence_chain.py、tools/*（不在本修复写路径）；
  freeze_file_yaml 不涉及候选路径，零改动。

### 行为保持实证
- 仓库两处 chain.yaml（`.zcode/skills/...` 与 `skills/...`）逐字节相同 →
  实仓 `verify_chain_yaml` 加载配置与修复前一致（修复前经 `.zcode` 副本、
  修复后经 `skills/` 源，内容同一）；
- 等价测试（tmp_path 仅含 `skills/` 源）与 scripts 实现逐字段相等不变；
- 注入候选优先/缺失回退均有测试覆盖（TestEvidenceChainHostInjection）。

### 测试结果
- `tests/test_code_quality.py::TestSelfCheck::test_loop_core_has_no_host_leaks`：**PASS**
- `tests/test_t0109_f5_tool_capability.py`（新增 TestEvidenceChainHostInjection 4 项
  宿主无关回归防护）：29 passed
- `tests/test_t0108_fixes.py`（含 P3-1 去耦合修复）：31 passed
- `tests/test_evidence_chain.py` + `tests/test_code_quality.py` 全量：73 passed
- 全量回归 `pytest tests/ -q`：见 commands.md 回归表（仅 3 项预登记瞬态，
  本 P1 失败项已消除）。
