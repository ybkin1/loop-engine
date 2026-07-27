# T-0036 素材库候选交付包完成 Gate 请求 v0.1

Gate ID：`G-T-0036-COMPLETE-MATERIAL-LIBRARY-REVIEW-PACKET-V0-1`

状态：`pending / user_decision_required`

## 请求用户决定

是否批准在现有 T-0036 候选素材库基础上，补齐用户可读素材库评审包、覆盖缺口与重复内容检查，并完成结构/来源/分类证据收口。批准只授权候选交付包补齐，不代表独立评审通过、候选基线接受、T-0037 评审或 Host Integration。

## 已有基础

- `materials/catalog.yaml`：46 条候选材料及统一元数据。
- `materials/templates/`：28 个可组合的软件工程、Agent、质量、安全、交付和人工评审模板。
- `materials/source-register.md`：来源层级、联网核验状态、最终 URL 和受限来源处理。
- `materials/coverage-matrix.md`：领域覆盖、缺口和待补队列。
- `.ai/evidence/T-0036/source-validation.v0.1.md`、`coverage-matrix.v0.1.md` 和 simulation evidence。

## 精确范围

- 核对并整理来源核验与证据分级：官方规范/官方文档、权威工程实践、方法论、模板、可执行工具、AI/Agent 专门实践和 Loop 适配层。
- 核对软件工程模板、规范、案例、用例和输出范式的分类、引用关系、适用条件和产出边界。
- 补充适用场景、风险、禁止误用和选用规则的用户可读说明。
- 执行覆盖缺口与重复内容检查，区分“缺失”“重复”“待复核”“仅入口页”“不可作为硬约束”的状态。
- 生成用户可读的 `material-library-review-packet`，列出已完成、未覆盖、待复核、候选基线边界和用户后续需要决定的事项。
- 运行素材库结构检查、YAML/Markdown 读取、`validate_state.py` 和 `git diff --check`。

## 登记阶段允许路径

- `.ai/tasks/T-0036.md`
- `.ai/evidence/T-0036/`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/task_graph.yaml`
- `.ai/HANDOFF.md`
- `.ai/DECISIONS.md`

## 获得批准并收到后续精确执行请求后的允许路径

- `materials/material-library-review-packet.md`
- `materials/coverage-duplication-review.md`
- `.ai/evidence/T-0036/material-library-completion-validation.v0.1.md`
- `.ai/evidence/T-0036/material-library-completion-changed-path-manifest.v0.1.md`
- `.ai/evidence/T-0036/commands.md`
- `.ai/tasks/T-0036.md`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/task_graph.yaml`
- `.ai/HANDOFF.md`

## 明确禁止

- 不执行 T-0036 独立评审、修复、复审或候选基线接受。
- 不冻结 T-0036 版本；冻结必须发生在独立评审、修复和复审完成且用户作出基线决定之后。
- 不评审或修改 T-0037，不执行真实模型，不进入 Codex Host Integration。
- 不把来源、模板、覆盖率、validator、测试或 AI 结论当作用户基线接受。
- 不修改全局 Codex、`AGENTS.md`、skill、MCP、plugin、automation、hook、生产数据或外部业务项目。

## 验证计划

- 逐项核对 catalog schema、来源登记、证据等级、模板目录、coverage matrix 和新增评审包的一致性。
- 对材料 ID、模板路径、source URL、verification status、category 和 evidence level 做结构检查。
- 明确记录重复内容判定规则、未覆盖项、访问受限来源和不得提升为硬约束的材料。
- 生成 changed-path manifest；确认 T-0037、全局配置和历史证据未变。
- 执行完成后停止，下一步必须另设 T-0036 独立评审 Gate。

## 回滚与恢复

- 只回滚本 Gate 后续产生的两个 `materials/` 评审包和 T-0036 新增验证证据；不删除历史来源或原有证据。
- 发现路径越界、来源状态伪造、重复检查不可复现或结构检查失败时停止并保留事实。
- 任何删除、重写来源历史、修复扩展、版本冻结、基线接受或下游 Gate 都需要另一个明确 Gate。

## 用户决策短语

- 批准：`批准 G-T-0036-COMPLETE-MATERIAL-LIBRARY-REVIEW-PACKET-V0-1`
- 拒绝：`拒绝 G-T-0036-COMPLETE-MATERIAL-LIBRARY-REVIEW-PACKET-V0-1`
- 执行：`执行 G-T-0036-COMPLETE-MATERIAL-LIBRARY-REVIEW-PACKET-V0-1`
