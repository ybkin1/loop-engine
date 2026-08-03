# T-0110 批 B-2 — human_review_packet / context_loader 行为等价拆分验收

日期：2026-08-03
执行：developer 子代理（批 B-2）
基线：工作树 = HEAD v3.12.46 + 批 A（constants.py）+ 批 B-1（governance_metrics/
intent_router 拆分）+ 本批
验收方法：**golden 快照先行**（拆分前捕获 → 拆分后重放 → 逐字节对比）

---

## 一、拆分边界表（按 design-common-weakness.md 1.4 / 1.5）

### 1.1 loop_core/human_review_packet.py（1307 → 643 行壳）

| 外提内容 | 原位置 | 目标新模块 | 实现 |
|---|---|---|---|
| 数据模型（PacketType/KeyChoice/RiskItem/DecisionRequired/DecisionPoint/ResumeSnapshot/ResumePayload/ResumeContext + to/from_dict、to_json/from_json 序列化）+ 异常族（ResumePayloadError/StateDriftError）+ 恢复常量（RESUME_PAYLOAD_SCHEMA/VERSION/PRESENTATION_VERSION） | :34-254 | `review_models.py`（236 行，**依赖图叶子**，零 loop_core 依赖） | 逐字迁移 |
| Resume 载荷逻辑（`_load_authoritative_yaml`/`_find_task`/`_find_gate`/`_TASK_RECOVERY_FIELDS`/`_GATE_RECOVERY_FIELDS`/`_task_recovery_record`/`_gate_recovery_record`/`_pending_tasks`/`build_resume_payload`/`resume_from_payload`） | :256-526 | `resume_payload.py`（293 行，仅依赖 review_models） | 逐字迁移 |
| 渲染器（`HumanReviewPacket.to_markdown`/`to_plain_text` 函数体 + `_phase_label`/`_format_ts`） | :570-682,1282-1307 | `review_renderer.py`（237 行，**依赖图叶子**，鸭子类型零导入） | 逐字迁移为 `render_markdown`/`render_plain_text` |
| **保留在壳**：HumanReviewPacket（数据类，to_markdown/to_plain_text 改为薄委托 `render_markdown(self)`，方法级局部导入避免壳命名空间新增绑定）、HumanReviewPacketBuilder（from_phase_completion/from_veto_escalation/_extract_key_choices/translate_technical_risk/_RISK_TRANSLATIONS） | :527-1277 | `human_review_packet.py`（643 行壳） | 保留 + 全量 re-export |

**设计说明（渲染器接线方式）**：渲染函数体迁移后，壳类方法必须仍为类方法
（`dir(类)` 方法面不变）且壳模块命名空间不得新增 `render_markdown` 等绑定
（dir() 逐名一致要求），故采用方法体内部局部导入的薄委托——运行时仅多一次
函数查表，输出逐字节不变。

### 1.2 loop_core/context_loader.py（1432 → 839 行壳）

> 注：设计文档 1.5 基线 1342 行，T-0108 接入 `_select_relevant_sections` 路由表
> 逻辑后为 1432 行；拆分边界按 1.5 表 + T-0108 路由逻辑一并外提。

| 外提内容 | 原位置 | 目标新模块 | 实现 |
|---|---|---|---|
| 正则常量族 + key 字段提取（`_TASK_ID_RE`/`_GATE_ID_RE`/`_PHASE_RE`/`_DECISION_RE`/`_HEADING_RE`/`_KEY_FIELD_LINE_RE`/`_CITATION_TOKEN_RE`/`_SENTENCE_SPLIT_RE`/`_ABBREV_RE`、`extract_key_fields`/`_format_key_fields`） | :189-212,321-365 | `loader_fields.py`（86 行，**依赖图叶子**） | 逐字迁移 |
| 引用解析（`CitationResolution`/`CitationResolver`/`repair_truncated_references`/`_find_citation_tokens`/`_truncate_citation` + `CITATION_MAX_CHARS`/`UNRESOLVED_MARKER`） | :130,162-181,254-264,267-279,481-637 | `citation_resolver.py`（229 行，仅依赖 loader_fields） | 逐字迁移 |
| 摘要级别/行选择（`_level_line_params`/`_level_body_cap`/`_select_body_lines`/`CITATION_LINE_CAP`/`_split_sentences`/`_truncate_line`/`summarize_text`/`estimate_tokens`） | :212-479 | `loader_summary.py`（226 行，依赖 loader_fields + citation_resolver） | 逐字迁移 |
| 文档节选择/框架标题 + **T-0108 F4 路由表逻辑**（`_extract_framework_titles`/`_select_relevant_sections`/`_ROUTING_CACHE`/`_parse_front_matter_yaml`/`_load_section_routing`） | :1268-1324,1374-1432 | `loader_sections.py`（184 行，**依赖图叶子**，DocumentIndex 仅 TYPE_CHECKING 注解） | 逐字迁移 |
| **保留在壳**：LoadLevel/LoadedContext/DocumentIndex/CompressionResult/ContextCompressor/_validate_budget_params/DEFAULT_* 常量/MINIMAL_MAX/STANDARD_MAX/_complexity_to_level/ContextLoader 全流程（含 _apply_memory_injection D3 语义）/ _parse_yaml/_extract_fixed_stance/_extract_contract_extras | :51-123,133-159,641-754,756-772,780-1193,1201-1272 | `context_loader.py`（839 行壳） | 保留 + 全量 re-export |

**D3/T-0104 硬约束保持**：`include_memories`（默认 False）、`memory_limit`（默认
5）、`memory_task_id`（默认 None）的 kwdefaults 与默认关闭不读知识库、损坏存储
fail-closed（开启时才抛）语义全部保持（golden 捕获 + 专项测试断言）。

依赖 DAG（无环）：`review_models`（叶）← `resume_payload`；`review_renderer`（叶）；
壳 import 三叶。`loader_fields`（叶）← `citation_resolver` ← `loader_summary`；
`loader_sections`（叶）；壳 import 四叶。静态断言见
tests/test_t0110_batch_b2.py `test_dependency_dag_order` 及叶子零反向引用壳测试。

## 二、新模块清单与壳规模

| 文件 | 角色 | 行数 |
|---|---|---|
| loop_core/review_models.py | 新增（数据模型 + 序列化 + 异常族，叶子） | 236 |
| loop_core/resume_payload.py | 新增（U6 resume 载荷 build/resume，fail-closed） | 293 |
| loop_core/review_renderer.py | 新增（markdown/plain 渲染 + 相位/时间格式化，叶子） | 237 |
| loop_core/loader_fields.py | 新增（正则族 + key 字段提取，叶子） | 86 |
| loop_core/loader_summary.py | 新增（摘要级别/行选择/summarize/estimate） | 226 |
| loop_core/citation_resolver.py | 新增（引用解析 + 截断修复 + UNRESOLVED） | 229 |
| loop_core/loader_sections.py | 新增（节选择 + T-0108 路由表/缓存，叶子） | 184 |
| loop_core/human_review_packet.py | 瘦身壳（1307 → 643，re-export + Packet/Builder 主流程） | 643 |
| loop_core/context_loader.py | 瘦身壳（1432 → 839，re-export + Loader/Compressor 主流程） | 839 |
| tests/t0110_b2_golden.py | 新增（golden 语料共享助手，非测试收集） | 1209 |
| tests/test_t0110_batch_b2.py | 新增（验收测试 20 条） | 404 |
| .ai/evidence/T-0110/golden/generate_golden_b2.py | 新增（golden 生成器） | 62 |
| .ai/evidence/T-0110/golden/golden-b2-before.json | 新增（拆分前基线快照） | 66,082 B |
| .ai/evidence/T-0110/golden/golden-b2-after.json | 新增（拆分后重放快照） | 66,082 B |

## 三、golden 等价证据（硬门槛 1）

**对比方法**：同一确定性捕获器（tests/t0110_b2_golden.py，复用 B-1 的
to_jsonable/norm_paths/try_exc + 本批新增 _mark_timestamps/_mark_packet_ids
归一化）在拆分前后各运行一次，产物为 sort_keys JSON 文本；`sha256` 逐字节对比。

- 捕获范围（human_review_packet）：常量/枚举/异常 mro、模型默认值、序列化往返
  6 例 + 失败路径 9 例（schema/schema_version/snapshot/decision_point 校验、
  坏 JSON）、build_resume_payload 成功（含 task 文件/evidence 目录指针）+ 11 例
  fail-closed（缺 state/task_graph、不可解析、非 mapping、task/gate/phase 漂移、
  任务/门缺失、门绑定错）、恢复字段辅助 8 例、resume_from_payload 成功（对象与
  dict 双形态）+ 9 例 drift（state 三字段漂移、任务/门移除、已裁决、重绑定、
  无效 payload、缺 snapshot）、to_markdown/to_plain_text 全文（全节/最小/否决包）、
  _phase_label 14 例（含 None 异常路径）、_format_ts 7 例、builder 三路
  （phase 满配/空配置/pass 字符串变体、veto 双记录/空/裸字符串）、
  translate_technical_risk 5 例、_extract_key_choices 4 例。
- 捕获范围（context_loader）：常量/枚举/正则 9 条 pattern/kwdefaults、
  _level_line_params/_level_body_cap 边界、_select_body_lines 5 例、
  _find_citation_tokens/_truncate_citation/_split_sentences/_truncate_line、
  extract_key_fields 3 例、_format_key_fields 3 例、summarize_text 5 例
  （L1-L3/空/引用）、estimate_tokens 5 例、CitationResolver 9 例（精确/前缀丢失/
  截断/裸名/歧义/不存在/空/无后缀/is_resolved）+ 自定义 search_roots、
  repair_truncated_references 3 例（含 T-0095 子串守卫、UNRESOLVED 包裹）、
  ContextCompressor 8 例（不触发/多级/参数覆盖/3 类非法参数/引用修复）、
  _validate_budget_params 6 例、_complexity_to_level 9 边界、
  load_role_context 3 级 + 3 失败、预算压缩路径、D3 记忆注入 6 例
  （默认=显式 False、开启注入 3 条、limit=2、task 过滤、损坏存储默认关闭
  不报错/开启 fail-closed）、文档索引 3 例 + 3 失败、load_for_role 3 例
  （路由表/遗留启发/预算压缩）、_parse_yaml/_extract_fixed_stance/
  _extract_contract_extras/_extract_framework_titles、_select_relevant_sections
  7 例（路由匹配/默认/无关键词/遗留/首 3/空索引/缺路由表回退）、
  _parse_front_matter_yaml 5 例、_load_section_routing 5 例（含缓存二次命中）。
- 两模块 dir() 全量快照（43 + 67 名）同步入基线。

**结果**：
```
golden-b2-before.json sha256 = c372a466f9967c804b0a77312579807031fa35c14cd1d4175b40b3752b017431
golden-b2-after.json  sha256 = c372a466f9967c804b0a77312579807031fa35c14cd1d4175b40b3752b017431
byte-identical: True（66,082 bytes）
```
（golden-after 在拆分后、lint 修复后各跑一次，两次均 byte-identical。基线中
仅 3 个 `datetime.now()` 非确定性字段按最终捕获器同一规则归一化为 `<TS>`。）

## 四、re-export 完整性断言（硬门槛 2）

- `sorted(dir(壳)) == 拆分前 dir 基线`（human_review_packet 43 名 / context_loader
  67 名，含私有名——覆盖 test_t0108_fixes.py 的 `_ROUTING_CACHE`/`_load_section_routing`/
  `_select_relevant_sections`、test_context_loader.py 的 `_complexity_to_level`、
  test_ai_doc_links.py 的 `_load_section_routing` 等直接私有导入路径）；
- `from loop_core.human_review_packet import *` / `from loop_core.context_loader
  import *` 可执行且公开名集合与 dir() 非下划线名一致；
- 对象同一性 30 项：壳绑定即新模块定义对象（`hrp.ResumePayload is rm.ResumePayload`、
  `hrp.build_resume_payload is rp.build_resume_payload`、`hrp._phase_label is
  rr._phase_label`、`cl._TASK_ID_RE is lf._TASK_ID_RE`、`cl.CitationResolver is
  cr.CitationResolver`、`cl.summarize_text is ls.summarize_text`、
  `cl._select_relevant_sections is lsec._select_relevant_sections`、
  `cl._ROUTING_CACHE is lsec._ROUTING_CACHE`（同一 dict——test_t0108_fixes 的
  `.clear()` 语义保持）等）；
- 壳 import 面逐名保留：`re`/`Any`/`Enum`/`Path` 等以 `# noqa: F401` 保留绑定
  （命名空间保持；context_loader 的 `__annotations__` 模块属性由
  `DEFAULT_BUDGET_TOKENS: int = 2600` 注解赋值保持存在）；pyproject.toml
  per-file-ignores 登记两壳 F401（与批 B-1 同模式）。

## 五、测试结果

- 新增验收 tests/test_t0110_batch_b2.py：**20 passed**（golden 逐字节等价 ×2、
  re-export 面 ×2、对象同一性 ×2、star import ×1、循环导入静态防线 ×7（叶子零
  反向引用壳 ×7 + DAG 顺序 ×1）、include_memories 默认 False ×2（kwdefaults +
  默认关闭不读知识库/损坏存储 fail-closed）、内嵌抽查 ×2、路由缓存 clear 语义 ×1）。
- 直接相关套件（test_human_review_packet / test_resume_payload / test_context_loader /
  test_context_compression / test_t0108_fixes / test_gate_feedback /
  test_veto_escalation / test_knowledge_memory / test_memory_injection /
  test_ai_doc_links / test_loop_core_coverage / test_t0110_batch_b1 /
  test_t0110_batch_b2）→ **441 passed**。
- 消费方套件（roles 族 ×6 / test_t0104_templates / test_t0105_batch2 /
  test_t0107_fixes / test_t0109_f2_write_convergence / test_context_controller /
  test_t0110_batch_a）→ **747 passed, 60 skipped**。
- 全量回归 tests/：**4126 passed + 64 skipped + 12 xfailed + 1 deselected**
  （deselect 为批 B-1 已登记环境依赖项 test_deployment_quality_checker::…）。
  2 项失败均为**工作树状态型测试、与拆分无关**（见 §六 遗留事项）：
  - test_manifest_t0095::test_manifest_exists_and_handoff_reference_is_real
    —— `.ai/HANDOFF.md`（本批前已 M）引用 `.ai/evidence/T-0110/evidence-manifest.v1.yaml`，
    该 manifest 在 T-0110 closeout 时生成；
  - test_t0109_f5_tool_capability::test_hooks_only_whitelist_file_changed
    —— 断言 `git diff HEAD -- hooks/ == [loop_enforcement.py]`，当前为零改动
    （T-0110 hooks 零触碰约束下必然为空，断言为 T-0109 时代的陈旧期望）。
- 编译：`python -m compileall` 触及文件 PASS；**loop_core 全部 74 个模块导入
  零循环导入/零错误**。
- lint：`ruff check` 12 个触及文件 All checks passed（新文件零违规；两壳按
  per-file-ignores 豁免 F401；顺带修复原文件遗留 UP045/F541/E702——均为
  `from __future__ import annotations` 下运行时零差异的注解/字面量风格问题，
  golden 重跑仍 byte-identical）。
- 消费方端到端冒烟：真实仓库 `ContextLoader(root).load_for_role('quality-engineer',
  .ai/README.md)` rc=0（路由表驱动 7 节，full 级）；`HumanReviewPacketBuilder.
  from_phase_completion` 生成 2109 字节 markdown rc=0。

## 六、约束自查（任务卡硬约束）

| 约束 | 自查 |
|---|---|
| hooks/ 零改动 | ✅ 本批未触碰 hooks/ 任何文件 |
| 治理内核判定零触碰 | ✅ 未触碰；golden 判定语义逐字节一致 |
| 不改变任何行为 | ✅ golden 逐字节等价（sha256 相同）；include_memories 默认 False、memory 注入路径、T-0108 路由表逻辑全保持；lint 修复为运行时零差异 |
| 零删除 | ✅ 全部公开+私有符号 re-export；无任何符号消失 |
| 写路径仅限 loop_core/ + tests/ + .ai/evidence/T-0110/ + pyproject.toml | ✅ 新增 7 模块 + 2 测试文件 + golden 3 文件 + 2 壳重写；pyproject.toml 仅 per-file-ignores 加两行 |
| 版本文件不改 | ✅ 未触碰 |
| T-0104 include_memories 默认 False | ✅ kwdefaults 断言 + 默认关闭不读知识库 golden/测试双覆盖 |

## 七、遗留事项（批 B-3/B-4/C 依赖）

1. 批 B-3/B-4（设计文档 1.1 拆分表称 batch-b3-review / batch-b4-loader 目录名，
   本批实际合并 review+loader 为 B-2）如需再拆，沿用本批壳+re-export 模式与
   per-file-ignores 登记。
2. 全量回归 2 项工作树状态型失败（evidence-manifest 引用先于生成、hooks-diff
   陈旧期望）非本批引入（前者由 T-0110 会话的 HANDOFF.md 先行修改导致，manifest
   将在 closeout 生成；后者源于 hooks 零触碰约束）——留给主会话登记/处置。
3. 批 C（hooks/scripts/loop_enforcement.py 2059 行）拆分时，本批的 loader_sections
   路由表/缓存模式与 T-0108 接入可作参考；自愈路径实测另行记录。
