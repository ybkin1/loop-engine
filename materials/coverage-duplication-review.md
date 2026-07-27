---
document_id: loop-engine-lab-coverage-duplication-review-t0036-v1
title: T-0036 覆盖缺口与重复内容检查
document_class: review_artifact
depth_profile: detailed
maturity: contract-ready
maturity_target: contract-ready
status: candidate-evidence-only
confidentiality: project-internal
---

# T-0036 覆盖缺口与重复内容检查

## 1. 检查边界

本报告是 T-0036 完成包的确定性结构检查，不是 T-0036 独立评审，不作候选基线接受决定。检查对象为 `materials/catalog.yaml`、`materials/material-schema.yaml`、`materials/source-register.md`、`materials/coverage-matrix.md`、`materials/templates/`、`materials/frameworks/` 和 `materials/profiles/`。

## 2. 可复现方法

1. 使用 PyYAML 解析 `catalog.yaml` 和 `material-schema.yaml`。
2. 对 46 条材料检查 schema 声明的 17 个必填字段。
3. 对 `material_id`、标准化 `title`、标准化 `source_url` 做精确重复检查。
4. 对 `problem_solved`、`when_to_use`、`when_not_to_use`、`adaptation_notes` 做标准化文本精确重复检查。
5. 将 `problem_solved + adaptation_notes` 做标准化序列相似度检查，阈值为 `0.72`；该检查只发现潜在文本重复，不代替人工语义评审。
6. 收集所有 `template_or_schema` 中的模板/framework/profile 路径，与磁盘文件清单比较。
7. 对 `verification_status`、`evidence_level`、覆盖矩阵领域和待补队列做一致性盘点。

## 3. 检查结果

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| catalog 材料数量 | `46` | 结构解析成功 |
| schema 必填字段 | `46/46` | 17 个字段均存在且非空 |
| `material_id` 精确重复 | `0` | 未发现重复 ID |
| `title` 精确重复 | `0` | 标准化标题无重复 |
| `source_url` 精确重复 | `0` | 标准化来源 URL 无重复 |
| 主要描述字段精确重复 | `0` | 四个文本字段均无精确碰撞 |
| 高相似文本对 | `0` | 序列相似度 `>=0.72` 未发现配对 |
| 模板等路径引用 | `67` 次 / `29` 个唯一路径 | 重复引用表示复用，不等于重复材料 |
| 悬空模板等路径 | `0` | 所有 29 个唯一路径存在 |
| 模板文件 | `28` | `materials/templates/` |
| framework 文件 | `3` | `materials/frameworks/` |
| profile 文件 | `2` | `materials/profiles/` |

## 4. 来源和覆盖缺口

| 缺口/风险 | 当前事实 | 处理建议 |
| --- | --- | --- |
| 非正文核验来源 | 4 `access_blocked`、4 `url_verified_only`、9 `not_yet_checked`，共 17 条 | 独立评审时检查是否可以保留为候选、降级证据或替换来源 |
| 单条材料检索日期 | catalog 顶层有 `retrieved_at: 2026-07-22`，但 46 条材料没有单条 `retrieved_at` | 如用户考虑接受基线，先决定是否补齐单条日期 |
| 交付/供应链分类 | 覆盖矩阵有独立领域，但 catalog 主要用 `SEC-004`、`OPS-003..004` 表达 | 独立评审决定保持映射还是增加独立 category |
| 领域覆盖 | 覆盖矩阵列出 14 个领域和 8 条待补队列 | 缺口不能被当前 46 条材料隐式视为已覆盖 |
| 语义重复 | 确定性相似度检查未发现高相似对 | 仍需独立评审判断同义材料、互补材料和过度重叠 |

## 5. 判定边界

- `0` 个结构性重复不等于材料内容没有语义重叠。
- `0` 个悬空路径只证明当前引用路径存在，不证明模板内容适用。
- `46/46` schema 完整只证明字段齐全，不证明来源正文已核验或材料适合所有项目。
- 17 条非 `content_read` 材料仍然是候选状态，不得作为已阅读标准正文引用。
- 本报告不会把 `PASS`、结构检查成功或 AI 建议转换为用户的基线接受。

## 6. Self-Audit

- [x] 检查规则、阈值、输入文件和结果均已落盘。
- [x] 结构重复、路径悬空、来源状态和覆盖缺口被分别报告。
- [x] 没有把确定性检查扩大解释为语义独立评审。
- [x] 未修改 catalog、schema、source register、coverage matrix 或历史 T-0036 证据。
- [x] 未生成 T-0036 baseline freeze、独立评审 verdict、修复结论或 T-0037 许可。

当前结论：`structural-check-complete / independent-review-required / baseline-not-accepted`
