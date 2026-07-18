你正在继续 T-0034 设计返修。

Project root:
C:\Users\Administrator\.codex\loop-engine-lab

Task:
T-0034 — Project Continuity, Controller Hierarchy, Neutral Audit, And Loop Assurance Design

Governing gate:
G-T-0034-DESIGN-PROJECT-CONTINUITY-CONTROLLER-HIERARCHY-LOOP-ASSURANCE

当前 L0 主控复核结论：
REPAIR_REQUIRED

本轮精确 finding：
requirements revision, authority separation, in-flight rebase safety, and result freshness protocol incomplete

一、当前结论

上一轮已经基本完成 Loop-wide Control-Plane Assurance Kernel、通用 Envelope、四层 Assurance、controller generation、single-active lease、split-brain、blocker/liveness、AssuranceProfile、成本与用户负担、证据生命周期、风险登记、Kernel-wide checks、acceptance、adversarial tests，以及 handoff-finalization specialization。

这些设计必须保留，不得退回局部 handoff-finalization patch。

但导致本项目真实发生偏移的机制性缺口仍未完整解决：执行会话绑定旧需求快照运行期间，用户向 L0 增加了对当前任务有约束力的新要求；L0 没有中断执行会话；旧结果在旧 revision 下局部正确，但相对于最新要求已经 stale，不能成为 task-level PASS。

本轮必须补齐 Requirements Revision, Delta, Rebase And Result Freshness Protocol，并强化 requirement authority、persistence、impact proof、安全中断点和防 perpetual rebase。

二、启动与只读检查

使用 $project-governor，以 UTF-8 独立读取：

1. .ai/state.yaml
2. .ai/HANDOFF.md
3. .ai/tasks/T-0034.md
4. .ai/gates.yaml 中精确 T-0034 gate
5. .ai/task_graph.yaml 中 T-0034
6. .ai/evidence/T-0034/current-main-controller-handoff.v0.1.md
7. .ai/evidence/T-0034/handoff-writing-standard.v0.1.md
8. .ai/evidence/T-0034/session-design-synthesis.v0.1.md
9. .ai/evidence/T-0034/project-continuity-controller-assurance.decision-packet.v0.1.md
10. .ai/evidence/T-0034/downstream-program-plan.v0.1.md

运行：

C:\Python312\python.exe C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab

C:\Python312\python.exe C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py C:\Users\Administrator\.codex\loop-engine-lab

预期两个命令均返回 2，且只报告 T-0002、T-0004、T-0005、T-0007、T-0009、T-0028。

若出现 pending gate、新错误、HANDOFF mismatch、baseline hash 变化、下游任务、active transaction、in-flight agent、候选安装或激活、runtime behavior change，立即停止并报告 BLOCKED 或 SCOPE_VIOLATION。

本轮保持 read_only，不得写入任何项目文件。

三、Requirement input、delta 和授权必须分离

必须明确区分：

1. observed requirement input

用户在聊天或其他入口表达的新要求。它可以成为 L0 观察到的业务输入，但在尚未持久化和确认前，不能伪称为 canonical requirement revision。

2. RequirementDeltaEnvelope

L0 可以把 observed input 结构化为 delta proposal，并进行 impact analysis；但 RequirementDeltaEnvelope 只是 evidence/change proposal，不自动获得 scope 扩展、风险接受、effect authorization、写入、中断、取消或 commit 权力。

3. committed requirement revision

只有经过适用的明确用户决定和授权持久化动作，才能成为 canonical requirement baseline。

4. execution/rebase decision

涉及 scope、authority、acceptance、成本、不可逆动作、风险接受或业务取舍时，必须进入 USER_DECISION_REQUIRED。L0 和 Kernel 不得把模糊业务表达自行扩写为新授权。

纯拼写、排版或经确定性证明无语义影响的澄清，可以进入 no-impact fast path。

四、必须区分 revision 身份

至少定义：

- observed_requirements_revision_id
- committed_requirements_revision_id
- execution_bound_requirements_revision_id
- latest_known_requirements_revision_id

同时定义：

- observed_requirement_delta_ids
- persisted_requirement_delta_ids
- unpersisted_requirement_delta_ids
- requirements_checkpoint_id
- requirements_checkpoint_hash
- authorization_revision_id
- acceptance_revision_id
- input_contract_hash
- requirement_coverage_ref

必须说明“最新需求”在每一种上下文中究竟指 observed、persisted evidence、committed baseline、execution-bound revision 还是 latest-known revision，禁止混用。

五、Common Envelope 合同

所有消费任务要求的 Envelope 必须根据用途携带：

- requirements_revision_id
- requirements_checkpoint_id
- requirements_checkpoint_hash
- requirement_ids
- covered_requirement_ids
- requirement_coverage_ref
- requirements_parent_revision_id
- requirements_observed_at
- latest_known_requirements_revision_id
- requirements_freshness_status
- authorization_revision_id
- acceptance_revision_id
- input_contract_hash
- known_unconsumed_deltas

说明哪些字段对所有 Envelope 必填，哪些只对 Task、Execution、Verification、Audit、Repair、Closeout、Handoff 和 UserDecision 必填。

Requirement hash 必须基于语义规范化模型，避免 Markdown 排版、空白、字段顺序等无关变化制造 false stale。语义变化、格式变化、拆分、合并、撤销、替代和 supersession 必须有确定规则。

六、新增 Envelope 类型

保留已有 Envelope，并至少增加：

1. RequirementBaselineEnvelope

表示 canonical、版本化的任务需求快照，绑定用户目标、稳定 requirement IDs、acceptance criteria、allowed/forbidden scope、authorization、non-goals、risk classification、cost policy 和 parent revision。

2. RequirementDeltaEnvelope

至少包含：delta_id、from_revision_id、proposed_to_revision_id、changed_requirement_ids、change_type、change_source、explicit_user_evidence、affects_current_task、affects_in_flight_execution、affects_acceptance、affects_authority、affects_risk、affects_recovery、urgency、proposed_rebase_policy、persistence_status、created_at、canonical hash。

3. ExecutionRebaseDecisionEnvelope

由 L0 准备，并由适用用户授权确认后选择：

- INTERRUPT_AND_REBASE
- QUEUE_AND_REBASE
- CONTINUE_OLD_REVISION_LOCAL_SLICE_ONLY
- ACCEPT_AS_SEPARATE_FOLLOW_UP
- CANCEL_AND_SUPERSEDE
- NO_IMPACT_CONTINUE

必须绑定 execution ID、old/new revision、delta、impact evidence、decision authority、safe point、permitted effects、forbidden effects、old result disposition、rebase checkpoint 和 next safe action。

Kernel 只能验证该 decision，不得替用户作业务取舍。

七、Persistence 与 requirement commit 必须分开

状态至少明确区分：

delta_observed
-> delta_persisted_as_evidence
-> impact_assessing
-> impact_assessed
-> revision_authorization_pending
-> revision_committed
-> consumers_notified
-> old_results_reconciled
-> closed

RequirementDeltaEnvelope 落盘只证明观察到了变化，不代表新 revision 已成为 canonical requirement baseline。

侧状态至少包括：

- unpersisted_requirement_delta
- impact_uncertain
- stale_requirements
- rebase_required
- queued_for_rebase
- interrupt_required
- user_decision_required
- blocked
- superseded
- cancelled
- timeout
- notification_failed
- rebase_failed
- emergency_recovery

每个 blocker 必须包含 owner、evidence、release condition、timeout、retry、cancel、recovery、user escalation 和 checkpoint regeneration。

八、NO_IMPACT_CONTINUE 必须可证明

不能由 L0 主观声明 no-impact。至少必须证明 delta 不改变：

- 当前 slice 输入；
- acceptance criteria；
- allowed/forbidden scope；
- authorization 和 declared effects；
- architecture、安全或风险等级；
- task-level coverage claims；
- rollback/recovery 要求；
- cost ceiling 或用户业务取舍。

证据不足时必须返回 IMPACT_UNCERTAIN 或 USER_DECISION_REQUIRED，不能默认 no-impact。

九、In-flight execution 与安全点

INTERRUPT_AND_REBASE 不等于立即强杀。

必须设计：

- 当前操作是否可安全停止；
- 是否正在原子写入或不可中断阶段；
- partial/untrusted writes 如何登记；
- controller lease 是否仍有效；
- execution checkpoint 如何生成；
- old result 如何标记和封存；
- rebase 从哪个 checkpoint 开始；
- interrupt timeout；
- timeout 后的 recovery；
- cancel 与 rollback 是否需要独立授权。

如果不能证明安全停止，应进入 SAFE_POINT_PENDING、RECOVERY_REQUIRED 或 USER_DECISION_REQUIRED，而不是强制终止。

十、运行中需求变化策略

NO_IMPACT_CONTINUE：仅适用于有确定性证据的无语义变化。

INTERRUPT_AND_REBASE：适用于 scope、authority、业务目标、安全边界或风险发生变化，继续运行会产生不可接受结果，或用户明确要求立即切换。

QUEUE_AND_REBASE：适用于不打断执行，但新要求影响 task-level acceptance。旧执行可以完成并成为 evidence，但不能成为 TASK_REQUIREMENTS_PASS。

ACCEPT_AS_SEPARATE_FOLLOW_UP：只有用户明确确认新要求不属于当前 task acceptance 时才允许。AI 不得为避免返修自行推到 T-0035 或其他下游任务。

CANCEL_AND_SUPERSEDE：用于用户撤销或替换目标，或者继续执行风险不可接受。

必须把本项目事件作为 worked example：原执行会话执行 handoff-finalization；用户向 L0 新增 Loop-wide Kernel 要求；L0 不打断；旧结果最多为 LOCAL_SLICE_PASS；相对于最新要求为 REBASE_REQUIRED；不能判定 TASK_REQUIREMENTS_PASS。

十一、Result freshness 必须是复合判断

不能只比较 revision ID。必须比较：

- requirements checkpoint hash；
- covered requirement IDs；
- delta impact classification；
- authorization revision；
- acceptance revision；
- input contract hash；
- execution checkpoint；
- unconsumed deltas；
- delta 是否影响 result claims；
- latest committed revision；
- latest observed but uncommitted input。

ExecutionResultEnvelope、VerificationEnvelope、AuditEnvelope、RepairEnvelope 和 CloseoutEnvelope 必须回显执行绑定 revision、latest observed/committed revision、coverage reference、known deltas 和 freshness verdict。

L0 或 deterministic ingestion 必须独立读取 canonical facts，输出：

- CURRENT_REQUIREMENTS
- STALE_REQUIREMENTS
- REBASE_REQUIRED
- SUPERSEDED_REQUIREMENTS
- UNPERSISTED_REQUIREMENT_DELTA
- REQUIREMENT_BASELINE_MISSING
- REQUIREMENT_CONFLICT
- IMPACT_UNCERTAIN
- USER_DECISION_REQUIRED
- BLOCKED

执行会话不得自行宣布自己的 revision 仍然最新。

十二、PASS 语义严格分层

LOCAL_SLICE_PASS：只证明旧 revision 下已执行 slice 的局部 claims，可以作为 evidence，不代表整个 task 当前要求满足。

TASK_REQUIREMENTS_PASS：证明当前 committed revision 的全部适用 requirements 均被覆盖，没有 blocking unconsumed delta，verification/audit 与当前 revision 对齐；仍不代表用户验收。

USER_ACCEPTED：只能来自明确用户决定，Kernel、L0、tests、validator、review、audit 和 AI 都不能生成。

TASK_CLOSED：canonical closeout transaction 已 commit，不能由任何 PASS 自动推导。

十三、防止 perpetual rebase

必须加入：

- delta batching window；
- semantic-equivalent delta merge；
- clarification-only fast path；
- maximum rebase count；
- maximum queued delta count；
- no-progress detection；
- rebase wait timeout；
- 明确 local-slice freeze；
- 超限后的 USER_DECISION_REQUIRED；
- 用户可 cancel、supersede 或明确接受 local-slice evidence。

不得因需求频繁变化而无限重启执行或形成治理自循环。

十四、未持久化需求

定义 UNPERSISTED_REQUIREMENT_DELTA：用户要求已进入 L0 会话，但 L0 当前 read_only，因此尚未成为 canonical disk requirement。

规则：

- 聊天中的明确用户要求可以成为 L0 review 输入；
- 不能伪称其已成为 committed revision；
- 必须阻止旧结果获得 TASK_REQUIREMENTS_PASS；
- 可以生成精确 persistence proposal；
- 只有明确授权的持久化动作才能生成新的 canonical requirement revision；
- 换会话前必须在 HANDOFF 中列出 unpersisted inputs、影响和 next reconciliation action；
- successor 必须独立恢复，不能只读取旧 baseline。

十五、Handoff continuity

HandoffEnvelope 和未来 HANDOFF projection 必须包含：

- observed_requirements_revision_id
- committed_requirements_revision_id
- execution_bound_requirements_revision_id
- latest_known_requirements_revision_id
- active_requirements_checkpoint_hash
- unpersisted_requirement_deltas
- persisted_uncommitted_deltas
- unconsumed_requirement_deltas
- in_flight_execution_revision
- safe_point_status
- rebase_required
- stale_results
- requirement_conflicts
- next requirement reconciliation action

Successor probe 必须验证这些字段，而不只是 task/gate/controller 状态。

十六、Machine checks、风险和攻击测试

至少增加：

- K-REQ-ID-001
- K-REQ-REV-001
- K-REQ-HASH-001
- K-REQ-DELTA-001
- K-REQ-PERSIST-001
- K-REQ-AUTH-001
- K-REQ-IMPACT-001
- K-REQ-SAFEPOINT-001
- K-REQ-REBASE-001
- K-REQ-STALE-001
- K-REQ-INGEST-001
- K-REQ-COVERAGE-001
- K-REQ-UNPERSISTED-001
- K-REQ-HANDOFF-001
- K-REQ-COMPLETE-001
- K-REQ-NOPROGRESS-001

攻击测试至少覆盖：执行启动后新增 acceptance 要求；旧结果自称完整 PASS；缺失或伪造 revision；delta 只存在于聊天；新 successor 只读旧 baseline；格式变化 false stale；语义变化伪装格式变化；scope 或 authority 变化后旧执行继续；强制中断破坏原子操作；并发 delta 分叉；delta 在 verification 后 closeout 前到达；auditor 使用旧 revision；AI 擅自推迟到下游任务；旧 coverage 全绿但最新 revision 缺口；USER_ACCEPTED 从 task PASS 错误推导；stale result 用于安装、激活或 handoff；queued rebase 永久不执行；delta/rebase 无限循环。

风险登记必须增加 asymmetric session context、stale requirement baseline、unpersisted user requirement、incorrect no-impact classification、unsafe interruption、perpetual rebase、delta explosion、false-current classification、unauthorized follow-up deferral、cross-session requirement loss。每项给出 mitigation、residual risk、machine check 和 user decision boundary。

十七、Coverage Matrix

更新 requirement IDs，覆盖本提示词全部要求，并重新计算 summary。不得继续声称原 60 项覆盖全部最新要求。

Coverage 必须标明 design section、status、evidence、residual risk、downstream dependency 和 user decision needed。

十八、Additive evidence 结构

当前两份 Kernel 文件尚未写入。不要写入任何文件。

下一版提案应明确采用三份 create-new additive evidence：

1. .ai/evidence/T-0034/control-plane-assurance-kernel.design-addendum.v0.1.md

保存 Kernel 总体架构，并引用 requirements revision protocol。

2. .ai/evidence/T-0034/control-plane-assurance-kernel.coverage-matrix.v0.1.md

保存完整 coverage matrix，包括 requirements drift requirements。

3. .ai/evidence/T-0034/control-plane-assurance-kernel.requirements-revision-protocol.v0.1.md

独立保存 requirements revision、delta、authority、persistence、impact、safe point、rebase、freshness、completion states、checks、tests 和本项目 worked example。

三份文件都只是 proposed paths，当前不得创建。

你必须输出三份文件的完整 create-new unified diff，不得只给增量片段。三份文件必须相互引用，并保持共同字段、状态、verdict 和 requirement IDs 一致。

十九、必须重新输出

1. 修订后的完整设计；
2. 上一版提案的保留/修改/新增摘要；
3. 三份 create-new 文件的完整 unified diff；
4. 完整 coverage matrix 和新 summary；
5. requirement authority/revision 状态机；
6. safe-point interrupt/rebase 设计；
7. result freshness reconciliation；
8. PASS 分层；
9. perpetual-rebase 防护；
10. 更新后的风险登记；
11. 更新后的 machine checks；
12. acceptance criteria；
13. adversarial tests；
14. 当前 T-0034 偏移事件 worked example；
15. changed-path baseline；
16. UTF-8 写入后验证计划；
17. rollback/recovery 计划；
18. 风险说明。

UTF-8 验证计划必须包含：

- 严格 UTF-8 回读；
- 验证文件存在非 ASCII 高位字节；
- 检查中文区域未出现大规模 ASCII 0x3F 替换；
- 检查 Unicode replacement character U+FFFD；
- 计算 SHA-256；
- 验证 changed paths 恰好为批准的新文件。

二十、禁止范围

当前不得写入任何文件。

不得修改 .ai/HANDOFF.md、.ai/state.yaml、.ai/tasks/T-0034.md、.ai/task_graph.yaml、.ai/gates.yaml、任何现有 T-0034 v0.1 evidence、T-0033 candidate 或全局 Project Governor。

不得创建 T-0035～T-0050；不得修复六项历史 mismatch；不得调用或启用 agent、automation、Loop、skill、MCP、plugin、hook 或 runtime；不得安装、激活、部署或进入真实项目；不得把设计、validator、audit 或 coverage PASS 当作 user acceptance。

二十一、通过标准

只有满足以下全部条件，L0 才会考虑批准 additive evidence 写入：

- Kernel 主体完整保留；
- observed、persisted、committed、execution-bound、latest-known revision 身份不混淆；
- Requirement Delta 不自动获得授权；
- persistence 与 revision commit 分离；
- NO_IMPACT_CONTINUE 有可审计证明；
- IMPACT_UNCERTAIN 和 USER_DECISION_REQUIRED 边界明确；
- in-flight interrupt 使用安全点，不进行盲目强杀；
- result freshness 使用复合判断；
- LOCAL_SLICE_PASS、TASK_REQUIREMENTS_PASS、USER_ACCEPTED、TASK_CLOSED 严格分离；
- perpetual rebase 有预算、no-progress 和用户升级；
- unpersisted requirement 和跨会话 continuity 完整；
- 三份 proposed evidence 的完整 unified diff 一致；
- coverage、checks、tests 覆盖本次真实偏移；
- UTF-8 写入验证计划能够防止再次出现 ASCII 问号损坏；
- 不扩大权限、不创建下游任务、不写入磁盘。

二十二、接口级收口条款（最高优先级）

本节是对前文的强制收口。若本节与前文存在字段名、角色、状态、授权、输出方式或通过标准冲突，以本节为准。修订后的三份 proposed evidence 和 coverage matrix 必须吸收本节，不得仅在回复正文中解释。

22.1 消除 requirements_revision_id 歧义

不得继续使用含义不明的 requirements_revision_id 公共别名。所有 schema、示例、checks、tests 和 coverage 必须使用完整身份字段：

- observed_requirements_revision_id
- committed_requirements_revision_id
- execution_bound_requirements_revision_id
- latest_known_requirements_revision_id

TaskEnvelope 必须明确绑定 committed_requirements_revision_id。ExecutionResultEnvelope、VerificationEnvelope、AuditEnvelope、RepairEnvelope 和 CloseoutEnvelope 必须明确绑定 execution_bound_requirements_revision_id。其他 revision 不得被简写或替代。

22.2 Requirement Revision 角色与职责分离

至少区分：

- Requirement Observer / Classifier：观察用户输入、建立候选 delta，不得 commit revision；
- Impact Assessor：评估 scope、acceptance、authority、risk、cost、recovery 和 in-flight execution 影响；
- User Decision Authority：对业务取舍、scope、acceptance、authority、风险接受和高风险 effect 作出明确决定；
- Requirement Revision Finalizer / Registrar：只执行精确授权的 create-new/registry transaction，分配或确认 committed revision，不得修改 requirement 内容、扩大 scope 或替用户决定；
- Result Freshness Reconciler：独立比较 result、committed revision、observed input 和 unconsumed delta，不得仅接受 producer 或 finalizer 的自我声明。

L0 可以准备 proposal、impact analysis 和 decision packet，但不得把自己的分类或建议当成用户授权。对于会改变 canonical revision 或 result eligibility 的 transaction，必须明确 finalizer 与 freshness reconciler 的独立复核边界。

22.3 Safe-point acknowledgment 与 generation fencing

安全中断和 rebase 协议必须包含：

rebase_requested
-> consumer_acknowledged
-> safe_point_pending
-> safe_point_reached
-> execution_generation_fenced
-> rebase_checkpoint_committed
-> successor_execution_admitted

必须定义每个状态的 owner、evidence、timeout、retry、cancel 和 recovery。

在 execution_generation_fenced 之后：

- 旧 execution generation 的任何 canonical state 写入、task-level result commit、closeout、installation/activation eligibility 或 controller ownership 变更必须被确定性拒绝；
- 旧 generation 后续输出只能作为绑定旧 revision 的 immutable evidence；
- 任何 late result 必须标记 OLD_GENERATION_EVIDENCE 或 STALE_REQUIREMENTS；
- successor execution 只有在 rebase checkpoint committed 且授权、lease 和 generation preconditions 满足后才能 admitted。

如果 consumer 未 acknowledgment、无法到达安全点或 fencing 失败，必须进入 SAFE_POINT_TIMEOUT、FENCE_FAILED、RECOVERY_REQUIRED 或 USER_DECISION_REQUIRED，不能假定中断成功。

22.4 Delta candidate ID 与 committed revision ID 分离

RequirementDeltaEnvelope 中不得使用 proposed_to_revision_id。改用 proposed_revision_candidate_id。

该字段只表示候选标识，不表示 canonical revision 已分配、授权或 commit。

committed_requirements_revision_id 只能由精确授权的 Requirement Revision Finalizer / Registrar transaction 分配或确认。RequirementDeltaEnvelope、Impact Assessor、执行者、reviewer、auditor 和 Kernel 均不得预先宣称候选 revision 已成为 canonical。

22.5 Requirement 双重 hash 绑定

所有 requirement baseline、delta 和 revision commit 必须同时记录：

- source_content_hash：原始用户输入、持久化 artifact 或 canonical source bytes 的 hash；
- semantic_model_hash：规范化 requirement model 的 hash；
- normalization_policy_id：版本化规范化政策；
- normalization_trace_ref：source-to-model 映射和丢失信息记录。

判断规则：

- source_content_hash 变化但 semantic_model_hash 不变：只能作为 formatting-only candidate，仍必须验证 normalization trace；
- semantic_model_hash 变化：视为语义 delta，进入 impact assessment；
- normalization_policy_id 变化：不得直接比较旧新 semantic hash，必须重新规范化并验证历史兼容；
- normalization trace 缺失、不完整或存在信息丢失争议：返回 IMPACT_UNCERTAIN 或 BLOCKED；
- hash 只能证明内容绑定，不能证明用户身份、授权或不可抵赖性。

22.6 Gate batching 与用户负担

不得默认每个 RequirementDeltaEnvelope、每句话或每次 evidence persistence 都需要一个新用户 gate。

以下事项可在现有精确 transaction policy 覆盖且不改变语义、scope、authority、acceptance、risk 或 declared effects 时批量处理：纯 evidence persistence、formatting-only delta、clarification-only fast path、已授权 task scope 内的确定性 requirement projection，以及多个相关 delta 的 batching 和一次性 impact review。

以下变化始终需要新的明确用户决定：scope 扩大或缩小；acceptance criteria 改变；authority、authorization revision 或 declared effects 改变；风险接受、业务目标或关键取舍；cost ceiling 显著变化；cancel、supersede 或 follow-up boundary；implementation、installation、activation、deployment、migration 或 real-project effect。

必须定义 batching window、batch identity、included delta IDs、排除规则、失效条件和用户可理解的决策摘要，避免 gate explosion。

22.7 输出预算与完整性 fail-safe

开始生成三份完整 proposed unified diff 前，必须执行 context/output admission，评估当前剩余 context/token、三份文件预计长度、coverage/risk/checks/tests/baseline/validation/recovery 输出预算，以及最终一致性检查和 closeout reserve。

若无法在当前回复中完整输出三份可独立应用的 create-new unified diff，并保留最终一致性检查余量，必须返回 OUTPUT_BUDGET_INSUFFICIENT，然后停止，不得输出被截断、不可应用或无法独立验证的部分 diff。

不得使用“其余类似”“省略部分”“见前文”“后续补充”等方式替代完整文件内容。回复中的设计说明应尽量引用 proposed file content，避免在 diff 外重复全文。每份 diff 后必须报告预计行数、终止标记、内容 hash 计算计划和 cross-file reference 检查结果。

22.8 Requirement conflict resolution

对于 REQUIREMENT_CONFLICT，必须输出：

- conflicting_requirement_ids
- conflicting_revision_ids
- precedence_evidence
- simultaneous_satisfaction_possible
- supersession_proven
- latest_explicit_user_instruction_ref
- user_decision_needed
- blocked_effects
- safe_local_work_allowed
- next_safe_action

用户最新明确指令只有在可以证明其意图是 supersede 旧要求时，才能替代旧要求。时间更新不自动等于 supersession。若两条要求互斥、优先级证据不足、业务取舍不明确或同时满足不可证明，必须进入 USER_DECISION_REQUIRED，并阻止受影响 effects。

22.9 Queued rebase 强制消费点

只要存在影响 task-level acceptance、scope、authority、risk、recovery 或 result claims 的 queued_for_rebase、blocking unconsumed delta、UNPERSISTED_REQUIREMENT_DELTA 或 REQUIREMENT_CONFLICT：

- CloseoutEnvelope 必须被 machine check 阻止；
- TASK_REQUIREMENTS_PASS 必须被阻止；
- installation、activation、handoff finalization 和 real-project eligibility 不得引用该结果；
- 只能保留明确绑定旧 revision 的 LOCAL_SLICE_PASS evidence；
- 必须输出 queue owner、消费 deadline、rebase checkpoint、阻止的 effects 和 next safe action。

只有当 queued delta 被正式消费、判定 no-impact 且证据充分、被用户明确拆分为独立 follow-up，或被合法 cancel/supersede 后，closeout 阻塞才能解除。

22.10 新增 machine checks 与 adversarial tests

至少新增：

- K-REQ-FIELD-SEMANTICS-001
- K-REQ-ROLE-SEPARATION-001
- K-REQ-REVISION-FINALIZER-001
- K-REQ-SAFEPOINT-ACK-001
- K-REQ-GENERATION-FENCE-001
- K-REQ-CANDIDATE-ID-001
- K-REQ-DUAL-HASH-001
- K-REQ-NORMALIZATION-TRACE-001
- K-REQ-GATE-BATCH-001
- K-OUTPUT-ADMISSION-001
- K-REQ-CONFLICT-001
- K-REQ-QUEUE-CLOSEOUT-BLOCK-001

Adversarial tests 至少增加：含义不明的 requirements_revision_id 被不同 consumer 解释为不同 revision；L0 同时分类、提交和验证自己的 revision；旧 generation 在 fence 后提交 task PASS；candidate ID 被伪装成 committed ID；normalization bug 隐藏语义变化；每个澄清触发独立 gate；三份 diff 在输出末尾被截断；最新消息被错误视为自动 supersession；blocking queued rebase 未消费但 CloseoutEnvelope 仍 PASS。

22.11 修订输出要求

修订后的三份 proposed evidence、coverage matrix、risk register、machine checks、acceptance criteria 和 adversarial tests 必须完整吸收 22.1 至 22.10。

Coverage matrix 必须为本节每项建立稳定 requirement ID，并重新计算 coverage summary。不得仅在回复正文声明“已考虑”，也不得把本节推迟到 T-0035 或其他下游任务。

二十三、最终通过标准补充

除前文全部通过条件外，还必须满足：

- 不存在含义不明的 requirements_revision_id；
- revision observer、assessor、user authority、finalizer 和 freshness reconciler 职责分离；
- safe-point acknowledgment 和 generation fencing 可确定性验证；
- candidate revision ID 与 committed revision ID 不混淆；
- source hash、semantic hash、normalization policy 和 trace 完整；
- gate batching 降低用户负担且不吞掉真实用户决定；
- 输出预算不足时 fail closed，不产生部分 diff；
- requirement conflict 有可审计 resolution contract；
- blocking queued rebase 必须阻止 task PASS 和 closeout；
- 所有新增 checks、tests 和 coverage 项均已进入三份完整 proposed diff。

完成后停止。不要再次请求批准旧版 diff，等待 L0 对修订后的完整 proposed diff 进行复核。

