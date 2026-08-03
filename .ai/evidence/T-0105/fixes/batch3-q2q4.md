# T-0105 批 3 — Q2 教学式多轮提问（B-1）+ Q4 低成本原型机制（B-2）落地记录

> 执行者：designer+developer 子代理（T-0105 批 3）
> 日期：2026-08-03
> 设计依据：`T-0103/design/D-02-gap-analysis.md` 表 1 Q2/Q4 行、表 3 P2-1/P2-2

## 一、Q2 教学式多轮提问（B-1，P2-1）— 设计决策 + 落地

### 设计决策

1. **多轮澄清机制**：inbox 增加 `ask_clarification` 追加语义（对已有 CLARIFYING
   条目追加问题轮次，问题在扁平 `clarification_questions` 数组中按轮累积），
   新增 `clarification_rounds` 计数；旧 `add_clarification_questions`（整体替换）
   保留不动 → 字段与行为双向后兼容。
2. **教学式提问提示词**：product-manager SKILL 新增第 14 节"缺口识别 + 教学式提问
   （Q2）"——提问前先列三栏清单（用户已知/缺什么/缺口如何影响结果），提问时
   每轮≤3 个、每个问题附"为什么问"、可多轮闭环（ask_clarification 追加），
   缺口未清空 verdict=BLOCKED。
3. **R11 语义微调**（治理约定调整，T-0105 已授权，非 hook/内核）：
   `agents/main-thread/CONTRACT.yaml` L27 R11 由"同一阶段内向用户提问不超过 3 次"
   改为"**同一轮提问不超过 3 个、可多轮**（轮次不限，但每轮必须围绕已识别缺口、
   问题附'为什么问'）；非关键决策自行处理并标注"——保留 R11 编号与主体语义，
   仅放开轮次限制。同步更新两处引用：main-thread SKILL.md 2.3 节（原"多轮属后续
   P2-1 设计"）、task-card.md 盲点清单规则 3（原"同阶段提问≤3 次"引用）。

### 落地清单

| # | 文件 | 改动 |
|---|------|------|
| A-1 | `loop_core/inbox.py` | `Requirement.clarification_rounds` 字段（to_dict/from_dict，缺省 0 向后兼容）；新增 `ask_clarification()` 追加轮次方法（空问题 raise InboxError，fail-closed）；`add_clarification_questions()` rounds 置 ≥1 |
| A-2 | `tools/tool_inbox.py` | 新增 `inbox_ask_clarification` MCP handler（参数校验：rid 必填、questions 非空 list） |
| A-3 | `agents/product-manager/SKILL.md` | 新增"## 14. 缺口识别 + 教学式提问（Q2）"节（三栏清单/每轮≤3/为什么问/多轮闭环）；工作流程步骤 1 引用第 14 节 |
| A-4 | `agents/main-thread/CONTRACT.yaml` | R11 语义微调（见上，仅文本） |
| A-5 | `agents/main-thread/SKILL.md` | 2.3 节 R11 引用更新为"每轮 ≤3 个、可多轮（P2-1 已落地）" |
| A-6 | `skills/loop-governance/templates/task-card.md` | 盲点清单规则 3 的 R11 引用更新 |
| A-7 | `tests/test_t0104_templates.py` | R11 断言更新：R10 原文零改动 + R11 新语义 + 旧硬上限措辞消失 |

## 二、Q4 低成本原型机制（B-2，P2-2）— 设计裁决 + 落地

### 裁决：最小落地（chain.yaml prototype 节点留档为候选）

影响面评估（读 chain.yaml 及全部消费方后）：
- 消费方仅两处：`scripts/evidence_chain.py` verify_chain 与
  `tools/tool_evidence_chain.py` `_basic_verify`；两者**优先读 `.zcode` 安装副本**
  （本批写范围不含 `.zcode/`，只改仓库副本 → 双副本漂移且线上验证读旧配置）；
- verifier 用 `Path.exists()` 判文件，**不支持 glob**——`human_review` 节点即以
  `required: false` 规避；prototype 若 required:true + glob 路径会在 strict 模式
  恒误报 BLOCKED；
- 无任何 hook/gate 以 strict 模式调用证据链验证（prototype 节点无门禁消费方，加=死配置）。

→ 结论：只落地模板 + 提示词层（planner 原型类型 + 任务卡说明 + gate-request
反馈字段）；chain.yaml prototype 节点完整设计与启用前置条件写入设计文档
`design/q4-prototype-design.md`（§2.4 候选节点 YAML + 3 条启用前置），供后续批次。

### 落地清单

| # | 文件 | 改动 |
|---|------|------|
| B-1 | `loop_core/planner.py` | `TaskType`（standard/prototype）、`PrototypeForm`（html_mock/cli_demo/data_sample）枚举；`TaskDraft.task_type`/`prototype_form` 字段（to_dict/from_dict 缺省兼容，旧 plan 默认 standard）；`generate_prototype()` 单任务 plan draft（S3-interface、LOW 复杂度、AC 含"低成本/可迭代/不追求完整/选择后反馈"） |
| B-2 | `tools/tool_planner.py` | 新增 `planner_generate_prototype` MCP handler |
| B-3 | `skills/loop-governance/templates/gate-request.md` | 决策记录后新增"## 选择后反馈（方案修正循环）"节：所选方案/选择理由（用户原话）/AI 据此调整/调整结果确认；规则：不代编理由、循环默认一轮、不满意重新发起 Gate |
| B-4 | `skills/loop-governance/templates/task-card.md` | 新增"## 原型交付（Q4，可选）"节（三种形态表 + 原型三原则）；相关经验规则 2 的 P2-2 引用更新为"已落地" |
| B-5 | `skills/loop-governance/chain.yaml` | **零改动**（候选设计见 `design/q4-prototype-design.md` §2.4） |
| B-6 | `.ai/evidence/T-0105/design/q4-prototype-design.md` | Q4 设计文档（目标/方案/影响面/裁决理由/回退/候选节点） |

## 三、测试结果

| 套件 | 结果 |
|------|------|
| `tests/test_t0105_batch3.py`（新建，24 个：Q2 inbox 多轮×9、Q2 提示词层×2、Q4 planner×10（含三种形态 parametrize）、Q4 模板层×3） | 全部通过 |
| `tests/test_t0104_templates.py`（R11 断言更新） | 11 passed |
| `tests/test_inbox.py` + `tests/test_planner.py`（既有，回归） | 22 passed |
| 宽回归（loop_core/tool_executor/operations/dashboard/governance_consistency/contract_*/roles/manifest） | 557 passed, 45 skipped, **1 失败为既有问题**：`test_manifest_t0095.py::TestT0095EvidenceManifest::test_manifest_exists_and_handoff_reference_is_real` —— HANDOFF 引用 `.ai/evidence/T-0105/evidence-manifest.v1.yaml`，该文件随 T-0105 任务完成时创建（任务进行中）；已用 `git stash` 验证**本批改动前同样失败**，与本批无关 |
| `validate_state.py .` | `[ok] state is usable`，0 warn/error，exit 0 |

## 四、约束自查

| 检查项 | 结果 |
|--------|------|
| `git diff --stat -- hooks/` | 空（零改动） |
| 治理内核（gate_guard/enforcement/hard_constraints/guard_health/state_machine/validate_state/context_loader） | 空（零触碰） |
| `.zcode/`（安装副本） | 零改动（chain.yaml 双副本无漂移） |
| R11 微调 | 仅语义文本（每轮≤3、可多轮），R11 编号保留、"非关键决策自行处理并标注"主体语义保留，未动其他约束 |
| fail-closed | 未触碰：inbox/planner 异常路径仍抛异常；空问题/非法原型形态 → 报错不通过 |
| 本批写出的目录 | 仅 .ai/、skills/loop-governance/、agents/、loop_core/、tools/、tests/ |

## 五、回退

- Q2：删 `ask_clarification` 与 `clarification_rounds`（to_dict/from_dict 缺省
  逻辑使旧数据零影响）；R11 文本改回原文（同步 test_t0104_templates 断言）。
- Q4：删 `generate_prototype` + 两个模板节；planner 新字段有默认值，旧数据零影响。
- chain.yaml 未动 → 无证据链回退面。
