# T-0096 D3 — 知识/记忆服务 设计证据（design）

> **T-0096（知识/记忆服务 D3）| 2026-07-31 | Gate: G-T-0096-REQUIREMENTS（approved）**
> 借鉴来源：OpenBMB/StaffDeck 知识库 + 长期记忆（见 `.ai/evidence/T-0086/staffdeck-benchmark.md` D3 行：OKF 知识库 + 记忆提取/注入），按 loop-engine 治理域轻量落地：**不做文档解析/OKF 重功能**，只做结构化知识沉淀 + 检索 + 跨任务经验提取/注入。
> 落地位置：`loop_core/knowledge_store.py`（新增）+ `loop_core/memory_service.py`（新增）+ `loop_core/context_loader.py`（可选注入，纯增量）。

## 1. 借鉴映射

| StaffDeck D3 | loop-engine T-0096 落地 | 差异说明 |
|---|---|---|
| OKF 知识库（文档解析/重功能） | `knowledge_store.py`：结构化 KnowledgeEntry（decision/lesson/pitfall/best_practice）+ 落盘 + 多维检索 | 治理域轻量实现：不做文档解析，只沉淀决策/经验/教训/最佳实践 |
| 记忆提取（experience → knowledge） | `memory_service.extract_memories`：gate_lessons（T-0089）+ 各任务验收报告 → 规则式提取（确定性，无 LLM） | 提取来源统一为治理域既有记录，不新造输入 |
| 记忆注入（recall → context） | `memory_service.recall`（top-N）+ `context_loader` 可选记忆段 | 默认关闭 + 注入上限（5 条），不污染既有上下文 |
| —（StaffDeck 无此语义） | **幂等去重**：同来源 + 同内容指纹 → 不重复写入 | 确定性 entry_id（SHA-256）即去重键，为 loop-engine 强化项 |

## 2. 数据流（单向：lessons/验收报告为源，knowledge 为派生视图）

```
                    ┌─────────────────────────────┐
  record_gate_lesson│ gate-lessons.yaml（T-0089） │ ← 源（T-0089 写入，T-0096 零改动）
  （不写 knowledge）└──────────────┬──────────────┘
                                  │
  .ai/evidence/T-*/acceptance/*.md│ ← 源（验收报告，只读）
                                  │
                     extract_memories()（规则式/确定性）
                                  │  幂等写入（同指纹不重复）
                                  ▼
        .ai/evidence/knowledge/knowledge-store.yaml ← 派生视图
                                  │
                     recall(task_id/gate_id/tag/keyword, limit=5)
                                  │
                     ┌────────────┴────────────┐
                     ▼                          ▼
        context_loader 记忆段（可选注入）     human_review_packet
        （include_memories 默认关闭）         related_experience（T-0089 既有）
```

- **无反向耦合**：`record_gate_lesson` 内部不写 knowledge（AC-03 测试锁定：记录 lesson 后 knowledge store 不存在）；knowledge 由 `extract_memories` 统一聚合。
- **源文件只读**：提取永不修改 gate-lessons.yaml / 验收报告（AC-03 测试按字节比对锁定）。

## 3. knowledge_store schema（v1）

落盘位置：`.ai/evidence/knowledge/knowledge-store.yaml`（追加式原子写：tmp + `os.replace`，进程内 `_PUT_LOCK` 串行化 RMW——沿用 T-0095 锁模式）。

```yaml
schema: knowledge_store
schema_version: 1
entries:
- entry_id: KE-<sha256(kind|source_type|source_id|normalized_content)[:16]>
  kind: lesson                # decision | lesson | pitfall | best_practice
  source_type: gate           # task | gate | lesson | incident
  source_id: G-T-0005-CLOSEOUT-REVIEW
  task_id: T-0005             # 可选：关联任务（lessons 透传/验收报告自身）
  tags: [gate, rejected, evidence]
  content: G-T-0005-CLOSEOUT-REVIEW rejected（evidence）: Closeout review failed ...
  recorded_at: '2026-08-01T06:00:00+00:00'
  version: 1
  schema_version: 1
```

- **entry_id 确定性**：`make_entry_id(kind, source_type, source_id, content)` = `KE-` + SHA-256(fingerprint) 前 16 位大写 hex；指纹 = `kind|source_type|source_id|normalized_content`（normalized = 去首尾空白 + 折叠空白 + casefold）。同来源+同内容 → 同 id（去重键）。
- **幂等（AC-01）**：`put_entry()` 先按 entry_id 扫描，命中返回 `(existing, False)` 不追加；内容/来源/类型任一不同 → 各自成条。
- **fail-closed 校验（AC-01）**：kind/source_type 枚举、source_id/content 非空、tag 规则（非空、无空白/分隔符、≤40 字符、≤32 个、大小写不敏感去重）、schema_version 受支持、version ≥ 1；`load_entries()` 对畸形记录抛 `InvalidKnowledgeEntryError`（机器不猜自己的记忆）。

## 4. 检索接口（AC-01，上限 20）

| 接口 | 语义 |
|---|---|
| `by_task(project_root, task_id, limit=20)` | 关联任务（entry.task_id 或 task 来源 source_id） |
| `by_gate(project_root, gate_id, limit=20)` | gate 来源条目（gate 裁决派生） |
| `by_tag(project_root, tag, limit=20)` | 主题标签（大小写不敏感）；坏 tag 明确拒绝 |
| `search(project_root, keyword, limit=20)` | 大小写不敏感子串：content/tags/source_id/task_id/kind/entry_id |
| `query(..., task_id/gate_id/tag/keyword, limit=20)` | 组合过滤（AND），最新优先，limit 截断 |
| `put_entry(...)` | 写入（幂等），返回 `(entry, created)` |

统一：最新优先（recorded_at 降序，同时间戳稳定保序）、`limit` 截断（`DEFAULT_SEARCH_LIMIT = 20`）。

## 5. 记忆服务（AC-02）

### extract_memories（规则式，无 LLM）

| 来源 | 规则 | 产出 kind | 来源类型 |
|---|---|---|---|
| gate_lessons（每条） | rejected/repair_requested → lesson；approved → best_practice；tags=[gate, decision, category]；content=原因文本 + 修复建议 | lesson / best_practice | gate（source_id=gate_id，task_id 透传） |
| 验收报告标题行 `> **T-XXXX: <标题> \| <日期>**` | → 决策条目 | decision | task |
| 验收报告 Gate 行 | 含"批准/approve" → best_practice；"拒绝/reject" → lesson；否则 decision | 按规则 | gate |
| 验收报告独立审查/最终裁决行 | → 裁决条目 | decision | task |
| 验收报告"已知遗留"小节 bullets | → 教训条目 | pitfall | task |

- 非标准格式报告（无 `# T-XXXX 验收报告` 标题/无标题行）整体跳过并计数（`sources["skipped_reports"]`），不产生垃圾条目。
- `task_ids` 过滤可按任务定向提取；返回 `MemoryExtractionReport`（created/duplicates/sources/total/created_entry_ids）。

### recall（供注入，AC-02）

`recall(task_id=None, gate_id=None, tag=None, keyword=None, limit=5)`：全部过滤 AND 组合、最新优先、`limit` 截断（注入默认 5——上下文注入的 top-N 约束）。空 store 返回 `[]`（无错误）。

### memories_to_context（渲染，AC-02）

召回条目 → 紧凑 markdown 记忆段（每条：`- (kind) source_id [tags]: content[:200]`）；空输入 → `""`。

## 6. context_loader 可选记忆注入（AC-04，默认不变）

- `load_role_context` / `load_for_role` 新增**可选关键字参数**：`include_memories: bool = False`、`memory_limit: int = 5`、`memory_task_id: str | None = None`（尾部追加，现有位置参数/关键字调用零破坏）。
- 开启时：`recall(task_id=memory_task_id, limit=memory_limit)` → `memories_to_context` → 在最终视图（含压缩后）追加 "## 相关经验（Related Memories）" 段 + `loaded_sections` 记录 `[memories: N recalled]` + 重算 `estimated_tokens`。
- **默认关闭**（AC-04 测试锁定）：`include_memories=False` 完全不读 knowledge store——即使 store 文件损坏也不报错、视图逐字节不变。
- 开启且 store 缺失/为空 → 不注入、无错误；store 损坏 → `KnowledgeStoreError` 明确抛出（fail-closed，不猜记忆）。

## 7. 文件清单（交付物）

| 文件 | 类型 | 说明 |
|---|---|---|
| `loop_core/knowledge_store.py` | 新增 | 551 行：schema/幂等写/多维检索/fail-closed 校验 |
| `loop_core/memory_service.py` | 新增 | 439 行：extract_memories/recall/memories_to_context |
| `loop_core/context_loader.py` | 修改（纯增量 +82） | 可选记忆注入（默认关闭） |
| `tests/test_knowledge_memory.py` | 新增 | 73 测试（AC-01/02/03/04） |
| `.ai/evidence/knowledge/knowledge-store.yaml` | 运行时产物 | 真实项目 extract_memories 结果：55 条（10 任务，0 lessons——gate-lessons 尚无记录） |
| `.ai/evidence/T-0096/knowledge/design.md` | 本文件 | 设计证据 |

## 8. 风险与缓解

| 风险 | 等级 | 缓解 |
|---|---|---|
| 与 gate_feedback 重复 | MEDIUM | 数据流单向（AC-03）：lessons 为源，knowledge 派生；record_gate_lesson 零改动 |
| 记忆注入污染上下文 | LOW | 默认关闭（AC-04）+ 注入上限 5 + 组合过滤 + fail-closed 拒绝坏 store |
| 提取噪声 | LOW | 仅解析标准化验收报告（T-0088+ 格式），其余跳过计数；真实运行 55 条人工抽查质量良好 |
