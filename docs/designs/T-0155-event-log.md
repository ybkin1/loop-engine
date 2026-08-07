# T-0155: 事件溯源影子层设计（loopx P0-1 采纳）

> 交付物：T-0155（AC-01~AC-07）
> 日期：2026-08-07
> 来源：docs/designs/T-0154-loopx-comparison.md P0-1

## 1. 目标

为 Loop 工程治理状态引入**审计可追溯性**：对状态写入追加 JSONL 事件链，
state.yaml 仍为权威投影，事件链回答「谁在何时改了什么状态」并可回放。

## 2. 设计

### 2.1 事件流

```
状态写入（validate_state --auto-sync / 治理工具）
        │
        ▼
event_log.append(event)  ──▶  .ai/evidence/observability/state-events.jsonl
        │                          （追加写，失败吞掉）
        ▼
read_events() ──▶ 回放序列（审计/排查）
        │
        ▼
replay_check() ──▶ 投影=事件回放一致性（测试断言）
```

### 2.2 事件类型

| event_type | 触发 | detail 示例 |
|------------|------|-------------|
| task_registered | 新任务登记 | {task_id, depends_on} |
| task_status_changed | 任务卡/图状态变更 | {from, to} |
| gate_created | gate 登记 | {gate_id, task_id} |
| gate_approved | 用户批准 | {approval_source} |
| gate_completed | 收口 | {} |
| evidence_attached | 证据写入 | {path} |
| handoff_generated | HANDOFF 重生成 | {action} |

### 2.3 事件字段

```json
{
  "ts": "ISO8601",
  "event_id": "hex16",
  "event_type": "task_status_changed",
  "actor": "ai|user|system",
  "task_id": "T-XXXX",
  "gate_id": "G-T-XXXX-REQUIREMENTS | null",
  "detail": {},
  "state_sha256": "投影哈希（回放一致性锚点）"
}
```

### 2.4 接入点（最小侵入）

- `validate_state.py --auto-sync` 分支：在治理文件变化后追加
  `handoff_generated` 事件（+ 检测到 state/gates/task_graph 变化时
  记 `task_status_changed` / `gate_approved` 等）
- 独立 CLI：`python .zcode/tools/event_log.py <root> append --type X ...`
  与 `read --tail N` / `replay-check`

### 2.5 一致性

- `replay_check(root)`：读取 state-events.jsonl，重放事件序列，断言
  最终投影与当前 state.yaml 一致（近似：校验事件数与最近
  state_sha256 锚点）
- 失败吞掉：append 任何异常 → logger.warning + return False
  （观测绝不阻断业务，与 guard-events 同原则）

## 3. 边界

- state.yaml 语义零变更（事件仅影子，不参与判定）
- hooks/ 零改动；validate_state 判定逻辑零变更（仅 auto-sync 分支追加写）
- 事件文件 gitignore 不跟踪（运行时产物，同 guard-events 治理）

## 4. 验收对照

| AC | 结果 |
|----|------|
| AC-01 append + read_events | event_log.py append/read/replay-check |
| AC-02 事件类型覆盖 | 7 类（task/gate/evidence/handoff 生命周期） |
| AC-03 replay_check 一致性 | 测试：追加→回放→投影匹配 |
| AC-04 失败吞掉 | 测试：写入失败不抛异常 |
| AC-05 设计文档 | 本文件 |
| AC-06 全量回归 | 见收口 |
| AC-07 独立审查 | 随批量审查 |
