# T-0157: 风险驱动执行分级设计（loopx P0-3 采纳）

> 交付物：T-0157（AC-01~AC-08）
> 日期：2026-08-07
> 来源：docs/designs/T-0154-loopx-comparison.md P0-3

## 1. 目标

引入风险驱动执行分级：按任务描述/标志自动判定执行等级
（LIGHT/STANDARD/FULL），为「低风险小改动」提供轻流程建议，同时
**critical_triggers 命中强制 FULL（不可降级）**，保住 fail-closed 底线。
**advisory-only**：分级仅建议/呈现，现有 gate 批准语义不变。

## 2. 设计

### 2.1 分级函数

```python
grade_risk(task_desc, flags) -> {
  "level": "LIGHT" | "STANDARD" | "FULL",
  "triggers_hit": [...],   # critical_triggers 命中项（命中→FULL）
  "score": N,              # score_rules 累计
  "reason": "一句话"
}
```

### 2.2 规则

**critical_triggers（任一命中 → FULL，不可降级）**：
`auth`, `permission`, `db_schema`, `external_side_effect`,
`core_state_transition`, `secret`, `payment`, `production_data`

**score_rules（加分）**：
| 信号 | 分值 |
|------|------|
| api_contract（接口/契约变更） | 3 |
| sql（SQL/数据访问变更） | 3 |
| mq（消息队列） | 3 |
| ambiguous_requirement（需求模糊） | 2 |
| multi_module（跨模块） | 1 |
| test_only / docs_only（仅测试/文档） | -1 |

**阈值**：score ≥ 4 → FULL；score ≥ 2 → STANDARD；否则 LIGHT。

### 2.3 ACCEPTED_RISK

- 降级建议（FULL→STANDARD/LIGHT）需用户确认 + 理由记录
- 实现：`accepted_risk(task_id, level, reason)` 记录到事件日志
  （T-0155 event_log，actor=user），**不自动改变 gate 流程**

### 2.4 SKIPPED 白名单

- `MODE_SKIPPABLE_STAGES` 单一事实源：仅审核/审计类门可 SKIPPED
  （如 design-review 在 LIGHT 下可建议跳过，开发/验证/健康门保留）
- 白名单常量 + `is_skippable(stage, level)` 校验

### 2.5 CLI

`/loop-risk <task_desc>`（cli_entries `main_risk`）：输出分级建议 +
triggers/score/reason。advisory-only。

## 3. 边界

- 分级仅建议；gate 批准语义零变更
- hooks/ 零改动；内核零触碰
- LIGHT 仅建议跳审核/审计门，开发/验证/健康门保留

## 4. 验收对照

| AC | 结果 |
|----|------|
| AC-01 grade_risk 三态 | level/triggers_hit/score/reason |
| AC-02 critical→FULL | 8 触发器测试（auth/db_schema/secret 等） |
| AC-03 打分阈值 | 高/中/低用例矩阵 |
| AC-04 ACCEPTED_RISK | 记录机制（event_log，user actor） |
| AC-05 SKIPPED 白名单 | is_skippable（仅审核/审计门） |
| AC-06 advisory-only | gate 语义不变（测试实证） |
| AC-07 设计文档 | 本文件 |
| AC-08 全量回归 + 审查 | 见收口 |
