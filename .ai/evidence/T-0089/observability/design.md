# U8 可观测性分层 — 设计证据 (T-0089 AC-03)

## 1. 设计来源（StaffDeck 对标，T-0086 staffdeck-benchmark.md）

StaffDeck `backend/app/observability/` 采用 **事件/span/日志三层分离**：
- `event_log.py` — 业务事件（发生了什么、何时、谁）
- `spans.py` — 耗时/调用链（性能与依赖）
- `runtime_logging.py` — 运行时日志

其核心纪律："**Observability must never turn a successful business request
into a failure**" —— 观测失败只影响"看得见"，不影响"做得了"。

U8 将同一模式应用于 loop-engine 的 **guard 检查观测**：guard 健康检查的
结果（耗时/频率/失败原因）作为事件落盘可查；观测层异常被捕获、计数、
继续，绝不阻断业务；安全裁决（fail-closed BLOCK）完全不受影响。

## 2. 分层落点

| 层 | StaffDeck 对应 | U8 落点 | 状态 |
|----|----------------|---------|------|
| Event | event_log.py | `loop_core/observability.py` 的 `GuardCheckEvent` + `GuardEventRecorder`，落盘 `.ai/evidence/observability/guard-events.jsonl` | **已实现** |
| Span | spans.py | 事件内嵌 `duration_ms`（单次控制/整 guard/整次 integrity 检查的墙钟耗时） | 已实现（轻量内嵌，不另建 span 文件） |
| Log | runtime_logging.py | 观测写入失败经 `logging` 记 warning | 已实现（仅失败路径） |

span/log 的独立文件与链路追踪属 T-0090+ 范围（SLO/异步设施），本 U8 以
内嵌字段与失败日志覆盖，不做独立文件。

## 3. 事件 schema（一行一事件，append-only JSONL）

```json
{
  "event_id": "<uuid4 hex[:16]>",
  "guard_id": "content_guard | .ai/checkers/rogue_checker.py | guard_health",
  "capability_id": null | "compile_gate",
  "check_type": "health | death | missing | drift | integrity",
  "result": "PASS | FAIL | REPORT",
  "duration_ms": 12.345,
  "failure_reason": null | "GC-003 clean content passes: expected PASS got block (rc=2)",
  "timestamp": "2026-08-01T00:00:00+00:00",
  "source": "registry:<snapshot_id[:12]>"
}
```

检查类型与结果语义：

| check_type | 产生点 | result 语义 |
|------------|--------|-------------|
| `health` | `GuardHealth.run()` 每个控制（正/负样例） | PASS=guard 表现符合预期；FAIL=control_error（reason 记录） |
| `death` | `run()` 每个 guard 一次 | PASS=ALIVE；FAIL=DORMANT/BROKEN（reason 记录） |
| `missing` | `missing_detection()` 每个发现一次 | REPORT（inform，永不翻转 verdict） |
| `drift` | `drift_detection()` 每个发现一次 | REPORT |
| `integrity` | `integrity_check()` 每次一次 | 与 `overall` 一致（PASS/FAIL） |

`source` = 检查运行时的 capability registry 确定性快照指纹
（`snapshot().snapshot_id` 前 12 位），回答"这次检查基于哪版注册表"。

## 4. 采集点（guard_health 路径挂观测）

- `GuardHealth.__init__(root, registry=None, observability=None)`：
  - `None` → 默认开，惰性创建 `GuardEventRecorder(<root>/.ai/evidence/observability/guard-events.jsonl)`（构造不碰文件系统，首个事件才建文件）
  - `False` → 关闭（无 recorder，零 IO）
  - `GuardEventRecorder` 实例 → 覆盖路径/开关
- `run()` → 每控制 `health` 事件 + 每 guard `death` 事件
- `missing_detection()` / `drift_detection()` → 每发现 `REPORT` 事件
- `integrity_check()` → 1 个 `integrity` 事件（附死亡 guard 名单）

观测是**旁路记录**：所有记录点位于裁决逻辑之后，事件构造/写入不参与任何
判定分支；`_observe()` 对 recorder 调用再做一层 try/except 兜底。

## 5. 观测异常不阻断业务（AC-03b）

- `GuardEventRecorder.record()` 永不抛错：写入失败 → `failures += 1`、
  `last_error` 记录、`logging.warning` 一条，然后返回 `False`，调用方继续。
- `GuardHealth._observe()` 二次兜底：即使 recorder 自身有 bug，异常也被
  吞掉，绝不传入 `run()/integrity_check()` 的调用方。
- 失败观测**可见**：`recorder.failures` / `recorder.last_error` /
  `summary()["observability_failures"]` —— 观测层自己也是被观测的。

## 6. 安全裁决红线（AC-06，diff 审查验证）

- `loop_core/enforcement_hub.py`、`loop_core/hard_constraints.py`：**零改动**。
- EnforcementHub 对观测层**零耦合**（不构造、不记录、不引用 recorder）——
  测试 `test_observability_state_never_changes_enforcement_verdicts` 证明
  观测层 absent / working / failing 三种状态下 BLOCK/PASS 判定逐字段一致；
  `test_observation_failure_does_not_swallow_safety_block` 证明观测层抛错
  期间 fail-closed BLOCK 照常触发。
- 观测不得吞掉安全 BLOCK：由于观测不在裁决路径上，天然无法吞掉；对照
  测试将其固化为回归防护。

## 7. 开关与惰性

- `GuardEventRecorder(enabled=False)` / `set_enabled(False)`：禁用时 record
  为 no-op，不创建文件（测试 `test_recorder_can_be_disabled`）。
- `GuardHealth(..., observability=False)`：整体关闭（测试
  `test_guard_health_observability_switch_off_creates_no_file`）。
- 默认开但惰性：文件在首个事件前不存在（测试
  `test_guard_health_default_recorder_uses_evidence_path`）。

## 8. 聚合查询（summary）

`GuardEventRecorder.summary()` 只读聚合：
- `total_events` / `by_result`（PASS/FAIL/REPORT 计数）
- `by_guard[guard_id]`：`total`（频率）、`results`、`failures`（FAIL 数）、
  `duration_ms.{total,avg,max}`
- `observability_failures`（观测层自身失败计数，与业务失败分开）

## 9. AC-03 测试映射（tests/test_observability.py）

| 验收 | 测试 |
|------|------|
| AC-03a 事件落盘可查（guard_id/耗时/结果/失败原因/来源） | `test_events_persisted_after_integrity_check`、`test_health_pass_and_death_alive_events_recorded`、`test_integrity_pass_event_recorded` |
| AC-03b 观测异常不阻断业务 | `test_observation_failure_never_blocks_guard_health`、`test_observation_failure_does_not_swallow_safety_block` |
| AC-03c 观测开关不影响 BLOCK/PASS（对照） | `test_observability_state_never_changes_enforcement_verdicts`、`test_observability_switch_never_changes_health_results` |
| AC-03d append-only 不修改历史 | `test_event_file_is_append_only_never_rewrites_history` |
| 聚合查询 | `test_summary_aggregates_frequency_duration_failures` |

## 10. 文件清单

- 新增 `loop_core/observability.py` — 事件 schema + append-only recorder + summary
- 修改 `loop_core/guard_health.py` — run/integrity_check/missing/drift 挂观测
  （裁决语义零变化；diff 可核对）
- 新增 `tests/test_observability.py` — AC-03a/b/c/d + summary + 开关/惰性
- 本文件 `.ai/evidence/T-0089/observability/design.md`
- 运行证据（落盘）：`.ai/evidence/observability/guard-events.jsonl`
