# T-0055 证据真实性与 NOT_VERIFIED 清单

## 当前确认的证据

- 当前工作树版本源：`pyproject.toml`、两个 Python init、plugin manifest 均为 3.11.2。
- `.ai/version-manifest.yaml` 仍保存 3.0.0，版本投影不一致已确认。
- session brief、reader、gate lifecycle、hook sync、质量入口和 router 的代码缺口已定位。
- T-0055 gate 已有用户明确批准记录；本阶段仍是 baseline audit，不授权修复。

## 必须保持 NOT_VERIFIED 的事项

- onboarding 是否在已有项目上实际覆盖/重置 state；
- 是否存在跨 state/task/gate/HANDOFF 的真实事务提交缺失；
- close_session 是否在失败路径修改额外状态；
- Continuity 与 HANDOFF 是否存在实际哈希环；
- takeover 是否存在统一生命周期状态；
- null task/checkpoint acknowledgment 的具体可复现失败；
- 历史契约 ID 漂移是否影响运行时兼容性。

## 证据规则

静态代码定位只能证明实现形态，不能自动证明运行时后果。上述 NOT_VERIFIED 项必须在后续审计中具备：fixture、命令、退出码、stdout/stderr、相关文件 hash、预期与实际结果；无法执行时必须保留 NOT_VERIFIED，不得写成 PASS 或 CONFIRMED。
