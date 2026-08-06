# Known Issues

## Open

- [session-source-disabled Medium] Qoder 工作区会话证据源未启用或源根配置不可用：分析报告出现 `disabled-source-root` / `missing-optional-root`，仅 1/5 个 enabled source roots 存在；即使有会话也无法读取，任务理解、可控执行、改动验证、可靠交付持续处于 Unobserved，评分被证据上限锁死，学习捕获也无法验证。→ 记录保留，不立项修复（T-0112 已撤销：Qoder 为外部会话宿主，其数据不作 ZCode 验收证据；T-0121 已落地 ZCode 原生会话存在性核验（呈现层 session_source 标注），如需进一步走 ZCode 原生会话证据路径按 T-0120 决策包评估）
- [env-dependent Low] `test_deployment_quality_checker::test_runtime_report_is_simulated_and_fail_closed` 本机环境依赖失败：localhost:3000/8000 被无关进程占用致 `service.startup=PASS`（T-0107 独立审查经 e083f7b baseline worktree 实证为预存在环境依赖，非代码缺陷；空闲端口环境应通过）
- Seeded defects test project exists but is not automatically invoked by the mutation tester (manual verification only).
- E2E integration test (test_E2E_CURRENT_001) is skipped due to lab fixture dependency.
- [Large-module-split-candidates Low] 8 个超大文件（>800 行）为拆分候选（T-0115 登记，deep_probe 已按"基线白名单 + 漂移检测"接受现状）：`loop_core/dashboard_views.py`(1108)、`loop_core/hard_constraints.py`(1107)、`loop_core/intent_router.py`(965)、`loop_core/evals.py`(905)、`loop_core/second_failure.py`(858)、`loop_core/context_loader.py`(839)、`loop_core/executor.py`(838)、`hooks/scripts/hook_common.py`(831)。→ 拆分需独立 gate 立项（涉及内核/hooks 文件）。→ **8/8 全部拆分完成（T-0124 七个 loop_core 模块 + T-0125 hook_common，v3.12.59/v3.12.60）**。
- [T-0117 P3 观察 Low] `scripts/certification_runner.py`（L613）存在 `security_report/v1` 字面量（challenge_security_engineer 夹具构造 CVE 旧形态样本，自仓库首个提交未改动，非 T-0117 引入）→ **T-0123 已统一为共享常量 SECURITY_REPORT_V1_SCHEMA（v3.12.58）**。
- [ROLE_CHALLENGES-gap Low] `loop_core/role_capability.py` ROLE_CHALLENGES 覆盖 11/12 角色，`test-engineer` 的 challenge 未定义（T-0115 探针现代化时确认；角色准入 `check_role_admission` 对 test-engineer 会因缺 challenge 而无法认证）。→ **T-0123 已补 CHALLENGE-TE-001（12/12，v3.12.58）**。
- [T-0104 P3 建议类 Low] 四象限落地任务审查遗留 4 项建议（T-0122 核实修正：**4 项均已由 T-0105 批 2（B-4-1~4）实施**，此条为 T-0116 登记时未对照 T-0105 证据的重复登记）：
  - context_packager 记忆召回过滤 → B-4-1 已实施（build_context memory_gate_id/memory_tag + recall 透传 task_id/gate_id/tag）
  - `_load_memory_injection_config` phases 容错 → B-4-2 已实施（_validated_phases 非法回退 disabled）
  - evidence-manifest 时序依赖 → B-4-3 已实施（CONTRACTS.md Completion Flow Conventions）
  - 配置读盘缓存 → B-4-4 已实施（_CONFIG_CACHE mtime 失效）
- [Large-module-split-candidates Low] 8 个超大文件（>800 行）为拆分候选（T-0115 登记，deep_probe 已按"基线白名单 + 漂移检测"接受现状）：`loop_core/dashboard_views.py`(1108)、`loop_core/hard_constraints.py`(1107)、`loop_core/intent_router.py`(965)、`loop_core/evals.py`(905)、`loop_core/second_failure.py`(858)、`loop_core/context_loader.py`(839)、`loop_core/executor.py`(838)、`hooks/scripts/hook_common.py`(831)。→ **8/8 全部拆分完成（T-0124 七个 loop_core 模块 <800 行 + T-0125 hook_common 727 行，v3.12.59/v3.12.60），deep_probe 模块大小项全部真实 PASS，白名单清零**。

## Recently Closed

- 2026-08-03: T-0106 排查确认的 12 条修复项全部移入 Closed — **T-0107 修复，v3.12.44**（编号引用 .ai/evidence/T-0106/design/audit-design-gaps.md）：
  - [D1-1 P1] `loop_core/context_packager.py` 任务卡 1000 字符静默截断 → token 预算（1500 tokens ≈ 6000 字符）+ AC/验收节优先保留 + truncated 标记（`_format_task_card`）。
  - [D1-2 P2] 角色指定文件按 max_content 截断无标记 → `…[truncated N chars]` 显式标记。
  - [D1-4 P2] knowledge cases JSON 中段截断 → 按 case 边界截断保持语法完整 + 标记。
  - [D2-1 P2] 1000/2000/3000/5/3 截断字面量 → 命名常量（TASK_CARD_TOKEN_BUDGET / EXTRA_FILE_MAX_CHARS / KNOWLEDGE_CASES_MAX_CHARS / MAX_EXTRA_FILES / MAX_KNOWLEDGE_CASES）。
  - [D2-2 P2] `loop_core/intent_router.py` 中风险 ≥3 升级阈值 → `MEDIUM_RISK_ESCALATION_MIN` 命名常量。
  - [D3-1 P2] `loop_core/audit_ledger.py` 无轮转 → 行/字节阈值轮转 + 保留 N 份归档（链哈希跨归档延续，verify_integrity 依然完整）。
  - [D3-2 P2] `context_packager` MAX=15000 死护栏 → total 真实累计 + 超限截断标记。
  - [D4-1 P2] git diff 段 `except Exception: pass` → warning + "diff unavailable" 占位节。
  - [D4-2 P2] `hooks/scripts/loop_enforcement.py` `is_loop_mode_enforced` state 读取失败 fail-open → **fail-closed 强化**（无法确认即按强制执行，与 runtime 投影路径语义一致）。
  - [D4-3 P2] `tools/tool_constraint_check.py` 非法 phase 静默丢弃 → `phase_problems` 告警字段。
  - [D5-1 P2] `loop_core/context_controller.py` `_naive_yaml_parse` 静默降级 → 显式告警 + gate/state schema 校验 + `_load_gates` 解析失败与"无 gate"分开上报。
  - [D5-2 P2] 双解析器分歧 → 共享契约解析模块 `loop_core/front_matter.py`（enforcement 与 context_controller 统一调用）+ 契约测试（表格 | 与列表格式一致）。
- 2026-08-03: Bash command interception via ZCode hooks — T-0060 已实现 `bash_content_guard`（Bash 写文件内容守卫，不再依赖通用命令拦截）。
- 2026-08-03: ProjectContinuity auto-generation first-run self-reference timing issue — T-0049 已拆 continuity 自引用/炸弹防护（源清单不再含自身，hash 自引用守卫 T-0058）。
- 2026-07-22: Stale project memory files (CONTRACTS.md, PROGRESS.md, KNOWN_ISSUES.md, DECISIONS.md) updated to reflect current project state (T-0033).
- 2026-07-22: Phase inconsistency fixed — constants.py synced to 12 phases matching loop_core/state_machine.py.
- 2026-07-22: zcode_adapter.py docstring fixed from STRONG to MEDIUM.
- 2026-07-22: T-0022~T-0032 completed full S0~S6 lifecycle with 193 passing tests.
- 2026-07-22: Independent audit by external AI validated Loop Core architecture and identified stale memory issues (now fixed).

## Historical (pre-merge)

- 2026-07-07: T-0005 closeout rerun passed; unified-governance-architecture.v0.2.1 installed as project-local AGENTS.md.
- 2026-07-07: Placeholder content in CONTRACTS.md, ACCEPTANCE.md, KNOWN_ISSUES.md replaced under T-0004.
