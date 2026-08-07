# gate_rejection_rate 语义修正（T-0129 AC-04）

## 问题

旧指标 `gate_rejection_rate = 0.0`（metrics-report，92 个 gate 零拒绝）无法解读：
无法区分"AI 自律从未提交越界请求"（好事）与"防御机制从未被真实挑战"
（防御有效性未知）。

## 拆分后口径

| 指标 | 语义 | 当前值 | 解读 |
|---|---|---|---|
| `rejected_requests` | guard-events 中 result=BLOCK/REJECTED 事件数（AI 曾提交被拦请求） | 0 / 4477 | AI 侧从未触发拦截——**防御未被真实挑战**（不等于防御无效） |
| `defense_drill_pass_rate` | T-0129 演练通过率（R1~R6 拒绝路径 + E1~E5 锁死恢复，tests/test_defense_drills.py） | 11/11 | **防御路径可用性被演练证明**（替代"从未被挑战"的空白） |

## 设计意图（T-0132 D-03 / 决策包 P2）

- "演练通过 → 才授权自治"：defense_drill_pass_rate 是自治授权的前置资格指标
- rejected_requests 保持 0 是目标态（AI 不越界）+ 演练证明防御有效，二者
  共同构成"防御可依赖"的证据
- 演练随真实事故补充场景（incident → 复盘 → 新增演练，复用 T-0097 学习回路）

## 存储

- metrics-report.json `gate_defense` 字段（读侧计数 + 口径说明）
- 演练本身：tests/test_defense_drills.py（11 用例，可重复执行）
