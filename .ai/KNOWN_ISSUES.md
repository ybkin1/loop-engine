# Known Issues

## Open

- [session-source-disabled Medium] Qoder 工作区会话证据源未启用或源根配置不可用：分析报告出现 `disabled-source-root` / `missing-optional-root`，仅 1/5 个 enabled source roots 存在；即使有会话也无法读取，任务理解、可控执行、改动验证、可靠交付持续处于 Unobserved，评分被证据上限锁死，学习捕获也无法验证。→ 独立会话源恢复任务（T-0112 候选；不得并入 T-0107 代码修复）
- [env-dependent Low] `test_deployment_quality_checker::test_runtime_report_is_simulated_and_fail_closed` 本机环境依赖失败：localhost:3000/8000 被无关进程占用致 `service.startup=PASS`（T-0107 独立审查经 e083f7b baseline worktree 实证为预存在环境依赖，非代码缺陷；空闲端口环境应通过）
- Seeded defects test project exists but is not automatically invoked by the mutation tester (manual verification only).
- E2E integration test (test_E2E_CURRENT_001) is skipped due to lab fixture dependency.

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
