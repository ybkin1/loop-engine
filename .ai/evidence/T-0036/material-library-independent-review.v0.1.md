---
document_id: loop-engine-lab-material-library-independent-review-t0036-v0.1
title: T-0036 全新独立只读评审报告
document_class: evidence_only_review
gate_id: G-T-0036-FRESH-INDEPENDENT-REVIEW-V0-1
reviewer_agent_id: 019f8e41-8ff8-7fa0-be82-448aa615f271
reviewer_context: fresh_spawned_read_only_context_without_parent_thread_history
verdict: REPAIR_REQUIRED
---

# T-0036 全新独立只读评审报告

## 1. 身份、独立性与边界

- 评审 Gate：G-T-0036-FRESH-INDEPENDENT-REVIEW-V0-1。
- 评审者：全新 spawned auditor 上下文，agent id 为 019f8e41-8ff8-7fa0-be82-448aa615f271。
- 上下文：不继承父会话历史的只读审计上下文；评审者从磁盘重新读取任务、冻结清单、候选素材和既有证据。
- 评审者未修改冻结对象、未创建评审证据、未执行修复、未复审、未接受基线、未冻结版本、未评审 T-0037，也未进入 Host Integration。
- 本报告由主控作为证据记录器追加写入；报告内容来自独立评审者的结构化结果及主控侧只读复核。

## 2. 冻结输入前置检查

冻结清单：.ai/evidence/T-0036/material-library-independent-review-freeze-manifest.v0.1.md

| 检查项 | 结果 |
| --- | --- |
| 冻结对象数量 | 58 |
| 相对路径存在 | 58/58 |
| 字节数一致 | 58/58 |
| SHA-256 一致 | 58/58 |
| 评审前后冻结漂移 | 0 |
| 哈希/路径不一致处理 | 未触发 BLOCKED |

前置检查确认后才开始内容评审。冻结对象继续保持只读。

## 3. 独立评审方法

- 从 .ai/tasks/T-0036.md 重建验收条件和非目标，不把完成包的自检结论直接当作 PASS。
- 检查 materials/catalog.yaml 的材料数量、必填字段、authority/source_type/verification_status 等分类与枚举边界。
- 对 source-register.md 与 catalog.yaml 的材料 ID、来源状态和核验粒度做交叉核对。
- 检查 coverage-matrix.md、coverage-duplication-review.md 和用户可读评审包之间的覆盖和结论边界。
- 检查模板、framework、profile、simulation 的路径引用、实例闭包、配置作用域和 design-only 声明。
- 抽查并重现结构性断言：46 条材料、17 个必填字段、67 次模板等引用/29 个唯一路径、覆盖矩阵展开后的材料 ID 数量和 authority 枚举。
- 将结构完整性、来源正文真实性、语义重复、生产适用性和用户基线接受分开判断。

## 4. 可复现基础结果

- catalog 材料数量：46。
- catalog 必填字段：17 个字段均存在且非空；这不等于枚举值全部合法。
- authority 枚举违规：1 条，见 F-001。
- source-register 缺少 catalog ID：8 条，见 F-002。
- 本地模板等引用：67 次、29 个唯一路径，未发现悬空路径。
- 模板/framework/profile 文件数量：28/3/2；T-0036 simulation 文件数量：11。
- simulation 任务节点/角色：20/12；既有模拟依赖、owner 和 critical path 结构检查未发现循环。
- coverage-matrix 展开后的材料 ID：45；catalog 材料 ID：46；差异为 ARCH-004，见 F-004。

## 5. 发现

### F-001 — P1：catalog 存在 authority schema 枚举违规

- 对象：materials/catalog.yaml:802-807。
- 对照：materials/material-schema.yaml:27。
- 证据：DOC-001 的 authority 为 industry_practice；material-schema.yaml 的 authority 允许值为 international_standard、government、official_vendor、industry_body、open_source_project、research_literature、community_method、loop_project，不包含 industry_practice。
- 影响：字段齐全不等于 Schema 合法；枚举型消费者可能拒绝该材料或错误分类，破坏材料库的可组合性和可验证性。
- 建议处置：另设修复 Gate，确定 DOC-001 的正确 authority 枚举归类或扩展 schema 后，重新执行枚举校验。

### F-002 — P1：source register 与 catalog 的来源登记不闭合且存在状态冲突

- 对象：materials/source-register.md:11-53；materials/catalog.yaml:441-477、840-865。
- 证据：source-register 仅出现 38 个 catalog ID，未出现 AGENT-002、AGENT-003、ARCH-004、API-004、CODE-002、CODE-003、LOOP-001、LOOP-002。
- 进一步证据：CODE-002、CODE-003 在 catalog 标记为 content_read，但 source-register 没有对应记录；DOC-002 在 catalog 标记为 not_yet_checked，而 source-register:38 标记为 url_verified_only。
- 影响：来源核验状态不能从两个核心登记文件一致重建；后续选择器可能把未登记或状态冲突的材料当作已核验输入。
- 建议处置：另设修复 Gate，明确 source-register 是否必须覆盖全部 catalog；若必须覆盖，补齐 8 条记录并统一 DOC-002 状态及逐条证据。

### F-003 — P1：simulation profile 引用了不存在的 phase-profile 实例

- 对象：.ai/evidence/T-0036/simulation/project-profile.v0.1.yaml:12。
- 引用：PHASE-PROFILE-T0036-SIM-FULL-DESIGN-V0.1。
- 证据：冻结的 simulation 目录没有该 ID 对应的具体 profile 实例文件，只有通用模板 materials/templates/phase-profile.yaml。
- 影响：simulation 的配置引用闭包不能完整复现；模板存在不能替代被引用的具体实例，后续消费者无法确定实际阶段配置。
- 建议处置：另设修复 Gate，补充可追踪的 phase-profile 实例或改为现存实例引用，并重跑引用闭包检查。

### F-004 — P2：覆盖矩阵漏列 catalog 材料

- 对象：materials/coverage-matrix.md:14；materials/catalog.yaml:327。
- 证据：coverage-matrix 在系统架构行列出 ARCH-001..003；catalog 另有 ARCH-004。展开覆盖 ID 后为 45 个，而 catalog 有 46 个，catalog_not_in_coverage 为 ARCH-004。
- 影响：覆盖矩阵与材料目录不完全一致，可能低估架构素材资产，也会让用户无法判断 ARCH-004 是遗漏还是有意排除。
- 建议处置：另设修复 Gate，补入 ARCH-004 或明确记录其排除理由和影响。

### F-005 — P2：simulation profile 与 material selection 的组合边界不清晰

- 对象：.ai/evidence/T-0036/simulation/project-profile.v0.1.yaml:1、10-12；.ai/evidence/T-0036/simulation/material-selection.v0.1.yaml:1-2、6、63。
- 证据：project-profile 使用 project_profile_id，selected_materials 为 17 条，并引用 phase_profile；material-selection 使用 project_profile，selected_materials 为 8 条，模板使用完整 materials/templates/ 路径。文件没有 selection_scope、有效版本或 subset 关系来说明 8 条是否为 17 条的阶段子集。
- 影响：后续消费者无法确定两份配置的加载关系和审查范围，可能加载超出已选定或已审查范围的材料。
- 建议处置：另设修复 Gate，增加 selection ID、作用域、版本或 subset 关系，并统一字段名和路径格式。

### F-006 — P2：来源新鲜度和逐条最终 URL 记录粒度不足

- 对象：materials/material-schema.yaml:38-40；materials/catalog.yaml:2；materials/source-register.md:3、9-53。
- 证据：catalog 只有顶层 retrieved_at: 2026-07-22；46 条材料均没有逐条 retrieved_at。source-register 只有全局核验日期和逐条来源状态/观察的混合记录，未形成统一的逐条 HTTP 状态、最终 URL、页面标题和检索时间字段闭包。
- 影响：来源重定向、版本漂移、逐条复核时间和访问失败原因难以统一审计；这会削弱未来基线冻结后的可追溯性。
- 建议处置：由用户在候选基线决策前决定全局日期是否足够；若不够，另设修复 Gate 补充逐条检索时间、HTTP/最终 URL、页面标题和失败原因。

## 6. 限制与未覆盖

- 本次没有联网重新读取外部来源正文，不能独立证明来源正文真实性；当前仍有 17 条材料不是 content_read。
- 精确重复检查确认无 ID、标题、URL、描述字段精确重复，阈值 0.72 以上的文本相似对为 0；这不等于不存在语义重复、来源冲突或生产适用性问题。
- simulation 的 design-only 边界成立：既有文件标记 simulation_only、planned_not_executed；这些文件不证明真实 Agent、Runtime、模型行为或 Host Adapter 已运行。
- 本次不作候选基线接受、版本冻结、用户验收或 T-0037 评审许可。

## 7. 证据性结论

Verdict：REPAIR_REQUIRED

P1 findings：F-001、F-002、F-003。

P2 findings：F-004、F-005、F-006。

该 verdict 仅是 G-T-0036-FRESH-INDEPENDENT-REVIEW-V0-1 的证据结论。它不授权修复、复审、候选基线接受、版本冻结、任务关闭、T-0037 评审或 Codex Host Integration。
