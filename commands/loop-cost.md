---
description: 查看 Loop 工程 Token 成本报告——按角色、阶段聚合
argument-hint: "[--by-role] [--by-phase]"
allowed-tools: [Bash, Read]
---

查看 Loop 工程所有阶段的 Token 消耗报告。

## 用法

```
/loop-cost                     # 完整成本报告
/loop-cost --by-role           # 仅按角色聚合
/loop-cost --by-phase          # 仅按阶段聚合
```

## 数据来源

`.ai/evidence/costs/cost_log.jsonl`——由各角色 agent 在执行完成后自动追加。

报告包含：
- 总 Token 消耗
- 按角色/阶段占比
- 返工成本估算（同一 task_id 在同阶段被多个角色多次调用）

如果没有成本记录，输出 "无成本记录"。
