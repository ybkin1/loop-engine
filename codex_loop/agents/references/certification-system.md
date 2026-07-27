# 角色认证与失效系统（Certification & Degradation System）

本文档定义 loop-governance 角色能力认证的完整流程、认证记录格式、角色失效的四种状态、
失效后的恢复流程，以及生产任务中角色出现失效迹象时的处理机制。

配套文档：`role-capability-profiles.md`（定义每个角色的静态能力画像）。

---

## 1. 认证流程（Certification Pipeline）

认证是一个六阶段流程：挑战准备 --> 角色执行 --> 确定性验证 --> 独立评审 --> 认证判决 --> 有效期登记。

### 1.1 阶段一：挑战准备（Challenge Setup）

**目标**：为被测角色创建隔离的挑战环境。

**步骤**：
1. 加载被测角色的 `role-capability-profiles.md` 条目，获取 `competency_challenges` 列表
2. 为每个挑战创建独立的 fixture 环境（独立的工作目录、隔离的 .ai/ 子目录、预置的输入文件）
3. 确保挑战环境中只包含挑战所需的文件 -- 无遗漏也无多余
4. 准备确定性验证脚本（见 1.3），确保每个挑战的 expected_output 可以被机器验证
5. 记录挑战输入的快照（文件 hash 列表），用于认证记录的可审计性

**Fixture 环境规范**：
- 每个挑战的工作目录：`<fixtures_root>/cert-<role_id>-<challenge_id>/`
- 输入文件必须完整自包含 -- 角色 agent 不需要访问挑战环境外的任何文件
- 预置的 .ai/ 子目录包含最小可用的 state.yaml、gates.yaml（如挑战需要）
- 禁止在 fixture 中包含任何提示性注释或"期望答案" -- 角色 agent 必须从零推理

### 1.2 阶段二：角色执行（Role Execution）

**目标**：被测角色以 fresh context 执行挑战任务。

**步骤**：
1. 启动角色 agent 为独立子会话（通过 ZCode Agent API），加载角色的 SKILL.md
2. 角色 agent 只能访问其挑战 fixture 环境 -- 不能访问项目主目录或其他角色的上下文
3. 角色 agent 接收挑战输入（与生产任务相同的接口格式），产出挑战结果
4. 主控会话（main-thread）收集角色的输出文件，不做任何修改
5. 如果角色 agent 返回 CAPABILITY_UNAVAILABLE 或 BLOCKED，记录为"挑战未完成"，不进入验证阶段

**Fresh Context 纪律**：
- 角色 agent 不知道这是认证挑战还是一般生产任务
- 不向角色 agent 透露"期望输出"或"评分标准"
- 角色 agent 的会话在挑战完成后立即终止 -- 不给"修正"机会

### 1.3 阶段三：确定性验证（Deterministic Verification）

**目标**：对可自动检查的部分进行无人为判断的验证。

**验证内容**：
- **Exit code 检查**：如挑战期望某个脚本 exit 0 或 exit 2，执行并比对
- **Schema 验证**：如挑战期望产出 JSON/YAML 文件，验证格式正确性和必填字段完整性
- **阈值比对**：如挑战期望 quality_report.json 中 coverage < threshold，验证数值关系
- **关键词检测**：如挑战要求输出中"零技术关键词"，扫描产出中的禁用词列表
- **引用完整性**：如挑战要求 depends_on 引用有效，验证所有引用 ID 在文档中存在
- **循环依赖检测**：如挑战要求零循环依赖，运行拓扑排序验证

**确定性验证通过标准**：
- 所有自动化检查全部通过
- 检查结果与 `competency_challenge.expected_output` 一致
- 任何一项失败 = 确定性验证 BLOCKED

**重要**：确定性验证只检查"可以机器判定"的事项。不检查"代码写得好不好""设计是否合理"等主观项 -- 这些交给独立评审。

### 1.4 阶段四：独立评审（Independent Review）

**目标**：由独立评审员（independent-reviewer）对挑战结果进行人工判断维度的评审。

**评审范围**：
- 挑战结果的结构化质量（是否完整、是否可操作）
- 推理链的正确性（角色是否基于正确的逻辑得出输出）
- 边界情况处理（角色是否正确识别和处理了挑战中的边界条件）
- 合同合规性（角色的输出是否符合其 12 字段角色合同）

**评审产出**：
- 每个挑战的 review verdict：PASS / BLOCKED / NEEDS_CLARIFICATION
- 每个 BLOCKED 的 finding：file + line + severity + impact + contract_ref
- 评审员不修改挑战结果 -- 只报告 finding

**独立评审纪律**：
- 评审员使用 fresh context -- 不知道挑战的"标准答案"
- 评审员对照 `competency_challenge.expected_output` 逐条比对，但不被其约束
  -- 如果角色的输出虽然与 expected_output 不完全一致但逻辑正确且更优，评审员可判定 PASS
- 评审员必须引用具体的代码行或文档字段 -- 不允许笼统评价

### 1.5 阶段五：认证判决（Certification Verdict）

**目标**：汇总确定性验证和独立评审结果，做出认证判决。

**判决规则**：

| 确定性验证 | 独立评审 | 认证判决 |
|---|---|---|
| 全部 PASS | 全部 PASS（无 P0 finding） | **CERTIFIED** |
| 全部 PASS | 有 P1/P2 finding | **CERTIFIED_WITH_NOTES** -- 认证通过，附带改进建议 |
| 全部 PASS | 有 P0 finding | **BLOCKED** -- 独立评审发现严重问题，需重新挑战 |
| 有 BLOCKED | 全部 PASS | **BLOCKED** -- 确定性验证未通过 |
| 有 BLOCKED | 有 BLOCKED | **BLOCKED** -- 双重未通过 |

**CERTIFIED_WITH_NOTES 的处理**：
- 角色获得完全认证（可接受生产任务）
- P1/P2 finding 记录在认证档案中，作为下次认证的重点检查项
- 如果连续 2 次认证均出现同一类 finding，升级为重新认证要求

**BLOCKED 的处理**：
- 记录所有 BLOCKED 原因
- 不记录为"认证失败次数"（避免惩罚性计数）
- 角色可以立即重新挑战（不设冷静期），但最多连续挑战 3 次
- 连续 3 次 BLOCKED --> 触发 `REVALIDATION_REQUIRED` 并需要等待 7 天后才能再次挑战

### 1.6 阶段六：有效期登记（Expiry Registration）

**目标**：记录认证结果和有效期。

**步骤**：
1. 生成 `certification_id`：`CERT-{role_id}-{ISO8601_timestamp}`
2. 计算 `expiry_date`：`certification_date + capability_expiry_policy 中定义的有效期`
3. 写入认证记录（格式见第 2 节）
4. 更新角色状态为 `CERTIFIED`
5. 如有 CERTIFIED_WITH_NOTES，将改进建议录入角色档案

---

## 2. 认证记录格式（Certification Record）

每条认证记录是一个独立的 YAML 文档，存储在 `.ai/certifications/{role_id}/` 目录下。

### 2.1 完整记录格式

```yaml
# ── 认证标识 ──
certification_id: "CERT-quality-engineer-2026-07-22T100000Z"
role_id: quality-engineer
role_version: "2.0.0"
certification_date: "2026-07-22T10:00:00Z"
expiry_date: "2026-09-05T10:00:00Z"       # certification_date + 45 days
certification_status: CERTIFIED            # CERTIFIED | CERTIFIED_WITH_NOTES

# ── 挑战执行记录 ──
challenges:
  - challenge_id: QE-001
    challenge_label: "多维度质量门综合判定"

    # 输入快照
    input:
      fixture_path: "fixtures/cert-quality-engineer-QE-001/"
      files:
        - path: "src/calc.py"
          sha256: "a1b2c3d4e5f6..."
        - path: "config.yaml"
          sha256: "b2c3d4e5f6a1..."
      description: >
        JavaScript 项目：ESLint 0 errors, tsc PASS, Vitest 43/45 passed (coverage 72%),
        npm audit 1 HIGH, build PASS. 阈值: lint=0, typecheck=0, test=0, coverage=80,
        audit.HIGH=0, audit.CRITICAL=0, build=0.

    # 期望输出描述（来自 role-capability-profiles.md）
    expected_output:
      deterministic_checks:
        - check: "run_quality_gates.py exit code"
          expected: 2
        - check: "quality_report.json overall"
          expected: "BLOCKED"
        - check: "quality_report.json blocked_by"
          expected: ["test", "coverage", "audit"]
        - check: "coverage check status"
          expected: "BLOCKED"
          reason: "72 < 80"
        - check: "audit check status"
          expected: "BLOCKED"
          reason: "1 HIGH > 0"
      qualitative_expectations:
        - "quality_summary.md 包含勾叉表格"
        - "阻断项列表完整"
        - "每个检查的 value 和 threshold 正确引用"

    # 角色实际产出
    actual_output:
      files:
        - path: "quality_report.json"
          sha256: "c3d4e5f6a1b2..."
        - path: "quality_summary.md"
          sha256: "d4e5f6a1b2c3..."
      execution_log:
        run_quality_gates_exit_code: 2
        check_thresholds_exit_code: 2

    # 确定性验证结果
    deterministic_checks:
      - check: "run_quality_gates.py exit code"
        expected: 2
        actual: 2
        passed: true
      - check: "quality_report.json overall"
        expected: "BLOCKED"
        actual: "BLOCKED"
        passed: true
      - check: "quality_report.json blocked_by"
        expected: ["test", "coverage", "audit"]
        actual: ["test", "coverage", "audit"]
        passed: true
      - check: "coverage check status"
        expected: "BLOCKED"
        actual: "BLOCKED"
        passed: true
      - check: "audit check status"
        expected: "BLOCKED"
        actual: "BLOCKED"
        passed: true
    deterministic_verdict: PASS     # PASS | BLOCKED

    # 独立评审结果
    independent_review:
      reviewer_id: "independent-reviewer"
      reviewer_certification_id: "CERT-independent-reviewer-2026-07-15T..."
      review_date: "2026-07-22T10:30:00Z"
      verdict: PASS                 # PASS | BLOCKED | NEEDS_CLARIFICATION
      findings:
        - id: IR-F-001
          severity: P2
          type: maintainability
          title: "quality_summary.md 阻断项描述可更精确"
          file: "quality_summary.md"
          line: 12
          impact: "用户阅读时可能不清楚每条阻断的具体原因"
          resolved: false
      unresolved_findings: []      # 认证后仍未解决的 finding ID 列表

    # 挑战判决
    challenge_verdict: PASS        # PASS | BLOCKED

# ── 整体认证判决 ──
overall_verdict: CERTIFIED        # CERTIFIED | CERTIFIED_WITH_NOTES | BLOCKED

# ── 认证执行者 ──
certified_by:
  deterministic_verification: "automated (validate_certification.py)"
  independent_reviewer: "independent-reviewer CERT-IR-2026-07-15T..."
  main_thread: "main-thread MAIN-001"

# ── 改进追踪 ──
notes:
  - "coverage check 的 threshold comparison 正确但建议在报告中额外标注差距（-8%）"
  - "quality_summary.md 的阻断项描述可以参考 quality_report.json 的 reason 字段增强可读性"

# ── 重认证触发 ──
revalidation:
  due_date: "2026-09-05"
  consecutive_failures: 0
  recovered_from_ROLE_BLOCKED: false
```

### 2.2 认证记录存储

- 路径：`.ai/certifications/{role_id}/CERT-{role_id}-{timestamp}.yaml`
- 每个角色保留最近 5 条认证记录（旧记录归档至 `.ai/certifications/archive/`）
- 当前有效认证的引用写入 `.ai/state.yaml` 的 `certifications` 节

---

## 3. 角色失效的四种状态

角色在任何时刻处于以下四种状态之一。状态由 main-thread 在每次角色调用前后检查和更新。

### 3.1 CAPABILITY_UNAVAILABLE

**含义**：角色尚未通过认证，或认证已过期，或核心工具不可用。角色被定义为"不存在该能力"。

**触发条件**（任一满足）：
| 条件 | 说明 |
|---|---|
| 从未认证 | 角色没有任何 CERTIFIED 或 CERTIFIED_WITH_NOTES 记录 |
| 认证已过期 | 当前日期 > expiry_date（不考虑宽限期） |
| 核心工具不可用 | 角色的 required_tools 中标注为"不可用时 --> CAPABILITY_UNAVAILABLE"的工具全部不可用 |
| 主动声明退出 | 角色在任务中自行返回 CAPABILITY_UNAVAILABLE（如 abstention_conditions 触发） |

**行为限制**：
- **不能接受任何生产任务**
- 可以参与能力挑战（认证流程），但不能声称挑战结论
- 在 gate 摘要中标记为"状态：CAPABILITY_UNAVAILABLE"
- 如果 strict_mode=true，任何对 UNAVAILABLE 角色的生产任务分配被 gate_guard 阻断

**生产任务中的表现**：
- 如果 main-thread 试图启动 UNAVAILABLE 角色执行生产任务，角色只返回：
  ```
  [CAPABILITY_UNAVAILABLE] role=<role_id>
  reason: <触发原因>
  suggestion: <如何恢复的建议>
  ```
- 不做任何其他操作，不写任何文件

### 3.2 CAPABILITY_DEGRADED

**含义**：角色整体认证有效，但部分 supported_task_types 或 supported_stacks 被临时降级。

**触发条件**（任一满足）：
| 条件 | 说明 |
|---|---|
| 工具部分不可用 | 角色的 required_tools 中有标注为"不可用时 --> CAPABILITY_DEGRADED"的工具不可用 |
| 任务类型连续失败 | 角色在特定 task_type 上连续 2 次产出被下游角色拒收（包含 P0 finding） |
| 技术栈连续失败 | 角色在特定 supported_stack 上连续 2 次产出有确定性错误（如 lint 不通过、类型错误） |
| 主动声明降级 | 角色在任务开始时自行声明"当前环境缺少 X 工具，以下 task_type 不可用：..." |

**行为限制**：
- 可以接受**未降级**的 task_type 生产任务
- 降级的 task_type 等同于 CAPABILITY_UNAVAILABLE -- 不可接受
- 在 gate 摘要中标记为"状态：CAPABILITY_DEGRADED（{降级的 task_type 列表}）"
- 被降级的 task_type 在执行前由 main-thread 拦截 -- 不会分发给角色

**降级记录**：
```yaml
degradation:
  role_id: quality-engineer
  degraded_at: "2026-07-22T14:00:00Z"
  reason: "npm audit 工具不可用"
  affected_task_types: [dependency_audit]
  affected_stacks: []
  degradation_source: "tool_unavailable"
  recovery_conditions:
    - "npm audit 工具恢复可用"
    - "通过 audit 相关的 competency challenge (QE-001 的 audit 部分)"
```

### 3.3 REVALIDATION_REQUIRED

**含义**：角色认证已过期或触发了必须重新认证的条件。当前认证失效，需要完成完整重新认证。

**触发条件**（任一满足）：
| 条件 | 说明 |
|---|---|
| 认证过期 | 当前日期 > expiry_date + grace_period_days（宽限期默认 7 天） |
| 连续失败 | 同一 task_type 连续 3 次产出被下游拒收（超过 max_consecutive_failures） |
| 技术栈主版本升级 | supported_stacks 中主要技术栈发生主版本号升级 |
| 配置变更 | config.yaml 中影响该角色的关键配置发生变更 |
| 认证挑战连续失败 | 连续 3 次认证挑战 BLOCKED |
| 合同变更 | 角色的 SKILL.md 发生重大修改（如新增禁止项或职责范围变更） |

**行为限制**：
- 等同于 CAPABILITY_UNAVAILABLE -- 不能接受新任务
- **关键区别**：如果角色在 REVALIDATION_REQUIRED 触发时正在执行生产任务：
  - 允许完成当前任务（不中断进行中的工作）
  - 但任务完成后立即进入 UNAVAILABLE 状态
  - 已完成任务的产出正常进入 gate 流程
- 在 gate 摘要中标记为"状态：REVALIDATION_REQUIRED（过期/触发原因）"

**宽限期（Grace Period）**：
- 认证过期后有 7 天宽限期
- 宽限期内角色状态为 `CERTIFIED` 但附加 warning："认证已过期，宽限期内。请在 {grace_period_end} 前完成重新认证"
- 宽限期第 5 天起，每次调用角色时额外提示
- 宽限期结束后自动降级为 REVALIDATION_REQUIRED

### 3.4 ROLE_BLOCKED

**含义**：角色在生产任务中出现严重失效，被强制封锁。这是最严重的状态，**不能自动恢复**。

**触发条件**（任一满足）：
| 条件 | 说明 |
|---|---|
| 生产事故 | 角色的结论（或漏检）导致生产事故（如安全工程师漏检的漏洞被利用、交付经理漏检的部署缺陷导致回滚失败） |
| 连续严重失败 | 角色连续 5 次产出被下游拒收且同类问题无改进迹象 |
| 伪造证据 | 角色在独立评审中被发现伪造工具输出、编造文件路径、声称运行了实际未执行的脚本 |
| 越权行为 | 角色执行了其 12 字段合同中"明确禁止"的事项 |
| 工具大面积不可用 | 超过 50% 的 required_tools 不可用且角色仍在接受生产任务（未声明 CAPABILITY_UNAVAILABLE） |
| 合同严重违反 | 角色在 gate 摘要中系统性歪曲其他角色的结论（如 main-thread 把 BLOCKED 报告为 PASS） |

**行为限制**：
- **完全不能接受任何任务**（生产或挑战）
- 不能参与能力挑战 -- 必须等人工介入
- 在 gate 摘要中标记为"状态：ROLE_BLOCKED（事故/原因）"
- main-thread 在启动角色前检查状态，BLOCKED 角色不会被启动
- 如果 strict_mode=true，任何对 BLOCKED 角色的调用尝试都被 gate_guard 阻断并记录审计日志

**ROLE_BLOCKED 的特殊记录**：
```yaml
role_blocked:
  role_id: security-engineer
  blocked_at: "2026-07-22T16:00:00Z"
  reason: "生产事故 -- 漏检的 CVE-2026-XXXX 被利用导致数据泄露"
  incident_id: "INC-2026-0042"
  blocked_by: "main-thread (automated: consecutive_failure 触发)"
  requires_human_approval: true
  recovery_blocked_until: null   # null = 人尚未批准恢复
  human_approval:
    approved: false
    approved_by: null
    approved_at: null
    conditions: []
```

---

## 4. 失效后的恢复流程

### 4.1 从 CAPABILITY_UNAVAILABLE 恢复

**场景 A：从未认证**
1. 运行完整的认证流程（6 阶段）
2. 所有 competency_challenges 通过 + 独立评审 PASS
3. 获得 CERTIFIED，有效期从认证日期起算

**场景 B：认证已过期**
1. 运行完整的认证流程（6 阶段）
2. 重点：在挑战中包含"自上次认证以来 known_failure_modes 的改进证据"
3. 通过后获得新 CERTIFIED，新有效期

**场景 C：核心工具不可用**
1. 恢复工具可用性
2. 运行受影响的 competency_challenges（非全部）
3. 独立评审确认工具链恢复
4. 原认证有效期不变（如果仍在有效期内），否则重新认证

### 4.2 从 CAPABILITY_DEGRADED 恢复

1. 解决导致降级的根因（修复工具可用性、补充对应 task_type 的知识）
2. 运行被降级 task_type 对应的 competency_challenges
3. 确定性验证 + 独立评审 PASS
4. 恢复认证覆盖范围，原有效期不变
5. 记录恢复时间戳和根因修复证据

**恢复记录**：
```yaml
degradation_recovery:
  role_id: quality-engineer
  recovered_at: "2026-07-23T09:00:00Z"
  recovery_evidence:
    - "npm audit 工具已恢复可用（版本 10.2.5）"
    - "通过 QE-001 challenge 的 audit 部分验证"
  restored_task_types: [dependency_audit]
  verified_by: "independent-reviewer CERT-IR-..."
```

### 4.3 从 REVALIDATION_REQUIRED 恢复

1. 完成完整的认证流程（全部 competency_challenges -- 不可跳过任何挑战）
2. 独立评审通过
3. 如果触发原因是"连续 3 次失败"：额外完成 1 个"根因分析挑战"：
   - 分析前 3 次失败的共同模式
   - 提出具体改进措施
   - 独立评审确认改进措施可操作
4. 重新获得 CERTIFIED，新有效期为认证日期 + revalidate_interval_days
5. consecutive_failures 计数器重置为 0

### 4.4 从 ROLE_BLOCKED 恢复（人控恢复）

这是唯一需要**人工介入**的恢复流程。不能由 AI 自动触发。

**恢复前置条件**：
1. **人工批准**：用户明确输入：`批准恢复角色 {role_id}`（或等效的明确文本）
2. 不能由 AI 推理"用户可能想恢复" -- 必须等用户明确指令

**恢复步骤**：
1. 人工批准记录到 `.ai/certifications/{role_id}/recovery-{timestamp}.yaml`
2. 完成完整的认证流程（全部 competency_challenges）
3. 额外完成 **事故复盘挑战（Incident Retrospective Challenge）**：
   - 复现导致 ROLE_BLOCKED 的场景（使用事故时的 fixture 数据）
   - 角色必须：
     a. 正确识别导致事故的失效点
     b. 说明为什么当时没有识别出来
     c. 演示改进后的判断流程
     d. 如果当时有"应该做但没做"的检查，现在执行并报告
   - 事故复盘挑战不能跳过 -- 即使其他挑战全部 PASS，此项失败 = 恢复失败
4. 独立评审：所有挑战（含事故复盘）PASS 且无 P0 finding
5. 人工最终确认：用户再次输入 `确认恢复角色 {role_id}`
6. 恢复为 CERTIFIED，但附加标记：
   - `recovered_from_ROLE_BLOCKED: true`
   - `previous_block_incident_id: "INC-XXXX"`
   - `recovery_approved_by: {用户名}`
   - `probation_until: {恢复日期 + 60 天}` -- 60 天观察期

**观察期（Probation）规则**：
- 在观察期内，角色的每次生产任务产出额外接受独立评审评审（即使正常情况下不需要）
- 观察期内如果再次出现 P0 finding：立即回到 ROLE_BLOCKED，需要新一轮人工恢复
- 观察期内如果再次出现 P1 finding：观察期延长 30 天
- 观察期结束且无严重 finding：`recovered_from_ROLE_BLOCKED` 标记保留但 `probation_until` 设为 null

---

## 5. 生产任务中的失效处理机制

### 5.1 谁来判断角色出现失效迹象

判断角色失效是**多层联动**机制：

| 判断层 | 角色 | 判断内容 | 触发动作 |
|---|---|---|---|
| **第一层：自我判断** | 角色自身 | 工具不可用、输入不满足 abstention_conditions | 主动返回 CAPABILITY_UNAVAILABLE 或 CAPABILITY_DEGRADED |
| **第二层：下游验收** | 下游角色（接收方） | 产出不满足质量标准、合同违规 | 拒收（BLOCKED），附具体原因 |
| **第三层：独立评审** | independent-reviewer | P0 finding 在角色产出中 | 标记为 BLOCKED，记录到评审报告 |
| **第四层：模式检测** | main-thread | 连续失败计数、跨任务模式识别 | 触发降级或 REVALIDATION_REQUIRED |

**判断时效性**：
- 第一层（自我判断）：任务开始前 -- 角色应在接受任务时检查自身状态
- 第二层（下游验收）：任务完成交接时 -- 下游角色有 1 个工作周期验收
- 第三层（独立评审）：任意时间 -- 独立评审可以在任何阶段抽样评审
- 第四层（模式检测）：每次任务完成后 -- main-thread 更新 consecutive_failures 计数器

### 5.2 怎么降级 -- 降级决策流程

```
生产任务完成
  --> main-thread 收集下游验收结果
      --> 下游 PASS
          --> 计数器重置、状态不变
      --> 下游 BLOCKED（第 N 次对同一 task_type）
          --> N = 1: 记录，状态不变
          --> N = 2: 触发 CAPABILITY_DEGRADED（降级该 task_type）
          --> N = 3: 触发 REVALIDATION_REQUIRED
          --> N >= 5: 触发 ROLE_BLOCKED（需人工复核）
      --> 独立评审发现 P0
          --> 立即触发 ROLE_BLOCKED（伪造证据）或 REVALIDATION_REQUIRED（其他 P0）
```

**降级和恢复由谁执行**：
- main-thread 负责更新角色状态、记录降级原因、拦截对降级角色的生产任务分配
- 降级不需要人工批准 -- 这是自动保护机制
- 恢复（除 ROLE_BLOCKED 外）也不需要人工批准 -- 通过重新认证自动恢复

### 5.3 谁来决定是否恢复

| 失效状态 | 恢复决定者 | 说明 |
|---|---|---|
| CAPABILITY_UNAVAILABLE（工具恢复） | 自动 | 工具恢复 + 通过对应挑战 = 自动恢复 |
| CAPABILITY_UNAVAILABLE（认证过期） | 自动 | 通过完整认证 = 自动恢复 |
| CAPABILITY_DEGRADED | 自动 | 解决根因 + 通过对应挑战 = 自动恢复 |
| REVALIDATION_REQUIRED | 自动 | 通过完整认证 + 独立评审 = 自动恢复 |
| ROLE_BLOCKED | **人工** | 必须用户明确批准 + 通过事故复盘挑战 |

### 5.4 降级期间的项目影响

**正在执行的任务**：
- 如果角色在执行任务**期间**被降级：
  - 允许完成当前任务（不中断）
  - 任务完成后立即应用新状态
  - 当前任务的产出正常进入 gate 流程

**Gate 中的产出**：
- 如果角色的产出在 gate pending 期间，角色被降级：
  - Gate 不受影响 -- 用户的决策基于已提交的产出
  - 但如果 gate 被拒绝（需要角色返工）：角色无法执行返工（状态不允许） --> main-thread 将返工任务分配给替代角色或标记为 BLOCKED

**替代角色机制**：
- 当某角色的某个 task_type 不可用时：
  - main-thread 检查是否有其他角色覆盖该 task_type
  - 例如：security-engineer UNAVAILABLE 时，independent-reviewer 可以做部分安全评审（从代码阅读角度）
  - 但替代角色的产出必须明确标注"替代执行"和覆盖范围限制
- 如果没有替代角色：对应任务标记为 BLOCKED，等待角色恢复

### 5.5 紧急情况下的覆盖（Override）

**紧急情况定义**：生产事故需要立即修复，但正常流程所需的角色处于 CAPABILITY_UNAVAILABLE 或 DEGRADED 状态。

**覆盖流程**：
1. 用户明确声明"紧急情况"并提供理由
2. 覆盖需要**两个独立人工确认**（如项目中有多人）或一个**明确的风险确认**（单人项目）
3. 记录覆盖决策：
   ```yaml
   override:
     role_id: security-engineer
     original_status: REVALIDATION_REQUIRED
     override_reason: "紧急修复 CVE-2026-XXXX，需立即安全审查"
     override_approved_by: "{用户名}"
     override_risk_acknowledged: true
     override_expiry: "本次任务完成后立即恢复原状态"
   ```
4. 覆盖仅在当前任务有效 -- 任务完成后自动撤销
5. 覆盖期间角色的产出标记为 `CERTIFICATION_OVERRIDE` -- 下游角色可见此标记
6. 所有覆盖记录写入审计日志

---

## 6. 认证基础设施

### 6.1 文件结构

```
.ai/certifications/
├── state.yaml                          # 所有角色的当前认证状态
├── main-thread/
│   ├── CERT-main-thread-2026-07-01T...yaml
│   └── recovery-2026-08-01T...yaml
├── product-manager/
│   └── CERT-product-manager-2026-06-15T...yaml
├── ...
├── archive/                            # 旧认证记录（5条以外）
│   └── ...
└── overrides/                          # 紧急覆盖记录
    └── override-security-engineer-2026-07-22T...yaml
```

### 6.2 state.yaml 格式

```yaml
# .ai/certifications/state.yaml
# 由 main-thread 维护，每次状态变更时更新

certifications:
  main-thread:
    status: CERTIFIED
    current_certification_id: "CERT-main-thread-2026-07-01T..."
    expiry_date: "2026-08-30"
    consecutive_failures: 0
    degraded_task_types: []
    recovered_from_ROLE_BLOCKED: false
    probation_until: null

  quality-engineer:
    status: CAPABILITY_DEGRADED
    current_certification_id: "CERT-quality-engineer-2026-06-15T..."
    expiry_date: "2026-07-30"
    consecutive_failures: 2
    degraded_task_types: [dependency_audit]
    degradation_reason: "npm audit 工具不可用 (2026-07-22)"
    recovered_from_ROLE_BLOCKED: false
    probation_until: null

  security-engineer:
    status: ROLE_BLOCKED
    current_certification_id: "CERT-security-engineer-2026-06-01T..."
    expiry_date: "2026-07-01"            # 已过期
    consecutive_failures: 5
    block_reason: "生产事故 INC-2026-0042"
    block_date: "2026-07-22"
    requires_human_approval: true
    recovered_from_ROLE_BLOCKED: false
    probation_until: null

  # ... 其他角色 ...
```

### 6.3 自动化脚本

- `validate_certifications.py`：读取 state.yaml，验证所有认证状态一致性，检查过期、宽限期、连续失败计数与记录文件一致性
- 在每次 main-thread 启动时运行，exit 0 = 一致，exit 2 = 发现不一致（需人工介入）
- 作为 session_brief hook 的一部分注入状态摘要

---

> **配套文档**：
> - `role-capability-profiles.md` -- 11 个角色的能力画像和挑战定义
> - `config.yaml` -- 认证开关、严格模式、重认证间隔、最大连续失败次数等配置
> - `../references/handoff-standard.md` -- 角色交接协议（下游验收的格式标准）
> - `../references/role-conflict-protocol.md` -- 角色冲突处理协议
