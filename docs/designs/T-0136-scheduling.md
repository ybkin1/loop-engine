# T-0136 批 3: 任务排布 T-0137~T-0142

> 交付物：T-0136 批 3（AC-03）
> 模式：与 T-0106 批 4 一致（排布仅文档产出，落地需用户独立 gate 批准）

## 排布总览

| 任务 | 标题 | 优先级 | 依赖 D-xx | 落地内容 | 复杂度 |
|---|---|---|---|---|---|
| T-0137 | 容量规划与压测模板落地 | P0 | D-01 | 2 模板 + 2 references + 4 检查点 | M |
| T-0138 | 稳定性设计模板落地 | P0 | D-02 | 1 模板 + 2 references + 4 检查点 | M |
| T-0139 | 数据迁移模板落地 | P0 | D-03 | 1 模板 + 2 references + 5 检查点 | L |
| T-0140 | 性能诊断模板落地 | P1 | D-04 | 1 模板 + 1 reference + 4 检查点 | M |
| T-0141 | 一致性设计模板落地 | P1 | D-05 | 1 模板 + 1 reference + 5 检查点 | M |
| T-0142 | 架构与方法决策指南落地 | P2 | D-06 | 2 模板 + 2 references + 4 检查点 + AI 边界小节 | S |

## T-0137: 容量规划与压测模板落地（P0）

- **来源设计**：T-0136 D-01
- **允许路径**：
  - skills/loop-governance/templates/capacity/（新建）
  - agents/system-architect/references/capacity-checklist.md
  - agents/release-engineer/references/load-test-checklist.md
  - skills/loop-governance/templates/deployment/release-checklist.md（检查点）
  - docs/、.ai/
- **AC**：
  1. capacity-estimate.md 模板（五步估算 + 3 示例场景含 2000→20 万 QPS）
  2. load-test-plan.md 模板（类型/流量模型/工具矩阵/四指标合格线）
  3. 两个角色 references 落地
  4. release-checklist 新增 4 检查点（report 级）
  5. 模板填用示例测试 + 全量回归 0 failed
  6. 独立审查 GO
- **边界**：hooks/ 零改动、内核零触碰；bump 3.12.67

## T-0138: 稳定性设计模板落地（P0）

- **来源设计**：T-0136 D-02
- **允许路径**：
  - skills/loop-governance/templates/stability/（新建）
  - agents/system-architect/references/resilience-checklist.md
  - agents/release-engineer/references/resilience-release-checklist.md
  - release-checklist 检查点
  - docs/、.ai/
- **AC**：
  1. resilience-design.md 模板（RT 治理五阶梯 + 熔断阈值推导 + 降级恢复三层判定）
  2. 2 references 落地
  3. release-checklist 新增 4 检查点
  4. 50ms→5s 完整案例 + 熔断参数推导示例
  5. 全量回归 0 failed + 独立审查 GO
- **边界**：hooks/ 零改动、内核零触碰；bump 3.12.67

## T-0139: 数据迁移模板落地（P0）

- **来源设计**：T-0136 D-03
- **允许路径**：
  - skills/loop-governance/templates/migration/（新建）
  - agents/system-architect/references/migration-checklist.md
  - agents/release-engineer/references/migration-release-checklist.md
  - release-checklist 检查点
  - docs/、.ai/
- **AC**：
  1. data-migration-plan.md 模板（四阶段法 + 回滚 + 不丢三层 + 拆分专项）
  2. 2 references 落地
  3. release-checklist 新增 5 检查点
  4. 百亿表案例 + 单体拆分案例填用示例
  5. 全量回归 0 failed + 独立审查 GO
- **边界**：hooks/ 零改动、内核零触碰；模板为设计方法论，实际迁移执行
  仍需用户单独 gate（外部边界不豁免）；bump 3.12.67

## T-0140: 性能诊断模板落地（P1）

- **来源设计**：T-0136 D-04
- **允许路径**：
  - skills/loop-governance/templates/performance/（新建）
  - agents/quality-engineer/references/performance-checklist.md
  - release-checklist 检查点
  - docs/、.ai/
- **AC**：
  1. performance-diagnosis.md 模板（分位指标表 + 长尾四步 + 慢 SQL 六阶梯
     + GC 四步）
  2. quality-engineer reference 落地
  3. release-checklist 新增 4 检查点
  4. 2s→20ms 案例 + 11 亿行案例
  5. 全量回归 0 failed + 独立审查 GO
- **边界**：hooks/ 零改动、内核零触碰；bump 3.12.67

## T-0141: 一致性设计模板落地（P1）

- **来源设计**：T-0136 D-05
- **允许路径**：
  - skills/loop-governance/templates/consistency/（新建）
  - agents/system-architect/references/consistency-checklist.md
  - release-checklist 检查点
  - docs/、.ai/
- **AC**：
  1. consistency-design.md 模板（缓存一致性对比 + 异步化取舍 + 三层不丢
     + 双端幂等）
  2. system-architect reference 落地
  3. release-checklist 新增 5 检查点
  4. 四案例填用示例（缓存/异步/MQ/幂等）
  5. 全量回归 0 failed + 独立审查 GO
- **边界**：hooks/ 零改动、内核零触碰；bump 3.12.67

## T-0142: 架构与方法决策指南落地（P2）

- **来源设计**：T-0136 D-06
- **允许路径**：
  - skills/loop-governance/templates/architecture/ddd-split-guide.md（新建）
  - skills/loop-governance/templates/deployment/release-strategy-guide.md（新建）
  - agents/system-architect/references/ddd-checklist.md
  - agents/delivery-manager/references/tradeoff-checklist.md
  - docs/designs/T-0136-D06-ai-boundary.md（AI 边界方法论独立文档）
  - release-checklist 检查点
  - docs/、.ai/
- **AC**：
  1. ddd-split-guide.md（何时用/不用 + 拆分决策表 + 顺序）
  2. release-strategy-guide.md（灰度/蓝绿/金丝雀决策矩阵）
  3. 2 references 落地
  4. AI 边界方法论文档（可复算可验证→AI；价值/风险裁决→人）
  5. release-checklist 新增 4 检查点
  6. 全量回归 0 failed + 独立审查 GO
- **边界**：hooks/ 零改动、内核零触碰；bump 3.12.67

## 排布顺序与依赖

```
T-0137 ─┐
T-0138 ─┼─ 并行（P0 批）
T-0139 ─┘
T-0140 ─┐
T-0141 ─┼─ 并行（P1 批，依赖 P0 批经验）
T-0142 ─┘（P2 批，可随时）
```

每批独立 gate 批准；每任务独立审查 GO + 全量回归 + bump 3.12.67（首个
落地任务统一 bump 一次，或每任务 bump —— 由用户裁决，默认每任务独立
bump 保持版本可追溯）。
