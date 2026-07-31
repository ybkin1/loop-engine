# U3 设计证据：上下文预算压缩（context-compression）

> **T-0088（G-T-0088-REQUIREMENTS，approved）U3 工作包 | 2026-07-31 | developer 子代理**
> 落地文件：`loop_core/context_loader.py`（升级）+ `tests/test_context_compression.py`（新增）
> 本设计只描述 U3；U5（intent_router）/U6（human_review_packet）由并行子代理承载，互不重叠。

## 1. 借鉴映射（StaffDeck → loop-engine）

| StaffDeck 机制（T-0086 对标，事实） | loop-engine 落地 |
|---|---|
| `context_projection.py` / `conversation_context.py`：游标摘要 + token 预算 70% 触发压缩 | `ContextCompressor.compress_if_needed`：`estimate_tokens(text) > budget_tokens * trigger_ratio`（`DEFAULT_TRIGGER_RATIO = 0.7`）时触发；压缩仅作用于加载视图 |
| 摘要的摘要（层级，可配置深度） | `summarize_text(text, level=N)` 递归应用，`max_levels` 可配（默认 2）；每层必须实际降低 token 估算，否则停止（防振荡/增长） |
| `citations.py` 唯一前缀恢复（邮箱前缀截断修复） | `CitationResolver`：对 `…/T-xxxx/…`、`evidence/…`（丢 `.ai/` 前缀）、裸文件名做唯一性文件系统匹配；多匹配 → `AMBIGUOUS`，无匹配 → `NOT_FOUND`，两者均显式标记 `UNRESOLVED`，绝不猜测 |
| token 估算（无外部 tokenizer） | 沿用项目既有 `estimate_tokens`（英文词 ×1.3 + CJK 字符 ×2），提取为模块级函数供 loader 与 compressor 共用同一估算器 |

## 2. 接口

新增/扩展（全部为可选能力，默认行为与旧版完全一致）：

```
loop_core/context_loader.py
├─ 常量
│  DEFAULT_BUDGET_TOKENS = 2600      # 对应 FULL 级 ~2600 token
│  DEFAULT_TRIGGER_RATIO = 0.7       # 70% 触发（StaffDeck）
│  DEFAULT_MAX_SUMMARY_LEVELS = 2    # 摘要的摘要深度
│  UNRESOLVED_MARKER = "UNRESOLVED"  # 无法唯一恢复的显式标记
├─ dataclass CompressionResult
│  text / original_tokens / estimated_tokens / triggered /
│  levels_applied / budget_tokens / trigger_ratio / max_levels / citations
├─ dataclass CitationResolution
│  original / status(RESOLVED|AMBIGUOUS|NOT_FOUND) / resolved / matches
│  .is_resolved
├─ 函数
│  estimate_tokens(text)                       # 模块级（原方法委托）
│  extract_key_fields(text)                    # 任务ID/gate/阶段/决策点
│  summarize_text(text, level=1)               # 确定性规则摘要（纯函数）
│  repair_truncated_references(text, project_root) -> (text, resolutions)
├─ class ContextCompressor
│  __init__(budget_tokens=2600, trigger_ratio=0.7, max_levels=2,
│           project_root=None)
│  compress_if_needed(text, *, budget_tokens=None, trigger_ratio=None,
│                      max_levels=None) -> CompressionResult
├─ class CitationResolver
│  __init__(project_root, search_roots=None)   # 默认 .ai/evidence/
│  resolve(truncated) -> CitationResolution
└─ class ContextLoader（向后兼容扩展）
   load_role_context(role_id, complexity=0.5, *,
                     budget_tokens=None, trigger_ratio=0.7, max_levels=2)
   load_for_role(role_id, doc_path, complexity=0.5, *,
                 budget_tokens=None, trigger_ratio=0.7, max_levels=2)
   LoadedContext.compression: CompressionResult | None = None  # 新增字段（默认 None）
```

## 3. 预算语义

- 触发条件：`estimate_tokens(view) > budget_tokens * trigger_ratio`（默认 70%）。
- 压缩循环：每轮 `summarize_text(level=N)`；**每轮必须使 token 估算严格下降**，否则立即停止（不放大、不振荡）；达到 `max_levels` 或降到阈值以下即停止。
- 校验：`budget_tokens <= 0`、`trigger_ratio ∉ (0,1]`、`max_levels < 1` → `ValueError`（fail-fast，不做静默猜测）。
- 未触发（under threshold）：返回原文本原样，`triggered=False`、`levels_applied=0`、逐字相等。
- 触发但无内容可压缩：保持原视图（`_apply_budget_compression` 在 `levels_applied == 0` 时不改写视图）。

### 3.1 摘要算法（确定性、无 LLM 依赖）

每层摘要保留（按输出顺序）：
1. 关键字段头 `[CONTEXT SUMMARY L{n}]`：task_ids / gates / phases / decisions（每项去重，最多 5 个；gate 正则优先，避免 `G-T-0088-REQUIREMENTS` 内的 `T-0088` 被重复计入 task_ids）。
2. 全部标题行（`#`/`##`/`###`）。
3. 键值字段行（`task_id:`/`gate:`/`phase:`/`decision:`，含上一摘要头的 `- task_ids:` 行）。
4. evidence 引用行（含 `.ai/`、`evidence/`、`T-xxxx/`、`…/` 标记的路径行）：独立保留（上限 `CITATION_LINE_CAP = 8`，不占正文预算）——决策密集正文无法把证据线索挤出压缩视图；超长路径截断为 `…/末两段`（可恢复）。
5. 正文行：决策点行（决策关键词/“decision”）优先，再按文档顺序取最早的，上限 `min(level_cap, ⌈正文行数/2⌉)`——保证每层严格减半收缩；行内截断按层级加深（L1：160 字符/2 句 → L2：110 字符/1 句 → L3+：80 字符/1 句）。

句子切分对 `e.g.`/`i.e.`/`etc.` 等缩写做保护，避免 “e.g. .ai/…” 被误判为句尾。

## 4. 引用截断修复语义（AC-03）

可处理的截断形态（按解析顺序）：
1. 完整路径（`resolve` 直查文件系统存在）→ `RESOLVED`。
2. 丢失 `.ai/` 前缀（`evidence/T-xxxx/x.json`）→ 补前缀直查 → `RESOLVED`。
3. 截断后缀（`…/T-xxxx/x.json`、`T-xxxx/x.json`）：剥离 `…` 标记后对搜索根（默认 `.ai/evidence/`，不存在则 `.ai/`，再退到项目根）做 `rel.endswith(suffix)` 唯一匹配。
4. 裸文件名（`x.json`）：按 basename 唯一匹配。

判定：唯一匹配 → `RESOLVED`（返回规范相对路径 `.ai/evidence/T-xxxx/...`）；多个匹配 → `AMBIGUOUS`；零匹配 → `NOT_FOUND`。`repair_truncated_references` 对后两者在文本中替换为 `[UNRESOLVED: <ref>]`，**不做任何猜测**；解析记录（`CitationResolution`）随 `CompressionResult.citations` 返回。

## 5. 与现有加载器集成 & 向后兼容

- `load_role_context` / `load_for_role` 新增**仅关键字**可选参数 `budget_tokens/trigger_ratio/max_levels`；不传 `budget_tokens` 时走原逻辑，逐字节等价（有测试证明）。
- `budget_tokens` 语义：对**最终装配视图**（角色上下文 + 文档章节）做压缩；`load_for_role` 在文档章节拼装完成后统一压缩，不重复压缩角色部分。
- 压缩结果回写 `ctx.system_prompt`（视图）、`ctx.estimated_tokens`、`ctx.compression`、`loaded_sections` 追加 `[compressed: N level(s), a → b tokens]`。
- **证据链完整性**：压缩是输入文本的纯函数（summarize 不落盘；resolver 只读）；测试用 SHA-256 前后对比证明 `.ai/evidence/` 文件字节与文件数均不变。
- 不修改任何业务源码；仅 `loop_core/context_loader.py` + 测试。

## 6. 测试映射（tests/test_context_compression.py，33 项）

| 验收 | 测试（类::方法） |
|---|---|
| AC-01 预算触发 | `TestBudgetTrigger::test_threshold_configuration_takes_effect`（阈值配置生效）、`test_trigger_fires_when_over_budget_and_output_shrinks`（触发后输出长度下降）、`test_no_compression_below_threshold`（触发前不压缩）、`test_trigger_ratio_configures_threshold`、`test_invalid_parameters_raise_valueerror`；`TestLoaderBudgetIntegration::test_loader_compresses_over_budget_view`（loader 集成）、`test_load_for_role_compresses_final_view` |
| AC-01 证据链完整性 | `TestEvidenceChainIntegrity::test_compression_does_not_modify_evidence_files`、`test_loader_with_budget_keeps_evidence_intact`（压缩前后 SHA-256 一致、文件数一致） |
| AC-02 层级摘要 | `TestHierarchicalSummary::test_summary_can_be_summarized_again`（多轮压缩后可再次压缩）、`test_level_count_configuration_takes_effect`（层级数配置生效）、`test_key_fields_preserved_at_every_level`、`test_decision_point_lines_survive_compression`、`test_summarize_is_pure_function` |
| AC-03 引用截断修复 | `TestCitationResolver::test_exact_reference_resolved`、`test_dropped_ai_prefix_resolved`、`test_ellipsis_truncated_suffix_resolved`、`test_bare_unique_basename_resolved`、`test_ambiguous_basename_is_not_guessed`、`test_ambiguous_suffix_is_not_guessed`、`test_missing_reference_is_not_found`、`test_long_citation_truncate_and_repair_roundtrip`；`TestTextRepair::test_text_repair_restores_unique_references`、`test_text_repair_marks_ambiguous_as_unresolved`、`test_text_repair_marks_missing_as_unresolved` |
| 向后兼容 | `TestBackwardCompatibility::test_load_role_context_signature_unchanged`、`test_estimate_tokens_module_function_matches_method`、`test_loaded_context_extra_field_has_default`、`test_compression_result_repr_fields` |

## 7. 约束与风险

- 压缩仅作用于加载视图；原始证据/任务文件零写入（测试证明）。
- 无法唯一恢复的引用 → `[UNRESOLVED: …]`，不猜测（测试证明：AMBIGUOUS/NOT_FOUND 均不产生猜测路径）。
- 摘要是有损的（MEDIUM 风险，任务文件已声明）：通过保留关键字段头 + 决策点/证据引用行缓解；证据链完整性由测试守护。
- 未弱化任何约束：本工作包不触碰 C1-C11 / hook 语义（fail-safe 语义属于 U5 范围）。
