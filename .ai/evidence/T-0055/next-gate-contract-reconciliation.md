# T-0055 下一 Gate：规范—实现—认证一致性

角色设计阶段发现一个必须修正的基线事实：当前 `agents/` 存在 12 个角色目录，而历史文档多处写成 11 个。后续不得以旧数量作为完整性证明。

建议进入 `G-T-0055-CONTRACT-RECONCILIATION`，重点验证：

1. 12 个角色的 SKILL、CONTRACT、profile、challenge 是否一一对应；
2. canonical 12 字段如何映射到现有合同，避免重复维护；
3. quality-engineer、test-engineer、independent-reviewer 的交叉职责和独立性边界；
4. challenge 数量/内容与 Python `role_capability.py` 是否一致；
5. 认证 JSON/YAML 记录、expiry/revalidation、admission 状态是否一致；
6. 12 角色数量是否应成为新的 canonical registry；
7. 设计候选内容是否需要经过独立 reviewer 后才能进入实现 gate。

本建议不改变任何认证状态，也不授权 v3.11.2 代码修复。
