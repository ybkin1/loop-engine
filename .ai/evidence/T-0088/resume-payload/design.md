# T-0088 U6 — Human Review Packet Resume Payload 设计证据（design）

> **T-0088（上下文与路由升级）U6 工作包 | 2026-08-01 | Gate: G-T-0088-REQUIREMENTS（approved）**
> 借鉴来源：OpenBMB/StaffDeck `backend/app/core/human_handoff_service.py`（164 行）的 resume payload 模式 —— HumanHandoffRequest 携带 resume payload（active skill/step/slots/pending tasks），暂停后可恢复 SOP 状态。见 `.ai/evidence/T-0086/staffdeck-benchmark.md` U6。
> 落地位置：`loop_core/human_review_packet.py`（新增 ResumePayload / build_resume_payload / resume_from_payload，与 HumanReviewPacket 可选集成）。

## 1. 借鉴映射

| StaffDeck human_handoff_service.py | loop-engine U6 落地 | 差异说明 |
|---|---|---|
| HumanHandoffRequest 携带 resume payload（active skill / step / slots / pending tasks） | `ResumePayload`（snapshot + recovery） | 按 loop-engine 治理语义收敛：以 state.yaml / task_graph.yaml / gates.yaml 为唯一权威来源 |
| 暂停时可恢复 SOP 状态 | gate 暂停决策 → 机器可恢复决策上下文 | 决策点快照（决策类型/呈现版本）+ 恢复数据（task/gate/pending_tasks） |
| 恢复时校验 payload 与当前状态 | `resume_from_payload()` 一致性校验 | **状态漂移 → 明确报错（StateDriftError），不猜测**（StaffDeck 无此 fail-closed 语义，为 loop-engine 强化项） |
| pending tasks 列表 | `recovery.pending_tasks`（task_graph.yaml 未完成/未阻塞任务） | 逐字段取自权威文件，不捏造 |

## 2. Resume Payload Schema（v1）

JSON 可序列化；`schema="resume_payload"`、`schema_version=1`、`generated_at`（UTC ISO 时间戳）。

```json
{
  "schema": "resume_payload",
  "schema_version": 1,
  "generated_at": "2026-08-01T07:00:00+00:00",
  "snapshot": {
    "task_id": "T-0088",
    "gate_id": "G-T-0088-REQUIREMENTS",
    "phase": "S6-delivery",
    "decision_point": {
      "decision_type": "gate_approval",
      "presentation_version": 1,
      "packet_id": "HRP-XXXXXXXX"
    },
    "context_pointers": [
      "…/.ai/state.yaml",
      "…/.ai/task_graph.yaml",
      "…/.ai/gates.yaml",
      "…/.ai/tasks/T-0088.md",
      "…/.ai/evidence/T-0088/"
    ],
    "sources": {
      "state.yaml": "…/.ai/state.yaml",
      "task_graph.yaml": "…/.ai/task_graph.yaml",
      "gates.yaml": "…/.ai/gates.yaml"
    }
  },
  "recovery": {
    "task": { "id": "T-0088", "title": "…", "status": "in_progress",
              "phase": "S6-delivery", "priority": "P0", "depends_on": [...],
              "gates": ["G-T-0088-REQUIREMENTS"] },
    "gate": { "id": "G-T-0088-REQUIREMENTS", "task_id": "T-0088",
              "gate_type": "user-approval", "status": "pending", "decision": null },
    "phase": "S6-delivery",
    "pending_tasks": [ { "id": "...", "title": "...", "status": "...",
                         "priority": "..." } ]
  }
}
```

- **快照字段**：task_id / gate_id / phase / 决策点（decision_type + presentation_version + 可选 packet_id）/ 上下文指针（仅指向实际存在的文件：3 个权威来源 + 任务文件 + evidence 目录）。
- **恢复数据**：task 与 gate 记录为权威文件字段子集的逐字拷贝（`_TASK_RECOVERY_FIELDS` / `_GATE_RECOVERY_FIELDS`）；pending_tasks 为 task_graph.yaml 中 status ∈ {pending, in_progress, active} 的任务（blocked/completed 排除），按 id 排序。
- **序列化**：`to_dict() / from_dict() / to_json() / from_json()`；`from_dict` 校验 schema 与版本，缺失 snapshot/字段 → `ResumePayloadError`。

## 3. 生成校验（build_resume_payload，fail-closed）

生成时（gate 暂停时刻）校验，任一失败抛 `ResumePayloadError`：

1. **来源存在**：state.yaml / task_graph.yaml / gates.yaml 三文件必须存在且可解析（`_load_authoritative_yaml`）。
2. **state.yaml 字段一致性**：`current_task_id == 请求 task_id`、`current_gate_id == 请求 gate_id`、`current_phase == 请求 phase`，否则 `state.yaml 字段不一致`。
3. **task_graph 存在性**：task_graph.yaml 中必须存在该任务。
4. **gates 存在性 + 绑定**：gates.yaml 中必须存在该 gate，且 `gate.task_id == 请求 task_id`。

签名：`build_resume_payload(project_root, *, task_id, gate_id, phase, decision_type, presentation_version=1, packet_id=None) -> ResumePayload`（decision_type 接受 `PacketType` 或 str）。

## 4. 恢复校验语义（resume_from_payload，fail-closed / 不猜测）

`resume_from_payload(payload: ResumePayload | dict, project_root) -> ResumeContext`，恢复时对照**当前**权威状态：

| 检查 | 不一致时 |
|---|---|
| state.yaml `current_task_id` == payload.snapshot.task_id | `StateDriftError`（状态已漂移） |
| state.yaml `current_gate_id` == payload.snapshot.gate_id | `StateDriftError`（状态已漂移） |
| state.yaml `current_phase` == payload.snapshot.phase | `StateDriftError`（状态已漂移） |
| task 仍存在于 task_graph.yaml | `StateDriftError`（任务已不存在） |
| gate 仍存在且 `task_id` 绑定一致 | `StateDriftError`（gate 已移除/改绑） |
| gate status 仍为 `pending`（未裁决） | `StateDriftError`（gate 已裁决，无需恢复） |
| payload schema / schema_version 受支持 | `ResumePayloadError`（unsupported） |

- 漂移错误消息含 `状态已漂移 (STATE_DRIFT)` 前缀 + 期望/实际值，**不做任何猜测性恢复**。
- 全部一致 → 返回 `ResumeContext`（task/gate/pending_tasks 从当前权威文件刷新 + 决策点 + 上下文指针 + resumed_at）。
- 支持从 JSON dict 直接恢复（`payload.to_dict()` / `from_json` 持久化后传入）。

## 5. 与 HumanReviewPacket 集成（向后兼容）

- `HumanReviewPacket` 新增可选字段 `resume_payload: ResumePayload | None = None`（默认 None）。
- `HumanReviewPacketBuilder.from_phase_completion(..., resume_payload=None)` 与 `from_veto_escalation(..., resume_payload=None)` 末尾追加可选关键字参数，透传至 packet。
- **默认行为不变**：不传 payload 时 packet 与渲染输出（to_markdown / to_plain_text）与升级前完全一致（AC-05d 测试锁定）。
- payload 为机器消费元数据，不渲染进面向非技术用户的文档。
- 现有调用方（veto_escalation.py 等）无签名破坏。

## 6. 文件清单（U6 交付物）

| 文件 | 角色 |
|---|---|
| `loop_core/human_review_packet.py` | ResumePayload/ResumeSnapshot/DecisionPoint/ResumeContext + build_resume_payload + resume_from_payload + HumanReviewPacket 可选字段（全部新增，现有接口不变） |
| `tests/test_resume_payload.py` | 34 项测试：AC-05a 生成 / AC-05b 恢复 / AC-05c 漂移 / AC-05d 兼容 + fail-closed 校验 |
| `.ai/evidence/T-0088/resume-payload/design.md` | 本设计证据 |

## 7. 验收对照（T-0088 AC-05）

- **AC-05**（resume payload 有测试：gate 暂停 → payload 可恢复决策上下文：任务/gate/阶段/决策点快照）：✅
  - `TestAC05aPayloadGeneration`（5 项）：快照字段完整（task/gate/phase/决策点）+ 上下文指针全部真实存在 + recovery 数据逐字段来自权威文件（task title/status/priority、gate status/task_id、pending_tasks 排除 blocked）+ JSON 可序列化。
  - `TestAC05bResumeSuccess`（3 项）：状态一致 → 返回可续跑 ResumeContext（决策点保留）；支持 dict/JSON round-trip；暂停→恢复全周期。
  - `TestAC05cStateDrift`（8 项）：task/gate/phase 不匹配、任务移除、gate 移除/改绑/已裁决 → `StateDriftError`（消息含"状态已漂移"，含期望/实际值），不猜测。
  - `TestAC05dBackwardCompatibility`（5 项）：默认无 payload、渲染不变、可选携带 payload（两种 builder）、原 5 位置参数签名不变。
- 回归：`test_human_review_packet.py` + `test_veto_escalation.py` + `test_task_queue.py` 134 项全过；全量测试见 acceptance 汇报。
- 无业务源码改动；新代码 ruff 零新增告警（模块内仅剩 13 项 HEAD 既有告警，未触碰）。
