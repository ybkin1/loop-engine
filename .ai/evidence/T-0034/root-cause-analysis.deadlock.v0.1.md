# 根因分析：gate_guard 死锁

版本：v0.1 | 状态：candidate | 日期：2026-07-23

## 死锁复现

```
1. Gate 注册 → status=pending, current_gate_id=G-T-0034-DESIGN
2. 用户批准 → gates.yaml status=approved ✓
3. state.yaml current_gate_id 仍为 G-T-0034-DESIGN ← 未同步清除
4. gate_guard:79-81 无条件追加 current_gate_id → pending
5. pending 非空 → EXIT_BLOCK（即使 gate 已批准）
6. 无法编辑 state.yaml 清除 → 死锁
7. 豁免集仅含 .ai/gates.yaml → 死锁不可自愈
8. 需人类手动介入
```

## 根因

### 一级（直接原因）：gate_guard.py:79-81

```python
if current_gate_id and str(current_gate_id) not in pending:
    pending.append(str(current_gate_id))
```

不交叉校验 gates.yaml 中对应 gate 的实际 status，无条件追加。

### 二级（使死锁不可自愈）：豁免集过窄

decision_recording_exempt 仅含 `.ai/gates.yaml`，state.yaml 无法自救。

### 为什么之前未暴露

历史流程中 gate 批准和 state.yaml 清除在同一批次写入中完成（原子性由会话连续性保证）。本轮会话的写入被 gate_guard 在中途阻断，打断了原子性。

## 永久避免（三层防护）

### 第一层：交叉校验

gate_guard 改为从 gates.yaml 读取 gate 的 status，只有 status=="pending" 才加入 pending 列表。

### 第二层：扩展豁免

decision_recording_exempt 增加 .ai/state.yaml 和 .ai/task_graph.yaml。

### 第三层：validate_state.py 检测

新增检查：current_gate_id 指向已批准/不存在的 gate → 报告不一致告警。

## 通用教训

1. **任何"以防万一"的防御代码必须交叉校验权威数据源**
2. **豁免集设计需覆盖所有"自愈"所需的最小路径**
3. **状态机中任何字段的"残留"必须被检测和报告**
4. **Hook 的阻断逻辑必须可被自身豁免路径自愈**
