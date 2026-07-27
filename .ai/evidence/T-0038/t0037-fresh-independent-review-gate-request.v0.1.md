# T-0038 对 T-0037 独立评审 Gate 请求 v0.1

Gate ID：`G-T-0038-T0037-FRESH-INDEPENDENT-REVIEW-V0-1`

状态：`pending / user_decision_required`

## 请求用户决定

是否批准对 T-0037 Codex 侧 Loop 工程候选实现执行一次全新上下文、独立、只读评审。批准只授权后续独立评审，不授权修复、真实模型执行、Host Integration、安装、激活、发布或用户验收。

## 评审对象

- T-0037 的本地 Codex-only 候选源码、测试和文档。
- T-0037 已生成的角色、阶段、任务、运行、功能设计包、Human Review Packet 和确定性验证证据。
- 冻结对象共 62 个文件，完整路径、字节数和 SHA-256 见冻结清单。

## 精确评审范围

- 独立复核需求与架构覆盖：角色合同、短提示词、输入/输出 Schema、工具和写入边界、停止/否决条件、能力探针及交接协议。
- 独立复核状态与隔离：项目意图路由、素材选择、上下文预算、RoleRunEnvelope、权限隔离、任务图、Gate 和修复/回归边界。
- 独立复核用户交付：Functional Design Packet 的使用方法、页面/元素/跳转、后端接口/数据/错误/安全、性能/可维护性、测试、风险和用户决策。
- 独立复核质量与安全：Schema、引用/追溯、越权写入、秘密标记、成本/上下文边界、测试和 T-0036 fixture 证据。
- 独立复核宿主边界：仅本地 Codex 候选，不修改全局配置，不实现其他宿主适配，不宣称稳定协议。
- 记录真实模型行为、生产项目编译/部署/性能/恢复等仍未验证，不将其伪装成已通过。

## 独立性要求

- 评审者必须是未参与 T-0037 实现的全新独立上下文。
- 评审者不得使用实现作者的结论作为 PASS 依据；已有验证材料只能作为待复现声明。
- 评审报告必须披露 reviewer identity、context、evidence 和 scope limitations。
- 无法证明独立性时，必须在实质评审前返回 `BLOCKED` 或 `USER_DECISION_REQUIRED`。

## 登记阶段允许路径

- `.ai/tasks/T-0038.md`
- `.ai/evidence/T-0038/`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/task_graph.yaml`
- `.ai/HANDOFF.md`
- `.ai/DECISIONS.md`

## 获得批准并收到后续精确执行请求后的允许路径

- `.ai/evidence/T-0038/`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`
- `.ai/tasks/T-0038.md`
- `.ai/task_graph.yaml`

## 明确禁止

- 修改、规范化、替换、重命名、删除或追加任何冻结对象或已有 T-0037 证据。
- 在本 Gate 下修复发现、修改候选实现、修改 T-0037、执行真实模型或认证角色行为。
- 创建修复 Gate、复审 Gate、Host Integration Gate 或其他下游任务/Gate。
- 修改全局 Codex、`AGENTS.md`、skill、MCP、plugin、automation、hook 或宿主行为。
- 部署、数据库、权限、密钥、支付、生产数据、迁移、真实业务项目或外部系统动作。
- 将 reviewer PASS、validator、测试或 AI 建议解释为用户批准、产品 PASS、生产认证或用户验收。

## Verdict Schema

允许：`PASS`、`REPAIR_REQUIRED`、`BLOCKED`、`USER_DECISION_REQUIRED`、`SCOPE_VIOLATION`。

verdict 仅为证据，不授权冻结对象修改、修复、关闭 T-0037、项目 PASS、用户验收、安装、激活、Host Integration、部署或真实项目进入。

## 验证计划

- 严格 UTF-8/YAML/Markdown 读取，并确认冻结清单中的 62 个路径、字节数和 SHA-256 全部匹配。
- 复现角色合同、提示词 marker、Schema、上下文/权限隔离、任务图、功能包、Human Review Packet 和确定性检查的关键断言。
- 核对 T-0037 changed-path manifest 与当前冻结边界，确认无全局配置或其他宿主变化。
- 评审者在实质评审前确认独立性；失败则停止并返回 `BLOCKED`。
- 评审完成后生成报告、命令记录、验证记录和 changed-path manifest，然后停止等待后续用户决策。
- 登记后运行 `git diff --check`、YAML/JSON 结构读取和 `validate_state.py`；后者预期只因本 Gate 为 pending 而阻断。

## 回滚与恢复

- Gate 登记失败时只回滚本次新增的 T-0038 任务、证据和治理元数据；不得触碰 T-0035/T-0036/T-0037 历史对象。
- 冻结清单不匹配、路径越界或独立性失败时保留证据并停止，结果为 `BLOCKED` 或 `SCOPE_VIOLATION`。
- 任何破坏性清理、候选实现回滚、修复扩展或下游动作都需要另一个明确用户 Gate。

## 用户决策短语

- 批准：`批准 G-T-0038-T0037-FRESH-INDEPENDENT-REVIEW-V0-1`
- 拒绝：`拒绝 G-T-0038-T0037-FRESH-INDEPENDENT-REVIEW-V0-1`
- 执行：`执行 G-T-0038-T0037-FRESH-INDEPENDENT-REVIEW-V0-1`
