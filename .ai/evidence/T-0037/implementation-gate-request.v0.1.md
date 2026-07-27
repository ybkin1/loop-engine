# T-0037 Codex 侧 Loop 候选实现 Gate 请求 v0.1

Gate ID：`G-T-0037-CODEX-LOOP-CANDIDATE-IMPLEMENTATION-V0-1`

状态：`pending / user_decision_required`

## 请求用户决定

是否批准在 `loop-engine-lab` 内实现 Codex-only 的本地 Loop 工程候选版本。批准只授权后续候选实现，不代表安装、启用、生产可用或用户验收。

## 精确范围

- 实现 `codex_loop/` 本地 Python 包和 CLI 候选。
- 实现角色合同注册、短提示词组装、能力探针、上下文/权限/写入隔离和 `RoleRunEnvelope`。
- 实现 Project Profile、Material Selection、Phase Profile、Task Graph、Work Packet、Finding、Repair、Regression、Gate 和 Human Review Packet。
- 实现 Codex-only 能力探测和本地文件/命令边界。
- 实现 T-0036 的 Functional Design Packet 示例和端到端本地演练。
- 使用 `materials/` 作为参考库，优先软件工程材料；不把提示词材料当作软件工程事实。

## 允许路径

- `codex_loop/`
- `tests/codex_loop/`
- `docs/codex-loop/`
- `.ai/tasks/T-0037.md`
- `.ai/evidence/T-0037/`
- `.ai/state.yaml`
- `.ai/task_graph.yaml`
- `.ai/gates.yaml`
- `.ai/HANDOFF.md`
- `.ai/DECISIONS.md`

## 明确禁止

- 修改 `AGENTS.md`、全局 Codex 配置或 `C:\Users\Administrator\.codex\skills`。
- 安装或启用 skill、MCP、plugin、automation、hook 或其他宿主适配。
- 部署、数据库、权限、秘密、支付、生产数据、迁移、真实业务项目或外部系统。
- 把 T-0037 候选实现写入 `stable/` 并宣称正式协议。
- 实现 Claude Code、Zcode、Qoder 适配。

## 实现分片

1. Core 数据模型和 Schema；
2. Registry、角色合同和短提示词组装；
3. Context/permission/run envelope；
4. Routing、Phase Profile、Task Graph、Work Packet；
5. Quality/security/cost checkers 和 finding loop；
6. Functional Design Packet、Human Review Packet 和 T-0036 本地演练。

每片必须先测试、再验证、再进入下一片；不得一次性生成整个 Runtime。

## 验证计划

- Python 单元测试和 Schema 测试。
- 角色隔离测试：越权读取、越权写入、越权修改架构、评审自修复、跨角色记忆污染。
- 任务图测试：循环依赖、缺输入、Gate 未决、并行写集冲突。
- 上下文测试：只加载必要材料、fingerprint 变化失效、预算超限阻断。
- 功能设计包测试：登录/注册示例必须包含前端、后端、安全、测试、性能和维护字段。
- T-0036 端到端本地演练、独立评审和修复回归。

## 回滚与恢复

- 只允许删除/回滚本 Gate 产生的 `codex_loop/`、`tests/codex_loop/`、`docs/codex-loop/` 和 T-0037 证据。
- 不回滚用户既有 T-0035/T-0036 文件和历史证据。
- 任何路径越界、全局配置变化、秘密/生产行为或测试无法恢复时立即阻断并保留证据。

## 用户决策短语

- 批准：`批准 G-T-0037-CODEX-LOOP-CANDIDATE-IMPLEMENTATION-V0-1`
- 拒绝：`拒绝 G-T-0037-CODEX-LOOP-CANDIDATE-IMPLEMENTATION-V0-1`
- 执行：`执行 G-T-0037-CODEX-LOOP-CANDIDATE-IMPLEMENTATION-V0-1`
