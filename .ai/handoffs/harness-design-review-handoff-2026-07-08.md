# Handoff: Harness 售后智算服务平台设计审查与文档补齐

Status: candidate
Approved: false
Installed: false

## Project

- Root: `C:\Users\Administrator\Documents\trae_projects\yb\harness\.codex\tasks\tk-20260614-001-agentic-backend-orchestration-design\artifacts`
- Name: Harness 售后智算服务平台（Agentic 后端编排设计）
- Current phase: 设计收敛与文档补齐
- Current task: 全量设计文档审查 + 缺失文档起草 + 约束违规修复 + 目录重构 + 部门评审资料包
- Current mode: **write-docs**（仅设计文档写作，无代码）

## User Origin

用户是售后智算服务平台的业务负责人。智算服务部同时承担智算机房服务器运维和平台开发建设。当前处于 Phase 1 MVP 设计收敛阶段，需要确保设计文档在正式开发前足够完整、一致、可评审且不违反"平台无法直连客户机房服务器"的硬性约束。

## Current Objective

完成全部设计文档的完整性审查、补齐缺失设计文档（共 8 份新文档）、修复跨文档约束违规（20+ 处）、统一组织架构称谓、重构项目目录结构、生成按部门划分的评审资料包。会话已产出可交付的设计文档集，下一会话应继续剩余缺口补齐或进入正式评审流程。

## Allowed

- 阅读 `artifacts/docs/` 下的全部设计文档
- 阅读 `artifacts/work/` 下的评审、计划、决策记录
- 阅读 `artifacts/README.md` 了解文档索引
- 修改 `artifacts/docs/` 下的设计文档（基于评审反馈）
- 创建新的设计文档
- 生成评审资料包或汇总报告
- 维护 `artifacts/README.md` 的索引同步

## Forbidden

- 不得编写业务代码、构建、部署、发布、回滚
- 不得进入真实生产系统、修改数据库、更改权限或密钥
- 不得安装 skill、MCP、agent 或自动化工具
- 不得将 candidate 状态文档宣称 approved、active 或 installed
- 不得假设平台可以直连客户机房服务器（硬性约束）
- 不得假设平台可以实时采集硬件指标（GPU 温度/ECC 计数/风扇转速）
- 不得将文档评审通过等同于用户正式批准上线
- 不得删除已有设计文档而不经用户确认

## Must Read

- `artifacts/README.md`：文档索引、目录结构、治理规则、Phase 归属总览
- `artifacts/docs/00-vision-and-scope/platform-vision-and-scope.md`：平台愿景、智算服务部双重职责、四部门关系、建设路径
- `artifacts/docs/01-business-design/organization-and-roles.md`：四部门定位、16 个角色定义、汇报关系（含部长/副部长/业务组）、部门 KPI
- `artifacts/docs/01-business-design/role-responsibility-approval-matrix.md`：9 角色 × 9 Matter 类型的审批矩阵、升级规则
- `artifacts/docs/01-business-design/design-r-end-to-end-functional-specification.md`：18 步端到端场景（权威流程源）
- `artifacts/work/reviews/agentic-design-assessment-2026-07-08.md`：上一次全面评估报告（70+ 修改点，跨 7 维度）
- `artifacts/work/reviews/department-review-package-2026-07-08.md`：按部门划分的评审资料包（可直接分发给四部门审阅）

## Current Artifacts

Candidate（本次会话新创建，未经用户 review）：
- `docs/00-vision-and-scope/platform-vision-and-scope.md` — 平台愿景与范围
- `docs/00-vision-and-scope/ai-transformation-roadmap.md` — AI 转型路线图
- `docs/01-business-design/organization-and-roles.md` — 组织架构与角色设计
- `docs/01-business-design/service-product-catalog-design.md` — 服务产品目录设计
- `docs/01-business-design/operations-management-design.md` — 运作管理设计
- `docs/02-domain-and-data/zhisuan-ops-domain-model.md` — 智算运维领域模型
- `docs/02-domain-and-data/spare-management-domain-design.md` — 备件管理领域设计
- `docs/02-domain-and-data/external-system-integration-map.md` — 外部系统集成地图
- `docs/04-ai-infrastructure/prompt-engineering-guide.md` — 提示词工程规范
- `docs/04-ai-infrastructure/llm-evaluation-plan.md` — LLM 评测计划
- `work/reviews/department-review-package-2026-07-08.md` — 部门评审资料包

Reviewed（本次会话修复的已有文档，未经用户逐份 review）：
- `docs/02-domain-and-data/zhisuan-ops-domain-model.md` — ObservationPlan 重设计、health_score/power_on_days 修正、状态机修复、集成表修正
- `docs/02-domain-and-data/external-system-integration-map.md` — 监控/CMDB/ITR 集成约束修正
- `docs/02-domain-and-data/spare-management-domain-design.md` — 库存 SoT 矛盾修复
- `docs/01-business-design/operations-management-design.md` — SLA 定义修正、MTTR 公式修正
- `docs/01-business-design/service-product-catalog-design.md` — SLA 计时规则修正
- `docs/03-architecture-and-protocol/agent-orchestration-architecture-design.md` — device_status → asset_profile_read 重命名
- `docs/00-vision-and-scope/platform-vision-and-scope.md` — 监控/仪表盘措辞修正
- `docs/01-business-design/organization-and-roles.md` — 组织架构称谓修正（总经理/部长/副部长/业务组）

User-approved:
- 无。所有新文档状态为 candidate，尚未获得用户正式批准。

Active:
- `artifacts/README.md` v2.0 — 重构后的文档索引入口（active，本次会话已更新）

Evidence（评估与审查产出）：
- `work/reviews/agentic-design-assessment-2026-07-08.md` — 首次 7 维度综合评估
- `work/reviews/department-review-package-2026-07-08.md` — 部门评审资料包
- `docs/02-domain-and-data/external-system-integration-map.md` — 事实来源矩阵、集成模式、降级策略

## Key Decisions

| 决策 | 状态 | 来源 |
|---|---|---|
| 智算服务部双重职责（运维+平台建设），平台先自用后推广 | active | `platform-vision-and-scope.md` §1.1 |
| 平台无法直连客户机房服务器，日志通过上传/邮件/Chat 获取是合法的 | active | 多文档约束修正 |
| ObservationPlan 从自动指标采集改为人工执行 checklist + 平台提醒 | candidate | `zhisuan-ops-domain-model.md` §3.6 |
| 组织称谓：总经理（顶层）、部长/副部长（部门）、业务组（子单元） | candidate | `organization-and-roles.md` §2 |
| 备件库存 SoT：WMS 是物理库存事实来源，SpareInventory 是平台运营投影 | candidate | `spare-management-domain-design.md` §2.3 |
| 监控系统在集成中降级为"可选信号源"而非事实来源 | candidate | `external-system-integration-map.md` §3.6 |
| Phase 1 MVP 聚焦智算机房故障处理闭环，暂不实现合同/服务产品/客户 360 | active | `mvp-scope-definition.md` |
| 目录结构：docs/（正式设计）/ work/（过程性）/ assets/（附件） | active | `README.md` |

## Open Questions

| 问题 | owner | 影响 |
|---|---|---|
| 11 份新设计文档是否被用户正式批准？（当前全为 candidate） | 用户 | 若不批准，实施依据不成立 |
| 部门评审资料包分发后反馈如何？是否需要调整设计？ | 四部门负责人 | 影响 Phase 1 范围确认 |
| CRM/CMDB/WMS/ITR 等外部系统的事实来源系统具体是哪一家？ | 用户 + IT | 阻塞 `external-system-integration-map.md` 落地 |
| 备件系统在 Phase 1 是真实出库还是模拟执行？ | 用户 + 运作管理部 | 影响开发范围 |
| 恢复时间 SLA 的故障开始时间如何采集？（以 Case 创建时间替代是否可接受？） | 用户 + 运作管理部 | 影响 SLA 履约计算准确性 |
| 工程师工时数据在 Phase 1 从哪来？（DispatchPlan 近似替代？） | 用户 + 运作管理部 | 影响 OPS_ENGINEER_UTILIZATION 等 KPI |

## Risks

- **candidate/approved 混淆**：11 份新文档均为 candidate，如被误读为 approved 可能导致未评审设计直接进入开发
- **上下文膨胀**：本会话跨 4 轮大型文档操作，下一会话需通过本 handoff 快速定位当前状态
- **跨文档一致性问题未全部修复**：上次评估报告中的 IC-01 到 IC-12 不一致项（如审批 API 两态 vs 三态、SSE 事件映射、NATS 降级落地）多数仍为 open
- **部门评审反馈可能触发大规模修改**：建议在反馈回来之前不再新增文档，专注修复和收敛
- **硬性约束违反可能残留**：虽然本轮已修复 P0/P1 违规，但更隐蔽的假设（如文档措辞中"实时""自动"等词）可能仍有遗漏

## Next Session First Step

1. 阅读 `artifacts/README.md`（新版索引）确认目录结构
2. 阅读 `artifacts/work/reviews/agentic-design-assessment-2026-07-08.md` 了解上次评估全貌
3. 确认用户是否已分发部门评审资料包、是否已有反馈
4. 基于反馈或用户指令，选择下一动作：
   - **修复剩余跨文档不一致项**（IC-01 ~ IC-12）
   - **补齐缺失的 5 份 P0/P1 设计文档**（business-kpi-definition、model-iteration-playbook、risk-confidence-decision-matrix、redteam-test-plan、fallback-response-design）
   - **将 candidate 文档提请用户逐份批准**
   - **进入 Sprint 0 Go/No-Go 评审**

## Startup Prompt

```text
Project root: C:\Users\Administrator\Documents\trae_projects\yb\harness\.codex\tasks\tk-20260614-001-agentic-backend-orchestration-design\artifacts

Current state:
- 设计文档集已完成目录重构（docs/ + work/ + assets/）
- 71 份正式设计文档 + 40+ 份过程性文档
- 本轮会话新增 11 份 candidate 设计文档
- 修复了 20+ 处"平台无法直连客户机房"约束违规
- 组织架构称谓已统一为总经理/部长/副部长/业务组
- 部门评审资料包已生成于 work/reviews/department-review-package-2026-07-08.md
- 11 份新文档状态为 candidate，尚未用户批准
- 跨文档一致性修复（IC-01 ~ IC-12）未全部完成
- 缺失的 5 份 P0/P1 设计文档尚未补齐

Must read first:
- artifacts/README.md
- artifacts/work/reviews/agentic-design-assessment-2026-07-08.md
- artifacts/work/reviews/department-review-package-2026-07-08.md

Mode: write-docs（仅设计文档，不写代码）
Forbidden: 代码/部署/数据库/安装 skill/MCP/agent
Hard constraint: 平台无法直连客户机房服务器，日志通过上传/邮件/Chat 获取合法

Next action:
请先确认部门评审资料包是否已分发、是否有反馈，然后决定下一步行动方向。
```
