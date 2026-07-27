---
document_id: loop-engine-lab-material-library-review-t0036-v1
title: T-0036 软件工程与提示词/Agent 素材库用户评审包
document_class: review_artifact
depth_profile: detailed
maturity: authoring-ready
maturity_target: authoring-ready
status: candidate-ready-for-independent-review
confidentiality: project-internal
---

# T-0036 素材库用户评审包

## 1. 这是什么

T-0036 建立的是 Loop 工程候选素材库，不是运行时规则、全量提示词包或已批准的工程标准。它的作用是让后续 Codex Loop 能从可追溯来源中选择软件工程知识、模板、检查方式和输出范式，再经过项目配置与用户 Gate 才能进入执行。

本包是 T-0036 候选交付包的用户可读说明和决策入口。它不是独立评审报告，也不是用户对候选基线的接受记录。

## 2. 当前候选资产

| 资产 | 数量/状态 | 说明 |
| --- | ---: | --- |
| `materials/catalog.yaml` | 46 条 | 每条有统一材料元数据、来源、适用/禁用边界和 Loop 适配说明 |
| 模板 | 28 个 | 需求、架构、API、测试、安全、发布、运维、角色、工作包和人工评审等 |
| Framework | 3 个 | 素材组合、来源到 Loop 映射、提示词/Agent 评估 |
| Profile | 2 个 | 项目画像和素材选择记录 |
| 覆盖矩阵 | 14 个领域 | 明确已有覆盖、候选状态和待补缺口 |
| 来源核验 | 46 条 | 29 `content_read`、4 `url_verified_only`、4 `access_blocked`、9 `not_yet_checked` |

## 3. 素材如何分级

### 3.1 来源类型

- `official_standard` / `official_guidance` / `official_tooling`：优先作为事实和工程入口，但仍要锁定版本与适用范围。
- `industry_practice`：成熟工程实践，必须标明适用条件，不能自动升级为规范。
- `methodology`：过程方法，提供组织和反馈原则，不替代项目具体验收。
- `template`：输出结构骨架，不代表内容已经完成。
- `research_paper`：实验或研究参考，不能独立作为生产门禁。
- `loop_adaptation`：本项目的适配层，必须持续引用外部来源并接受独立评审。

### 3.2 证据等级

- `E1`：可直接读取的官方规范、官方文档或官方工具说明。
- `E2`：官方入口、权威摘要或正式出版物入口，正文可能受访问/版权限制。
- `E3`：成熟工程实践、开源文档或行业方法论。
- `E4`：研究论文、实验性 Agent 方法或 Loop 自定义设计，不能单独作为生产门禁。

当前统计：E1 10 条、E2 8 条、E3 24 条、E4 4 条。证据等级不是项目结论，项目仍需按风险、技术栈和用户目标选材。

## 4. 适用场景和选用规则

1. 先根据项目意图、项目类型、风险和阶段选择领域，再选择来源、方法、模板和工具。
2. 优先使用 `content_read` 且来源层级匹配的材料；`url_verified_only`、`access_blocked` 和 `not_yet_checked` 只能作为候选线索，不能被描述为已核验正文。
3. 每次选择都要记录材料 ID、版本/日期、选择理由、拒绝或裁剪理由、输入、输出、检查器和剩余风险。
4. 规范、实践、方法论、模板、工具和 Loop 适配层保持分层；模板只规定产物形状，不替代事实和验收。
5. 一个 Work Packet 只装载任务需要的材料，不把全库或所有角色提示词放进上下文；超过预算时先裁剪并记录原因。
6. 涉及安全、数据、生产、部署、迁移或合规的项目，必须重新核验来源和项目约束，不能直接复用本库候选结论。

## 5. 禁止误用

- 不把博客、搜索摘要、入口页或模型自报当作已核验规范。
- 不把 `PASS`、测试通过、覆盖率、构建成功或 AI 推荐解释为用户验收或生产认证。
- 不把提示词结构当作角色行为能力证明；角色必须有输入/输出 Schema、能力探针、权限边界和失败处理。
- 不把研究论文或 Loop 自定义适配单独升级为硬门禁。
- 不复制受版权保护的规范正文；只保留元数据、短摘要、来源观察和适配说明。
- 不因材料进入 catalog 就认为它已成为 Codex Loop 规则；候选基线仍待独立评审和用户决定。

## 6. 覆盖结论

当前覆盖矩阵包含提示词工程、Agent/工具/上下文、AI 风险、需求、生命周期、架构、API/数据契约、编码、测试、安全、交付/供应链、运维/可观测性、文档/人工评审和 Loop 自定义层。覆盖表示已有候选来源与模板，不表示穷尽、合规或生产就绪。

主要未覆盖/待补方向：模型评估与数据集版本化、长上下文与缓存、配置管理和发布签名、迁移/备份/隐私、可访问性与移动端、行业合规、跨宿主互操作实测、真实项目数据校准。

结构性注意：覆盖矩阵将交付/供应链作为独立领域，但 catalog 当前主要通过 `SEC-004`、`OPS-003..004` 表达，未建立独立 `delivery` category；这不是静默补齐，留给独立评审决定是否需要拆分。

## 7. 用户可以看到的候选使用流程

```text
用户意图
  -> 项目类型与风险画像
  -> 检索候选素材
  -> 选择/拒绝/裁剪并记录理由
  -> 形成 project-profile / phase-profile / quality-profile
  -> 独立评审与证据检查
  -> 用户 Gate 决定是否进入项目执行
```

用户主要决定目标、可见行为、重大取舍、剩余风险和是否继续；材料的来源、Schema、权限、质量和证据检查由 Loop 内部负责，但任何内部结论都不能代替用户 Gate。

## 8. 完整性对标

| 源材料/资产 | 当前适配 | 适配位置 | 未适配或限制 |
| --- | --- | --- | --- |
| `material-schema.yaml` | 已适配 | catalog 46 条材料的 17 个必填字段 | `retrieved_at` 为补充字段，当前只在 catalog 顶层/来源登记记录日期 |
| `source-register.md` | 已适配 | 来源层级、最终 URL、页面标题、访问状态和受限处理 | 17 条材料仍不是 `content_read` |
| `coverage-matrix.md` | 已适配 | 本包第 6 节和覆盖/重复检查报告 | 待补队列仍未完成 |
| `templates/` | 已适配 | 本包第 2、4、7 节和模板引用检查 | 模板内容仍需项目化裁剪 |
| `frameworks/` 与 `profiles/` | 已适配 | 来源到 Loop 映射和选择记录 | 不得把 Loop 适配层当作外部标准 |
| T-0036 simulation | 作为示例适配 | `.ai/evidence/T-0036/simulation/` | 仅设计模拟，不是 Runtime 或真实 Agent 执行证明 |

## 9. Self-Audit

- [x] 已逐项对比 catalog、schema、source register、coverage matrix、templates、frameworks、profiles 和 simulation。
- [x] 已显式列出未核验来源、覆盖缺口、分类映射注意和未决用户决定。
- [x] 未把“有材料”写成“已接受基线”，未用“见原版”替代来源状态说明。
- [x] 已声明当前成熟度为 `authoring-ready`，但没有宣称 `publish-ready`、生产合规或候选基线已接受。
- [x] 已把覆盖/重复检查作为独立证据文件，而不是只在本包中口头声称完成。

## 10. 当前用户决定

本 Gate 仅完成候选交付包。下一步必须另设 T-0036 独立评审 Gate，完成独立评审、必要修复和独立复审后，用户再决定是否接受 T-0036 为 Codex Loop 候选素材基线并冻结版本。

当前结论：`candidate / ready_for_independent_review / baseline_not_accepted`
