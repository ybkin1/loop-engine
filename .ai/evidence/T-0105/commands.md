# T-0105 批 1 + 批 2 + 批 3 + 批 4 执行命令记录（commands.md）

> 执行者：developer 子代理（批 1 文档漂移 + 批 2 T-0104 P3 四项）+ designer+developer 子代理（批 3 Q2/Q4）+ developer 子代理（批 4 安装副本同步 + eval 最小实验）
> 日期：2026-08-03

## 批 1：文档漂移修复

| # | 路径 | 改动点 | 状态 |
|---|------|--------|------|
| A-1 | `.ai/evidence/observability/finding-idle-semantics.md` | 状态 `OPEN（待用户裁决是否立项 T-0101）` → `CLOSED`；追加关闭记录行：T-0101 已完成 idle 语义修复（NO_ACTIVE_TASK exit 3 分流 + 消费端对齐，v3.12.40）；其余内容保留 | DONE |
| A-1 | `.ai/evidence/observability/finding-handoff-none-placeholder.md` | 状态 `OPEN（待用户裁决是否立项修复）` → `CLOSED`；追加关闭记录行：T-0102 已完成 handoff 生成器 idle 占位缺陷修复（.ai/evidence/none/ 悬挂引用消除，v3.12.41）；其余内容保留 | DONE |
| A-2 | `.ai/KNOWN_ISSUES.md` | Open 区移除 2 项过时项并移入 Recently Closed：① Bash command interception（注明 T-0060 已实现 `bash_content_guard`）；② ProjectContinuity 自引用 timing issue（注明 T-0049 已拆 continuity 自引用/炸弹）；保留 seeded defects 手动、E2E lab fixture 2 项 | DONE |
| A-3 | `.ai/HANDOFF-NEXT.md` → `.ai/evidence/S6/handoff-next-archived-2026-07-23.md` | 全库 grep 确认无活动引用（无 .py 代码引用；HANDOFF.md/CONTRACTS.md/docs/skills/agents 均无引用；仅历史任务卡/证据/生成式 manifest 记录）→ 归档移动（非删除）；同步处置：`.ai/project_continuity.yaml` source_manifest 移除该条目并重算 source_sha256（semantic_sha256 不变），随后 `repair_continuity.py` + `close_session.py` 重生成 HANDOFF.md 使连续性契约恢复干净 | DONE |
| A-4 | `.ai/tasks/T-0102.md`、`.ai/tasks/T-0104.md` | `## Status` 段 `in_progress` → `completed`（与 task_graph 一致）；T-0103 本就 completed 未动；表格区其他内容未动 | DONE |

**批 1 验证**：`validate_state.py` 前后对比 —— 前：`[warn] [legacy] Historical task status mismatch: T-0102 / T-0104` ×2；后：0 warn、`[ok] state is usable`、exit 0（见 `fixes/batch1-doc.md`）。

## 批 2：T-0104 P3 四项修复（代码 + 测试）

| # | 路径 | 改动点 | 状态 |
|---|------|--------|------|
| B-4-1 | `loop_core/context_packager.py` | `build_context` 新增 `memory_gate_id`/`memory_tag` 关键字参数；记忆召回 `recall(root, limit=memory_limit)` → 透传 `task_id=task_id or None, gate_id=memory_gate_id, tag=memory_tag`（None = 不过滤，与 context_loader 语义一致；无过滤时行为与 T-0104 现状完全一致） | DONE |
| B-4-1 | `loop_core/role_orchestrator.py` | `build_dispatch_manifest` 派发 S4+ 时 task_id 已透传至 prompt 构建链（既有管道），增加注释明确 task_id 同时作为记忆召回过滤；补测试断言 task_id 透传 | DONE |
| B-4-2 | `loop_core/role_orchestrator.py` | `_load_memory_injection_config` 增加校验：新增 `_validated_phases`（phases 必须为 list，误写为字符串 → 整体回退 disabled 默认）与 `_validated_memory_limit`（非正数/非数字/bool → 默认 5；正浮点 int() 截断沿用现状）；非法配置走 fail-closed 回退 | DONE |
| B-4-3 | `.ai/CONTRACTS.md` | 新增 `## Completion Flow Conventions` 节：主会话收尾顺序固定为 先创建/重生成 evidence-manifest（create-only）→ 再更新 HANDOFF 引用 → 最后跑 `test_manifest_t0095`（选 CONTRACTS.md 而非 skills/ 副本，避免安装副本同步面） | DONE |
| B-4-4 | `loop_core/role_orchestrator.py` | `_load_memory_injection_config` 增加模块级进程内缓存 `_CONFIG_CACHE: path -> (mtime_ns, cfg)`；mtime 变化才重读；读取/解析失败清缓存并回退 fail-closed；两候选路径（repo 源 / 安装副本）均缓存 | DONE |
| 测试 | `tests/test_t0105_batch2.py`（新建） | B-4-1×7 / B-4-2×9 / B-4-4×5 / B-4-3×1 = 21 个测试全部通过 | DONE |

**批 2 验证**：新增 21 passed；相关既有测试 `test_memory_injection.py + test_knowledge_memory.py + test_context_loader.py + test_context_compression.py` = 153 passed 无回归；全量回归见 `fixes/batch2-p3.md`。

## 约束自查

| 检查项 | 结果 |
|--------|------|
| `git diff --stat -- hooks/` | 空（零改动） |
| `git diff --stat -- loop_core/context_loader.py` | 空（默认值不动） |
| loop_core 改动文件 | 仅 context_packager.py、role_orchestrator.py（T-0104 P3 指定的两个落地文件） |
| fail-closed 语义 | 配置缺失/损坏/非法 → 回退 disabled 默认；空召回 no-op；store 损坏抛异常（未变） |
| validate_state | 0 legacy warn、无连续性漂移、exit 0 |

## 批 3：Q2 教学式多轮提问（B-1/P2-1）+ Q4 低成本原型机制（B-2/P2-2）

| # | 路径 | 改动点 | 状态 |
|---|------|--------|------|
| A-1 | `loop_core/inbox.py` | `Requirement.clarification_rounds` 字段（to_dict/from_dict 缺省 0，向后兼容）；新增 `ask_clarification()` 追加问题轮次（问题跨轮累积、rounds 计数、NEW→CLARIFYING、空问题 raise InboxError 保持 fail-closed）；`add_clarification_questions()`（替换语义）rounds 置 ≥1 | DONE |
| A-2 | `tools/tool_inbox.py` | 新增 `inbox_ask_clarification` MCP handler（rid 必填、questions 非空 list 校验） | DONE |
| A-3 | `agents/product-manager/SKILL.md` | 新增"## 14. 缺口识别 + 教学式提问（Q2）"节：提问前三栏清单（用户已知/缺什么/缺口如何影响结果）、每轮≤3 个、问题附"为什么问"、多轮闭环（ask_clarification 追加）、缺口未清空 verdict=BLOCKED；工作流程步骤 1 引用第 14 节 | DONE |
| A-4 | `agents/main-thread/CONTRACT.yaml` | R11 语义微调（T-0105 授权，非 hook/内核）："同一阶段内向用户提问不超过 3 次" → "同一轮提问不超过 3 个、可多轮（轮次不限，但每轮必须围绕已识别缺口、问题附'为什么问'）；非关键决策自行处理并标注"——保留 R11 编号与主体语义，仅放开轮次限制 | DONE |
| A-5 | `agents/main-thread/SKILL.md` + `skills/loop-governance/templates/task-card.md` | R11 引用同步更新（原"多轮属后续 P2-1 设计"/原"同阶段提问≤3 次"引用） | DONE |
| B-1 | `loop_core/planner.py` | `TaskType`/`PrototypeForm` 枚举（html_mock/cli_demo/data_sample）；`TaskDraft.task_type`/`prototype_form` 字段（序列化缺省兼容，旧 plan 默认 standard）；`generate_prototype()` 生成单任务原型 plan draft（S3-interface、LOW 复杂度、AC 含低成本/可迭代/不追求完整/选择后反馈） | DONE |
| B-2 | `tools/tool_planner.py` | 新增 `planner_generate_prototype` MCP handler | DONE |
| B-3 | `skills/loop-governance/templates/gate-request.md` | 决策记录后新增"## 选择后反馈（方案修正循环）"节：所选方案/选择理由（用户原话）/AI 据此调整/调整结果确认；规则：理由不代编、循环默认一轮、不满意重新发起 Gate | DONE |
| B-4 | `skills/loop-governance/templates/task-card.md` | 新增"## 原型交付（Q4，可选）"节（三种形态表 + 原型三原则）；P2-2 引用更新为已落地 | DONE |
| B-5 | `skills/loop-governance/chain.yaml` | **零改动**（裁决：最小落地；prototype 节点候选设计留档 `design/q4-prototype-design.md` §2.4） | DONE |
| B-6 | `.ai/evidence/T-0105/design/q4-prototype-design.md` | Q4 设计文档（目标/方案/影响面/裁决理由/回退） | DONE |
| 测试 | `tests/test_t0105_batch3.py`（新建，24 个）+ `tests/test_t0104_templates.py`（R11 断言更新） | 批 3 测试 24 passed；test_t0104_templates 11 passed；test_inbox + test_planner 22 passed 无回归 | DONE |

**批 3 裁决摘要**：Q4 采**最小落地**——chain.yaml prototype 节点不做。理由：消费方
（scripts/evidence_chain.py、tools/tool_evidence_chain.py）优先读 `.zcode` 安装副本
（本批写范围不含），只改仓库副本会双副本漂移且线上验证读旧配置；verifier 用
`Path.exists()` 不支持 glob，required+glob 会在 strict 模式恒误报 BLOCKED；且无任何
hook/gate 以 strict 调用证据链验证（节点无门禁消费方）。

**批 3 验证**：新增 24 passed；相关既有 33 passed 无回归；宽回归 557 passed / 45 skipped，
唯一失败 `test_manifest_t0095.py::test_manifest_exists_and_handoff_reference_is_real`
为**既有问题**（HANDOFF 引用 T-0105 evidence-manifest，随任务完成时创建；git stash
验证本批改动前同样失败，与本批无关）；`validate_state.py .` → `[ok] state is usable`
0 warn/error exit 0。详见 `fixes/batch3-q2q4.md`。

## 批 3 约束自查

| 检查项 | 结果 |
|--------|------|
| `git diff --stat -- hooks/` | 空（零改动） |
| 治理内核（gate_guard/enforcement/hard_constraints/guard_health/state_machine/validate_state/context_loader） | 空（零触碰） |
| `.zcode/` 安装副本 | 零改动（chain.yaml 双副本无漂移） |
| R11 微调 | 仅语义文本（每轮≤3、可多轮），编号与主体语义保留 |
| 本批写出的目录 | 仅 .ai/、skills/loop-governance/、agents/、loop_core/、tools/、tests/ |
| fail-closed | 未触碰；inbox/planner 异常路径仍抛异常返回 BLOCKED |
| validate_state | 0 warn/error、exit 0 |

## 批 4：C-1 安装副本同步 + B-3 eval 最小实验 + C-2 AiDecisionLedger 真实路径

| # | 路径 | 改动点 | 状态 |
|---|------|--------|------|
| C-1 | `.zcode/skills/loop-governance/config.yaml` | **合并同步**：源最新内容（新增 `memory_injection` 节，T-0104 设计-5）同步到安装副本；**合并保留**安装副本专有节（`quality_gates.compile_threshold: 0`、python 模板 `compile_command`、`runtime_delivery`——消费方 run_quality_gates/runtime_delivery_gate 只读安装副本）。同步后 YAML 解析通过、role_orchestrator 加载 memory_injection 正常、slo_gate 加载安装副本配置正常 | DONE |
| C-1 | `skills/loop-governance/templates/`、`SKILL.md`、`references/`、`examples/` | **安装副本保持精简（不复制）**：唯一代码消费方 template_injector 读源目录；安装副本 2 个遗留模板（gate-decision-summary/phase-acceptance-summary）保留不动；D-03 §1.3.3 已记录同决策 | DONE（裁决） |
| B-3 | `.ai/evidence/T-0103/evals/blindspot-experiment/`（新建） | D-04 最小实验**降级路径**（规则式模拟/构造性评估，零 LLM 外部调用）：fixtures 5 份 JSON（任务卡+种子盲点）、prompts/blindspot-injection-v1.md（唯一变量固化件）、outputs/ 10 份实验产出 + 2 校准样例、cases/cases-blindspot.yaml 96 case、eval-report.json、scores.csv、gen_cases.py + run_experiment.py（可复跑） | DONE |
| B-3 | eval 评分 | EvalRunner 全链路真实运行（EvalCase/EvalRunner/EvalReport/CLI 复跑一致）；校准通过；4/4 维度信号（D1 3.8 vs 0、D2 100% vs 0%、D3 漏检 1.2 vs 5.0、D4 全在 [1,3]），无副作用 → 成功信号（模拟层级，结论"有条件支持"） | DONE |
| C-2 | `.ai/ledger/ai-decisions.jsonl` | 走 AiDecisionLedger 自身 API（`AiDecisionRecord.create()` + `append()`，chain_hash 链式）真实追加 1 条决策（AD-7ce9f67bca96，T-0105/S6-delivery）；`verify_chain()` = True（1 entries）；ledger_guard 子进程校验 exit 0（append + 链连续） | DONE |
| 连续性 | `.ai/project_continuity.yaml`、`.ai/HANDOFF.md` | 父会话 task_graph.yaml 编辑（新增 T-0105/T-0106）导致 2 项 hash 漂移——走官方 `repair_continuity.py`（Fixed 2 hashes）+ `close_session.py` 重生成 HANDOFF，漂移清零 | DONE |
| 报告 | `.ai/evidence/T-0105/fixes/batch4-sync-eval.md`、`.ai/evidence/T-0105/design/eval-experiment-report.md`、`.ai/evidence/T-0105/fixes/verify_ai_decision_ledger_path.py` | 同步差异清单与决策 + 实验报告 + ledger 验证脚本 | DONE |

**批 4 验证**：相关测试 116 passed 无回归（batch2/memory_injection/t0104_templates/evals/ai_decision_ledger/ledger_guard）；全量回归见下节；validate_state：0 warn、0 连续性漂移，唯一 error 为**父会话创建的 pending gate G-T-0106-REQUIREMENTS**（T-0106 任务门，非本批产生、AI 不得代批，需用户决策后恢复 exit 0）。

## 批 4 约束自查

| 检查项 | 结果 |
|--------|------|
| `git diff --stat -- hooks/` | 空（零改动） |
| 治理内核 | 零触碰（仅运行官方 repair_continuity/close_session 重算 hash） |
| `.zcode/tools/`、`.zcode/config.json` | 零改动（仅运行 validate_state/repair/close_session） |
| `.zcode/skills/loop-governance/` | 仅 config.yaml 合并同步（T-0105 授权） |
| LLM 外部调用 | 零（eval 用规则式/构造性路径） |
| AiDecisionLedger | 走自身 API append + chain_hash，未手写文件 |
| fail-closed | 不变；gate 语义未触碰（G-T-0106 pending 未代批） |
| validate_state | 0 warn / 0 漂移；pending gate G-T-0106-REQUIREMENTS 待用户决策 |
