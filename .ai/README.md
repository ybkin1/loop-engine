---
# 机器可读路由表（T-0108 F4，D5-3 消解）：
# loop_core/context_loader._select_relevant_sections 读取本区块的
# section_routing 做文档节选择（替代角色名关键词启发式）；README 缺失或
# 无本区块时回退旧启发式并告警。keyword 语义与旧启发式一致（小写子串匹配），
# golden 快照保持不变。
section_routing:
  quality-engineer: [test, quality, coverage, lint, gate]
  security-engineer: [security, auth, encrypt, vulnerab]
  frontend: [frontend, ui, component, page, style]
  developer: [implement, code, module, build]
  architect: [architect, design, pattern, structure]
  system-architect: [architect, design, pattern, structure, system]
  module-architect: [architect, design, module, pattern]
  project-manager: [plan, schedule, milestone, risk]
  product-manager: [requirement, feature, user, story]
  delivery-manager: [deploy, release, delivery, ship]
  release-engineer: [deploy, release, ci, pipeline]
  default: []
---
# .ai 治理目录 Switchboard（F4，T-0108）

> 本文件是 `.ai/` 治理目录的路由入口：新会话/子代理按"Owns / Does Not Own /
> Read Next"三节快速定位。顶部 front-matter 的 `section_routing` 是
> context_loader 节选择的路由表（机器可读，勿删）。目录四态与文档活/死
> 归类见下表；死文档归档至 `.ai/archive/`（非删除）。

## Owns（本目录拥有）

| 条目 | 类型 | 说明 |
|------|------|------|
| `.ai/state.yaml` | active | 状态单一数据源（phase/task/gate/loop_mode） |
| `.ai/gates.yaml` | active | 门禁注册表（approval/执行状态） |
| `.ai/task_graph.yaml` | active | 任务图（全部任务状态） |
| `.ai/HANDOFF.md` | generated | 会话交接（close_session 结构化生成） |
| `.ai/DECISIONS.md` | active | 设计决策记录 |
| `.ai/KNOWN_ISSUES.md` | active | 已知问题登记 |
| `.ai/PROGRESS.md` | active | 进度记录 |
| `.ai/project_continuity.yaml` | active | 连续性契约（源清单 + 语义哈希） |
| `.ai/tasks/` | active | 任务卡（T-XXXX.md，front-matter 契约区） |
| `.ai/evidence/` | generated | 任务证据（不可变，superseded_not_deleted） |
| `.ai/schemas/` | target | 治理 schema（state/gate/task/finding…） |
| `.ai/checkers/` `.ai/checks/` `.ai/guards/` `.ai/policies/` | target | 治理检查/规则（演进受控） |
| `.ai/archive/` | archived | 死文档归档（非删除，本表归类） |
| `.ai/README.md` | active | 本文件（Switchboard） |

## Does Not Own（本目录不拥有）

| 域 | 归属 |
|----|------|
| `docs/`（产品/架构文档，如 `docs/02-architecture.md`） | 文档域 |
| `loop_core/`（宿主无关控制内核） | 代码域 |
| `hooks/`（执行层强制钩子） | hook 强制层 |
| `tools/` `scripts/` `agents/` `tests/` | 工具/角色/测试域 |
| `skills/` `.zcode/`（宿主配置与技能） | 宿主域 |
| `archive/` `docs/archive/`（仓库级历史归档） | 仓库级归档 |

## Read Next（新会话按序阅读）

1. `.ai/state.yaml` — 当前状态（phase / current_task_id / gate）
2. `.ai/HANDOFF.md` — 上一会话交接（含连续性投影）
3. `.ai/README.md` — 本路由表
4. `.ai/tasks/<current_task_id>.md` — 当前任务卡（AC/允许路径）
5. `.ai/gates.yaml` — 待决/已批门禁
6. `.ai/KNOWN_ISSUES.md` — 已知问题与登记

## 目录四态（active / generated / target / candidate）

| 目录 | 状态 | 说明 |
|------|------|------|
| `.ai/` 顶层权威文档（state/gates/task_graph/DECISIONS/KNOWN_ISSUES/PROGRESS/README） | **active** | 手工维护的权威数据 |
| `.ai/evidence/` `.ai/runtime/` `.ai/ledger/` `.ai/HANDOFF.md` | **generated** | 生成产物，只增不改/由工具重生成 |
| `.ai/schemas/` `.ai/checkers/` `.ai/checks/` `.ai/guards/` `.ai/policies/` | **target** | 契约目标，演进受 gate 控制 |
| 历史 DRAFT 计划（原 `.ai/plans/`，T-0081 后清空） | **candidate→archived** | 草稿/候选；已完成任务的历史计划已归档至 `.ai/archive/plans/`（planner 按需重建空目录） |
| `.ai/archive/` | **archived** | 死文档（非删除；continuity 源清单同步） |

## 文档活/死归类（20+ 顶层文档）

| 文档 | 归类 | 说明 / 去向 |
|------|------|-------------|
| `.ai/state.yaml` | 活 | 状态权威，active |
| `.ai/gates.yaml` | 活 | 门禁注册，active |
| `.ai/task_graph.yaml` | 活 | 任务图，active |
| `.ai/HANDOFF.md` | 活 | 会话交接，generated |
| `.ai/DECISIONS.md` | 活 | 决策记录，active |
| `.ai/KNOWN_ISSUES.md` | 活 | 问题登记，active |
| `.ai/PROGRESS.md` | 活 | 进度记录，active |
| `.ai/ACCEPTANCE.md` | 活 | 产品验收契约（validate_state REQUIRED_FILES） |
| `.ai/ARCHITECTURE.md` | 活 | 架构速览（指向 docs/02-architecture.md） |
| `.ai/CODEMAP.md` | 活 | 代码地图 |
| `.ai/CODING_STANDARDS.md` | 活 | 编码标准（context_packager 角色上下文引用） |
| `.ai/CONTRACTS.md` | 活 | 冻结契约 |
| `.ai/CONVENTIONS.md` | 活 | 命名/约定 |
| `.ai/NON_GOALS.md` | 活 | 非目标（REQUIRED_FILES） |
| `.ai/PROJECT.md` | 活 | 项目定义（REQUIRED_FILES） |
| `.ai/QUALITY_GATES.md` | 活 | 质量门禁清单（REQUIRED_FILES） |
| `.ai/README.md` | 活 | 本 Switchboard（新增） |
| `.ai/archive/plans/PLAN-20260729-001.yaml` | **死** | T-0081 历史 DRAFT 计划，无活动引用 → 已归档（T-0108；原 `.ai/plans/` 位置清空） |
| `.ai/archive/plans/PLAN-20260729-002.yaml` | **死** | 同上 → 已归档（T-0108；原 `.ai/plans/` 位置清空） |
| `.ai/reviews/TEMPLATE.md` | 活 | 审查报告模板 |
| `.ai/schemas/` 全部 | 活 | 契约 schema（finding.schema.json 等） |
| `.ai/evidence/` 全部 | 活（不可变） | 任务证据，只增不改 |

> 归档规则（T-0105 先例）：死文档移动（非删除）至 `.ai/archive/<原相对路径>`；
> `project_continuity.yaml` source_manifest 同步（移除条目 + 重算 source_sha256，
> semantic_sha256 不变）；HANDOFF.md 由 close_session/render_handoff 重生成。
