# loopx (huangruiteng) 深读留档 — T-0154

> subagent 深读记录（只读研究，克隆于 /tmp/loopx-huang）
> 深读时点：2026-08-07（commit db19e9b，v0.4.2）

## 关键发现（摘要）

- 6 层持久控制面 + 4 职责运行时模型：Registry / Goal state / Run log /
  Run history / Status-attention queue / Compute quota
- 事件溯源状态内核（event_sourced_state.py，schema loopx_state_event_v0）
- 配额决策：quota should-run 5 路（normal_delivery/recovery/self_repair/
  capability_repair/workspace_repair → deliver/ask/wait/repair/quiet）
- 可执行 todos：9+ 元数据字段（claim/blocks/successor/resume/continuation）
- 证据三档隐私分级 + 自动脱敏（public_safe/local_private/private_pointer）
- handoff 预算（≤16 行/1800 字符）+ gate 状态机
- 工程：GitHub Actions 6 workflow、契约先行文档（137KB status contract）

## 对 loop-engine 的借鉴（详见 docs/designs/T-0154-loopx-comparison.md）

P0: 事件溯源影子层 / 配额决策路由；P1: todo 元数据 / 证据隐私分级；
P2: handoff 预算 / 交互模式目录
