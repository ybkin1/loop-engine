# 性能测试检查清单（quality-engineer）

> **T-0136 D-04 落地。** 质量工程师在性能测试与诊断时使用。
> 配套模板：`skills/loop-governance/templates/performance/performance-diagnosis.md`

## 必查项

- [ ] 性能测试报告含分位指标（p50/p95/p99，不只平均）
- [ ] 慢 SQL 清单 + explain 分析记录（key/type/扫描行数）
- [ ] 索引使用确认证据（EXPLAIN key 字段 / 强制索引对比）
- [ ] 长尾定位记录（慢请求采样 + 根因归类）
- [ ] 11 亿行级场景说明（分区/冷热分离/汇总表方案是否适用）

## 常见驳回场景

- 只测平均不测 p99 → 驳回（长尾决定体验）
- 慢 SQL 无 explain 记录 → 驳回（无法确认索引是否用上）
- 声称"优化了"无前后对比 → 驳回
