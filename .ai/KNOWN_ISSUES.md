# Known Issues

## Open

- [hooks-not-loaded Critical] **ZCode 宿主安全策略忽略项目 hooks——loop 工程强制层从未生效**（2026-08-10 日志核实）：ZCode 运行日志确认 `config_project_hooks_ignored`（"Project hooks were ignored by the security policy"，今日 61 次）指向 `.zcode/config.json` 的 hooks 配置被忽略；bootstrap `hookCount: 0`（今日 69 次）——session_brief/gate_guard/path_guard/loop_enforcement 等进程级守卫从未被加载执行；同时 `mcpServerCount: 0`——插件声明的 MCP 服务器（loop-tools）也未加载。**仅 skills 层生效**（skillRootCount 4，loop-governance SKILL.md 可被主会话自觉遵循）。影响：本项目的全部 gate 拦截/状态注入/写保护都是**主会话按 SKILL.md 自觉模拟**，机器强制层（不可绕过）实际不存在——治理降级为自律，与设计意图（执行层强制）不符。配置本身正确（.zcode/config.json + .zcode-plugin/plugin.json + 插件缓存 hooks.json 内容完整），是 **ZCode 平台加载机制未启用**。→ 记录留档，需 ZCode 平台侧修复（项目 hooks 信任开关 / 用户级 hooks 注册方式），loop-engine 仓库内无法解决；在平台修复前，治理依赖主会话自律 + 证据链自校验（pi_evidence_import/verify_evidence_check 等确定性工具仍有效）。
- [session-source-disabled Medium] Qoder 工作区会话证据源未启用或源根配置不可用：分析报告出现 `disabled-source-root` / `missing-optional-root`，仅 1/5 个 enabled source roots 存在；即使有会话也无法读取，任务理解、可控执行、改动验证、可靠交付持续处于 Unobserved，评分被证据上限锁死，学习捕获也无法验证。→ 记录保留，不立项修复（T-0112 已撤销：Qoder 为外部会话宿主，其数据不作 ZCode 验收证据；T-0121 已落地 ZCode 原生会话存在性核验（呈现层 session_source 标注），如需进一步走 ZCode 原生会话证据路径按 T-0120 决策包评估）
- [execution-delegation Medium] 执行委派演进方向（用户观察 2026-08-07）：Loop 工程当前执行拓扑 = **主会话编排 + 子代理审查**（T-0062 仅强制 quality checkpoint 派发子代理；委托链 C-001~C-005 解决的是授权拓扑，非执行拓扑）。主任务（设计/编码/测试/收口）全部由主会话执行。**这是 ZCode 宿主约束下的合理现状**（子代理不能拉子孙代理、上下文不跨会话共享、无持久状态），非治理缺陷；但对照 loopx 对等代理模型（claim/lease/typed continuation），执行委派（executor: subagent 标记 + 上下文打包派发 + 产物回收校验）是明确的演进方向。**ZCode 上为 P2 候选（candidate-only 设计，需 gate）；Pi agent（支持 3 层子代理递归）可先行试点** —— 引导见 docs/designs/T-0159-pi-agent-onboarding.md。→ 记录留档，不立项（待用户发起）。**2026-08-08 更新：Pi 侧 loop 工程治理升级已由 T-0160 启动**（gate 生命周期/状态校验闸/证据 SHA256 锚定/事件溯源/HANDOFF 投影/反幻觉补漏/升级协议/旧数据迁移，Pi mini-loop 对齐 ZCode 核心治理机制）；执行委派（executor: subagent 标记）本身仍为 Pi 侧后续候选。

## Recently Closed

- 2026-08-07: E2E integration test 记录过时关闭 — **T-0150 核验**：`test_E2E_CURRENT_001.py` 在 git 历史中从未存在（无提交记录），KNOWN_ISSUES 的 skipped 记录为过时项；实际集成测试资产为 `tests/lab/test_project_governor_consistency.py`（64 用例，可收集、可运行、全通过，纳入全量回归 testpaths=tests 覆盖）。已关闭并改述。

- 2026-08-07: Seeded defects 未自动调用关闭 — **T-0128 变异测试接线，v3.12.63**：`mutation_tester.py scan` 子命令自动加载 defect_registry（6 SD）+ `tests/seeded_defects/detector.py` 确定性检出规则库（M1 6/6，AST/正则，可复算）；M2 真实角色检出（security-engineer + quality-engineer subagent 独立审查，6/6，sd_ref 标注）；检出率报告落盘 `observability/mutation-report-m1/m2.json` 并接入 `release.py check` mutation_gate（M1>=5/6 且 M2>=4/6，缺失 fail-closed）。
- 2026-08-06: env-dependent 测试关闭 — **T-0126 端口注入修复，v3.12.61**：`test_runtime_report_is_simulated_and_fail_closed` 改为 bind 随机端口（绑定不监听，连接必被拒）注入 `service_url`（显式 127.0.0.1），与端口占用/localhost 解析/代理配置完全无关（占用 3000/8000 实证确定性 FAIL，AC-01）；checker 零改动，fail-closed 断言原样保留。
- 2026-08-06: Large-module-split-candidates 8/8 关闭 — **T-0124（v3.12.59）+ T-0125（v3.12.60）**：`loop_core` 7 模块（executor/context_loader/second_failure/evals/intent_router/hard_constraints/dashboard_views）+ `hooks/scripts/hook_common.py`(831→727) 全部拆分至 <800 行；deep_probe 模块大小项全部真实 PASS，人工白名单清零；独立审查 GO（AST 逐行等价 + dir() 一致）。
- 2026-08-06: T-0117 P3 观察关闭 — **T-0123 已统一共享常量，v3.12.58**：`scripts/certification_runner.py` L613 `security_report/v1` 字面量替换为 `SECURITY_REPORT_V1_SCHEMA`（自仓库首个提交即存在的旧形态样本，非新引入）。
- 2026-08-06: ROLE_CHALLENGES-gap 关闭 — **T-0123 已补 CHALLENGE-TE-001，v3.12.58**：`loop_core/role_capability.py` 12/12 角色 challenge 全覆盖，`check_role_admission` 对 test-engineer 可正常认证。
- 2026-08-06: T-0104 P3 建议类关闭 — **T-0122 核实，v3.12.57**：4 项建议均已由 T-0105 批 2（B-4-1~4）实施（context_packager 召回过滤/phase 容错/manifest 时序约定/配置缓存），为 T-0116 重复登记。
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

## Debt Register（T-0151 落地，T-0152 语义修正）

> 技术债结构化账本（roadmap backlog bug-caps/debt-register 项落地）。
> 分级：P0 安全/数据风险（无豁免）> P1 稳定性（故障面）> P2 性能 > P3 维护性。
> 无法即时修复的项登记于此（含"老系统不可改"场景：隔离+监控+封装，不强行重构）。
> **本表只保留未决债务**；已闭环项移入下表 Closed。新增债务：
> `- [编号 等级] 描述 → 来源/处理`。

| 编号 | 等级 | 债务 | 来源 | 处理 |
|------|------|------|------|------|
| DR-001 | P3 | Qoder 会话源不可用（session-source-disabled，保留不立项） | T-0112 边界 | 保留记录 |

### Debt Register Closed（已闭环）

| 编号 | 等级 | 债务 | 闭环 |
|------|------|------|------|
| DR-002 | P3 | defense_drill_pass_rate 以用例数/用例数为口径 | T-0149 动态统计 + 口径文档化 |
| DR-003 | P3 | render_markdown 未渲染 mutation/gate_defense | T-0149 已渲染 |
| DR-004 | P3 | repro_norm 生产方接线 | T-0158 生产方约定文档化 + 事件记录 repro_norm |
| DR-005 | P3 | E2E 以 lab 64 用例承载 | T-0150 确认纳入回归 |
