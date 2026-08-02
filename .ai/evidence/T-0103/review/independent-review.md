# D-05 独立审查报告 — T-0103 四象限方法论评估（D-01 ~ D-04）

> 任务：T-0103（人机协作四象限方法论评估）
> 审查对象：`.ai/evidence/T-0103/design/D-01-inventory.md`、`D-02-gap-analysis.md`、`D-03-integrated-design.md`、`D-04-eval-experiment.md`
> 审查人：independent-reviewer（fresh context，不知道 D-01~D-04 作者与写作过程，全部结论亲自复验）
> 审查时间：2026-08-02
> 审查方法：只读复验——`git status/diff` 核对生产零改动；对 D-01 的 A~G 类约 70 个条目逐一打开引用文件核对路径存在性、行号引用、功能摘要；对 D-02 的"已有机制/差距"断言逐一对照代码；对 D-03 的全部兼容性声明（schemas/task_contract/ledger JSONL/memory_service 正则/context_loader 默认参数/插入位置行号）逐行核对；对 D-04 引用的 EvalCase/EvalRunner/EvalReport/tool_eval/test_evals 接口逐项核对。审查全程零修改（仅写本报告）。

---

## 一、裁决

# **GO**（无阻断项；P1=0，P2=1，P3=5，均不构成落地阻断）

- 生产零改动：**通过**（git 验证仅 `.ai/` 治理登记类改动，生产文件零改动）。
- D-01 盘点真实性：**通过**（约 70 项抽查，2 处事实性偏差、8 处行号轻微漂移，均不影响结论）。
- D-02 差距分析：**通过**（四象限+三阶段覆盖完整，P1/P2/P3 优先级与证据一致，无"把已有机制说成缺失"的误判）。
- D-03 设计合规：**通过**（5 项设计全部 candidate-only；hook 强制层与治理内核零触碰声明属实；兼容性声明与代码一致，仅 1 处行号引用漂移）。
- D-04 实验设计：**通过**（单一变量成立、4 维评分可度量、成功/失败信号可判定、EvalRunner 复用描述与代码一致）。

P2/P3 发现为文档级瑕疵，建议在 D-05 决策包交付前由作者修订，但不阻塞 GO。

---

## 二、生产零改动验证（亲自执行 git 验证）

命令：`git status --short` + `git diff --stat`（2026-08-02 实际运行）。

### 实际改动清单（分类）

**治理登记类（任务启动时登记，全部在 G-T-0103-REQUIREMENTS gate 的 allowed_paths=.ai/ 范围内）**：

| 文件 | 改动内容 | 分类 |
|---|---|---|
| `.ai/state.yaml` | current_task_id=T-0103、current_gate_id=G-T-0103-REQUIREMENTS、notes 增加 T-0103 登记 | 治理登记 |
| `.ai/task_graph.yaml` | T-0103 节点（+14 行） | 治理登记 |
| `.ai/gates.yaml` | 新增 G-T-0103-REQUIREMENTS（user-approval，approved，含 scope/evidence_required/exit_criteria） | 治理登记 |
| `.ai/HANDOFF.md` | Current Task/Current Gate/Evidence manifest 更新为 T-0103 | 治理登记 |
| `.ai/project_continuity.yaml` | gates.yaml/task_graph.yaml 的 sha256 重算（源文件哈希同步） | 治理登记（自动同步） |
| `.ai/evidence/observability/guard-events.jsonl` | 追加 guard health/death 事件 54 行（guard_health 自检产物） | 治理证据（自动生成） |
| `.ai/evidence/T-0087/contract-planes/conformance-report.json` | 仅 generated_at 时间戳更新 | 治理证据（自动生成） |
| `.ai/tasks/T-0103.md`（新增） | 任务卡 | 治理登记 |
| `.ai/evidence/T-0103/`（新增） | design/ 4 文档 + 本报告 | 治理证据 |

**生产代码类：0 个。** `agents/`、`skills/`、`hooks/`、`loop_core/`、`tools/`、`.zcode/tools/`、`tests/`、`docs/`、`pyproject.toml`、`AGENTS.md`、`USER-PROMPTS.md` 均不在 git status 输出中，`git diff --stat` 无任何生产路径。任务卡 T-0103.md 的 OUT OF SCOPE 约束（不修改生产代码/不安装 skill/不 bump 版本）被遵守。

**验证结论：生产零改动成立。**

---

## 三、D-01 抽查表（条目 | 路径存在 | 行号准确 | 摘要一致 | 备注）

抽查方法：A~G 类每类 4~17 个条目，用 `wc -l` 核对文件与行数、`grep -n`/`sed -n` 核对引用行内容。共约 70 项内容级核对。

### A 类（角色提示词体系）

| 条目 | 路径存在 | 行号准确 | 摘要一致 | 备注 |
|---|---|---|---|---|
| A-01 main-thread/SKILL.md | ✅（239L，与"239 行"精确一致） | ✅ L31"军师"、L89 §4、L187 §5 | ✅ | — |
| A-02 CONTRACT.yaml | ✅ | ✅ L12 known_blind_spots、L26-27 R10/R11 原文逐字一致、L67 veto_escalation | ✅ | — |
| A-03 THINKING_FRAMEWORK.md | ✅ | ✅ L8 Before/After、L25 Anti-patterns | ✅ | — |
| A-04 INTERNAL_LOOP.md | ✅ | ✅ L8 接收阶段、L37 Boundaries | ✅ | — |
| A-05 product-manager | ✅ | ✅ SKILL L13-30 立场、L33-45 做/不做、CONTRACT L54"交付物原型或可交互版本" | ✅ | — |
| A-06 project-manager | ✅ | ✅ CONTRACT L69 原文逐字一致（15%预警/30%否决） | ✅ | — |
| A-07 system-architect | ✅ | ✅ architecture-checklist.md L32 原文一致 | ✅ | 实际路径为 references/architecture-checklist.md，摘要一致 |
| A-09 developer/SKILL.md | ✅ | ✅ L63 unimplemented、L70 clarification_requests、L76 known_deviations、L79-80 deviation/adr_ref | ✅ | L59-91 区间含全部字段 |
| A-10 quality-engineer | ✅ | ✅ L22"只认数字"、L104 酌情、L164 不猜测默认命令 | ✅ | — |
| A-11 independent-reviewer | ✅ | ✅ L13-25 fresh context | ✅ | — |
| **A-12** security-engineer 等 5 角色 | ✅ 文件存在 | **❌ 引用句归属错误**：`"监控必须在生产流量到达前就位"` 实际位于 `agents/release-engineer/SKILL.md` **L127**，不在 security-engineer/SKILL.md（该文件无"监控/生产流量"字样） | ⚠️ 摘要实质正确（拒绝交付权属实），但引文文件归属错 | **P2** |
| A-13 role-capability-profiles.md | ✅（1119L 精确一致） | ✅ L49-51 MC-001、L852 原文一致 | ✅ | — |
| A-14 certification-system.md | ✅（643L 精确一致） | ✅ L43、L82 | ✅ | — |
| A-15 phase-loop-state-machine.md | ✅（477L 精确一致） | ✅ L64 BLOCKED_AT_ENTRY、L124 关键决策 | ✅ | — |
| A-16 role-conflict-protocol.md | ✅ | ✅ L54 原文一致 | ✅ | — |
| A-17 handoff/tool-request | ✅ | ✅ 行数与引用区间一致（77L/46L） | ✅ | — |
| A-18 README.md | ✅ | ✅ L24-38 | ✅ | — |

### B 类（治理技能与模板）

| 条目 | 路径存在 | 行号准确 | 摘要一致 | 备注 |
|---|---|---|---|---|
| B-01 SKILL.md | ✅ | ⚠️ 核心原则表头 L18（文中 L20-35，漂移 2 行）；启动检查 L26 ✅；hooks 表 L37 ✅；禁止动作 L82 ✅ | ✅ | — |
| B-02 decision-rules.md | ✅ | ⚠️ "Evidence≠Approval" 标题 L3（区间对）；双段确认 L15 ✅；"hook 是地板" L50（文中 L46-50，漂移 4 行） | ✅ | 标题实际写法含空格 "Evidence ≠ Approval"，grep 原文一致 |
| B-03 governance-lifecycle.md | ✅ | ✅ L38 USER_ACCEPTED、L47 磁盘事实 | ✅ | — |
| B-04 hook-protocol.md | ✅ | ✅ L34-35 历史教训原文一致、L75 设计决策 | ✅ | — |
| B-05 INDEX.md | ✅ | ✅ L3-7"必填表单…打回重做" | ✅ | — |
| B-06 gate-request.md | ✅ | ✅ L48 可选方案、L68 不推荐、L112 Gate 是用户的决策 | ✅ | — |
| B-07 human-review-packet.md | ✅ | ✅ L66-76 决策表、L79 六、下一步、L96 | ✅ | — |
| B-08 ADR | ✅ | ✅ L43 必填≥2、L161 Alternatives Considered | ✅ | — |
| B-09 system-architecture.md | ✅ | ✅ L107 四列表头原文一致 | ✅ | — |
| B-10 design-review-checklist.md | ✅ | ✅ L24、L159 | ✅ | — |
| B-11 config.yaml | ✅ | ✅ L43 quality_gates、L84 certification、L234 DEGR-009、L258 DEGR-011；.zcode 副本 L55 compile_threshold、L86 runtime_delivery（源文件无此两节） | ✅ | 源 309L / 副本 321L 与"安装副本额外含两节"一致 |
| B-12 chain.yaml | ✅ | ✅ L5 chain、L48 verify | ✅ | — |
| B-13 examples | ✅ | ✅ 01 L33-46 三问题、L124-131 关键要点 | ✅ | 02 实际文件名 02-pending-gate-blocking.md（内容相符） |
| B-14 .zcode 副本模板 | ✅ | ✅ 两文件存在 | ✅ | — |

### C 类（hook 层）

| 条目 | 路径存在 | 行号准确 | 摘要一致 | 备注 |
|---|---|---|---|---|
| C-01 hooks.json | ✅ | ✅ L3 SessionStart、L34 PreToolUse | ✅ | 亲自确认仅 SessionStart/PreToolUse 两事件（无 UserPromptSubmit/PostToolUse）→ 支持 C 类小结"无盲点/偏离/反向考察钩子" |
| C-02 session_brief.py | ✅ | ✅ L70-81 人工评审提醒、L89-106 Layer 4 MISSING ROLE EVIDENCE | ✅ | — |
| C-03 template_injector.py | ✅ | ✅ L44 PHASE_TEMPLATE_MAP、L69 MAX=8000、L110 build_template_context | ✅ | — |
| C-05 gate_guard.py | ✅ | ✅ L4-8 pending→exit 2、L15 决策记录豁免、L100-105 属当前任务才阻断、L132-160 T-0067、L305 T-0056 | ✅ | — |
| C-06 path_guard.py | ✅ | ✅ L12-16 T-0086-P1、L19-23 ask/deny | ✅ | — |
| C-08 bash_content_guard.py | ✅ | ✅ L43-78 DANGEROUS_PATTERNS | ✅ | — |
| C-09 ledger_guard.py | ✅ | ✅ L45 LEDGER_DIR、L74-87 verify_ledger_chain、L47-51 恢复提示 | ✅ | — |
| C-11 loop_enforcement.py | ✅（2059L 精确一致） | ✅ L3-18 头、L1700/L1733 DISPATCH_REQUIRED、L1799 SELF_REVIEW | ✅ | — |
| C-12 hook_common.py | ✅（831L 精确一致） | ✅ | ✅ | — |
| C-13 zcode_adapter.py | ✅ | ✅ tools/loop_execute_phase.py L13 引用属实 | ✅ | — |

### D 类（loop_core）

| 条目 | 路径存在 | 行号准确 | 摘要一致 | 备注 |
|---|---|---|---|---|
| D-01 context_loader.py | ✅（1342L 精确一致） | ✅ L23-30 D3、L48-53 LoadLevel、L117-123 | ✅ | 亲自确认 include_memories 默认 False（L806/L1122） |
| D-02 context_packager.py | ✅ | ✅ L6-18 ROLE_CONTEXT、L57-65 knowledge 前 3 条、L66-67 execution_mode | ✅ | — |
| D-04 role_orchestrator.py | ✅ | ✅ L13-26 PHASE_ROLES、L32 build_dispatch_manifest | ✅ | — |
| D-05 subagent_manifest.py | ✅ | ⚠️ SubagentSpec 实际 L36（文中 L35-60，漂移 1 行）；validate L93 ✅ | ✅ | — |
| D-06 inbox.py | ✅ | ✅ L42 CLARIFYING、L62 字段、L159-163 方法 | ✅ | — |
| D-07 planner.py | ✅ | ⚠️ TaskDraft 实际 L45（文中 L57-75 区间偏后）；clarification_needed L74 ✅ | ✅ | — |
| D-08 intent_router.py | ✅ | ✅ L92 HIGH_RISK、L11 置信度规则 | ✅ | — |
| D-09 knowledge_store.py | ✅ | ✅ L43-59 四类条目 | ✅ | — |
| D-10 memory_service.py | ✅ | ⚠️ 正则实际 L53-57（D-01 内 L28-40 的引用区间偏前 25 行） | ✅ | 正则语义与 D-03/D-04 描述一致（见第五节） |
| D-11 gate_feedback.py | ✅ | ⚠️ suggest_related_lessons L18（文中 L13-14）；DECISIONS L55 | ✅ | — |
| D-12 human_review_packet.py | ✅（1307L 精确一致） | ✅ L46/61/71 三类、L86/95 错误类、L566 related_experience | ✅ | — |
| D-13 retrospectives.py | ✅ | ✅ ActionItem L67、owner/deadline L5-7 | ✅ | — |
| D-14 evals.py | ✅ | ✅ L53-56 断言类型、L72 DEFAULT_EVAL_REPORT、L101 EvalCase | ✅ | — |
| D-15 llm/output_policy.py | ✅ | ✅ L27-39 OUTPUT_TOKEN_CAPS 逐字一致 | ✅ | — |
| D-16 context_controller.py | ✅（538L 精确一致） | ✅ | ✅ | — |
| D-17 三账本 | ✅ | ✅ execution_ledger L6-11/L157-182、audit_ledger L27 事件枚举、approval_ledger L40/45/L71-73 | ✅ | — |
| D-18 治理内核 | ✅ | ✅ second_failure 头注 | ✅ | — |
| 计数声明 | ✅ loop_core 57 py + llm 11 py（与"57+11"一致） | — | ✅ | — |

### E 类（工具层）

| 条目 | 路径存在 | 行号准确 | 摘要一致 | 备注 |
|---|---|---|---|---|
| E-01 loop_self_audit.py | ✅ | ✅ L15-18 fail-safe、L55 SYSTEM_PROMPT | ✅ | — |
| E-02 loop_onboard.py | ✅ | ⚠️ onboard() 实际 L36（文中 L27-35） | ✅ | — |
| E-03 loop_execute_phase.py | ✅ | ⚠️ build_script 实际 L25（文中 L13-22） | ✅ | — |
| E-04 loop_dispatch_role.py | ✅ | ✅ L1-10 用法 | ✅ | — |
| E-06 tools/ 36 py | ✅ | — | ✅ | 亲自确认 26 个 tool_*.py，无偏离/原型/考察类工具（支持"无原型工具、无偏离日志工具"小结） |
| E-07 .zcode/tools/validate_state.py | ✅ | ✅ L351-355 任务文件存在校验（L354-355 原文一致） | ✅ | 且 skills/loop-governance/SKILL.md L32 确有"运行 validate_state.py" |
| E-08 audit_handoff.py | ✅ | ✅ L16-24 必需标题 | ✅ | — |
| E-09 .zcode/tools/ 15 py | ✅ | — | ✅ | 与"15 个"一致 |

### F 类（文档与流程）

| 条目 | 路径存在 | 行号准确 | 摘要一致 | 备注 |
|---|---|---|---|---|
| F-01 07-phase-specification.md | ✅ | ✅ L163-177 人工评审汇总（S1/S2 必须、S4 无需机器已拦截、S5/S6 必须） | ✅ | — |
| F-02 docs 4 篇 / F-03 designs 3 篇 | ✅（docs 9 篇、designs 3 篇与声明一致） | — | ✅ | — |
| F-04 AGENTS.md | ✅ | ✅ L1-25 | ✅ | — |
| F-05 USER-PROMPTS.md | ✅ | ✅ L7-49 模板、L53/L59 [AI判断] | ✅ | — |
| F-06 .zcode/commands 2 个 | ✅ | ✅ | ✅ | — |

### G 类（.ai 数据层）

| 条目 | 路径存在 | 行号准确 | 摘要一致 | 备注 |
|---|---|---|---|---|
| G-01 state.yaml | ✅ | — | ✅ current_task=T-0103、loop_mode=FULL 属实 | — |
| G-03 inbox 2 个 REQ | ✅ | — | ✅ | — |
| G-04 plans 2 个 | ✅ | — | ✅ | — |
| G-05 knowledge/ | ✅ | — | ✅（case_index/cases/cases.json/schemas 4 项） | — |
| G-06 schemas 8 个 | ✅ | — | ✅ 8 文件，**无 task-card schema**（支持 D-03 兼容性声明） | — |
| G-07 policies 11 条 | ✅ | — | ✅ 11 条 policy（deployment/rollback/database/permission/secret/payment/production_data/migration/agents_md/runtime_tool/real_project_entry 全部核实） | — |
| **G-08** feedback/knowledge | ⚠️ `gate-lessons.yaml` 的**配置写入目标**确为 `.ai/evidence/feedback/gate-lessons.yaml`（gate_feedback.py L40），但**该目录当前不存在**（自项目至今未写入过教训） | — | ⚠️ "目录存在，当前为空"表述不准确；knowledge-store.yaml 存在 ✅ | **P3** |

### 抽查统计

- 内容级核对约 **70 项**：功能摘要与代码一致率 **100%**（结论性内容全部吻合）。
- 事实性偏差 **2 处**（A-12 引文归属错误、G-08 目录存在性表述），行号轻微漂移 **约 8 处**（1~25 行，均内容无误、不误导结论）。
- **抽查准确率 ≈ 97%**（2/70 事实偏差）。

---

## 四、D-02 逻辑审查

### 覆盖完整性：通过

- **四象限**：Q1/Q2/Q3/Q4 各一行 + 横向"象限切换判据"行，共 5 行；每行的"已有机制"均带 D-01 条目编号（A-xx/B-xx/C-xx/D-xx/E-xx/F-xx），抽查 8 个引用全部可回溯到 D-01 对应条目且与代码一致。
- **三阶段**：执行前简报 / 执行中偏离日志 / 执行后解释+反向考察各一行，同样带证据引用，抽查一致。
- 覆盖了方法论要求的全部要素（Q3 盲点自检、Q2 教学式提问、Q4 原型、偏离日志三要素、反向考察）。

### 优先级判断合理性：通过

- **P1-1（Q3 盲点自检）**：判断合理。亲自核实：任务卡模板（task-card.md）无盲点节；INDEX.md 模板体系无盲点自检模板；现有 only known_blind_spots（AI 自身盲点声明，12 角色 CONTRACT）与 role-capability-profiles known_failure_modes——确实只是"AI 不知道自己会什么"，无"用户没想到的项目变量"事前机制。Q3 确为空白象限，风险最大、成本最低（纯提示词+模板），P1 成立。
- **P1-2（偏离日志）**：判断合理。亲自核实：known_deviations 只在 developer/SKILL.md（契约偏离）；R10 [AI判断] 标注无结构化落盘（approval_ledger 仅记录用户批准，human_actor 恒为 "user"，L73）；无偏离日志工具（tools/ 26 个 tool_*.py 无 deviation 类）。"替用户做的关键决定无落盘"与"用户即信任锚"冲突的论证成立。
- **P1-3（反向考察）**：判断合理。亲自核实：grep 全工程（loop_core/hooks/tools/.zcode/tools/skills）发现 USER_ACCEPTED 仅出现在 governance-lifecycle.md L38 文档层，无任何机器校验——"纯语义标签"说法属实，加字段不触碰强制层。
- **P2-1（Q2 连续追问）**：合理。inbox add_clarification_questions 为一次性设置（L159-163），无多轮循环方法；R11 为"同阶段≤3 次"硬上限（CONTRACT L27），与教学式连续提问存在张力，分析属实。
- **P2-2（原型）**：合理。"原型"仅 product-manager CONTRACT L54 一句，无原型任务类型/模板/chain 节点。
- **P2-3 / P3**：合理（记忆注入默认关闭属实的判断——context_loader L806/L1122 默认 False）。

### 误判检查：通过

逐条核对"差距"断言，未发现把已有机制说成缺失的情况。特别核对：
- "无开工前盲点自检步骤" ✅（无模板/提示词要求）。
- "无 UserPromptSubmit 提示词钩子、无 PostToolUse 记录钩子" ✅（hooks.json 仅 SessionStart/PreToolUse）。
- "记忆注入默认关闭=形同虚设" ✅（默认 False 属实）。
- 唯一可议点：D-02 表 2 执行前行说"经验：记忆注入基础设施存在但默认关闭…knowledge 前 3 条注入（D-02）"——knowledge 前 3 条注入在 context_packager 中**默认生效**（cases[:3] 无开关），与"经验环节形同虚设"的说法略有出入：注入本身存在但仅 3 条且无"相关经验"字段引导。此属措辞轻微过度，非误判。

---

## 五、D-03 合规审查（candidate-only / hook 与内核零触碰 / 兼容性声明）

### 5.1 candidate-only 确认：通过

- git 验证：设计文档引用的全部生产文件（agents/skills/hooks/loop_core/tools）**零改动**（见第二节）。
- 5 项设计（设计-1 盲点自检 / 设计-2 定位声明区 / 设计-3 偏离日志 / 设计-4 反向考察 / 设计-5 执行前简报）全部为候选文本，明确标注"落地需 gate"；涉及 loop_core 代码的设计-3（approval_ledger 新记录类型）、设计-5（role_orchestrator/context_packager 调用点）均标注"落地需独立 gate"。
- 设计-3 的"落地前必须验证 verify_ledger_chain 对新文件兼容"表述为只读验证承诺，无 hook 改动。

### 5.2 hook 强制层与治理内核零触碰：通过

- hooks/* 17+1 文件零改动（git 验证）。
- 治理内核（gate_guard/loop_enforcement/hard_constraints/guard_health/state_machine 等）零改动。
- 唯一交互是设计-3 对 ledger_guard 的**只读兼容性验证**，且文中明确"零改动（仅验证）"。
- 注意：设计-3/设计-4 触碰 `loop_core/approval_ledger.py`（新增 AiDecisionRecord / 可选字段），设计-5 触碰 role_orchestrator/context_packager——按 D-01 自身分类这些属"记忆服务层/上下文工程层"，非 D-18 治理内核；D-03 影响清单表也如实标注"落地需 gate"。合规。

### 5.3 兼容性声明核对结果：全部与代码一致（1 处行号漂移）

| D-03 声明 | 代码实况（亲自核对） | 结论 |
|---|---|---|
| 任务卡无机器 schema 校验（G-06 8 个 schema 无 task-card） | `.ai/schemas/` 8 文件确无 task-card schema | ✅ |
| validate_state.py 只校验任务文件存在（L351-355） | L351-355 确为 task 文件存在性检查（L354-355"Current task file missing"） | ✅ |
| task_contract.py 只解析 developer_agent_id/reviewer_agent_id/phase（L43-77） | L40-55 三字段解析（含 no self-review 检查 L6），无其他任务卡字段解析 | ✅ |
| ledger_guard 只保护 .ai/ledger/（L45）+ 全目录追加链校验（L74-87） | LEDGER_DIR=".ai/ledger" L45；verify_ledger_chain 对目录内 JSONL 通用 | ✅ |
| **verify_ledger_chain 空链返回 True（L87）** → 新 ai-decisions.jsonl 从空起步兼容 | L87 `return True, "empty ledger"` **逐字一致** | ✅（设计-3 关键前提成立） |
| chain_hash = SHA256(prev\|row)（execution_ledger L157-182） | _compute_chain_hash L157-161、append_entry 物理追加 | ✅ |
| approval_ledger human_actor 恒为 "user"（L63/L70）→ 不混入 AI 决策的论证 | L73 `human_actor: str # Always "user"`；ApprovalRecord 10 必填+3 可选字段 L65-68 | ✅（设计-3 不采用 ApprovalRecord 复用的理由成立） |
| audit_ledger 事件枚举 gate_advance/role_activate/veto/handoff（L27） | L27 注释逐字一致 | ✅ |
| memory_service 正则只匹配 `# T-XXXX 验收报告`/`> **T-XXXX:**`/`> Gate:` → 新增 `> 理解确认：` 行零影响 | _ACCEPTANCE_HEADING_RE（L53）、_TITLE_LINE_RE（L55）、_GATE_LINE_RE（L57）三个正则逐字核对，均不匹配 `> 理解确认：` 前缀行 | ✅（向后兼容声明正确；仅行号 L28-40→实际 L53-57 漂移，见发现 P3-2） |
| USER_ACCEPTED 无机器校验（grep 确认） | 全工程 grep：仅 governance-lifecycle.md L38 文档层出现 | ✅ |
| context_loader include_memories 默认 False（L806/L1122）→ 设计-5 不动默认值 | L806/L1122 `include_memories: bool = False` 逐字一致 | ✅ |
| 空召回即 no-op（L945-980 区） | L945-980：include_memories=False 直接 return；recall 失败 fail-closed | ✅ |
| 插入位置行号：task-card L44（范围与边界 L30-42 与验收标准 L46 之间 `---`） | task-card 结构：L30 范围与边界、L44 `---`、L46 验收标准 **逐行一致**；L21（基本信息 L9-19 后、用户可见目标 L22 前）与 L28（L22-26 后、L30 前）亦一致 | ✅ |
| main-thread 插入位置：§2.2 L60-67 后 / §5.2 L213-230 / §5.3 L232-239 / §4 开发工程师 L129 / aggregation_prompt L198 | §2.2 速查 L60-67 ✅、§5.2 呈现包 L213 ✅、§5.3 自检 L232 ✅、开发工程师节 L129 ✅、aggregation_prompt 字段 L198 ✅ | ✅ |
| human-review-packet "六、下一步" L79-84 前插入 | HRP 节结构：五、决策 L68、六、下一步 L79 ✅ | ✅ |
| 01-example 第四步插入 L54-60 附近 | L54-60 为第三步项目分级后 AI 输出区 ✅ | ✅ |
| R10/R11 原文不动（设计-2） | CONTRACT L26-27 现有文本（git 未改动） | ✅ |

### 5.4 兼容性声明总结

**D-03 的"0 触碰 hook/内核"与全部兼容性声明与代码一致**，仅 memory_service 正则行号引用漂移（L28-40 vs 实际 L53-57），不影响结论。

---

## 六、D-04 科学性审查

### 单一变量：通过

- 实验组/对照组仅差"盲点自检提示词注入文本"，任务卡文本、模型、temperature=0、输出约束、评分方式均固定；控制变量清单明确（§1）。单一变量成立。
- 唯一可注意点：步骤 3 harness 中模型经 build_llm_driver 解析，若驱动不可用降级手工路径 B，两组仍保持同协议——降级不影响组间可比性（同一路径内 A/B 对称）。

### 评分维度可度量性：通过

- D1 盲点覆盖率：条目数（`B\d` 正则计数）+ 种子命中（5 个关键词 text_contains）——可度量。
- D2 问题质量：后果标志词 text_contains（"若不考虑"/"后果"/"影响"/"否则"）+ 可选 LLM judge（SKIP 不阻断）——可度量。
- D3 返工风险：5 种子各一 case，漏检数=FAIL 数——可度量。
- D4 确认次数：正则计数断言 1≤n≤3——可度量，且与 R11 兼容性挂钩合理。
- 校准先行（2 份高/低质量样例验证区分度）与"规则失效≠产出不合格"分流（失败信号 3）补足了关键词断言的脆弱性。

### 成功/失败信号可判定性：通过

- 成功：D1 均值差 ≥1.5 条或 ≥3/5、D2 ≥80% vs ≤50%、D3 ≤一半且无致命漏检、D4 落在 1-3 区间、≥3/4 维度占优且无副作用——阈值明确、可判定。
- 失败：4 维均 p≥0.05 且 d<0.5；副作用（token 膨胀 ≥30%、确认>3、空清单、格式合规率下降）——可判定。
- 统计口径（Mann-Whitney U n=25/组、Fisher、Cohen's d、α=0.05）与 n=50 次规模匹配探索性实验定位。

### EvalRunner 复用描述与代码一致性：通过（逐项核对）

| D-04 引用 | 代码实况 | 结论 |
|---|---|---|
| EvalCase（L100-223） | EvalCase L101，校验 L155-171（text_contains/text_matches/json_equals 参数校验） | ✅ |
| 断言类型 rule-first（L52-57） | L53-56 四类断言 + L10 rule-first 注释 | ✅ |
| default_executor 对无 command case 透传 input（L349-393） | L349-370 注释"the case input IS the produced output (offline transcript/evidence evaluation)" | ✅（"离线断言引擎"判断属实） |
| LLM judge 可选且永不阻断（L514-553） | score_llm L514-525 fail-safe SKIP 契约 | ✅ |
| build_llm_driver（L556-582） | L556 定义 | ✅ |
| EvalRunner（L587-656） | L587 class、L620 run() | ✅ |
| EvalReport 绑定 git_commit（L661-672） | git_commit() L661、ReportBinding git_commit L692-702 | ✅ |
| EvalReport（L675-744） | L675 class | ✅ |
| 输出预算 agent_eval（L76） | L76 LLM_OPERATION="agent_eval" | ✅ |
| 内置 guard 样例（L806-905） | _BUILTIN_CASE_DATA L806、builtin_cases() L898 | ✅ |
| tool_eval CLI（L20-42）：--cases/--report/--json | argparse --cases 等 L31+ | ✅ |
| tests/test_evals.py 使用模式 | 文件存在 | ✅ |
| docs/designs/loop-v4 §1 B1 eval 栈 pass@k | L22 统计门禁、L166-169 pass@k/pass^k 定义 | ✅ |
| --report 不覆盖既有 eval-report.json | DEFAULT_EVAL_REPORT=".ai/evidence/observability/eval-report.json"（L72），显式 --report 指向实验目录不冲突 | ✅ |

### 其他科学性观察（非阻断）

- 实验度量的是"提示词对产出质量"的直接效应（先导实验定位明确，威胁有效性 §10 已声明"与真实流程差异"），不做下游任务质量推断——定位诚实。
- D3 种子命中用关键词判定存在假阴性风险（AI 表达"目标设备"而非"移动端"），设计已用"校准样例+规则失效分流"缓解；建议落地时对未命中项做人工复核。
- 步骤 3 的 harness 脚本 tools/blindspot_experiment.py 属 candidate（需 gate）——与任务卡"不修改生产代码"一致（实验期新增脚本属 T-0103 范围外，需独立任务落地，设计已声明）。

---

## 七、发现清单

### P0（阻断）：无

### P1（必须修复）：无

### P2（应修复，不阻塞 GO）

- **P2-1【D-01 A-12】引文文件归属错误**：`agents/security-engineer/SKILL.md L127 "监控必须在生产流量到达前就位"` ——该句实际位于 `agents/release-engineer/SKILL.md` **L127**（security-engineer/SKILL.md 全文无"监控/生产流量"字样；L127 处为工作流程节）。影响：A-12 将 5 角色合并描述，实质结论（拒绝交付权）正确，但证据引用指向错误文件，读者按引用核查会落空。建议：D-01 修正为 release-engineer/SKILL.md L127。

### P3（建议修订，不影响结论）

- **P3-1【D-01 G-08】目录存在性表述错误**：`gate-lessons.yaml` 的写入目标 `.ai/evidence/feedback/` **目录当前不存在**（gate_feedback.py L40 `DEFAULT_LESSONS_RELATIVE_PATH` 为配置路径，从未写入过；find 全 .ai 无该文件）。建议改为"配置写入目标，当前未创建/为空"。
- **P3-2【D-01 D-10 / D-04 §4.2】memory_service 正则行号漂移**：`_ACCEPTANCE_HEADING_RE/_TITLE_LINE_RE/_GATE_LINE_RE` 实际位于 memory_service.py **L53-57**（D-01 写 L28-40，漂移 25 行）。正则语义与两文档描述完全一致，仅行号需修正。
- **P3-3【D-03 §0/§7】设计-5 超出任务卡点名范围**：任务卡 T-0103.md 点名的整合设计为 4 项（盲点自检/定位声明区/偏离日志/反向考察），D-03 实际含 5 项（追加"执行前简报 4 要素补全"P2-3）。因 D-02 差距分析本就包含 P2-3 且任务卡目标 2 为"四象限+三阶段差距分析"，属合理扩展；建议在 D-03 开头或决策包中显式说明与任务卡 4 项的关系。
- **P3-4【D-01 各条目】行号轻微漂移汇总**（内容均无误）：B-01 核心原则表头 L18（文 L20-35）、B-02 "hook 是地板" L50（文 L46-50）、D-05 SubagentSpec L36（文 L35-60）、D-07 TaskDraft L45（文 L57-75）、D-11 suggest_related_lessons L18（文 L13-14）、E-02 onboard L36（文 L27-35）、E-03 build_script L25（文 L13-22）。均为区间引用偏移 1-8 行，指向内容正确。
- **P3-5【D-02 表 2 执行前行】措辞轻微过度**："经验…记忆注入默认关闭导致'经验'环节形同虚设"——实际 context_packager 的 knowledge 前 3 条注入（cases[:3]）默认生效，只是无"相关经验/不熟悉处"字段引导且 recall 默认关。建议措辞改为"记忆召回默认关闭、knowledge 注入仅 3 条且无字段引导"。

---

## 八、总结论

D-01~D-04 四份文档经独立复验：**生产零改动成立**（git 验证仅 .ai/ 治理登记+自动生成证据）；D-01 盘点内容级准确率约 97%（2 处事实偏差 A-12/G-08，不影响任何结论）；D-02 四象限+三阶段覆盖完整、P1 优先级与证据一致、无误判；D-03 五项设计全部 candidate-only、hook 强制层与治理内核零触碰属实、全部兼容性声明（任务卡无 schema、ledger 空链/链式 JSONL 契约、approval human_actor 语义、memory_service 正则、context_loader 默认参数、插入位置行号）与代码一致；D-04 单一变量成立、4 维可度量、成功/失败信号可判定、EvalRunner 复用描述与 evals.py/tool_eval.py/test_evals.py 逐项吻合。

**裁决：GO。** P1=0；P2=1（D-01 A-12 引文归属，建议 D-01 修订）；P3=5（文档级修订建议）。P2/P3 均不影响"设计候选是否值得交用户决策"的判断，建议在交付决策包时一并附上本报告的修订建议。
