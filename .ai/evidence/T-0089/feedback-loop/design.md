# T-0089 U4 — Gate 决策反馈回路 设计证据（design）

> **T-0089（学习回路与工程化）U4 工作包 | 2026-08-01 | Gate: G-T-0089-REQUIREMENTS（approved）**
> 借鉴来源：OpenBMB/StaffDeck `backend/app/feedback/service.py` 的"反馈归因 6 bucket + 技能健康度回流"模式（见 `.ai/evidence/T-0086/staffdeck-benchmark.md` U4：拒绝/修复请求 → 经验沉淀 → human_review_packet 质量改进）。
> 落地位置：`loop_core/gate_feedback.py`（新增）+ `loop_core/human_review_packet.py`（可选集成字段）。

## 1. 借鉴映射

| StaffDeck feedback/service.py | loop-engine U4 落地 | 差异说明 |
|---|---|---|
| 反馈归因 6 bucket（分类归因） | 拒绝/修复原因分类：`scope` / `evidence` / `risk` / `wording` / `other` | 按 loop-engine gate 决策语义收敛为 5 bucket + other 兜底 |
| 反馈 → 技能健康度回流 | gate 拒绝/修复请求 → gate_lessons 结构化沉淀（可检索） | 面向"决策包质量改进"而非技能健康度 |
| 反馈记录可追溯（归因/效果） | lesson 记录含 gate/task/decision/原因文本/修复建议/来源（决策包版本）/时间戳/schema 版本 | 追加式落盘 `.ai/evidence/feedback/gate-lessons.yaml`，不修改历史 gate 记录 |
| —（StaffDeck 无此语义） | **幂等去重**：同 gate + 同决策 + 同原因指纹 → 不重复记录 | 确定性 lesson_id（SHA-256）即去重键，为 loop-engine 强化项 |

## 2. gate_lessons Schema（v1）

落盘位置：`.ai/evidence/feedback/gate-lessons.yaml`（追加式；历史 gate 记录不做任何修改）。

```yaml
schema: gate_lessons
schema_version: 1
lessons:
- lesson_id: GL-<sha256(gate_id|decision|category|normalized_reason)[:16]>
  gate_id: G-T-0005-CLOSEOUT-REVIEW
  task_id: T-0005
  decision: rejected            # rejected | repair_requested | approved
  reason_category: evidence     # scope | evidence | risk | wording | other
  reason_text: Closeout review failed because CONTRACTS.md and KNOWN_ISSUES.md still contain stale pre-installation statements.
  repair_suggestion: Repair stale installation-state wording, then rerun closeout review.
  source: HRP-00000001          # 可选：决策包版本
  recorded_at: '2026-08-01T06:00:00+00:00'
  schema_version: 1
```

- **lesson_id 确定性生成**：`make_lesson_id(gate_id, decision, reason_category, reason_text)` = `GL-` + SHA-256(fingerprint) 前 16 位大写 hex；指纹 = `gate_id|decision|reason_category|normalized_reason`，其中 normalized_reason = 去首尾空白 + 折叠空白 + casefold。同指纹 → 同 id（去重键）。
- **去重（幂等）**：`record_gate_lesson()` 先按 lesson_id 扫描现有记录，命中则返回 `(existing, False)`，不追加；未命中返回 `(lesson, True)`。原因文本不同 / 决策不同 / 分类不同 / gate 不同 → 各自成条。
- **fail-closed 校验**：decision/category 枚举校验、gate_id/task_id/reason_text 非空、schema_version 受支持；`load_lessons()` 对畸形记录抛 `InvalidLessonError`，不静默丢弃（机器不猜自己的记忆）。
- **原子写**：tmp 文件 + `os.replace`，避免半写文件。

## 3. 检索接口

| 接口 | 语义 |
|---|---|
| `by_gate_id(project_root, gate_id)` | 同 gate 的全部 lesson（记录顺序） |
| `by_reason_category(project_root, category)` | 同原因分类的 lesson；未知分类抛 `InvalidLessonError` |
| `recent(project_root, limit=10)` | 最新 N 条（recorded_at 降序，稳定排序） |
| `search(project_root, keyword)` | 大小写不敏感子串匹配：reason_text / repair_suggestion / gate_id / task_id / decision / category / source；空 keyword 返回全部 |
| `suggest_related_lessons(project_root, *, gate_id=None, reason_category=None, limit=5)` | 决策包集成用：同 gate ∪ 同分类，按 lesson_id 去重、最新优先、limit 截断 |
| `related_lessons_summary(lessons, limit=None)` | 渲染为紧凑 markdown 摘要（每条：gate — decision (category): 原因 + 修复建议 + 来源） |

## 4. 决策包集成（可选增强，默认行为不变）

- `HumanReviewPacket` 新增可选字段 `related_experience: str = ""`（默认空串）。
- `HumanReviewPacketBuilder.from_phase_completion(..., related_experience=None)` 与 `from_veto_escalation(..., related_experience=None)` 末尾追加可选关键字参数（现有位置参数签名不变），透传至 packet。
- 渲染（to_markdown / to_plain_text）仅在 `related_experience` 非空时输出 "Related Past Experience" 小节（置于决策区之前）——**默认行为与升级前完全一致**（AC-01d 测试锁定）。
- 典型用法：gate 被拒/要求修复时 `record_gate_lesson()`；下一次同 gate / 同分类 gate 生成决策包时 `suggest_related_lessons()` + `related_lessons_summary()` → 附到 packet，非技术用户可见历史经验（含修复建议）。
- 现有调用方无签名破坏；resume_payload（U6）字段与渲染不受影响。

## 5. 文件清单（U4 交付物）

| 文件 | 角色 |
|---|---|
| `loop_core/gate_feedback.py` | 新增：GateLesson / record_gate_lesson（幂等）/ load_lessons / by_gate_id / by_reason_category / recent / search / suggest_related_lessons / related_lessons_summary |
| `loop_core/human_review_packet.py` | 纯增量：`related_experience` 字段 + builder 可选参数 + 条件渲染小节（现有接口不变） |
| `tests/test_gate_feedback.py` | 43 项测试：AC-01a 结构化记录 / AC-01b 去重 / AC-01c 检索 / AC-01d 决策包集成 + fail-closed 校验 |
| `.ai/evidence/T-0089/feedback-loop/design.md` | 本设计证据 |

## 6. 验收对照（T-0089 AC-01）

- **AC-01**（反馈回路：gate 拒绝/修复请求经验沉淀有测试 — 记录结构化 + 可检索 + 含拒绝原因/修复建议）：✅
  - `TestAC01aStructuredRecording`（15 项）：字段完整（gate_id/task_id/decision/reason_category/reason_text/repair_suggestion/source/recorded_at/schema_version）+ 确定性 lesson_id + YAML 落盘 + round-trip + fail-closed（非法 decision/category/空字段/畸形文件/不支持 schema）。
  - `TestAC01bDedup`（7 项）：同指纹幂等（created=False、仅 1 条）；空白/大小写归一；原因文本/决策/分类/gate 不同各自成条；跨追加代际去重。
  - `TestAC01cRetrieval`（13 项）：by_gate_id / by_reason_category / recent（降序 + limit + 默认值）/ search（原因文本、修复建议、gate_id、大小写、空 keyword）/ suggest_related_lessons（并集去重 + limit）。
  - `TestAC01dPacketIntegration`（8 项）：默认 packet 无 related_experience 且渲染无新小节（向后兼容）；from_phase_completion / from_veto_escalation 可选参数生效；摘要内容含 gate/decision/分类/原因/修复建议/来源；端到端：记录 → 检索 → 摘要 → 决策包。
- 回归：`test_human_review_packet.py` + `test_resume_payload.py` 108 项全过；全量测试结果见 acceptance 汇报。
- 无业务源码改动；历史 gate 记录零修改；约束层（enforcement/hooks/C1-C11）零改动。
