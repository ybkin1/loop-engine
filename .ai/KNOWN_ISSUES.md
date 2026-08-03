# Known Issues

## Open

- Seeded defects test project exists but is not automatically invoked by the mutation tester (manual verification only).
- E2E integration test (test_E2E_CURRENT_001) is skipped due to lab fixture dependency.

### T-0106 排查确认的修复项（编号引用 .ai/evidence/T-0106/design/audit-design-gaps.md，T-0107 修复）

- [D1-1 P1] `loop_core/context_packager.py:42` 任务卡按 1000 字符静默截断且无标记，AC/验收节被切掉（T-0106 已知项确认）。→ T-0107 修复
- [D1-2 P2] `loop_core/context_packager.py:62` 角色指定文件按 max_content 截断无标记。→ T-0107 修复
- [D1-4 P2] `loop_core/context_packager.py:76` knowledge cases JSON 中段截断产出语法无效 JSON 无标记。→ T-0107 修复
- [D2-1 P2] `loop_core/context_packager.py:42,68,76,65,74` 1000/2000/3000/5/3 字面量未命名散落。→ T-0107 修复
- [D2-2 P2] `loop_core/intent_router.py:558` 中风险因素 ≥3 升级 loop 模式阈值魔法数。→ T-0107 修复
- [D3-1 P2] `loop_core/audit_ledger.py:84` 核心审计账本 append 无轮转/归档/保留策略。→ T-0107 修复
- [D3-2 P2] `loop_core/context_packager.py:37-38` MAX=15000 全局护栏死代码（total 从不递增）。→ T-0107 修复
- [D4-1 P2] `loop_core/context_packager.py:57-58` git diff 段 `except Exception: pass` 静默吞错，Diff 节消失无感知。→ T-0107 修复
- [D4-2 P2] `hooks/scripts/loop_enforcement.py:214-219` `is_loop_mode_enforced` 状态读取异常 return False（fail-open，loop 强制静默关闭）。→ T-0107 修复（最小 diff，独立门禁）
- [D4-3 P2] `tools/tool_constraint_check.py:18,21` 非法 phase `except ValueError: pass` 静默丢弃，约束在无 phase 上下文下运行。→ T-0107 修复
- [D5-1 P2] `loop_core/context_controller.py:444-538` `_naive_yaml_parse` 缩进/位置推断替代 schema 校验，静默降级且列表键/类型保真丢失。→ T-0107 修复
- [D5-2 P2] `hooks/scripts/loop_enforcement.py:259-295` 与 `loop_core/context_controller.py:400-414` 任务卡 front-matter 双解析器行为分歧。→ T-0107 修复（共享解析模块）

## Recently Closed

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
