# T-0097 — B2 学习回路补全：Incident / Retrospective / Second-Failure Doctrine

| | |
|---|---|
| **Task** | T-0097 — B2 学习回路补全（G-T-0097-REQUIREMENTS，approved） |
| **Role** | developer |
| **Date** | 2026-07-31 |
| **Status** | implemented（AC-01..AC-04 验收通过） |
| **Basis** | `docs/designs/loop-v4-slo-metrics-learning.md` B2 §3（learning loop）、T-0089 gate_lessons、T-0093 SLO 门禁豁免模式、T-0096 knowledge_store |
| **Scope** | incident 记录 + 复盘 + second-failure 自动检测/阻断 + gate_lessons 衔接；**不自动登记 task_graph** |

---

## 1. 目标与边界

B2 §3 剩余落地：把 S11→S1 从"循环"变成"学习回路"——每次失败有结构化
incident 记录，复盘产生带 owner + deadline 的行动项，同类失败复发由机器
检测并阻断，直到存在被认领的行动项（Amazon COE second-failure doctrine：
"第二次失败是流程的失败"）。

**明确不做的**（T-0097 约束）：
- 检测产生的任务**建议草稿只落盘** `.ai/evidence/observability/second-failures.yaml`
  （report 级），**绝不自动登记 task_graph**——用户批准后才可成为正式任务。
- 不修改业务源码；仅新增 loop_core 模块 + checker + hook 接线（opt-in）。

## 2. 交付物

| 文件 | 职责 |
|---|---|
| `loop_core/incidents.py` | IncidentRecord schema、落盘（追加式原子写 + 进程内锁 + 幂等）、检索、gate_lessons 桥 |
| `loop_core/retrospectives.py` | Retrospective schema、行动项 owner/deadline/status 跟踪、全 done → retro closed |
| `loop_core/second_failure.py` | 复发检测（纯函数）、报告落盘、`second_failure_block` 门禁、豁免、开关 |
| `.ai/checkers/second_failure_checker.py` | compile_gate 同款 CLI，退出码 0/1/2，`--detect` 报告维护模式 |
| `hooks/scripts/loop_enforcement.py` | S6 发布分支新增 `check_second_failure_gate_evidence`（**默认关闭**） |
| `hooks/scripts/hook_common.py` | DEFAULT_CONFIG 新增 `second_failure_gate.enabled: false` |
| `tests/test_learning_loop.py` | AC-01..AC-04 + checker CLI + S6 接线（81 tests） |
| `docs/designs/loop-v4-slo-metrics-learning.md` | 未修改（只读基准） |

## 3. 数据模型与落盘

### 3.1 IncidentRecord（`incidents.yaml`）

字段：`incident_id`（确定性 `IN-<hex10>`）、`category`
（gate_rejection / guard_failure / regression / slo_breach / other）、
`severity`（critical / high / medium / low）、`scope`（影响范围描述）、
`occurred_at` / `discovered_at`（时间线）、`resolution`（可选处置）、
`status`（open / resolved / closed）、`source_type` / `source_id`
（来源，如 gate_id）、`title` / `root_cause`（可选，可检索）、
`recorded_at`、`schema_version`。

**幂等键** = `category | source_type | source_id | 归一化 root_cause |
occurred_at`。设计要点：`occurred_at` 是幂等键的一部分——**同一事件**的重复
登记（如 hook 双触发）去重；**不同时刻**的同类失败是不同 incident，这正是
second-failure 复发可检测的前提（§4.1）。同来源 + 同指纹 + 同时刻 → 不重复。

落盘：`.ai/evidence/observability/incidents.yaml`，tmp+rename 原子写 +
进程内锁（T-0095 并发模式），追加式（历史记录永不改写）。

检索：`by_category` / `by_status` / `by_severity` / `search(keyword)` /
`by_source(source_type[, source_id])`；非法过滤值 fail-closed 抛错；
文件损坏 fail-closed（绝不静默丢弃）。

### 3.2 Retrospective（`retrospectives.yaml`）

字段：`retro_id`（确定性 `RT-<hex8>` = incident_id + 归一化 root_cause，
一个 incident 一个复盘）、`incident_id`、`root_cause`、`action_items[]`
（`id`=`AI-<hex6>` / `owner` / `deadline`（ISO date 或 datetime，可解析）/
`status`（open/done）/ `description` / `done_at`）、`status`（open/closed）、
`created_at` / `updated_at`、`schema_version`。

状态跟踪：`update_action_item` open→done（写 `done_at`）；**全部 done →
retro 自动 closed**。closed 复盘不可变（不可加行动项、不可翻转状态；
同状态幂等 no-op 除外）。零行动项的复盘保持 open——"无任何认领计划"本身
就是未解决状态（§4.2 的阻断依据）。

### 3.3 SecondFailureRecord（`second-failures.yaml`，report 级）

字段：`second_failure_id`（确定性 `SF-<hex8>` = 首次+复发 incident id 对）、
`first_incident_id` / `second_incident_id`、`category`、
`root_cause_fingerprint`（= category|source_type|source_id|归一化原因）、
`source_type` / `source_id`、**`task_draft`**（title / scope / reason——
建议任务草稿）、`status`（open/resolved）、`detected_at`、`schema_version`。

report 级 = 派生产物：检测结果可增量落盘（按 `second_failure_id` 幂等），
`resolve_second_failure()` 可显式置 resolved（incident 台账保持只追加，
报告允许状态更新）。

## 4. Second-failure 检测与门禁

### 4.1 `detect_second_failure(incidents)`（纯函数）

按 `root_cause_fingerprint`（同类别 + 同根因指纹：来源 + 归一化原因）分组，
第 2 次及以后每次出现与**紧邻前一次**配对生成一条 SecondFailureRecord
（第 3 次出现 → 第二条，形成 escalation 链）。`min_recurrences` 默认 2。

### 4.2 `second_failure_block(project_root)`（fail-closed 门禁）

| 情形 | 判定 |
|---|---|
| 开关未启用（默认） | PASS（DISABLED，advisory 说明） |
| 证据文件**缺失**（无 incident/无报告） | PASS（缺失不是证据；没有记录就没有复发） |
| 证据文件**不可解析** | BLOCK（NOT_AVAILABLE，列出文件——机器不猜自己的记忆） |
| 未解决复发：关联 retro 无 open 行动项（无 retro / retro 零行动项） | **BLOCK** `SECOND_FAILURE_UNRESOLVED`，逐条明细（incident 对、类别、原因、task_draft） |
| 关联 retro 有 ≥1 open 行动项（owner+deadline） | PASS（有认领计划） |
| 关联 retro 已 closed（全部行动项 done） | PASS（闭环即完成——完成的计划是 doctrine 的出口） |
| 记录显式 resolved | PASS |
| 有效豁免（未过期 + approver 非空） | PASS（原因含豁免记录） |

关联 retro 解析：优先 second incident 的 retro，回退 first incident 的 retro。

豁免：`.ai/evidence/observability/second-failure-exemptions.json`
（append-only，SLO 豁免同款：reason / expires_at / approver；
`SF-EX-####` 序号）。

### 4.3 开关

`LOOP_SECOND_FAILURE_GATE_ENABLED` 环境变量（显式值优先）→
`.zcode/skills/loop-governance/config.yaml` 的
`second_failure_gate.enabled` → **默认 false**（wave 1 advisory / opt-in）。
启用只会**新增**阻断条件，绝不放松既有检查（T-0093 AC-06 姿态延续）。

### 4.4 S6 接线（最小侵入）

`loop_enforcement.py` 的 S6-delivery 分支在 SLO 门禁之后追加
`check_second_failure_gate_evidence(root)`：模块加载/执行异常 fail-closed
阻断（同 SLO 门禁的插件缓存规避模式）；默认关闭 → 既有项目与全部既有
测试行为零变化。启用路径的放行/阻断语义与 `second_failure_block` 完全一致。

### 4.5 为什么默认关闭而不是默认开启

- SLO 门禁默认开启是因为 error budget 是"有数据才能算"的定量闸；而
  second-failure 阻断的前提是项目已建立 incident 记录习惯（wave 1 是
  记录 + 报告，先有数据）。
- 与 B2 §3.6 迁移路径一致：wave 1 advisory（手动/opt-in）→ wave 2 enforced
  → wave 3 default-on。本任务交付 wave 1 全套机制 + wave 2 的开关就绪。

## 5. 与 gate_lessons 衔接（AC-04）

`register_gate_rejection_incident(gate_id, *, min_rejections=2, ...)`：
从 gate_lessons（T-0089，`.ai/evidence/feedback/gate-lessons.yaml`）统计
该 gate 的 rejected / repair_requested 次数，≥2 次 → 登记
`gate_rejection` incident（source_type=gate，source_id=gate_id）。
`occurred_at` 取最新一条 rejection lesson 的 `recorded_at`——**确定性**：
同一批 lesson 重跑幂等去重；新 rejection 使发生时刻前移 → 新 incident →
可被 second-failure 检测配对（跨计数的复发链）。

## 6. 与 T-0096 knowledge 的衔接（说明）

`knowledge_store` 已预留 `SOURCE_INCIDENT` 来源类型；incident 沉淀到
knowledge 是 memory_service 的**派生视图**职责（记录侧不反向耦合，
与 gate_lessons→knowledge 同构）。本任务不实现该派生（超出 AC 范围），
留作后续记忆侧任务。

## 7. 验收对照

| AC | 证据（tests/test_learning_loop.py） | 结果 |
|---|---|---|
| AC-01 incident schema/落盘/检索/幂等 | TestAC01Incidents（22 tests：字段完整性、确定性 IN-id、同事件幂等、异事件分立、检索四轴、fail-closed、并发锁） | 通过 |
| AC-02 复盘 owner/deadline/status 跟踪 | TestAC02Retrospectives（16 tests：RT-id 去重、行动项校验、open→done、全 done→closed、closed 不可变） | 通过 |
| AC-03 second-failure 复发→草稿 + 未解决阻断 | TestAC03SecondFailure（21 tests：检测配对、三次复发链、task_draft、BLOCK/PASS 决策表、豁免、fail-closed、开关） | 通过 |
| AC-04 gate_lessons ≥2 拒绝 → incident | TestAC04GateLessonsBridge（8 tests）+ TestSecondFailureCheckerCli（6 tests）+ TestS6HookWiring（4 tests） | 通过 |

全量回归：`pytest tests/ -q` ≥ 3594 passed（本任务新增 81 tests，无既有
测试回归——second-failure 门禁默认关闭保证 hook 行为零变化）。

## 8. 运行示例

```bash
# 登记 incident（gate_lessons 桥）
python - <<'EOF'
from loop_core.incidents import register_gate_rejection_incident
register_gate_rejection_incident("." , "G-T-0097-REQUIREMENTS")
EOF

# 检测 + 落盘报告（--detect 才写文件；门禁本身只读）
python .ai/checkers/second_failure_checker.py . --detect
# exit 0 = PASS（含 DISABLED/豁免），1 = BLOCK，2 = 参数错误

# 启用门禁（config.yaml）
# second_failure_gate:
#   enabled: true
```
