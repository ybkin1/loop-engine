# T-0156: 配额决策路由设计（loopx P0-2 采纳）

> 交付物：T-0156（AC-01~AC-07）
> 日期：2026-08-07
> 来源：docs/designs/T-0154-loopx-comparison.md P0-2

## 1. 目标

在 cost_tracker 之上引入「该不该跑」的机器决策：输入成本账本 + gate
状态 + 悬空轮次，输出 5 态决策（deliver/ask/wait/repair/quiet）+ reason。
**只建议不执行** —— 放行必须用户 gate，与 loop 用户 gate 驱动哲学兼容。

## 2. 设计

### 2.1 决策函数

```python
decide_quota(ctx) -> {
  "decision": "deliver" | "ask" | "wait" | "repair" | "quiet",
  "reason": "一句话",
  "factors": {"cost_tokens": N, "pending_gates": [...], "stale_rounds": N, "budget_ratio": 0.xx}
}
```

### 2.2 决策规则（fail-safe 优先级从高到低）

| 条件 | 决策 | 理由 |
|------|------|------|
| 有 pending gate | ask | 需要用户裁决（规则层） |
| 悬空轮次 > 0 | repair | 需先修复悬空（心跳 fail-stop） |
| 成本超预算阈值（如 80%） | quiet | 暂停，节省预算 |
| 返工率高（> 30%） | wait | 需用户介入方向 |
| 以上全否 | deliver | 可继续自治 |
| 输入异常/不确定 | wait | 默认保守（fail-safe） |

### 2.3 输入

- `cost_tracker.summary()`：token 成本 / 返工率 / 预算
- pending gates（gates.yaml status=pending）
- `rounds_heartbeat` 悬空轮次
- 预算阈值常量（BUDGET_RATIO_QUIET = 0.8）

### 2.4 CLI

`/loop-quota`（loop_engine/cli_entries.py 新增 `main_quota`）：
`loop-quota <root>` → 打印决策 + reason + factors。**不执行任何动作。**

## 3. 边界

- 决策只建议；执行仍需用户 gate（与升级协议一致）
- hooks/ 零改动；cost_tracker/rounds_heartbeat 只读调用
- 默认 quiet/wait（fail-safe）；异常降级 wait

## 4. 验收对照

| AC | 结果 |
|----|------|
| AC-01 5 态决策 | decide_quota（decision/reason/factors） |
| AC-02 规则矩阵 | 6 用例（pending→ask / 悬空→repair / 超预算→quiet / 返工→wait / 正常→deliver / 异常→wait） |
| AC-03 /loop-quota CLI | cli_entries main_quota（只建议） |
| AC-04 fail-safe | 异常降级 wait（测试实证） |
| AC-05 设计文档 | 本文件 |
| AC-06 全量回归 | 见收口 |
| AC-07 独立审查 | 随批量审查 |
