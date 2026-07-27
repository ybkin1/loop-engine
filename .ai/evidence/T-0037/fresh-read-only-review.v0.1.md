# T-0037 Fresh Read-Only Review v0.1

## Review scope

本记录从磁盘重新检查 T-0037 候选实现、角色合同、运行时准入、用户可读交付包、测试和 T-0036 fixture。它是证据性审查，不是用户 Gate，也不是独立模型/人工签字。

## Findings

### Correctness

- `PASS`: 角色注册、上下文预算、路径边界、素材选择、P0-P12、任务图、功能包和 Human Review Packet 均有可重复测试。
- `PASS`: 缺工具、越界写入、开发角色写入 `.loop/state/`、上下文超预算和秘密标记会阻断。
- `PASS`: T-0036 fixture 从初始化到 `verify` 完成，candidate store 检查通过。

### Architecture and isolation

- `PASS`: 11 个 stable role 加 1 个 T-0036 research-engineer；独立评审员只读，只有 controller 声明可写 Loop 状态。
- `PASS`: 角色合同、项目 overlay、work packet 和选定证据分层组装；运行时控制层单独持久化 envelope。
- `PASS`: prompt 文件只能位于 registry 目录内，避免注册表路径越界。

### Security and cost

- `PASS`: 本候选无网络、子进程或其他宿主适配调用；写入仅在 `.loop` 或显式项目边界内。
- `PASS`: 选定素材而非全库进入上下文，角色和任务声明上下文预算；超预算直接阻断。
- `PASS`: 外部素材被作为证据文本处理，秘密标记和 token-like 值会被拒绝。

## Residual risks

- `OPEN`: 当前 CodexRuntime 只生成 invocation spec，不执行真实模型，因此 `capability_probe.status=NOT_RUN`；角色的实际行为能力尚未认证。
- `OPEN`: 当前 deterministic checks 仍是候选级最小门禁，尚未覆盖真实项目代码的编译、测试、依赖扫描、部署、性能和恢复执行。
- `OPEN`: T-0036 素材库本身仍是 active candidate，T-0037 未批准或提升它为规范基线。

## Evidence-only verdict

`PASS_FOR_CANDIDATE_IMPLEMENTATION_WITH_OPEN_RUNTIME_VALIDATION`

该结论只说明本地候选实现达到本 Gate 的代码/文件工件验证范围，不等于生产级认证、Codex 全局安装、用户验收或发布批准。
