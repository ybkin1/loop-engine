# AI 能力边界方法论（ai-boundary）

> **T-0136 D-06 落地（由 T-0142 从设计文档拆出）。**
> 判定准则：**可复算可验证 → AI 可增强；不可复算的价值/风险裁决 → 人**。
> 与引擎「机器可验证链」原则一致（EVIDENCE_ONLY_BOUNDARY / USER_AUTHORITY）。

## 1. AI 可替代/增强环节（已有实践可外推）

| 环节 | 能力 | 状态 |
|------|------|------|
| 代码生成/重构/测试生成 | developer / test-engineer | 已落地 |
| 审查辅助/模式识别 | independent-reviewer | 已落地 |
| 文档/报告生成 | tech-writer 角色 | 评估中 |
| 容量估算/压测分析 | 数据驱动模板（capacity-estimate） | T-0137 落地后 AI 可执行 |
| 性能诊断初筛 | 慢 SQL/GC 模式识别（performance-diagnosis） | T-0140 落地后 AI 可执行 |

## 2. 必须工程能力（AI 无法替代）

| 环节 | 原因 |
|------|------|
| 用户价值判断与取舍 | 升级协议 4 类场景；EVIDENCE_ONLY_BOUNDARY（reviewer PASS ≠ 批准） |
| 规则层/权限/安全边界裁决 | USER_AUTHORITY 不可代理 |
| 生产数据/真实业务项目最终操作 | 外部边界 gate（forbidden effects） |
| 故障止损决策 | 演练预案内可 AI 执行；预案外须人工 |

## 3. 判定准则应用

```
某项任务交给 AI 前问三个问题：
1. 结果可复算吗？→ 否 → 人做
2. 有明确验收标准吗？→ 否 → 先定 AC 再议
3. 涉及价值/风险裁决吗？→ 是 → 人裁决（AI 只提供材料）
全否 → AI 可增强（但证据链仍须完整）
```

## 4. 角色指引

- **谁用**：main-thread（编排时判断环节归属）；delivery-manager（交付
  分工）；用户（了解边界）
