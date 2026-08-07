# DDD 与拆分决策检查清单（system-architect）

> **T-0136 D-06 落地。** 架构师在拆分决策时使用。
> 配套模板：`skills/loop-governance/templates/architecture/ddd-split-guide.md`

## 必查项

- [ ] 微服务拆分决策表已填（团队/变更/数据/隔离四问 + 理由留档）
- [ ] DDD 适用性判断（复杂业务才用；CRUD 不用——防过度设计）
- [ ] 拆分顺序正确（限界上下文 → 数据边界 → 服务边界 → 契约先行）
- [ ] 拆分迁移引用 data-migration-plan Part D（边界先行 + 兼容层）
