# 设计：Approval Record Schema + Gate 真实读取

版本：v0.1 | 状态：candidate | 日期：2026-07-23

## 1. 问题

### gates.yaml 当前缺陷
- 字段不一致（approval_text 有时缺失）
- 无完整性校验（无 packet_hash / scope_hash）
- 无过期机制
- 运行时不可消费（Hook 只看 status=="pending" 一个布尔值）

### P0-E 死锁（已现场复现）
- gate_guard.py:79-81 无条件追加 current_gate_id → pending
- 不交叉校验 gates.yaml 中 gate 的 status
- 豁免集仅含 .ai/gates.yaml → state.yaml 无法自愈
- 需人类手动清除 current_gate_id

## 2. 设计

### 2.1 ApprovalRecord（10 必填字段）

```python
@dataclass
class ApprovalRecord:
    approval_id: str           # AR-{uuid12}
    gate_id: str
    human_actor: str           # "user"
    decision: Decision         # approved|rejected|repair_requested
    source: Source             # explicit_user_message|interactive_dialog|cli_flag
    packet_hash: str           # 决策包 SHA256
    scope_hash: str            # allowed_paths + allowed_actions SHA256
    input_fingerprint: str     # 去敏用户输入 SHA256
    recorded_at: str           # ISO 8601
    expiration: str            # ISO 8601（+30天）
```

### 2.2 gates.yaml 集成

不替代 gates.yaml，作为 gate 的子记录：

```yaml
- id: G-T-XXXX-YYYY
  status: approved
  approval:
    approval_id: AR-abc123def456
    human_actor: user
    decision: approved
    source: explicit_user_message
    packet_hash: "sha256:..."
    scope_hash: "sha256:..."
    input_fingerprint: "sha256:..."
    recorded_at: "2026-07-23T14:05:00+08:00"
    expiration: "2026-08-22T14:05:00+08:00"
```

### 2.3 EvidenceEnvelope（因果链 + TTL）

```python
@dataclass
class EvidenceEnvelope:
    envelope_id: str
    content_hash: str           # 证据内容 SHA256
    created_at: str
    ttl_days: int = 90
    causal_parent_hash: str | None  # 因果链
    evidence_path: str | None
```

### 2.4 gate_guard 修复

```python
# 旧（有 bug）：
if current_gate_id and str(current_gate_id) not in pending:
    pending.append(str(current_gate_id))  # 无条件追加

# 新：
gate = _find_gate_by_id(all_gates, current_gate_id)
if gate and gate.get("status") == "pending":
    pending.append(current_gate_id)
# gate.status != pending → 忽略（不追加到 pending）
```

### 2.5 豁免集扩展

```yaml
# config.yaml
gate_guard:
  decision_recording_exempt:
    - .ai/gates.yaml
    - .ai/state.yaml         # 允许清除 current_gate_id
    - .ai/task_graph.yaml    # 允许更新任务状态
```

## 3. 测试策略

- ApprovalRecord.create() 自动计算 hash + 过期
- is_expired() / is_valid() 逻辑验证
- gate_guard 不再因 current_gate_id 残留死锁
- pending gate 期间按 allowed_paths 放行
