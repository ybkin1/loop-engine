# D-01 资产盘点清单 — Loop Engine 提示词工程现状（T-0103）

> 任务：T-0103（人机协作四象限方法论评估）
> 产出：D-01 只读资产盘点（本文件）、D-02 差距分析
> 盘点范围：`agents/`、`skills/loop-governance/`、`hooks/`、`loop_core/`、`tools/`、`.zcode/tools/`、`docs/`、`.ai/`（schemas/policies/knowledge/inbox/plans 等）
> 方法：只读调查（Read/Bash 只读命令），未修改任何生产文件。行号引用基于 2026-08-02 实际读取。
> 四象限定义：Q1 已知的已知（直接执行不猜测）；Q2 已知的未知（老师问答/围绕缺口连续提问）；Q3 未知的未知（开工前盲点自检）；Q4 未知的已知（低成本原型/多方案+用户选择）。三阶段：执行前简报 / 执行中偏离日志 / 执行后解释+反向考察。

---

## A. 角色提示词体系（agents/）

| 编号 | 路径 | 类型 | 功能摘要 | 四象限定位 | 证据 |
|---|---|---|---|---|---|
| A-01 | `agents/main-thread/SKILL.md`（239 行） | 角色提示词 | 主控线程"军师"提示词：单阶段编排者，产出 SubagentManifest（自包含 prompt 的编排计划），聚合角色产出、逐项对照 11 角色验证标准、呈现 gate。硬约束：角色隔离、developer≠reviewer、否决链不可绕过、一个阶段一个军师。 | Q1 主导（编排/验收均有明确标准，不猜测）；gate 呈现部分服务 Q4（给用户可决策内容）；执行中（聚合验证）。 | L31-37"main-thread 不是工头，是军师"；L89-185 全 11 角色验证标准表；L187-239 输出格式（manifest/gate 呈现包）+ 自检规则 6 条 |
| A-02 | `agents/main-thread/CONTRACT.yaml` | 角色合同 | 12 字段合同。关键规则：R10_ai_judgment_first（遇需决策事项先自己判断并标注 [AI判断]，只在真正无法确定时才问用户）、R11_reduce_questions（同阶段内向用户提问≤3 次，非关键决策自行处理并标注）。`known_blind_spots` 声明 AI 自身盲点（不精通技术实现/架构/质量/安全）。 | R10/R11 是 Q4 的"AI 先给判断"机制 + 对 Q2 提问的显式数量约束；known_blind_spots 是 Q3 的雏形（但只声明 AI 盲点，非用户盲点/影响结果变量）；执行中（决策标注）。 | L12-17 known_blind_spots；L26-27 R10/R11；L67-71 veto_escalation（双角色否决自动升级用户 Gate + HumanReviewPacket） |
| A-03 | `agents/main-thread/THINKING_FRAMEWORK.md` | 思考框架 | Before/During/After 三段式行动检查：执行前问范围/禁止项/用户批准；执行中一次一改、留证据、测试≠批准；执行后跑 validator、更新 HANDOFF、如实报告。反模式清单（不伪造完成证据等）。 | 执行前/中/后的微循环自律；Q1（范围内直接做，不扩展）。 | L8-23 三段检查；L25-29 反模式 |
| A-04 | `agents/main-thread/INTERNAL_LOOP.md` | 内部循环 | 5 步内部循环：接收阶段→出计划→等会话调度→做汇总→退场。边界明确（不调 Agent、不批准 gate、不改 AGENTS.md）。 | 执行中流程定义；Q1。 | L8-35 五步循环；L37-42 Boundaries |
| A-05 | `agents/product-manager/SKILL.md` + CONTRACT.yaml | 角色提示词 | 需求澄清角色：与用户访谈式澄清目标/痛点/场景，产出用户故事+Given-When-Then AC+P0-P3 优先级+范围边界（MVP/后续/不做）。明确禁止代替用户做决策、禁止技术语言。CONTRACT 含 known_blind_spots、`交付物原型或可交互版本`（L54）。 | **Q2 核心资产**（访谈式澄清=老师问答式）；Q4 雏形（原型一词）；执行前（需求阶段）。 | SKILL L13-30（立场：不接受含糊目标）；L33-45（做/不做表）；CONTRACT L54"交付物原型或可交互版本" |
| A-06 | `agents/project-manager/SKILL.md` + CONTRACT.yaml | 角色提示词 | 任务图/依赖/风险/进度管理。进度偏差预警（偏离计划 15% 预警、30% 否决）。 | 执行前（计划）+ 执行中（偏离预警——偏离日志的雏形，但只覆盖进度维度）；Q1。 | CONTRACT L69"进度偏差预警阈值：偏离计划 15% 触发预警，30% 触发否决" |
| A-07 | `agents/system-architect/SKILL.md` + references/architecture-checklist.md | 角色提示词 | 架构设计角色。checklist 强制"有备选方案（主选型不行时用哪个）"。 | **Q4 机制**（备选方案要求）；执行前（S2）。 | architecture-checklist.md L32"有备选方案（主选型不行时用哪个）" |
| A-08 | `agents/module-architect/SKILL.md` + CONTRACT.yaml | 角色提示词 | 模块/接口详细设计，产出接口契约（输入/输出/错误），scripts/validate_contract.py 自动校验。 | Q1（契约确定性）。 | SKILL L3-11 输出契约结构；scripts/validate_contract.py |
| A-09 | `agents/developer/SKILL.md` | 角色提示词 | 实现角色。输出 JSON 含 `unimplemented`（原因+decision_by）、`clarification_requests`（歧义描述）、`known_deviations`（偏离描述+adr_ref）、summary。 | **执行中偏离记录机制雏形**（契约偏离+澄清请求）；Q2 一部分（歧义上报）；Q1（契约强制）。 | L59-91：unimplemented/decision_by、clarification_requests/ambiguity、known_deviations/deviation/adr_ref |
| A-10 | `agents/quality-engineer/SKILL.md` | 角色提示词 | 质量门角色："我只认数字，不认解释"。跑 lint/typecheck/test/audit/build，数字对比门槛，产出 quality_report.json+summary。无权放低门槛；缺失配置→BLOCKED 不猜测默认命令。TOOL_REQUEST 协议。 | **Q1 典型**（机器输出对比门槛，零猜测空间）；执行中（质量门）。 | L22-28"覆盖率少一个点就是少一个点"；L95-104 可否决 5 项"不存在酌情空间"；L162-165"不尝试猜测或使用默认命令" |
| A-11 | `agents/independent-reviewer/SKILL.md` | 角色提示词 | 独立评审角色：fresh context（不知道开发历史/谁写的/为什么），三重检查（安全 7 项+架构 4 项+功能 5 项），每条发现含文件+行号+代码，只报告不修改。 | Q1（客观检查清单）；Q3 一部分（fresh context 防止"已知污染"）。 | L13-25 fresh context 规则；L25"不知道的就不假设" |
| A-12 | `agents/security-engineer` / `test-engineer` / `delivery-manager` / `release-engineer` / `module-architect`（SKILL+CONTRACT） | 角色提示词 | 安全审查（security_scan）、测试用例、交付清单（release-checklist/deployment/rollback）、发布运维。均有 12 字段合同 + 拒绝交付权（证据不足时拒绝）。 | Q1（清单化执行）；执行中/后。 | 各 SKILL 的"拒绝交付"节；security-engineer/SKILL.md L127"监控必须在生产流量到达前就位" |
| A-13 | `agents/references/role-capability-profiles.md`（1119 行） | 参考文档/决策材料 | 12 角色能力画像：supported_stacks、required_knowledge/tools、competency_challenges、minimum_pass_conditions、known_failure_modes、abstention_conditions、capability_expiry_policy。认证挑战场景。 | **Q3 较完整资产**（known_failure_modes/abstention_conditions 是 AI 侧盲点清单）；Q1（能力-任务匹配）。 | L49-107 main-thread 画像（Challenge MC-001/002、known_failure_modes、abstention_conditions）；L852"不在评审报告中提'看起来设计初衷是……'（不知道设计初衷）" |
| A-14 | `agents/references/certification-system.md`（643 行） | 参考文档/决策材料 | 角色认证体系：生产任务前须持有效认证；认证挑战中角色不知道自己被考；评审员 fresh context 不知道标准答案；连续失败触发降级。 | Q1/Q3（用"不知道"隔离防作弊）；执行后（再认证）。 | L43"角色 agent 不知道这是认证挑战还是一般生产任务"；L82"评审员使用 fresh context -- 不知道挑战的'标准答案'" |
| A-15 | `agents/references/phase-loop-state-machine.md`（477 行） | 参考文档/决策材料 | 12 阶段状态机（S0-S11）+ 任务/gate/产物生命周期。BLOCKED_AT_ENTRY 终止态：用户决策前不得继续；关键决策附理由和备选方案。 | Q4（决策需备选方案）；执行前/中状态定义。 | L64"BLOCKED_AT_ENTRY 是终止态…用户的选项：补充缺失项并重试，或跳过该阶段"；L124"关键决策（附理由和备选方案）" |
| A-16 | `agents/references/role-conflict-protocol.md` | 参考文档/决策材料 | 角色冲突处理（如覆盖率争议）：升级时呈现"选项、代价、收益、为什么推荐"。 | **Q4 机制**（选择材料结构化）。 | L54"选项、代价、收益、为什么推荐" |
| A-17 | `agents/references/handoff-standard.md` / `tool-request-protocol.md` | 参考文档 | 交接标准（HANDOFF 必须包含"下一步"）；工具请求协议（TOOL_REQUEST JSON）。 | 执行中/后；Q1。 | handoff-standard.md L1-77；tool-request-protocol.md L1-46 |
| A-18 | `agents/README.md` | 文档流程 | 两层架构说明：会话调度、角色平级、12 角色清单、12 字段合同标准。 | 元文档（架构说明）。 | L24-38 |

**A 类小结**：12 角色 ×（SKILL+CONTRACT+THINKING_FRAMEWORK+INTERNAL_LOOP）+ 6 参考文档，共约 55 文件。角色提示词以"合同化约束+清单化验收"为主，Q1 覆盖最强；Q2 由 product-manager 访谈式澄清承担；Q4 有备选方案要求但无原型流程；Q3 只有 AI 侧盲点声明（known_blind_spots / known_failure_modes），无"开工前盲点自检"步骤。

---

## B. 治理技能与模板（skills/loop-governance/ + .zcode/skills/loop-governance/）

| 编号 | 路径 | 类型 | 功能摘要 | 四象限定位 | 证据 |
|---|---|---|---|---|---|
| B-01 | `skills/loop-governance/SKILL.md` | 技能模板（角色提示词） | 治理启动器：4 条不可协商核心原则（Gate 是用户决策、批准≠执行、局部完成≠产品完成、治理是手段）；启动检查清单 6 步（读 state/HANDOFF/tasks/gates/task_graph → 跑 validate_state → pending gate 停止等待决策）；禁止动作清单（不代批 gate、不绕过 hook、保护区写入需 gate）。 | **Q1 执行前**（启动检查=执行前简报的强制版）；gate 用户决策原则服务 Q4；执行中（禁止动作=不越界）。 | L20-35 核心原则；L26-35 启动检查清单；L82-89 禁止动作；L37-45 hooks 强制层表 |
| B-02 | `skills/loop-governance/references/decision-rules.md` | 决策材料 | Evidence≠Approval 权威文档：reviewer PASS/validator 0/测试全绿/hook 放行都只是 evidence；用户批准唯一起源是明确决策文本（approval_text/approval_evidence/approval_source=explicit_user_message）；批准与执行双段确认；hook 是地板不是天花板。 | Q1/Q4（用户决策边界）；执行前/后。 | L3-13 Evidence≠Approval；L15-21 双段确认；L46-50"hook 是地板，不是天花板" |
| B-03 | `skills/loop-governance/references/governance-lifecycle.md` | 决策材料 | 三套状态机（任务/产物/gate 生命周期）：pending gate 是全停信号；批准≠执行（需"执行已批准的 G-XXXX"）；PASS 语义分层（LOCAL_SLICE_PASS→TASK_REQUIREMENTS_PASS→USER_ACCEPTED→TASK_CLOSED）；磁盘事实优先级 7 级。 | Q1（状态确定性）；Q4（USER_ACCEPTED 是用户验收语义）；执行中/后。 | L16-29 gate 状态机；L36-38 PASS 分层；L47-55 磁盘事实优先级 |
| B-04 | `skills/loop-governance/references/hook-protocol.md` | 文档流程 | ZCode hook 协议实施依据：事件/matcher/退出码/JSON 形态；设计决策记录（exit 2 vs JSON deny、path_guard ask 默认、sys.dont_write_bytecode）；排障速查。历史教训：旧版 hooks.scripts[] 结构无效导致 hook 从未运行（"纸面执行的活标本"）。 | 元文档（hook 工程规范）；Q1（fail-closed 语义）。 | L34-35 历史教训；L75-92 设计决策；L77-85 五个决策点 |
| B-05 | `skills/loop-governance/templates/INDEX.md` + 30 个模板 | 技能模板 | 模板库索引："每个模板是**必填表单**，不是参考文档。角色启动时自动加载对应模板，主控验收时逐项检查，缺任何必填项=打回重做"。8 类模板：requirements/architecture/design/testing/security/deployment/review/coding + gate-request + human-review-packet + task-card + phase-delivery-index。 | **Q1 核心机制**（必填表单=不给猜测空间）；执行前（模板注入）。 | INDEX.md L3-7"必填表单…缺任何必填项 = 打回重做"；L5-7 使用方式 |
| B-06 | `skills/loop-governance/templates/gate-request.md` | 决策材料 | 用户决策展示模板：通俗语言解释"这是什么/您需要决定什么"，**可选方案 A/B/C 表（方案/说明/效果/风险代价）**，AI 建议+不推荐其他方案的原因，批准/拒绝/推迟三态后果，决策记录表。 | **Q4 核心资产**（多方案+推荐+用户选择）；执行前/后决策点。 | L48-54 可选方案表（A 推荐/B 备选/C 暂不决定）；L75-86 三态后果；L112"Gate 是用户的决策，不是 AI 的结论" |
| B-07 | `skills/loop-governance/templates/human-review-packet.md` | 决策材料 | 阶段结束 Human Review Packet 模板：阶段概览/参与角色产出/质量门结果/发现的问题（已解决/跟踪/已知未处理）/**用户需要做的决策**（决策事项+背景+可选方案+AI 建议+截止时间）/下一步（需要您说的一句话）。语言：纯中文无术语。 | **Q4 + 执行后解释**（单向解释给非技术用户，有"需要您说的一句话"但无反向考察）。 | L1-6 定位说明；L66-76 决策表；L79-84 下一步/需要您说的一句话；L96"如有疑问，请直接向 AI 助手提出" |
| B-08 | `skills/loop-governance/templates/architecture/architecture-decision-record.md` | 技能模板 | ADR 模板：**备选方案（必填，至少 2 个）**，含备选方案比较参考。 | **Q4 机制**（方案对比必填）。 | L43"备选方案（必填，至少 2 个）"；L161 Alternatives Considered 参考 |
| B-09 | `skills/loop-governance/templates/architecture/system-architecture.md` | 技能模板 | 架构文档模板：每项设计选择"选择/备选方案/选择理由/代价风险"四列。 | **Q4 机制**。 | L107"选择 | 备选方案 | 选择理由 | 代价/风险" |
| B-10 | `skills/loop-governance/templates/review/design-review-checklist.md` | 技能模板 | 设计评审清单：含"考虑了至少 2 个备选方案"检查项。 | Q4（备选方案成为验收标准）。 | L24"考虑了至少 2 个备选方案 [ ]"；L159 备选方案示例 |
| B-11 | `skills/loop-governance/config.yaml`（源）/ `.zcode/skills/loop-governance/config.yaml`（安装副本） | 配置 | hook 行为配置（gate_guard fail_on_state_error=closed、path_guard decision=ask + 保护区、session_brief max_pending_listed=10）、quality_gates 语言模板（lint/typecheck/test/audit/build 命令+门槛）、certification 认证配置、degradation 13 条降级规则（DEGR-009 生产事故→ROLE_BLOCKED 需人工恢复；DEGR-011 伪造证据零容忍）。安装副本额外含 compile_threshold 与 runtime_delivery 节。 | Q1（门槛数字=确定性）；Q3 一部分（事故/伪造证据的自动封锁=机器盲点防御）；执行后（再认证）。 | 源 config L7-36 hook 配置；L43-78 quality_gates；L84-130 certification；L136-309 degradation（DEGR-009 L234-242、DEGR-011 L257-265） |
| B-12 | `skills/loop-governance/chain.yaml` | 配置 | 证据链结构：requirements→architecture→interface_contract→source_code→quality_report→(security/review/human_review)，upstream 依赖 + required 标志 + strict_mode/max_stale_hours 验证规则。 | Q1（证据完整性确定性）；执行中/后（证据校验）。 | L5-45 链定义；L48-50 验证规则 |
| B-13 | `skills/loop-governance/examples/`（3 例） | 文档流程 | 场景示例：01 新任务创建（**展示 Q2 需求对齐：AI 在开工前问 3 个关键问题：平台/数据存储/用户数量**，并说明"这些问题的答案会影响项目的规模和开发方式"）；02 pending gate 阻断；03 独立评审（seeded defect）。 | **Q2 的示范文档**（"AI 与用户对齐需求"=围绕缺口提问的教学示例）；执行前。 | 01 L33-46 第二步 AI 输出 3 个问题；L124-131 关键要点（"AI 不替用户做决定…需求对齐时 AI 问了三个问题"） |
| B-14 | `.zcode/skills/loop-governance/templates/gate-decision-summary.md` / `phase-acceptance-summary.md` | 技能模板 | 安装副本专用模板：gate 决策摘要、阶段验收摘要（比源模板库精简的呈现格式）。 | Q4（决策呈现）；执行后（验收总结）。 | 两文件实际读取 |

**B 类小结**：约 44 文件（源 39 + 安装副本 4-5）。模板体系是"必填表单"哲学（Q1 最强），gate-request/human-review-packet 是 Q4 呈现核心，examples/01 是 Q2 教学示例。**缺 Q3 盲点自检模板、缺执行后反向考察模板、缺原型类模板。**

---

## C. Hook 注入/拦截（hooks/）

| 编号 | 路径 | 类型 | 功能摘要 | 四象限定位 | 证据 |
|---|---|---|---|---|---|
| C-01 | `hooks/hooks.json` | hook 注入配置 | 事件注册：SessionStart 挂 loop_auto_activate+template_injector+session_brief（3 个注入类）；PreToolUse 挂 loop_enforcement+bash_content_guard+gate_guard+content_guard+ledger_guard+role_isolation+path_guard（7 个拦截类），matcher 覆盖 Read/Write/Edit/Bash/Agent/Skill/mcp 等。 | 全部四象限的执行强制层（注入=上下文供给，拦截=范围强制）。 | L2-32 SessionStart；L34-96 PreToolUse |
| C-02 | `hooks/scripts/session_brief.py` | hook 注入 | SessionStart 注入治理状态摘要（additionalContext）：phase/current_task_id/current_gate_id、pending gate 列表、HANDOFF Next Session First Step、**人工评审中断提醒**（S1/S2/S5/S6 阶段提示展示强制产出+审查报告+gate 选择）、**MISSING ROLE EVIDENCE (Layer 4)** 检查（S5/S6 缺角色证据则提示必须 dispatch）、Dashboard 摘要。永不阻断（失败 exit 0）。 | **执行前简报的自动化形态**（状态注入+该做什么的提醒）；Q2 一部分（"展示给用户"节）；执行中（缺证据拦截提醒）。 | L63-131 build_brief：L70-87 human review 提醒；L89-112 Layer 4 缺角色证据；L114-130 pending gates+HANDOFF next step |
| C-03 | `hooks/scripts/template_injector.py` | hook 注入 | SessionStart 按 current_phase 自动注入对应模板目录内容（S1→requirements/、S2→architecture/、S3→design/+interface-contract、S4→coding/+design、S5→testing/+security、S6→deployment），上限 8000 字符。 | **Q1 执行前**（模板=必填表单的自动供给，让 AI 拿到"已知的已知"边界）。 | L44-66 PHASE_TEMPLATE_MAP；L69 MAX_TEMPLATE_CHARS=8000；L110-146 build_template_context |
| C-04 | `hooks/scripts/loop_auto_activate.py` | hook 注入 | SessionStart 自动激活 Loop 模式：按客观风险因子（gates.yaml/requirements.txt/pyproject.toml/migrations 等）自动 FULL/STANDARD，"Loop 永不 opt-in"；注入激活状态。 | 执行前（模式分级自动化）；Q3 一部分（风险因子=机器版"未知变量"预判）。 | L10-17 目标说明；L27-38 AUTO_FULL/AUTO_STANDARD_TRIGGERS |
| C-05 | `hooks/scripts/gate_guard.py` | hook 拦截 | PreToolUse：pending gate（属当前 task）→ exit 2 阻断一切写入；gate 生命周期交叉校验（missing/rejected/blocked/task 不匹配均 fail-closed）；决策记录豁免（.ai/gates.yaml 可写，防死锁）；T-0067 子代理评审证据存在性+session 独立性深校验；C7 HardConstraints blocker；T-0056 独立评审证据缺失阻断。 | Q1/Q4 执行强制（用户决策前一切停摆=Q4 用户选择权的机器保证）；执行中。 | L5-18 语义说明；L183-189 决策记录豁免；L261-268 pending 阻断；L132-160 T-0067 证据校验；L305-325 T-0056 |
| C-06 | `hooks/scripts/path_guard.py` | hook 拦截 | PreToolUse：保护区（AGENTS.md/stable//registry//.zcode/config.json/.zcode/tools/）写入 → 默认 ask（用户当场点击确认，"用户即信任锚"）或 deny 硬阻断；项目外路径写入阻断（fail-closed）；执行形态 Bash 引用项目外路径→阻断（T-0086-P1）；只读豁免。 | Q1/Q4（授权边界=让用户对"执行层改动"做当场决策）；执行前。 | L6-26 ask/deny 模式；L139-158 T-0086-P1；L167-192 阻断/ask 逻辑 |
| C-07 | `hooks/scripts/content_guard.py` | hook 拦截 | PreToolUse Write/Edit：ruff 检查（fail-closed）、硬编码密钥正则扫描（5 类模式）、架构合规（新文件路径对照 docs/02-architecture.md）、注入/动态执行模式（SS-010/SS-011）。 | Q1（质量/安全确定性）；执行中。 | L3-11 三项检查；L41-57 密钥+注入模式；L64-100 ruff fail-closed |
| C-08 | `hooks/scripts/bash_content_guard.py` | hook 拦截 | PreToolUse Bash：拦截绕过 Write/Edit 的文件操作（echo>/cat>/cp/mv/rm/touch/dd/curl -o/git checkout --/tee/sed -i/python open()/PowerShell/解压等 11 类模式）。 | Q1（写入通道唯一化=强制 AI 走受管工具）；执行中。 | L43-78 DANGEROUS_PATTERNS 11 类；L3-14 目的说明 |
| C-09 | `hooks/scripts/ledger_guard.py` | hook 拦截 | PreToolUse：.ai/ledger/ 只允许追加（open("a") 语义）、chain_hash 连续校验、Edit 工具禁用、死锁恢复提示。 | Q1（账本不可篡改=审计确定性）；执行中（执行记录）。 | L3-17 四条强制；L47-51 恢复提示；L74-79 chain_hash 定义 |
| C-10 | `hooks/scripts/role_isolation.py` | hook 拦截 | PreToolUse：检测 self-review（developer_agent_id==reviewer_agent_id）→ FULL 模式 deny（exit 2），STANDARD/LIGHTWEIGHT 仅 WARN；任务合同角色分配不完整→WARN；评审证据 session 独立性检查（T-0062）；治理文件豁免防死锁。 | Q1（独立审查的机器强制=防止"自评自审"污染 Q1 信任）；执行中。 | L110-122 enforcement level 映射；L199-223 SELF_REVIEW 阻断；L132-140 T-0062 |
| C-11 | `hooks/scripts/loop_enforcement.py`（2059 行） | hook 拦截 | PreToolUse 总闸：FULL/STANDARD 模式下一切写入必须在批准任务范围（allowed_paths）内，否则 DISPATCH_REQUIRED 阻断；只读豁免；项目外写入阻断；runtime projection 校验（SETUP_INCOMPLETE fail-closed）；IDENTITY_REQUIRED（runtime 项目要求 caller 身份）；MCP 工具能力白名单（mcp_allowed_tools）；GOVERNANCE_RECOVERY 受限恢复通道；self-review 证据阻断（B6）；多门禁证据检查（delivery/slo/second_failure/security/phase gate）；自愈同步+重执行。 | Q1 全域执行强制（"阻止 AI 自己动手干所有事"）；Q3 一部分（fail-closed 姿态=机器不猜）；执行中。 | L3-18 核心逻辑四步；L1629-1652 只读/路径安全；L1697-1716 MCP 白名单；L1729-1734 DISPATCH_REQUIRED；L1797-1803 SELF_REVIEW 阻断；L1265-1351 SLO/second-failure 门禁 |
| C-12 | `hooks/scripts/hook_common.py`（831 行）+ `_hook_bash.py` `_hook_path.py` `_hook_state.py` `_hook_config.py` `_hook_sync.py` | hook 共享库 | 单一判定源：is_governance_project/load_state/pending_gates/is_path_safe/is_readonly_exempt/is_governance_tool_command/should_fail_closed/auto_sync_to_plugin_cache 等。fail-closed 姿态统一。 | 元层（所有 hook 的判定地基）；Q1。 | hook_common.py L1-831；各 _hook_*.py |
| C-13 | `hooks/zcode_adapter.py` | 适配层 | ZCode 会话适配器（Agent 调用封装），供 tools/loop_execute_phase.py 使用。 | 执行中（调度执行）。 | 实际读取（tools/loop_execute_phase.py L13 import） |

**C 类小结**：17 个 Python 文件 + hooks.json。这是"机器强制替代 AI 自觉"的执行层：注入类（C-02/C-03/C-04）负责执行前上下文供给，拦截类（C-05~C-11）负责 Q1 范围强制与用户决策权（Q4）的机器保证。**hook 层没有任何"盲点自检/偏离日志/反向考察"类钩子**（无 UserPromptSubmit 提示词钩子、无 PostToolUse 记录钩子），偏离日志完全依赖 AI 自觉。

---

## D. 上下文/记忆/LLM 层（loop_core/）

| 编号 | 路径 | 类型 | 功能摘要 | 四象限定位 | 证据 |
|---|---|---|---|---|---|
| D-01 | `loop_core/context_loader.py`（1342 行） | 上下文工程 | 渐进式角色上下文加载：MINIMAL(~200 tokens)/STANDARD(~600)/FULL(~2600)，按任务复杂度取；ContextCompressor（token 预算 70% 触发压缩，确定性规则摘要，max_levels=2）；CitationResolver 恢复被截断的证据引用（UNRESOLVED 标记不猜）；**D3 可选记忆注入**（include_memories 默认 False，recall 前 5 条）。 | Q1（上下文确定性供给+防爆）；执行前；D3 是"经验复用"=执行前简报中"经验"要素的基础设施（但默认关闭）。 | L1-30 功能说明；L48-53 LoadLevel；L117-123 预算/记忆参数；L23-30 D3 记忆注入 |
| D-02 | `loop_core/context_packager.py` | 上下文工程 | 按角色打包代码上下文：每个角色固定文件清单+git diff（开发/评审）+知识 cases 前 3 条+任务卡前 1000 字符，上限 15000，尾部追加"execution_mode: SIMULATED_MAIN_SESSION / agent_takeover: false"。 | Q1（角色-上下文匹配确定性）；执行前。 | L6-18 ROLE_CONTEXT 表；L20-68 build_context；L66-67 执行模式声明 |
| D-03 | `loop_core/role_loader.py` | 上下文工程 | 角色加载器：load_role_prompt = SKILL.md + CONTRACT（fixed_stance/prohibitions/veto_power/responsibilities）+ 任务上下文 + 输出要求（JSON 匹配角色 schema + reviewer_session_id）；load_role_prompt_with_context = 身份+代码上下文（"ONE method for agent dispatch"）。 | Q1（角色提示词组装确定性）；执行前。 | L63-118 load_role_prompt；L129-133 组装；L134-149 dispatch 指令模板 |
| D-04 | `loop_core/role_orchestrator.py` | 上下文工程 | 阶段→角色映射表（S0-S11 共 12 阶段）+ build_dispatch_manifest（自动生成 SubagentManifest）。 | Q1（阶段-角色确定性）；执行前。 | L13-26 PHASE_ROLES；L32-66 build_dispatch_manifest |
| D-05 | `loop_core/subagent_manifest.py` | 上下文工程 | SubagentManifest 协议：SubagentSpec 自包含（prompt+input_files+expected_output_schema+max_parallel+timeout），validate() 校验完整性（9 项）。 | Q1（子代理 prompt 的自包含=无外部上下文猜测）；执行前。 | L10-16 设计原则；L35-60 SubagentSpec；L93-120 validate |
| D-06 | `loop_core/inbox.py` | 记忆服务/需求摄入 | 需求摄入：自然语言需求→结构化 Requirement；**CLARIFYING 状态 + clarification_questions 字段**（add_clarification_questions 将状态置 CLARIFYING）；需求≠任务（须经 Planner→用户批准→Gate）。 | **Q2 基础设施**（澄清问题被记录为状态）；执行前。 | L40-42 CLARIFYING；L62 clarification_questions；L159-163 add_clarification_questions；L13 约束说明 |
| D-07 | `loop_core/planner.py` | 上下文工程 | 计划生成：需求→任务图草稿（DRAFT 只读，须 plan-approval Gate 批准才注册）；TaskDraft 含 acceptance_criteria/suggested_roles/estimated_complexity；**clarification_needed 字段**。 | Q2（澄清需求标记）+ Q1（草稿须批准）；执行前。 | L57-75 TaskDraft/PlanDraft（clarification_needed L74）；L5-12 设计约束；L122-140 Planner |
| D-08 | `loop_core/intent_router.py` + `router.py` | 上下文工程 | 意图路由：关键词域检测（web/mobile/api/data/cli/ai_ml…）+ 风险分级（HIGH_RISK 自动升级 FULL 不可降级；置信度<0.5 升级；LIGHTWEIGHT 仅单文件/一次性）。 | **Q3 雏形**（风险变量自动识别=机器预判"用户没说的风险"）；执行前（模式分级）。 | L8-14 核心规则；L35-80 域关键词；L92-104 HIGH_RISK 关键词；L122-150 规模指标 |
| D-09 | `loop_core/knowledge_store.py` | 记忆服务 | 知识库：decision/lesson/pitfall/best_practice 四类结构化条目，按 task/gate/tag/关键词检索（上限 20），幂等写入（SHA-256 指纹去重），append-only。 | 执行后（沉淀）；Q2/Q4 的"经验供给"（相关经验供决策包）。 | L1-27 设计说明；L43-59 条目类型/来源/检索上限 |
| D-10 | `loop_core/memory_service.py` | 记忆服务 | 记忆提取/召回：extract_memories 从 gate-lessons + 验收报告确定性提取（无 LLM）→ knowledge store；recall 按任务/gate/标签检索（默认 5 条）；memories_to_context 渲染为记忆段供 context_loader 注入。 | 执行后（教训→记忆）；执行前（经验注入，默认关）；**"执行前简报-经验"要素的基础设施**。 | L1-24 数据流；L47-49 上限；L106-113 lesson→knowledge |
| D-11 | `loop_core/gate_feedback.py` | 记忆服务 | Gate 决策反馈：rejected/repair_requested 决策→结构化 lesson（append-only、幂等）；suggest_related_lessons 供 Human Review Packet 关联历史。 | **Q4 增强**（决策时给用户看相关历史教训）；执行后（沉淀）。 | L1-20 设计说明；L13-14 suggest_related_lessons；L44-47 DECISIONS |
| D-12 | `loop_core/human_review_packet.py`（1307 行） | 决策材料 | Human Review Packet 数据模型：KeyChoice（问题/方案A/方案B/为什么选A/为什么不选B/选错的风险——非技术语言）、RiskItem（风险+日常类比）、DecisionRequired（问题/选项/AI 推荐/截止时间）；U6 ResumePayload（暂停 gate 可机器恢复，状态漂移拒绝恢复=不编造）；U4 related_experience（历史教训注入）。 | **Q4 核心**（结构化多方案决策包）；执行后（解释）；U6=执行中断恢复。 | L1-24 定位；L45-77 KeyChoice/RiskItem/DecisionRequired；L79-101 ResumePayload/StateDriftError"机器从不猜测"；L19-23 related_experience |
| D-13 | `loop_core/retrospectives.py` | 记忆服务 | 复盘：根因分析+带 owner/deadline 的行动项（B2 §3.3）；幂等、append-only、行动项全 done 自动关闭；second_failure 门禁消费。 | 执行后（AI 侧复盘=学习回路，**但无用户参与验证**）。 | L1-26 设计说明；L67-80 ActionItem（owner/deadline） |
| D-14 | `loop_core/evals.py` | eval | Agent 行为评估栈：EvalCase（rule-first 断言：text_contains/text_matches/json_equals/exit_code；LLM judge 可选且永不阻断 SKIP）；EvalRunner→EvalReport→.ai/evidence/observability/eval-report.json。 | Q1（agent 行为质量的确定性评估）；执行后。 | L1-32 设计说明；L52-60 断言类型；L71-76 报告路径 |
| D-15 | `loop_core/llm/`（11 文件） | LLM 层 | 模型接入层：anthropic_driver（Messages API+SSE）、openai_driver、protocol_driver（统一接口）、output_policy（按 operation 限输出 token：router 4000/audit 8000/self-review 6000/summarize 2000/classify 1000）、json_repair、redaction（密钥脱敏）、retry、zcode_config、keys、errors。 | Q1（LLM 调用的确定性护栏：限长/修复/脱敏/重试）；执行中（self-audit 用）。 | output_policy.py L27-39 OUTPUT_TOKEN_CAPS；anthropic_driver.py L1-41（错误映射/脱敏）；loop_self_audit.py L55-74 内嵌 SYSTEM_PROMPT |
| D-16 | `loop_core/context_controller.py`（538 行） | 上下文工程 | 上下文控制（预算/加载策略控制器）。 | Q1；执行前。 | 实际读取（538 行） |
| D-17 | `loop_core/execution_ledger.py` + `audit_ledger.py` + `approval_ledger.py` | 记忆服务（账本） | 链式 hash 追加写账本：executions.jsonl（每行执行记录 chain_hash）；audit_ledger.jsonl（gate_advance/role_activate/veto/handoff 事件）；approval_ledger（批准记录 scope_hash 防范围蔓延、TTL 30 天）。 | **执行中记录层**（机器侧执行日志）；Q1（可审计=可验证"发生了什么"）。 | execution_ledger.py L1-14；audit_ledger.py L1-12；approval_ledger.py L1-20（scope_hash/防 creep） |
| D-18 | `loop_core/second_failure.py` / `slo_gate.py` / `contract_verifier.py` / `evidence_chain.py` / `guard_health.py` / `hard_constraints.py` / `security_scanner.py` / `static_analyzer.py` / `subagent_evidence_verifier.py` / `verdicts.py` / `governance_metrics.py` / `incidents.py` / `observability.py` / `enforcement_hub.py` / `runtime_controller.py` / `dispatcher.py` / `executor.py` / `task_queue.py` / `veto_escalation.py` / `design_reviewer.py` / `intent_router` 依赖链等 | 治理内核 | 门禁与内核：second_failure（同类失败复发未解决→阻断发布）、SLO 预算门、契约验证、证据链验证、guard health 自检、硬约束 C1-C9、安全扫描、静态分析、子代理证据真实性校验、运行时控制器（身份/能力授权）。 | Q1（机器确定性门禁）+ Q3（fail-closed=不猜）；执行中/后。 | second_failure.py L1-26；hard_constraints.py；runtime_controller.py；subagent_evidence_verifier.py |

**D 类小结**：loop_core 57 个 py + llm 11 个 py。上下文工程（D-01~D-05）把"角色该看什么"做成确定性装配；记忆服务（D-06~D-11、D-13、D-17）提供澄清/教训/账本的记录与回放；LLM 层（D-15）是自审计的模型接入（内嵌 SYSTEM_PROMPT 于 tools/loop_self_audit.py）。**核心缺口：无"执行偏离日志"结构化模块（known_deviations 只在 developer 输出里）、无盲点自检模块、无用户反向考察模块。**

---

## E. 工具层（tools/ + .zcode/tools/）

| 编号 | 路径 | 类型 | 功能摘要 | 四象限定位 | 证据 |
|---|---|---|---|---|---|
| E-01 | `tools/loop_self_audit.py` | 工具（eval） | 自审计运行器：validate_state+guard health+compile+pytest+security scan+static analysis → self-audit.json；--llm 时收集规则结果→脱敏摘要→LLM 语义分析（SYSTEM_PROMPT 内嵌：审计员角色+JSON 输出约束"不得编造摘要外的事实"）→ self-audit-llm.json；LLM 阶段永不阻断规则审计。 | **Q3 实践**（AI 审计自身=元层盲点检查）；执行后。 | L1-25 说明；L55-74 SYSTEM_PROMPT/USER_PROMPT_TEMPLATE；L15-18 fail-safe |
| E-02 | `tools/loop_onboard.py` | 工具 | 一键接入：创建 .ai 治理骨架（state/gates/task_graph/HANDOFF）、AGENTS.md、runtime controller 初始化、validate_state 确认。 | 执行前（项目级启动）。 | L1-14 用法；onboard() L27-35 |
| E-03 | `tools/loop_execute_phase.py` | 工具 | 阶段执行器：按 SubagentManifest 生成完整执行脚本（Agent 调用参数/重试策略/角色隔离验证），会话照脚本执行。 | 执行中（调度执行自动化）；Q1。 | L1-16；build_script L13-22 |
| E-04 | `tools/loop_dispatch_role.py` | 工具 | 角色派遣 CLI：prepare（role/task/phase/gate/prompt/路径）/complete/verify/list。 | 执行中（派遣留痕）。 | L1-10 用法 |
| E-05 | `tools/mcp_agent_runtime.py` + `tools/server.py` | 工具（MCP） | MCP 服务器：agent runtime 的 MCP 暴露（供主会话调用）。 | 执行中（工具通道）。 | 实际读取（36 个 tools/*.py 之一） |
| E-06 | `tools/tool_*.py` 系列（tool_inbox/tool_planner/tool_route_intent/tool_eval/tool_safe_bash/tool_quality_gates/tool_review_packet/tool_handoff/tool_veto_escalate/tool_task_queue/tool_evidence_submit/tool_security_scan/tool_dashboard/tool_execution_log/tool_cost_tracker 等约 30 个） | 工具（MCP 注册） | 治理能力工具化：每条能力一个 MCP 工具（意图路由/计划/需求/门禁/证据提交/安全扫描/审查包/交接/否决升级…），工具本身携带结构化参数 schema。 | Q1（能力-参数确定性=减少自然语言歧义）；执行中。 | tools/ 目录 36 个 py；tool_*.py 命名体系 |
| E-07 | `.zcode/tools/validate_state.py` | 工具（校验） | 状态校验器：state/gates/task_graph/HANDOFF 一致性 + 治理不变量（governance_invariant_errors）；loop-governance SKILL 启动检查必跑。 | Q1（状态确定性）；执行前/中/后。 | loop-governance/SKILL.md L32；validate_state.py L1-20 |
| E-08 | `.zcode/tools/audit_handoff.py` | 工具（校验） | HANDOFF 审计：13 个必需标题（Product Direction/Current Phase/Allowed Scope/Forbidden Scope/Evidence/Next Session First Step…）+ 模型校验；NO_ACTIVE_TASK 独立 [info] 态（exit 3）。 | Q1（交接确定性）；执行后。 | L16-24 REQUIRED_HEADINGS；L31-43 idle 稳态分流 |
| E-09 | `.zcode/tools/continuity_auditor.py` / `continuity_producer.py` / `repair_continuity.py` / `governor_lib.py` / `governance_action.py` / `authority_records.py` / `evidence_manifest.py` / `task_contract.py` / `transaction_registry.py` / `validation_runner.py` / `close_session.py` / `sync_plugin_cache.py` | 工具（连续性/校验） | 连续性保障：project_continuity.yaml 审计/生成/修复、权威记录、证据清单、任务合同、事务注册表、统一校验入口、会话关闭、插件缓存同步。 | Q1（状态机/连续性确定性）；执行前/后。 | .zcode/tools/ 15 个 py 实际读取（governor_lib 被 audit_handoff import） |

**E 类小结**：tools/ 36 + .zcode/tools/ 15 = 51 文件。工具层把治理能力参数化（Q1 确定性），loop_self_audit 是唯一 LLM 参与的工具（Q3 元审计）。**无"原型工具"（如 mock/prototype 生成）、无"偏离日志工具"、无"反向考察/测验生成工具"。**

---

## F. 文档与流程（docs/、AGENTS.md、USER-PROMPTS.md、.zcode/commands/）

| 编号 | 路径 | 类型 | 功能摘要 | 四象限定位 | 证据 |
|---|---|---|---|---|---|
| F-01 | `docs/07-phase-specification.md` | 文档流程 | 12 阶段权威规范（目标/入口/角色/强制产出/退出条件/人工评审点）+ **人工评审汇总表**（S1 必须/S2 必须/S4 无需机器已拦截/S5 必须/S6 必须 GO-NOGO…）。 | 执行前/中/后阶段定义；Q4（人工评审点=用户决策点清单）。 | L163-177 人工评审汇总表 |
| F-02 | `docs/01-requirements.md` / `02-architecture.md` / `03-interface-contract.md` / `06-delivery.md` | 文档流程 | 需求/架构/接口/交付四大权威文档（模板必填项的落地载体，content_guard 架构合规引用 02）。 | Q1（权威事实）。 | content_guard.py L112-120 引用 docs/02-architecture.md |
| F-03 | `docs/designs/loop-v4-ai-agent-governance.md` 等 3 篇 | 文档流程 | 设计文档（B1 eval 栈 §1、B2 learning loop §3 等的依据）。 | 元文档（设计依据）。 | evals.py L4 引用；retrospectives.py L1 引用 |
| F-04 | `AGENTS.md`（根） | 文档流程 | 项目级指令：涉及实现/评审/调试/设计/交接/状态变更→先调 loop-governance skill；启动 6 步（与 SKILL 一致）；边界清单（不装 skill/MCP/不碰生产/证据≠批准）。 | Q1 执行前（项目级强制启动流程）。 | L1-25 |
| F-05 | `USER-PROMPTS.md` | 决策材料 | **用户提示词模板**：给用户的"复制即用"短语（"批准 G-{id}"/"拒绝 G-{id}，原因是…"/"继续执行当前任务"/"当前状态是什么？有什么需要我决定的？"）+ "你永远不需要做的事"清单（不需要审查代码/不需要手动跑测试/不需要问'能不能这样做'（AI 会先判断并标注 [AI判断]））。 | **Q2/Q4 的用户侧配套**（教用户怎么与 AI 协作、怎么回答问题）；全阶段。 | L7-49 模板；L52-59 不需要做的事（L59 [AI判断]） |
| F-06 | `.zcode/commands/loop-onboard.md` / `loop-update.md` | 文档流程 | Slash 命令：一键接入/更新 Loop 治理（跑 loop_onboard.py，验证 state/角色 SKILL 安装）。 | 执行前（项目启动）。 | loop-onboard.md L1-27 |

**F 类小结**：docs/ 9 篇 + designs 3 篇 + AGENTS.md + USER-PROMPTS.md + 2 命令。人工评审点表（F-01）是四象限执行前/后的骨架；USER-PROMPTS.md 是罕见的"用户侧提示词"资产（方法论中"让用户知道怎么答"的配套）。

---

## G. .ai/ 数据层（状态/模式/知识/决策数据）

| 编号 | 路径 | 类型 | 功能摘要 | 四象限定位 | 证据 |
|---|---|---|---|---|---|
| G-01 | `.ai/state.yaml` | 决策材料/状态 | 权威状态：schema/phase/current_task/current_gate/loop_mode(FULL)/历史 notes（含"用户已批准继续"等决策轨迹）。 | 全象限的事实地基；执行前（session_brief 读它）。 | 实际读取（loop_mode: FULL，current_phase: S6-delivery，T-0103） |
| G-02 | `.ai/HANDOFF.md` | 决策材料/状态 | 跨会话连续性：Product Direction And Authority（allowed/forbidden effects、north_star"每个非技术用户都能借助 AI 交付可用软件"）+ 13 标题结构。 | 执行前（恢复简报）；执行后（交接）。 | 实际读取；audit_handoff.py L16-24 |
| G-03 | `.ai/inbox/REQ-*.yaml`（2 个） | 需求数据 | 结构化需求记录（requirement_id/title/type/priority/status/clarification_questions[]）。 | Q2 数据（澄清问题槽位存在但样例为空）。 | 实际读取（clarification_questions: []） |
| G-04 | `.ai/plans/PLAN-*.yaml`（2 个） | 计划数据 | 计划草稿（DRAFT，须批准）。 | 执行前（计划审批）。 | 实际读取 |
| G-05 | `.ai/knowledge/`（case_index/cases/cases.json/schemas） | 知识数据 | 知识案例库（context_packager 取前 3 条注入）。 | 执行前（经验供给）；Q3/Q4 参考。 | context_packager.py L57-65 |
| G-06 | `.ai/schemas/`（8 个） | 模式数据 | JSON Schema：gate-register/requirement/plan-draft/task-queue/dashboard/dispatch-runtime-contract/checker-result/runtime_quality。 | Q1（输出确定性=机器校验）。 | 实际读取（8 文件） |
| G-07 | `.ai/policies/tool-entry-restrictions.yaml` | 决策材料 | 工具准入策略：deployment/rollback/database/permission/secret/payment/production_data/migration/agents_md/runtime_tool/real_project_entry 均须单独 gate。 | Q1/Q4（高风险动作=单独用户决策门）。 | 实际读取（11 条 policy） |
| G-08 | `.ai/evidence/feedback/gate-lessons.yaml`（目录存在，当前为空）、`.ai/evidence/knowledge/knowledge-store.yaml` | 记忆数据 | 教训/知识落盘（gate_feedback/memory_service 的写目标）。 | 执行后（学习回路数据）。 | memory_service.py L6-13；knowledge-store.yaml 存在 |

---

## 资产总览表

| 资产类别 | 文件数（约） | 主要机制 | 四象限覆盖 |
|---|---|---|---|
| 角色提示词（agents/） | 55（12 角色×4 + 6 references + README） | 合同化约束（12 字段）、清单化验收、fresh context、known_blind_spots | Q1 强；Q2 中（PM 访谈澄清）；Q3 弱（仅 AI 侧盲点声明）；Q4 中（备选方案要求） |
| 技能模板（skills/ + .zcode/skills/） | 44 | 必填表单模板（30 个）、gate-request A/B/C 方案、Human Review Packet、Q2 教学示例、config（门槛/降级规则） | Q1 强；Q2 中（示例+澄清字段）；Q3 无；Q4 强（多方案模板）；执行前/后模板齐 |
| Hook 注入/拦截（hooks/） | 17 py + hooks.json | SessionStart 注入（状态摘要/模板/模式激活）×3；PreToolUse 拦截（gate/path/content/bash/ledger/role/enforcement）×7 | Q1 最强（机器强制）；Q4 有（用户决策权机器保证）；Q2/Q3 无钩子；执行中拦截强、执行前注入强 |
| 上下文工程（loop_core） | 10 | 渐进式加载、角色-上下文装配、SubagentSpec 自包含、意图路由分级 | Q1 强；Q3 中（风险自动分级）；执行前 |
| 记忆服务（loop_core） | 7+ | 知识库、记忆提取/召回、gate 教训、复盘、三账本 | Q2 中（澄清状态）；Q3 弱（教训事后补）；Q4 中（相关经验注入）；执行中/后 |
| LLM 层（loop_core/llm） | 11 | 双驱动、输出预算、JSON 修复、脱敏、重试 | Q1（护栏）；执行中（自审计用） |
| eval/审计（loop_core + tools） | 20+ | evals 栈、guard health、self-audit（LLM 语义分析）、硬约束 C1-C9、SLO/second-failure 门禁 | Q1 强；Q3 中（元审计）；执行后 |
| 工具层（tools/ + .zcode/tools/） | 51 | 能力参数化（MCP 工具约 30）、validate_state/audit_handoff/continuity 校验 | Q1 强；执行前/中/后都有校验工具 |
| 决策材料 | 10+ | gate-request、Human Review Packet（KeyChoice/DecisionRequired/ResumePayload）、USER-PROMPTS、role-conflict 协议、人工评审点表 | Q4 强；Q2 用户侧配套；执行后解释强、反向考察无 |
| 文档流程 | 15+ | 12 阶段规范、启动检查、AGENTS.md 边界、工具准入策略 | Q1 强；Q4（评审点=用户决策点） |
| .ai 数据层 | 20+ | state/HANDOFF/schemas/policies/knowledge/inbox/plans | 全象限事实地基 |

**总盘点**：约 290+ 文件（agents 55 + 技能模板 44 + hooks 17 + loop_core 67 + tools 51 + 文档 15 + .ai 数据 20+ 决策材料 10+）。核心哲学是"**机器强制 + 必填表单 + 用户决策门**"：Q1（已知的已知→直接执行不猜测）覆盖最厚，Q4（多方案+用户选择）有完整的 gate-request/Human Review Packet 机制，Q2（澄清问答）有基础设施但缺连续追问闭环，Q3（盲点自检）只有 AI 侧盲点声明、无开工前自检步骤。
