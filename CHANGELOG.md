# Changelog

## v3.12.46 (2026-08-03) — T-0109 — BH 融合·分层期（F2-2 写入收敛/F3 gates 分层/F1 评估模型/F5 工具 capability 化）

### Changed (T-0109 — BH 融合·分层期（F2-2 写入收敛/F3 gates 分层/F1 评估模型/F5 工具 capability 化）)
- 版本同步：release.py bump 更新 pyproject/CHANGELOG/版本载体（原子写）；提交流程约定：先 bump 再提交（版本与 git HEAD 一致）

## v3.12.45 (2026-08-03) — T-0108 — BH 融合·收敛期（F4 文档路由/F6 上下文打包/F7 finding 契约/F8 契约测试/F2-1 新鲜度）

### Changed (T-0108 — BH 融合·收敛期（F4 文档路由/F6 上下文打包/F7 finding 契约/F8 契约测试/F2-1 新鲜度）)
- 版本同步：release.py bump 更新 pyproject/CHANGELOG/版本载体（原子写）；提交流程约定：先 bump 再提交（版本与 git HEAD 一致）

## v3.12.44 (2026-08-03) — T-0107 — 设计漏洞修复（P1 context_packager 截断专项 + P2 全量 + P3 首批 + hook 门禁强化）

### Changed (T-0107 — 设计漏洞修复（P1 context_packager 截断专项 + P2 全量 + P3 首批 + hook 门禁强化）)
- 版本同步：release.py bump 更新 pyproject/CHANGELOG/版本载体（原子写）；提交流程约定：先 bump 再提交（版本与 git HEAD 一致）

## v3.12.43 (2026-08-03) — T-0105 — Loop 工程收尾修复包（文档漂移/P3 修复/Q2 多轮提问/Q4 原型机制/eval 验证）

### Changed (T-0105 — Loop 工程收尾修复包（文档漂移/P3 修复/Q2 多轮提问/Q4 原型机制/eval 验证）)
- 版本同步：release.py bump 更新 pyproject/CHANGELOG/版本载体（原子写）；提交流程约定：先 bump 再提交（版本与 git HEAD 一致）

## v3.12.42 (2026-08-02) — T-0104 — 四象限整合设计落地（盲点自检/定位声明/偏离日志/反向考察/简报要素）

### Changed (T-0104 — 四象限整合设计落地（盲点自检/定位声明/偏离日志/反向考察/简报要素）)
- 版本同步：release.py bump 更新 pyproject/CHANGELOG/版本载体（原子写）；提交流程约定：先 bump 再提交（版本与 git HEAD 一致）

## v3.12.41 (2026-08-02) — T-0102 — handoff 生成器 idle 占位修复 + P3 观察项清零

### Changed (T-0102 — handoff 生成器 idle 占位修复 + P3 观察项清零)
- 版本同步：release.py bump 更新 pyproject/CHANGELOG/版本载体（原子写）；提交流程约定：先 bump 再提交（版本与 git HEAD 一致）

## v3.12.40 (2026-08-02) — T-0101: idle 稳态语义修复（NO_ACTIVE_TASK exit 3 分流 + 消费端对齐）

### Changed (T-0101)
- validate_state / audit_handoff：NO_ACTIVE_TASK 独立 exit code 3 + 独立 [info] 输出段
  （idle 合法阻塞态：current_task_id=null 且无其他 blocker）；真实治理损坏（连续性
  漂移/缺文件）保持 [error] + exit 2（fail-closed 不变）；idle 不输出
  "[ok] state is usable"（安全意图保留）
- release.py check：step_validate_state 感知 rc=3 → PASS 并标注"idle 合法阻塞态"
  （check 支持 idle 稳态运行，6/6 可达）；rc 0/2 语义不变
- test_governance_consistency：idle 适配（None 断言 idle 契约，消除 TypeError；
  激活态断言原样保留，repo/idle 双场景参数化）
- loop_self_audit：validate_state rc 判定 0/2 → 0/2/3（三处约定对齐）
- 新增 tests/test_idle_semantics.py（idle exit 3 / 损坏 exit 2 / idle+blocker exit 2）
- 版本同步：release.py bump 更新 pyproject/CHANGELOG/版本载体（原子写）；
  提交流程约定：先 bump 再提交（版本与 git HEAD 一致）

## v3.12.39 (2026-08-02) — T-0100: 质量验收 findings 修复包（F-03~F-06）

### Changed (T-0100)
- 版本同步机制：release.py 新增 bump 子命令（`bump --to <version>` 原子更新
  pyproject.toml + CHANGELOG 头部 + 全部版本载体，临时文件 + os.replace）；
  提交流程约定：先 bump 再提交（版本与 git HEAD 一致，version_sync fail-closed 不变）
- F-01：tool_registry_status `--json` 模式 UnboundLocalError 修复（death 变量
  作用域），--json 正常退出 0 并输出合法 JSON
- F-04：安全扫描 dependency_check 语义 —— pip-audit 环境不可用（缺 venv/命令缺失/
  非预期失败）→ 明确 SKIPPED（附 reason），不再合成阻断级 HIGH；真实 CVE 结果照常判定
- F-05：SLO 口径统一 —— release_fee 计算收敛为 governance_metrics 单一函数，
  metrics 与 slo_gate 输出一致；未接线数据源（wave-2 ledger）逐项 advisory 标注，
  不因部分源未接线而整体 NOT_VERIFIED（computed 项按实值判定）；门禁语义不变
- F-06：安全扫描误报白名单 —— 规则表自指/测试夹具/seeded_defects/文档示例/
  SafeLoader 子类 yaml.load 不再误报；真实代码路径不豁免

## v3.12.38 (2026-08-02) — T-0099: Loop 工程自身质量验收（dogfooding）

### Changed (T-0099)
- 四组全能力端到端验收（静态门禁/动态质量/治理质量/发布就绪，13 项）；
  裁决 CONDITIONAL_GO，记录 F-01~F-06 待修复（T-0100 修复）

## v3.12.37 (2026-08-02) — T-0098: D8 发布/产物体系（wheel/sdist + release 流程）

### Added (T-0098)
- release.py check/build/manifest/release/smoke 子命令 + dist/ 产物清单/SHA256SUMS
- 版本同步基线：pyproject 为唯一事实来源；6/6 AC GO

## v3.12.36 (2026-08-02) — T-0097: B2 学习回路补全（incident + 复盘 + second-failure）

### Added (T-0097)
- incident 记录：事故/失败事件（类别/影响/时间线/处置）结构化落盘 + 检索
- 复盘：与 incident 关联的根因分析 + 行动项（owner/deadline）+ 状态跟踪（open/closed）
- second-failure 检测：同类复发识别 → 任务建议（report 级）+ 阻断语义（无 owner 行动项则阻断）
- 与 gate_lessons/SLO 门禁衔接（失败事件来源统一）；6/6 AC GO

## v3.12.35 (2026-08-02) — T-0096: 知识/记忆服务（D3）

### Added (T-0096)
- 知识存储：结构化记录（决策/经验/教训）+ 多维度检索（任务/gate/主题/关键词）
- 记忆服务：跨任务经验提取（gate 决策/gate_lessons/验收记录）与注入（决策包/路由上下文）
- 与 T-0089 gate_feedback 单向整合 + U3 context_loader 可选注入衔接；6/6 AC GO

## v3.12.34 (2026-08-02) — T-0095: 遗留清理包

### Changed (T-0095)
- 10 项 P3 技术遗留系统性清理；slo.yaml 配置显式化
- 事件轮转机制 + 环境变量链统一；7/7 AC GO

## v3.12.33 (2026-08-01) — T-0094: AutoPlan dashboard 升级（D4）

### Added (T-0094)
- 任务图可视化（节点/依赖/状态）+ gate 状态可视化（pending/approved/rejected + 决策记录）
- 指标与 guard 健康展示（D2 metrics-report + U8 guard-events 衔接）
- 状态快照报告生成（HTML/文本，可保存可分享）；6/6 AC GO

## v3.12.32 (2026-08-01) — T-0093: SLO 门禁 wave 2（error budget 冻结发布）

### Added (T-0093)
- SLO 门禁检查器（budget 状态 → BLOCK/PASS，fail-closed：不可判定 → BLOCK）
- 接入 S6 发布门 + 恢复机制（budget 健康恢复 → 放行；豁免显式记录）
- P1 修复转 GO

## v3.12.31 (2026-08-01) — T-0092: AI-agent eval 栈（B1 设计落地）

### Added (T-0092)
- eval 用例集 schema（输入/预期/评分规则 + 版本 + 分级）
- eval 运行器（规则评分起步；LLM 判定可选、fail-safe 降级规则）+ eval 报告落盘（observability/eval-report.json）
- 与 guard/约束验证衔接（防护有效性评测）；6/6 AC GO

## v3.12.30 (2026-08-01) — T-0091: B5 自举审计接线（LLM 驱动 self-audit）

### Added (T-0091)
- self-audit 增加 LLM 语义分析环节（审计数据 → 风险发现/根因/修复建议 → 报告落盘）
- 模型配置复用 ZCode 宿主配置（env 优先 → ~/.zcode/v2/config.json；provider 可配置）
- Anthropic Messages 协议驱动；LLM 不可用 → fail-safe 降级为规则式审计；5/5 AC GO

## v3.12.29 (2026-08-01) — T-0090: 新能力引入（D1 LLM 抽象层 + D5 工具/MCP + D7 异步队列 + D2 SLO/指标）

### Added (T-0090)
- D1 LLM 客户端抽象：协议驱动接口 + OpenAI 兼容驱动 + 统一错误码 + 重试 + JSON 修复 + 脱敏；key 仅环境变量
- D5 工具执行器 + MCP 客户端（白名单 + 超时 + stdio 传输起步）
- D7 异步任务队列（后台执行 + 状态跟踪 + 租约防重复派发）
- D2 SLO/指标：SLI 采集 + SLO/error budget + DORA 指标报告；6/6 AC GO

## v3.12.28 (2026-08-01) — T-0089: 学习回路与工程化（U4 gate 反馈 + U7 可靠投递 + U8 可观测性 + U9 生命周期）

### Added (T-0089)
- U4 gate 拒绝/修复请求 → 经验沉淀（结构化记录 + 可检索 + 决策包改进建议）
- U7 evidence 写入幂等 + 失败退避重试 + 卡死重置
- U8 guard 检查观测：耗时/频率/失败原因事件落盘；观测层异常不阻断业务
- U9 生命周期脚本（up/down/status + pid + 健康轮询）；6/6 AC GO

## v3.12.27 (2026-08-01) — T-0088: 上下文与路由升级（U3 预算压缩 + U5 路由粘性/任务帧 + U6 resume payload）

### Added (T-0088)
- U3 上下文加载按 token 预算触发压缩（阈值 + 触发测试；层级摘要可配置）
- evidence 引用截断修复（.ai/ 证据引用前缀思路移植）
- U5 路由对 active 任务粘性 + 多意图回合任务帧编排 + 异常 fail-safe 降级
- U6 人工接管决策包带 resume payload（gate 暂停 → 机器可恢复上下文）；7/7 AC GO

## v3.12.26 (2026-08-01) — T-0087: 运行时契约化（U1 checkers/guards 注册表化 + U2 vertical_slice 契约平面化）

### Added (T-0087)
- U1 治理资产注册表化：显式登记/版本/契约版本/不可变快照（seal 后不可变，sha256 指纹）
- 重水合 fail-closed：版本/契约不匹配抛错，不静默降级
- 与 guard_health 集成：死亡 + 遗漏 + 漂移三向完整性检测
- U2 vertical_slice 契约平面化；7/7 AC GO

## v3.12.25 (2026-08-01) — T-0086: 治理清障 + StaffDeck 对标落地

### Changed (T-0086)
- hook 只读豁免（治理脚本直接读写）+ P1/P2 拦截收紧
- StaffDeck 对标分析落盘为可审计证据；形成 T-0087~T-0090 任务计划编排

## v3.4.0 (2026-07-24) — T-0047 + T-0048: 治理硬化 + 收尾

### Fixed (T-0047)
- **FAIL-CLOSED**: `enforcement_hub.py` — corrupted/missing governance YAML now blocks writes (was: silent pass through)
- **FAIL-CLOSED**: `role_isolation.py` — state read error now returns exit 2 DENY (was: exit 0 silent pass)
- `executor.py` `_write_state()`: atomic write via `.tmp` + `os.replace()` (T-0048)

### Added (T-0047)
- `tests/test_role_isolation.py` — 8 tests (normal, self-review, corruption, fail-closed)
- `tests/test_enforcement_hub.py` — 12 fail-closed corruption tests
- Hook split modules: `_hook_state.py`, `_hook_path.py`, `_hook_config.py`, `_hook_sync.py` (T-0048)

### Completed
- T-0041: vertical slice verification (23 tests, S0→S6 trail documented)
- T-0043: role capability certification (11 roles, 23 tests)
- T-0044: Qoder improvements port (6/7 items; atomic write fixed in T-0048)
- T-0042: Loop engineering optimization (see v3.1.0)

## v3.1.0 (2026-07-23) — T-0042: Loop 工程优化

### Added
- **Change iteration**: `REENTRY_TRANSITIONS` — 5 change types: bug_fix, feature_add, refactor, requirement_change, quality_fix
- **Project lifecycle**: `ProjectStatus` enum (draft, released, maintenance)
- **Reentry validation**: `validate_reentry()` with status-aware phase admission
- **Shell tokenizer**: quote/escape-aware Bash command extraction (`_hook_bash.py`, 155 lines)
- **Bash enhancement**: detection for curl, wget, tar, pip, npm, rsync, scp, openssl
- **Deep QA probes**: 75 new probe tests covering enforcement edge cases

### Changed
- `hook_common.py`: reduced from 998 to 830 lines (Bash logic extracted to `_hook_bash.py`)
- `zcode_adapter.py`: `ENFORCEMENT_LEVEL` MEDIUM → STRONG

### Fixed
- 5 issues found and fixed via deep QA probe testing:
  1. Shell tokenizer false positives on `\binstall\b` patterns
  2. Tokenizer segmentation with nested quotes
  3. Change type detection gaps in Chinese keyword matching
  4. Negation detection in shell commands
  5. Role capability state persistence after profile reload

## v3.0.0 (2026-07-23) — T-0040: EnforcementHub + HARD 阻断

### Added
- `enforcement_hub.py` (473 lines): Hook↔Core bridge
- `EnforcementLevel` enum: HARD, PARTIAL, ADVISORY
- Role domain separation: DEVELOPMENT_ROLES, QUALITY_ROLES, GOVERNANCE_ROLES
- `tests/test_enforcement_hub.py`: 39 tests

### Changed
- `role_isolation.py` v2.0: FULL mode self-review → HARD block (exit 2)

## v2.0.0 (2026-07-23) — T-0034: Runtime Controller

### Added
- `runtime_controller.py`, `approval_record.py`, `agent_adapter.py`, `executor.py`
- `state_machine.py`: phase transition graph, gate resolution, constraint checking
- 24 agent definitions, 30+ modules

## v1.0.0 (2026-07-22) — T-0022~T-0027: Loop Engine 初始交付

### Added
- Loop Engine plugin: hooks, MCP tools, skills, commands
- 11 agent role contracts
- S0→S6 governance phase machine
- Quality gate system
- docs/: requirements, architecture, interface contract, delivery
