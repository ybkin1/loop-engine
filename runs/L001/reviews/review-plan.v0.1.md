# Review Plan v0.1

## 评审对象

`outputs/loop-protocol.candidate.v0.1.md`

## 中心思想

评审必须围绕：

- 当前主题：Codex 跨会话 loop 工程机制。
- 用户立场：非代码背景，希望把自己从多会话复制粘贴中释放出来。
- 当前问题：主线程如何安全编排一次性 subagent。
- 最终目标：产出真实可用、可部署、可验收、可持续迭代的软件项目治理能力。

## 必须检查项

- 是否区分 stable 权威文档和 runs 过程产物。
- 是否明确每类 subagent 的输入、输出和禁止行为。
- 是否定义 reviewer-plan、reviewer、repair 的职责差异。
- 是否防止候选文档冒充已批准协议。
- 是否有 promotion gate。
- 是否有刹车条件。
- 是否说明如何降低上下文压力。

## 判定

- `PASS`: 所有必须检查项都有可执行规则。
- `FAIL`: 可修复缺口存在。
- `BLOCKED`: 输入缺失、权限冲突或需要用户 gate。

