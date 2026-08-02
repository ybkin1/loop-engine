# T-0104 执行命令记录（developer 子代理）

> 任务：T-0104（gate G-T-0104-REQUIREMENTS 已批准）—— 落地 D-03 全部 5 项设计。
> 设计依据：`.ai/evidence/T-0103/design/D-03-integrated-design.md`
> 执行人：developer 子代理（ZCode）
> 执行日期：2026-08-02
> 约束：hooks/ 零改动；loop_core 治理内核（gate_guard/enforcement/hard_constraints/
> guard_health/state_machine/context_loader 默认参数）零改动；R10/R11 原文零改动；
> fail-closed 语义不变；不部署/不发布/不安装；版本文件不改（bump 由主会话执行）。

## 批 1（纯文档，设计-1/2/4）—— 完成

| 路径 | 改动点 | 设计编号 | 完成 |
|---|---|---|---|
| `skills/loop-governance/templates/task-card.md` | 新增 3 个必填节：①"信息完整度声明 + 象限判定"（"基本信息"之后，候选文本 D-03 §2.3.1）②"相关经验与不熟悉处"（"用户可见目标"之后，D-03 §5.3.1）③"盲点清单（必填，≥3 条）"（"范围与边界"与"验收标准"之间，D-03 §1.3.1）。节顺序：基本信息 → 信息完整度 → 用户可见目标 → 相关经验 → 范围与边界 → 盲点清单 → 验收标准 | 1、2、5 | 是 |
| `skills/loop-governance/SKILL.md` | 启动检查清单第 6 步后新增第 7 步"盲点简报（开工前，Q3）"（候选文本 D-03 §1.3.2） | 1 | 是 |
| `skills/loop-governance/templates/human-review-packet.md` | "六、下一步"之前新增"六、理解确认（用户答对才算验收）"节（候选文本 D-03 §4.3.1）；原"六、下一步"顺延为"七、下一步" | 4 | 是 |
| `agents/main-thread/SKILL.md` | ①§2.2 后新增 §2.3"象限判定 → 行为选择（开工前必做）"（D-03 §2.3.2）②§5.2 Gate 呈现包强制附"本阶段偏离摘要"小节（D-03 §3.3.3 模板文本）③§5.3 自检规则新增第 7 条（needs_user_review 条数 = 偏离摘要"替您做的决定"条数，不匹配 = 打回）④§4 开发工程师检查表加"deviations 数组格式合规"；主控自检表加"任务卡盲点清单 ≥3 条"与"Human Review Packet 含理解确认节" | 1、2、3、4 | 是 |
| `agents/main-thread/CONTRACT.yaml` | fixed_stance 末尾新增 1 句"象限判定先行"（D-03 §2.3.3 可选）；R10/R11 原文零改动（git diff 实证仅 +1 行） | 2 | 是 |
| `skills/loop-governance/references/governance-lifecycle.md` | PASS 分层说明补充：`USER_ACCEPTED` 前须完成 Human Review Packet"理解确认"节（user_comprehension_confirmed），拒绝回答则降级标记（D-03 §4.3.4 可选） | 4 | 是 |
| `USER-PROMPTS.md` | 新增"关于'AI 会先声明信息完整度再决定是否提问'"说明节（D-03 §2.3.3 可选） | 2 | 是 |

批 1 小计：7 个文件，全部完成。

## 批 2（记录层，设计-3）—— 完成

| 路径 | 改动点 | 设计编号 | 完成 |
|---|---|---|---|
| `agents/developer/SKILL.md` | §5.1 产出 JSON Schema 在 `known_deviations` 后新增可选数组 `deviations`（候选文本 D-03 §3.3.2，缺省 `[]`）；`known_deviations/unimplemented/clarification_requests` 原样保留；并附字段规则说明（reason 必填；ai_decisions 每条须含 why_not_ask + impact_if_wrong；needs_user_review:true 须进 gate 呈现；决策写入 ai-decisions.jsonl） | 3 | 是 |
| `loop_core/approval_ledger.py` | 新增 `AiDecisionRecord` dataclass（候选代码 D-03 §3.3.4，字段含 decision_id/task_id/phase/role_id/decision/why_not_ask/impact_if_wrong/reason_ref/recorded_at，无 human_actor 语义）+ `AiDecisionLedger`（append/read/verify_chain/find_by_task，链契约照抄 execution_ledger：chain_hash = SHA256(prev_hash \|\| row)，root seed 与 ExecutionLedger/ledger_guard 相同；复用 _sha256/_short_uuid/_utc_now_iso） | 3 | 是 |
| `loop_core/approval_ledger.py` | `ApprovalRecord` 新增可选字段 `user_comprehension_confirmed: bool \| None = None`；`create()` 增参；`record_approval` 仅在非 None 时写入该键；`get_approval` 用 `.get()` 读取（存量记录无此键 → None） | 4 | 是 |
| `.ai/ledger/ai-decisions.jsonl` | 新建链式 JSONL 数据文件（空链起步 = 空链合法；ledger_guard 追加+链校验自动覆盖，零 hook 改动，已干跑验证 exit 0） | 3 | 是 |

批 2 小计：3 个文件（approval_ledger.py 含两项改动）+ 1 个新数据文件，全部完成。

## 批 3（开关+调用点，设计-5）—— 完成

| 路径 | 改动点 | 设计编号 | 完成 |
|---|---|---|---|
| `skills/loop-governance/config.yaml` | 新增 `memory_injection: {enabled: true, phases: ["S4","S5","S6","S8","S9","S10"], memory_limit: 5}` 配置节（非 hook 配置，附注释说明回退语义） | 5 | 是 |
| `loop_core/role_orchestrator.py` | 新增 `_load_memory_injection_config`（读取 skills/loop-governance/config.yaml，其次 .zcode 安装副本；缺失/损坏 → disabled fail-closed）与 `_memory_injection_for`（阶段前缀匹配，如 "S4-implementation" ↔ "S4"）；`build_dispatch_manifest` 对 config phases 内的阶段显式传 `include_memories=True, memory_limit=N`；enabled=false 时传 False，行为与现状完全一致 | 5 | 是 |
| `loop_core/context_packager.py` | `build_context` 新增关键字参数 `include_memories=False, memory_limit=5`（默认 False 零行为变化）；开启时经 memory_service.recall + memories_to_context 追加"相关经验（Related Memories）"节（渲染格式与 context_loader 一致；空召回 no-op；store 损坏 fail-closed 抛 KnowledgeStoreError） | 5 | 是 |
| `loop_core/role_loader.py` | 参数转发管道（plumbing）：`build_role_context` / `load_role_prompt_with_context` 新增可选关键字 `include_memories=False, memory_limit=5` 透传给 context_packager（默认 False 时与现状逐字节一致；D-03 设计-5 的"调用点显式传参"机制必需的传递路径） | 5 | 是（管道） |

批 3 小计：3 个目标文件 + 1 个转发管道文件，全部完成。

## 测试

新增/更新测试文件（tests/）：

| 文件 | 覆盖 | 结果 |
|---|---|---|
| `tests/test_approval_ledger.py`（更新） | user_comprehension_confirmed 有值（True/False）round-trip、存量记录无键 → None、record_approval 值为 None 时不写键 | 通过 |
| `tests/test_ai_decision_ledger.py`（新增） | AiDecisionRecord 生成/round-trip/无 human_actor；AiDecisionLedger 追加+链校验、篡改/插入检测、find_by_task；**ledger_guard 子进程兼容验证**（合法追加 exit 0、篡改 exit 2） | 通过（14） |
| `tests/test_memory_injection.py`（新增） | config 开关 enabled=true（S4+ 注入）/false（不注入）/缺失/损坏（fail-closed）、阶段前缀匹配、dispatch 传参（S4 → True、S3 → False）、context_packager 注入节/limit 上限/空 store no-op/store 损坏 fail-closed | 通过（14） |
| `tests/test_t0104_deviations.py`（新增） | developer schema 含 deviations + 既有字段保留、格式校验（缺 reason/why_not_ask/impact_if_wrong → 无效；空数组合法）、main-thread §5.2/§5.3 规则存在 | 通过（12） |
| `tests/test_t0104_templates.py`（新增） | task-card 三节存在且顺序正确、SKILL 第 7 步、理解确认节 + "七、下一步"、R10/R11 原文、象限判定先行、lifecycle/USER-PROMPTS | 通过（11） |

全量回归：`pytest tests/`（排除 deep_probe_v35.py/lab/vertical_slice）
- 结果：**3635 passed, 64 skipped, 12 xfailed**；唯一失败
  `test_manifest_t0095.py::...test_manifest_exists_and_handoff_reference_is_real`
  为开工前即存在的环境状态问题（主会话 HANDOFF 已引用 `.ai/evidence/T-0104/evidence-manifest.v1.yaml`，
  但清单尚未由主会话 evidence 管线生成）——与本批改动无关，见遗留事项。

## 约束自查（git diff 实证）

| 约束 | 结果 |
|---|---|
| hooks/ 目录零改动 | ✅ `git diff --stat -- hooks/` 为空 |
| loop_core 治理内核零触碰（enforcement/hard_constraints/guard_health/state_machine） | ✅ diff 为空 |
| context_loader.py 默认参数（include_memories=False）零改动 | ✅ `git diff --stat -- loop_core/context_loader.py` 为空 |
| R10/R11 原文零改动（CONTRACT.yaml 仅 fixed_stance +1 行） | ✅ diff 仅新增"象限判定先行"一句 |
| fail-closed 语义不变 | ✅ 记忆注入缺失/损坏配置 → disabled；store 损坏 → 抛 KnowledgeStoreError（与 context_loader 一致）；ledger 空链合法 |
| 不部署/不发布/不安装；版本文件不改 | ✅ 未执行任何安装/发布；无版本文件改动 |

## 遗留事项

1. **evidence-manifest**：主会话需在本任务证据产出完成后生成
   `.ai/evidence/T-0104/evidence-manifest.v1.yaml`（其 evidence 管线，create-only 不可预占），
   否则 `test_manifest_t0095.py::TestT0095EvidenceManifest::test_manifest_exists_and_handoff_reference_is_real`
   持续失败（该失败在本子代理开工前即存在：HANDOFF 的 T-0104 引用先于清单生成）。
2. **role_loader.py 管道改动**：为让"调用点显式传参"到达 context_packager，
   `build_role_context`/`load_role_prompt_with_context` 新增了默认 False 的转发参数
   （非 D-03 §6 清单文件，属最小管道，默认行为逐字节不变），已在批 3 注明。
3. **安装副本同步**：若项目使用 `.zcode/skills/loop-governance/` 安装副本，
   批 1/批 3 的模板与 config.yaml 改动需按既有同步机制（loop-update）同步
   （D-03 §1.3.3 注明安装副本 templates/ 目前无 task-card）。
4. **版本文件**：CHANGELOG/版本 bump 由主会话执行，本子代理未动。
5. **真实 S4 执行验证**：D-03 §3.6 验收方式 2（一次真实 S4 执行写入至少 1 条
   [AI判断] 决策到 ai-decisions.jsonl 并通过 ledger_guard）需在后续真实阶段执行时验证，
   本批已提供自动化兼容证据（tests/test_ai_decision_ledger.py 子进程 exit 0）。
