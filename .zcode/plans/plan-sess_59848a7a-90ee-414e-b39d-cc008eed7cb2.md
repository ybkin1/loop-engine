# 目标

可以做到，但“全面超越 Qoder”不能用文档数量或测试数量证明，必须定义可验收的超越标准，并通过真实软件工程垂直切片、宿主级拦截、独立角色执行和反向缺陷挑战证明。

目标不是复制 Qoder，而是形成：

```text
Qoder 的干净 Core 模型
+ ZCode 的真实工具入口控制
+ 更严格的 Gate/Approval/Role/证据闭环
+ 真正可运行的 Agent 调度
+ 可审计的交付、回滚和运维
+ 多宿主能力分级
```

当前基线已经发现一个治理阻塞：

```text
validate_state.py 当前因 current_task_id=null 尝试读取 .ai/tasks/None.md 而异常退出
```

因此第一阶段必须先修复状态校验和基线可信度，不能在无效状态上继续宣布完成。

---

# 一、先定义“超越 Qoder”的验收维度

最终比较不能只看代码量，建立 12 个硬指标：

1. **真实强制性**：所有声明为 STRONG 的宿主必须通过真实 Write/Edit/ApplyPatch/Bash/命令绕过矩阵；不能通过的宿主明确标记 MEDIUM 或 ADVISORY。
2. **真实 Agent 执行**：生产路径禁止模拟角色输出；真实 Agent 不可用只能 BLOCKED。
3. **角色独立性**：Developer、Reviewer、Security、Quality 使用可审计的独立 actor/session/input snapshot/write scope。
4. **Approval 闭环**：只有真实用户 approval record 能推进敏感 Gate，AI、测试、reviewer、validator 不能替代。
5. **证据可信度**：证据绑定完整输入版本、代码 fingerprint、命令、环境、退出码、actor、权限、时间、因果父证据和 freshness。
6. **状态一致性**：Schema、代码、文档、注册表、运行时状态只有一个权威来源，并自动生成派生文档。
7. **质量门禁真实性**：lint/test/typecheck/build/coverage/security/performance/deploy 的失败不能被 fallback、日志污染或错误解析吞掉。
8. **安全完整性**：路径穿越、符号链接、TOCTOU、命令注入、脚本间接写入、依赖风险、密钥泄露、权限越界均有可复现测试。
9. **阶段完整性**：需求、架构、详细设计、实现、单测、集成、功能、修复、性能、交付、维护有明确 Gate 和回环。
10. **交付能力**：安装、升级、迁移、回滚、监控、日志、健康检查、运维交接有真实演练。
11. **成本效率**：通过风险路由、证据复用、增量验证、失败短路和返工统计降低总交付成本，而不是只降低单轮 token。
12. **用户可理解性**：非技术用户只看到目标、风险、决策包、阻塞原因和下一步，不要求审核代码。

“超越”必须以矩阵和证据包证明，不以角色报告自评证明。

---

# 二、目标架构：四层、一个权威协议、一个控制入口

```text
┌──────────────────────────────────────────────┐
│ Product & Human Decision Layer               │
│ 目标、范围、业务取舍、风险接受、Gate 决策     │
└──────────────────────────────────────────────┘
                     │
┌──────────────────────────────────────────────┐
│ Loop Core Protocol                           │
│ Project / Intent / Task / Phase / Role       │
│ Gate / Approval / Evidence / Handoff         │
│ Certification / Freshness / Cost / Risk      │
└──────────────────────────────────────────────┘
                     │
┌──────────────────────────────────────────────┐
│ Runtime Controller                           │
│ tool policy / path guard / command guard     │
│ actor scope / gate enforcement / audit       │
│ process sandbox / timeout / transaction      │
└──────────────────────────────────────────────┘
                     │
┌──────────────────────────────────────────────┐
│ Host Adapters                                │
│ ZCode Hooks / MCP / CLI / Claude / Qoder     │
└──────────────────────────────────────────────┘
```

核心原则：

- 所有 Write/Edit/Bash/MCP/CLI/executor/evidence/state transition 进入同一个 Runtime Controller；
- Hook 只是一个宿主入口，不是唯一安全边界；
- Core 不依赖某个宿主；
- Host 能力不足时绝不伪装成强制；
- 生产模式和 test fixture 模式分离，fixture 不能生成生产 PASS。

建议将当前 Python/YAML/Markdown 分散规则收敛成版本化协议：

```text
loop_protocol/
  schemas/
  domain/
  state/
  gates/
  roles/
  evidence/
  approvals/
  handoff/
  migrations/

runtime/
  controller.py
  policy_engine.py
  actor_scope.py
  command_guard.py
  transaction.py
  audit.py

adapters/
  zcode.py
  qoder.py
  claude.py
  standalone.py
```

不要求一次性重写；先建立 canonical schema 和 compatibility adapter，再逐步迁移旧文件。

---

# 三、P0 根修复顺序

## P0-1：恢复治理状态可信度

先处理：

- `current_task_id=null` 时校验器不能崩溃；应返回结构化 `NO_ACTIVE_TASK`，而不是读取 `None.md`；
- state、task graph、gates、continuity、handoff 的 schema 校验统一；
- 区分 `no_active_task`、`pending_gate`、`invalid_state`、`blocked`；
- 清理 Handoff/Continuity 的 mutable source 自包含问题；
- 生成唯一基线报告，记录失败原因和当前限制。

验收：

- 空任务状态能稳定返回机器可读错误；
- 不发生 traceback；
- 所有状态文件通过 schema/lineage 校验；
- 不能把修复后的 validator PASS 当用户批准。

## P0-2：关闭模拟 Agent PASS

生产执行路径：

```text
真实 Agent executable/session 不存在
→ BLOCKED(REAL_AGENT_UNAVAILABLE)
```

`_simulate_role_output()` 只能在显式 fixture flag、隔离 fixture root 和测试证据中使用，并且输出 verdict 必须是 `TEST_ONLY`，禁止被 Gate 消费。

## P0-3：实现真实 Agent Adapter

统一 Agent 运行协议：

```json
{
  "actor_id": "...",
  "session_id": "...",
  "role_id": "...",
  "task_id": "...",
  "input_snapshot": "sha256:...",
  "allowed_read": [],
  "allowed_write": [],
  "forbidden_write": [],
  "prompt_fingerprint": "sha256:...",
  "started_at": "...",
  "ended_at": "...",
  "exit_code": 0,
  "output_artifact": "..."
}
```

角色执行器必须：

- 调用真实宿主 Agent/独立会话接口；
- 保存真实 session/actor ID；
- 对输入做冻结和指纹；
- 对写入范围做控制；
- 捕获超时、异常、非零退出和非法结构化输出；
- 没有独立 Agent 时不允许模拟完成。

## P0-4：实现 Approval/Gate 闭环

定义不可伪造的 Approval Record：

```json
{
  "approval_id": "...",
  "gate_id": "...",
  "decision": "approved|rejected|repair_requested",
  "actor_type": "human",
  "actor_id": "...",
  "source": "zcode_ui|explicit_user_message|signed_local_record",
  "scope_hash": "...",
  "packet_hash": "...",
  "recorded_at": "...",
  "expires_at": null
}
```

规则：

- 只有 actor_type=human 的有效记录可以放行用户 Gate；
- reviewer PASS、测试通过、validator PASS、delivery GO 都只能是 evidence；
- approval 必须绑定 Human Review Packet hash、Gate scope hash 和当前输入 fingerprint；
- 需求、架构、任务、代码或证据变化后 approval 自动失效；
- Gate 状态必须从 register 真实读取，不得仅凭 `current_gate_id` 推断 pending。

## P0-5：强制任务范围 fail-closed

将：

```python
allowed_paths 为空 → allow
```

改为：

```text
allowed_paths 为空 → TASK_SCOPE_MISSING → BLOCKED
```

任务合同必须至少包含：

- task_id/version；
- phase；
- objective；
- allowed_read；
- allowed_write；
- forbidden_paths；
- developer actor；
- reviewer actor；
- required evidence；
- exit criteria；
- rollback boundary。

## P0-6：高风险路由设不可降低的安全下限

用户可提高模式，不能降低最低模式：

```text
payment / production_data / migration / permission / secret / auth / external API
→ minimum FULL
```

`user_forced_mode=LIGHTWEIGHT` 对高风险意图必须拒绝并返回结构化原因。

## P0-7：统一所有执行入口

必须建立 `RuntimeController.authorize()`，覆盖：

- ZCode Write/Edit/ApplyPatch/Bash Hook；
- MCP tools/call；
- CLI command；
- executor role launch；
- evidence submit；
- state/gate transition；
- install/upgrade/rollback。

任何入口绕过 Controller 都是 P0 缺陷。

---

# 四、按软件工程阶段重新设计完整 Loop

## S0：意图与项目分级

输入：用户自然语言目标。

输出：

- Product Intent；
- scope/non-goals；
- risk register；
- complexity score；
- minimum enforcement level；
- proposed phase profile；
- Human Decision Packet。

规则：不确定时升级，不降级。

## S1：需求工程

角色：Product Manager、Domain Analyst、QA。

产物：

- PRD；
- user journeys；
- business rules；
- acceptance criteria；
- non-functional requirements；
- data classification；
- threat assumptions；
- traceability matrix。

Gate：用户批准目标、范围、优先级和验收标准。

## S2：系统架构

角色：System Architect、Security、SRE。

产物：

- context/container/component architecture；
- module boundaries；
- data flow；
- external dependencies；
- trust boundaries；
- deployment topology；
- resilience and failure modes；
- observability strategy；
- ADR。

Gate：架构评审和安全边界评审。

## S3：详细设计与接口契约

角色：Module Architect、API/Interface Designer、QA。

产物：

- module/component inventory；
- interface contracts；
- data schemas；
- function-level contracts for high-risk functions；
- allowed/forbidden dependencies；
- error model；
- performance budgets；
- test boundaries；
- migration/rollback behavior。

不要求逐变量、逐行设计；按风险分层设计，保留 Qoder 的简洁性。

## S4：实现准备

角色：Project Manager、Developer、QA。

产物：

- executable task graph；
- task contracts；
- dependency graph；
- parallel batches；
- actor assignment；
- allowed read/write scopes；
- test plan；
- review plan；
- evidence plan。

Gate：没有批准任务包禁止写业务代码。

## S5：实现与单元验证

Developer 只能在允许范围工作。

每个任务必须产生：

- code diff；
- unit tests；
- local verification evidence；
- deviations；
- risk notes。

Developer 不能批准自己的实现。

## S6：独立评审

Reviewer 使用新上下文和冻结输入：

- 不读 Developer 的结论作为事实；
- 不能修改业务代码；
- 检查需求、架构、接口、实现、测试、安全和可维护性；
- 只输出结构化 verdict：PASS / BLOCKED / REPAIR_REQUIRED；
- BLOCKED 不能被主控改为 PASS。

## S7：集成与功能验证

执行：

- integration tests；
- contract tests；
- end-to-end tests；
- seeded defect detection；
- mutation tests；
- regression tests。

测试证据必须绑定：

- commit/code fingerprint；
- test suite fingerprint；
- command/args；
- environment；
- exit code；
- stdout/stderr hash；
- start/end time。

## S8：安全与性能

安全：

- SAST；
- dependency audit；
- secret scan；
- permission/auth tests；
- injection/path/TOCTOU tests；
- threat model verification。

性能：

- baseline；
- load profile；
- latency/error/resource budgets；
- concurrency behavior；
- degradation behavior。

## S9：修复回环

缺陷分类：

- P0/P1/P2/P3；
- security blocker；
- architecture deviation；
- quality gap；
- delivery gap。

每次修复必须：

- 新建 repair task；
- 使受影响证据失效；
- 重新运行最小相关验证集；
- 必要时重新架构评审；
- 记录返工成本和原因。

## S10：交付准备

Delivery Manager、Release Engineer、SRE 共同检查：

- build artifact；
- deployment config；
- secrets boundary；
- migrations；
- monitoring/alerts；
- runbook；
- rollback；
- backup/restore；
- support handoff；
- user-observable acceptance。

输出 Human Review Packet，不自动发布。

## S11：维护与演进

维护变更重新进行：

```text
impact analysis → task → design delta → implementation → verification → release
```

保留完整 lineage，不覆盖历史证据。

---

# 五、角色体系优化：从 Markdown 合同升级为可执行角色

保留当前 11 角色，但新增统一 Role Contract Schema：

```text
RoleDefinition
RoleAuthority
RoleCapability
RoleInput
RoleOutput
RoleEvidence
RoleHandoff
RoleCertification
```

每个角色必须同时具备：

- contract 文件；
- machine-readable schema；
- executable adapter；
- certification challenge；
- allowed read/write scope；
- veto conditions；
- output validator；
- handoff validator；
- independent actor requirement。

角色隔离最低要求：

```text
developer_actor_id != reviewer_actor_id
developer_session_id != reviewer_session_id
reviewer_input_snapshot != developer_conclusion_snapshot
reviewer_write_scope 不包含业务代码
```

认证不能只跑固定 fixture。应分三层：

1. contract challenge；
2. seeded-defect challenge；
3. live project challenge。

只有三层都通过才能进入 `CERTIFIED_FOR_PROJECT`。

---

# 六、证据系统优化：全面超过 Qoder 的关键

把证据模型统一为：

```json
{
  "evidence_id": "...",
  "kind": "test|review|security|build|deployment|approval",
  "status": "valid|stale|superseded|invalid",
  "producer_actor_id": "...",
  "producer_session_id": "...",
  "task_id": "...",
  "phase": "...",
  "gate_id": "...",
  "input_fingerprint": "...",
  "subject_fingerprint": "...",
  "binding": {
    "requirements": "...",
    "architecture": "...",
    "task": "...",
    "code": "...",
    "tests": "...",
    "environment": "..."
  },
  "command": {"argv": [], "cwd": "..."},
  "result": {"exit_code": 0, "stdout_sha256": "...", "stderr_sha256": "..."},
  "created_at": "...",
  "expires_at": null,
  "depends_on": [],
  "supersedes": [],
  "content_sha256": "...",
  "envelope_sha256": "..."
}
```

关键超越点：

- 不只 hash content，同时 hash 完整 envelope；
- 绑定 actor、权限、task、phase、Gate、环境和输入；
- 证据不可覆盖，只能 supersede；
- 依赖图必须检测 cycle；
- 代码、需求、架构、测试或环境变化自动使证据 stale；
- Handoff 使用真实 artifact content hash，不使用 `path + version` 伪哈希；
- 证据输出区分 `TEST_ONLY`、`SIMULATED`、`HOST_VERIFIED`、`USER_APPROVED`。

---

# 七、质量、安全和性能系统优化

## 质量执行器

禁止以下模式：

```text
command failure → echo skipped → exit 0
invalid JSON → generic PASS
non-zero exit + valid stdout → PASS
coverage config exists → assume coverage passed
```

每个 checker 必须返回统一结果：

```json
{
  "checker_id": "...",
  "status": "PASS|FAIL|BLOCKED|NOT_RUN",
  "exit_code": 0,
  "command": [],
  "environment": {},
  "stdout_sha256": "...",
  "stderr_sha256": "...",
  "metrics": {},
  "unverified": []
}
```

### 必须增加的质量能力

- typecheck；
- lint；
- unit/integration/e2e；
- coverage threshold；
- mutation score；
- architecture dependency check；
- API/schema compatibility；
- build reproducibility；
- performance budget；
- security baseline。

## Bash/命令防护

短期：

- 未能可靠解析目标的 Bash 命令直接 BLOCKED，而不是放行；
- 覆盖 PowerShell、cmd、bash、Python、Node 和脚本间接调用测试；
- 对外部脚本执行建立 process policy；
- 将 command interception 能力诚实标记为 MEDIUM。

长期：

- 使用宿主原生命令入口拦截；
- 使用受控 subprocess runner；
- 按 argv 而不是 shell 字符串授权；
- 进程沙箱和工作目录约束；
- 记录子进程树、文件变化和网络访问；
- 必要时使用 filesystem watcher 作为补充检测，不把 watcher 当作事前阻断。

---

# 八、业务产品层优化

Loop 不只是开发工具，应该有面向非技术用户的产品模型：

## 用户只做五类决策

1. 目标是什么；
2. 范围和优先级；
3. 业务取舍；
4. 风险接受或拒绝；
5. 阶段 Gate 放行。

## 每个阶段只给用户一个 Human Review Packet

Packet 必须包含：

- 本阶段完成了什么；
- 用户目标覆盖情况；
- 可观察结果；
- 关键风险；
- 未完成项；
- 为什么需要用户决策；
- 选项和后果；
- 推荐下一步；
- 不允许用户跳过的硬阻断。

不要求用户：

- 审核源代码；
- 理解架构图细节；
- 运行命令；
- 看测试日志；
- 判断漏洞是否存在。

## 产品级状态展示

用户看到：

```text
项目状态：进行中 / 等待决策 / 被阻断 / 可交付 / 已回滚
当前阶段：需求 / 架构 / 实现 / 验证 / 交付
风险等级：低 / 中 / 高 / 严重
阻塞原因：一句话
需要你决定：三个以内选项
```

系统内部保留完整工程证据，用户不需要承担工程审计责任。

---

# 九、成本和性能策略

目标不是每次 token 最少，而是总返工成本最低。

## 成本分级

- LIGHTWEIGHT：低风险、单模块、无数据/权限/外部系统；
- STANDARD：多模块或中风险；
- FULL：认证、权限、支付、生产数据、并发、外部 API、部署和不确定性。

## 降低成本的方法

1. 只对高风险函数做函数级详细设计；
2. 证据 fingerprint 未变化时复用验证；
3. 变更影响分析选择最小回归集；
4. 角色按阶段和风险启用，不无脑 11 角色全跑；
5. 无依赖任务真实并行；
6. 失败快速短路，避免无效后续角色调用；
7. reviewer 使用结构化输入摘要，而不是全部历史上下文；
8. 缓存静态标准和角色合同；
9. 记录 token、工具调用、返工次数和失败原因；
10. 对重复失败自动升级流程，而不是无限重试。

成本指标：

```text
cost_per_deliverable
cost_per_verified_change
rework_ratio
blocked_attempts
average_gate_cycles
verification_reuse_rate
```

---

# 十、多宿主策略

每个宿主必须输出 capability manifest：

```json
{
  "host": "zcode|qoder|claude|standalone",
  "can_intercept_writes": true,
  "can_intercept_commands": false,
  "can_launch_isolated_agents": true,
  "can_enforce_exit_codes": true,
  "can_collect_actor_identity": false,
  "can_present_user_gate": true,
  "can_freeze_inputs": true,
  "enforcement_level": "MEDIUM"
}
```

规则：

- Capability 必须通过 live probe 取得，不能只由适配器自报；
- 每个宿主有独立 conformance suite；
- 低于要求时自动降级或阻断高风险项目；
- 不能在 Qoder/standalone 上伪装 STRONG；
- Host Adapter 只能提供能力，不得自行修改 Core 状态或伪造 approval。

---

# 十一、验证路线：先证明控制，再证明交付

## V0：基线和状态修复

- 运行状态校验并修复崩溃；
- 统一 Schema 和文档事实；
- 生成能力矩阵；
- 明确所有当前未验证项。

## V1：Runtime Controller

- 测试所有入口不能绕过；
- allowed_paths 缺失阻断；
- Gate 状态真实读取；
- Approval Record 验证；
- 模拟 Agent 禁止进入生产路径。

## V2：真实 Agent 和角色隔离

- 启动真实 ZCode Agent；
- 记录 actor/session；
- developer/reviewer 独立；
- reviewer 无业务写权限；
- 角色输出结构化校验；
- 无 Agent 时 BLOCKED。

## V3：真实 Hook Conformance

矩阵：

- Write 普通文件；
- Edit 普通文件；
- ApplyPatch；
- Bash 重定向；
- Bash cp/mv/tee/cat；
- PowerShell；
- Python/Node 脚本内部写入；
- 外部进程；
- 非治理项目放行；
- 治理文件死锁豁免。

每项保存：

- 输入 payload；
- Hook source；
- matcher；
- stdout/stderr；
- exit code；
- 宿主 UI 结果；
- 文件前后 fingerprint。

## V4：真实 Gate/Review Packet

- 运行一阶段；
- 生成 Packet；
- 用户批准/拒绝/请求修复；
- 验证状态推进或阻断；
- 验证旧 approval 在输入变化后失效。

## V5：真实垂直切片

选择一个受控、非生产、可观察的样例产品，完成：

```text
需求 → 架构 → 详细设计 → 实现 → 测试 → 独立评审
→ 预埋缺陷发现 → 修复 → 回归 → 构建 → 运行 → 用户可观察结果
```

必须人为制造至少三类缺陷：

- 业务验收缺陷；
- 架构/依赖缺陷；
- 安全或权限缺陷。

要求 Loop：

- 发现；
- 阻断错误交付；
- 生成 repair task；
- 修复；
- 通过独立回归。

## V6：多宿主 Conformance

先验证 ZCode，再验证 Qoder/Claude/standalone。

每个宿主输出：

```text
host capability report
hook/tool conformance report
unsupported controls
minimum safe project class
```

---

# 十二、交付门禁

全面超越 Qoder 前，不允许以“文档完成”作为 release 条件。

最终 Release Gate 必须要求：

- validator 无 traceback；
- 所有 P0=0；
- 真实 Agent 路径通过；
- 真实 reviewer 独立通过；
- Approval 闭环通过；
- Hook conformance 通过；
- Bash 未识别命令 fail-closed；
- MCP/CLI 无绕过；
- Evidence freshness 和 envelope hash 通过；
- 质量、安全、性能、构建证据有效；
- 回滚演练通过；
- Human Review Packet 经用户明确批准；
- 所有声明与实际 capability 一致。

若任何一项未通过，发布状态必须是：

```text
BLOCKED / CANDIDATE / MEDIUM / ADVISORY
```

不能自动标记 PASS。

---

# 最终答案

能做到，但要把“全面超越 Qoder”定义成一项可验证的工程目标，而不是继续堆角色、模板和报告。

最核心的改造方向是：

```text
1. Qoder 的 Core 建模
2. ZCode 的宿主 Hook 控制
3. 真实 Agent 调度
4. 真实 Approval/Gate
5. 统一 Runtime Controller
6. 证据 envelope + TTL + 因果链
7. 多宿主 capability conformance
8. 一条真实垂直切片
```

在当前状态下不建议直接进入大规模实现，因为 `validate_state.py` 仍会因无活动任务崩溃；应先建立新的基线修复任务和 Gate，再按 P0→P1→P2 分阶段推进。