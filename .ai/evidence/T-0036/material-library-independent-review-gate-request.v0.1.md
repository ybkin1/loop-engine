# T-0036 全新独立评审 Gate 请求 v0.1

Gate ID：G-T-0036-FRESH-INDEPENDENT-REVIEW-V0-1

状态：pending / user_decision_required

## 请求用户决定

是否批准对已冻结的 T-0036 候选素材库执行一次全新、独立、只读、可复现的评审。批准只授权后续独立评审；不代表评审通过、候选基线接受、版本冻结、修复、复审、T-0037 评审或 Codex Host Integration。

用户可选决定：

- 批准 G-T-0036-FRESH-INDEPENDENT-REVIEW-V0-1
- 拒绝 G-T-0036-FRESH-INDEPENDENT-REVIEW-V0-1

批准后仍需用户另行发出精确执行请求，才可开始评审。

## 前置事实

- T-0036 候选交付包已在 G-T-0036-COMPLETE-MATERIAL-LIBRARY-REVIEW-PACKET-V0-1 下完成。
- 已有确定性证据为：46 条材料、28 个模板、3 个 framework、2 个 profile；schema 必填字段 46/46；结构性重复和悬空模板引用检查通过。
- 17 条来源尚不是 content_read；覆盖缺口、分类映射、单条检索日期和语义重叠仍需独立判断。
- T-0036 尚未被用户接受为 Codex Loop 候选素材基线，也尚未完成最终版本冻结。
- 旧的 T-0038/T-0037 评审 Gate 已因顺序修正而 superseded，不属于本 Gate 范围。

## 精确评审范围

- 从冻结清单重建 T-0036 的验收条件、候选资产边界和用户可读结论。
- 独立检查来源核验状态、来源层级、证据等级、版本/日期记录和受限来源处理。
- 独立检查 catalog schema、材料分类、适用场景、禁止误用、风险、输入/输出、模板/Schema 和 Loop 适配边界。
- 独立检查模板、framework、profile、覆盖矩阵、覆盖缺口与重复内容检查之间的一致性。
- 独立检查用户可读评审包是否明确区分候选素材、外部来源、Loop 适配层、未覆盖项和用户决定项。
- 独立检查 T-0036 simulation 是否被明确限制为设计模拟，而不是 Runtime、真实 Agent 或模型行为证明。
- 可在不改变冻结对象的前提下重现选定结构检查；所有重现结果均为证据，不自动构成 PASS。
- 输出一个带有要求、对象、复现步骤、证据、影响和处置建议的证据性 verdict。

## 冻结评审输入

- manifest：.ai/evidence/T-0036/material-library-independent-review-freeze-manifest.v0.1.md
- frozen_subject_count：58
- hash_or_path_mismatch_result：BLOCKED
- 冻结对象包含 materials/ 全部候选素材文件，以及既有 T-0036 完成交付、来源核验、覆盖和 simulation 证据。
- 冻结对象不包含本 Gate 的请求、冻结清单、登记命令、未来评审输出和治理状态投影文件。

## Gate 登记阶段允许路径

- .ai/tasks/T-0036.md
- .ai/evidence/T-0036/material-library-independent-review-gate-request.v0.1.md
- .ai/evidence/T-0036/material-library-independent-review-freeze-manifest.v0.1.md
- .ai/evidence/T-0036/material-library-independent-review-registration-commands.v0.1.md
- .ai/gates.yaml
- .ai/state.yaml
- .ai/task_graph.yaml
- .ai/HANDOFF.md
- .ai/DECISIONS.md

## 获得批准并收到后续精确执行请求后的允许路径

- .ai/evidence/T-0036/material-library-independent-review.v0.1.md
- .ai/evidence/T-0036/material-library-independent-review-commands.v0.1.md
- .ai/evidence/T-0036/material-library-independent-review-validation.v0.1.md
- .ai/evidence/T-0036/material-library-independent-review-changed-path-manifest.v0.1.md
- .ai/gates.yaml
- .ai/state.yaml
- .ai/HANDOFF.md

## 独立性要求

- 评审必须从全新上下文开始，且不得是创建或整理 T-0036 候选交付包的同一作者上下文。
- 评审者不得把完成包、validator、结构检查、测试或先前 AI 结论直接当作 PASS 证明，必须独立重建并复现关键断言。
- 评审报告必须披露评审者身份、上下文、可见证据、未覆盖范围和任何独立性限制。
- 无法建立独立性时，须在实质性评审前返回 BLOCKED 或 USER_DECISION_REQUIRED。

## Verdict 约束

允许值：PASS、REPAIR_REQUIRED、BLOCKED、USER_DECISION_REQUIRED、SCOPE_VIOLATION。

Verdict 仅是证据，不授权：

- 修改或修复冻结对象；
- T-0036 复审、候选基线接受或最终版本冻结；
- T-0036 任务关闭、项目 PASS 或用户验收；
- 创建下游任务或 Gate；
- T-0037 独立评审或 Codex Host Integration；
- 安装、激活、部署、迁移、运行时/工具/skill/MCP/plugin/automation/hook/protocol 启用；
- 真实模型行为认证或真实业务项目进入。

## 禁止事项

- 不得修改、删除、重命名、规范化或追加任何冻结评审输入。
- 不得在 Gate 批准前或没有后续精确执行请求时开始实质性评审。
- 不得执行修复、复审、基线接受、版本冻结或 T-0037 评审。
- 不得把来源数量、覆盖率、测试、验证器或 AI 推荐解释为用户接受。
- 不得修改全局 Codex、AGENTS.md、skill、MCP、plugin、automation、hook 或协议行为。
- 不得部署、改库、改权限、处理密钥/支付/生产数据、迁移或进入外部业务项目。

## 验证计划

- 严格 UTF-8 读取并解析新增 Markdown/YAML 证据。
- 实质性评审前按冻结清单逐一核对 58 个文件的相对路径、字节数和 SHA-256；任一失败即 BLOCKED。
- 评审后再次核对 58 个冻结对象，确认评审只产生允许的新增证据和治理投影。
- 对 catalog、schema、source register、coverage matrix、templates、frameworks、profiles 和 simulation 做独立结构复核。
- 运行 validate_state.py、audit_handoff.py 和 git diff --check。
- 确认 verdict 仍为证据性结论，未改变用户决策边界或下游顺序。

## 回滚与失败恢复

- 冻结输入哈希、路径或字节数不一致时，在内容评审前停止并记录 BLOCKED。
- 独立性不足时停止并记录 BLOCKED 或 USER_DECISION_REQUIRED，不继续推断。
- 路径越界或发生禁止效果时记录 SCOPE_VIOLATION，并保留真实的部分证据。
- 不删除或重写历史 T-0036、T-0037、T-0038 证据；任何破坏性恢复都需要单独 Gate。
- 发现需要修复时只记录发现，另行创建修复 Gate；不得在本 Gate 内修复。

## 当前结论

pending / user_decision_required / review_not_started / baseline_not_accepted
