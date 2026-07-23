# 当前主控会话交接文档 v0.1

## Identity

- Artifact ID: `T-0034-CURRENT-MAIN-CONTROLLER-HANDOFF-v0.1`
- Handoff type: `program_controller_rotation`
- Generated at: `2026-07-15T16:31:41.8113059+08:00`
- Project root: `C:\Users\Administrator\.codex\loop-engine-lab`
- Predecessor role: L0 项目/计划主控（当前会话）
- Intended successor: fresh-context L0 项目/计划主控
- Governing task: `T-0034`
- Governing gate: `G-T-0034-DESIGN-PROJECT-CONTINUITY-CONTROLLER-HIERARCHY-LOOP-ASSURANCE`
- Gate decision source: 用户明确消息 `批准 G-T-0034-DESIGN-PROJECT-CONTINUITY-CONTROLLER-HIERARCHY-LOOP-ASSURANCE`
- Package status: `HANDOFF_PACKAGE_READY_SUCCESSOR_ATTESTATION_PENDING`

## Mission And User Position

- 最终服务对象是非技术用户。
- 最终目标是把用户意图持续交付为可用、可验证、可部署、可迭代的软件产品。
- 用户负责目标、业务事实、关键取舍和明确 gate 决策。
- Codex 负责批准范围内的技术分析、规划、实施、验证、审计、返修和交付准备。
- 治理是降低风险和用户负担的工具，不是产品本身，不得演变成只生产治理文档的自循环。
- 用户期望的未来体验：发起正式任务后，仅在真实业务决策或 gate 时介入，最终收到经过独立验证和深度审计、可追溯残余风险的任务结果。

## Common Position

- 实际运行行为必须与用户明确授权一致。
- implementation、installation、activation 和 real-project entry 必须分开。
- 测试、review、validator、audit、subagent 和 AI 推荐都是证据，不是授权。
- 基础治理系统存在 P0/P1 问题时停线修复，不继续堆后续任务。
- 原始证据保留；修复通过 addendum 追加，不覆盖失败证据或改写历史。
- 授权不清时停止，不扩大影响。
- 每个任务或阶段结束时给用户明确、可复制的下一步提示词。

## Current Control State

```yaml
current_phase: S0-method-repair
current_task_id: T-0034
current_task_status: active
current_gate_id: null
governing_gate_status: approved
current_execution_slice: phase_1_handoff_documents
phase_1_status: completed_pending_successor_verification
pending_gate_count: 0
active_transaction: false
in_flight_agents: []
partial_write: false
candidate_installed: false
candidate_activated: false
automatic_loop_enabled: false
```

T-0034 整体尚未完成。本次用户只授权执行第一阶段的两个输出：交接文档写作规范与当前主控会话交接文档。不得把第一阶段完成理解为 T-0034 全部设计完成。

## Authorization Matrix

| Capability | State | Boundary |
|---|---|---|
| T-0034 design | `authorized` | 受用户当前回合“第一阶段只编写两份文档”进一步缩小 |
| implementation | `not_authorized` | 不修改候选或运行时实现 |
| candidate modification | `not_authorized` | T-0033 隔离候选保持不变 |
| installation | `not_authorized` | candidate 仍未安装 |
| activation | `not_authorized` | candidate 仍未激活 |
| runtime behavior change | `not_authorized` | 不改变 Project Governor 或 Loop 行为 |
| agent orchestration | `not_authorized` | 不启用或调用自动 Loop；本阶段未使用 subagent |
| downstream task creation | `not_authorized` | 不创建 T-0035～T-0050 |
| real-project entry | `not_authorized` | 不进入真实业务项目 |
| deployment/high-risk actions | `not_authorized` | 不部署、迁移、改权限、处理密钥/支付/生产数据 |

## Allowed Scope For This Checkpoint

- 读取 T-0034 canonical records 与 planning evidence。
- 编写 `.ai/evidence/T-0034/handoff-writing-standard.v0.1.md`。
- 编写 `.ai/evidence/T-0034/current-main-controller-handoff.v0.1.md`。
- 更新必要的 project-local `.ai` 治理投影，使其如实反映第一阶段已执行、T-0034 仍 active。
- 运行只读 `validate_state.py` 与 `audit_handoff.py`。
- 停止并等待用户把本交接文档交给 fresh successor。

## Forbidden Scope

- 不编写 T-0034 其余合同、schema、state machine、audit charter 或实现计划。
- 不创建 T-0035 或任何 T-0035～T-0050 task/gate/task-graph node。
- 不修改 `candidates/T-0030-project-governor-repair/`。
- 不修改 `C:\Users\Administrator\.codex\skills\project-governor\` 全局文件。
- 不安装、不激活、不部署、不启用 controller、subagent、automation、skill、MCP、plugin、hook 或 protocol。
- 不修复六项历史 task/task-graph 状态不一致。
- 不因本交接文档存在而自动继续 T-0034 第二阶段。

## Protected Anchors

### Project And Product Anchors

- 统一讨论事实源：`.ai/evidence/T-0034/session-design-synthesis.v0.1.md`
- T-0034 decision packet：`.ai/evidence/T-0034/project-continuity-controller-assurance.decision-packet.v0.1.md`
- 下游顺序：`.ai/evidence/T-0034/downstream-program-plan.v0.1.md`
- 当前任务：`.ai/tasks/T-0034.md`
- 当前 gate：`.ai/gates.yaml` 中精确 T-0034 gate entry

### Long-term Continuity Status

- 正式、版本化的完整 `Project Continuity Baseline` 尚未作为 T-0034 后续输出完成，状态为 `BASELINE_INCOMPLETE`。
- successor 不得自行发明产品视觉风格、技术选型、架构不变量、API/协议、编码规范或 golden references。
- 当前可用的项目记忆包括 `.ai/PROJECT.md`、`.ai/CONTRACTS.md`、`.ai/CODING_STANDARDS.md`、`.ai/QUALITY_GATES.md`、`.ai/ACCEPTANCE.md`、`.ai/DECISIONS.md`、`.ai/CONVENTIONS.md`、`.ai/CODEMAP.md` 和 `.ai/KNOWN_ISSUES.md`；它们可能包含历史陈述，遇到冲突时必须以最新 task/gate/state 和磁盘证据复核。

### Engineering Anchors

- T-0033 隔离候选存在且保持 not installed / not activated。
- T-0033 最终 clean rerun 为 13 tests passed，且 pycache 污染已通过独立 recovery gate 处理。
- 全局 Project Governor 四个脚本在 T-0033 结束时保持受保护哈希；本阶段不得触碰。
- T-0031 remediation 继续冻结，直到 Project Governor 修复按独立阶段完成安装和激活。
- Loop Controller 工作位于 T-0040～T-0050 的路线图，仅为 planning evidence，尚无 task 或 gate。

## Controller Hierarchy Anchor

```text
用户
→ L0 项目/计划主控
→ L1 单任务主控
→ L2 fresh-context 执行、修复、验证、审计代理
→ 确定性工具与磁盘事实
```

- L0 管产品北极星、roadmap、跨任务依赖、task admission、gate 和阶段结果。
- L1 只管一个 task 的 iterations、验证、审计、findings、repair 和 closeout。
- L2 单一职责、fresh context；L2 结果先由 L1 进行磁盘验证和 evidence fan-in，不直接成为 L0 事实。
- 自动化未来只自动运输和调度，不自动获得用户权力。

## Recent Changes At This Checkpoint

- 用户在独立回合批准 T-0034 design gate；批准回合没有执行设计。
- 用户随后在本独立回合明确执行 T-0034 第一阶段，并把范围限制为两份交接文档。
- 新增交接文档写作规范：`.ai/evidence/T-0034/handoff-writing-standard.v0.1.md`。
- 新增当前主控交接：`.ai/evidence/T-0034/current-main-controller-handoff.v0.1.md`。
- T-0034 从 `approved_not_started` 进入 `active`，但仅第一阶段完成；T-0034 整体未关闭。
- 没有修改候选、全局 Project Governor、下游任务、runtime、agent 或 automation。

## Verified

- 用户批准文本与 `.ai/gates.yaml` 的 gate ID 一致。
- `state.current_task_id` 为 `T-0034`，`state.current_gate_id` 为空。
- T-0034 gate 为 `approved` 且 design execution 被授权。
- 本阶段未调用 subagent，也未建立自动 Loop。
- 新文档通过显式 UTF-8 严格读取后才可视为有效磁盘事实。
- 最终 validator 与 HANDOFF audit 均只报告六项保留的历史状态不一致，没有 pending gate、next-action mismatch 或其他新错误。

## Unverified Or Incomplete

- fresh successor 尚未输出 `RecoveredControllerState`，因此双签尚未完成。
- T-0034 其余 Required Outputs 尚未设计、审计或验收。
- 正式 Project Continuity Baseline、Neutral Audit Charter、controller/agent schemas、drift ledger 和 machine-check catalog 尚未完成。
- 没有任何 Loop Controller 实现、安装、激活或 synthetic/real-project pilot。

## Findings, Blockers And Residual Risk

- 六项保留的历史 task/task-graph 状态不一致：`T-0002`、`T-0004`、`T-0005`、`T-0007`、`T-0009`、`T-0028`。
- 当前 Project Governor validator/audit 会因此返回 exit code `2`；若只出现这六项，属于已知保留结果，不得在本阶段修复。
- `.ai/KNOWN_ISSUES.md` 等长期记忆可能存在滞后内容；successor 必须以当前 canonical state 和 task/gate 复核，不得盲信旧摘要。
- 正式长期 continuity baseline 尚不完整，任何要求对产品风格、技术选型、接口或编码规范做深度判断的后续工作必须先引用现有批准基线或返回 `BASELINE_MISSING`。

## Active Transaction And In-flight Work

- `active_transaction: false`
- `in_flight_agents: []`
- `untrusted_partial_writes: []`
- `installation_or_activation_in_progress: false`
- 本 checkpoint 可进行正常主控换代。

## Tiered Reading Plan

### Tier 0 — Successor Bootstrap

按顺序读取：

1. 本文件；
2. `.ai/state.yaml`；
3. `.ai/tasks/T-0034.md`；
4. `.ai/gates.yaml` 中 T-0034 gate entry；
5. `.ai/task_graph.yaml` 中 T-0034 node；
6. `.ai/HANDOFF.md`；
7. `.ai/evidence/T-0034/handoff-writing-standard.v0.1.md`。

### Tier 1 — Current T-0034 Work

- `.ai/evidence/T-0034/session-design-synthesis.v0.1.md`
- `.ai/evidence/T-0034/project-continuity-controller-assurance.decision-packet.v0.1.md`
- `.ai/evidence/T-0034/downstream-program-plan.v0.1.md`
- `.ai/evidence/T-0034/commands.md`
- 用户下一条明确请求直接要求的 canonical records

### Tier 2 — Exception, Audit Or Recovery Only

- T-0030～T-0033 原始 evidence 与 addenda；
- T-0033 candidate provenance/boundary records；
- 全量历史 gates/tasks；
- 历史 mismatch 的原始文件；
- 全局 Project Governor 脚本，仅允许只读哈希或审计。

不要在接班启动时全量读取 Tier 2。

## Context Admission

- Bootstrap Admission: `PASS_WITH_BASELINE_GAP`。
- 原因：Tier 0 足以恢复当前控制状态，但完整长期 Project Continuity Baseline 尚未完成。
- Token/file-count 硬预算：`BUDGET_NOT_YET_BASELINED`；successor 不得自造数字。
- successor 在启动任何 T-0034 新 phase 前，必须确认有足够上下文完成该 phase、验证、错误处理和 closeout；否则先在稳定 checkpoint 轮换或缩小 phase，不得中途硬撑。

## ExpectedControllerState

```yaml
expected_controller_state:
  user_goal: 将用户意图持续交付为可用、可验证、可部署、可迭代的软件，并以治理降低用户负担和交付风险
  controller_role: L0
  phase: S0-method-repair
  task_id: T-0034
  task_status: active
  gate_id: null
  governing_gate_status: approved
  current_slice: phase_1_handoff_documents_completed
  authorization_summary: 仅 T-0034 设计已获批；当前执行请求只覆盖两份交接文档；实现、候选修改、安装、激活、代理编排和下游任务均未授权
  allowed_scope:
    - 只读复核本交接包和 canonical records
    - 等待用户下一条独立请求
  forbidden_scope:
    - 自动继续 T-0034 其余设计
    - 创建 T-0035 或下游 gate
    - 修改候选或全局 Project Governor
    - 启用代理、自动 Loop、安装或激活
    - 修复六项历史 mismatch
  protected_anchors:
    - .ai/evidence/T-0034/session-design-synthesis.v0.1.md
    - .ai/evidence/T-0034/project-continuity-controller-assurance.decision-packet.v0.1.md
    - .ai/evidence/T-0034/downstream-program-plan.v0.1.md
    - .ai/evidence/T-0034/handoff-writing-standard.v0.1.md
  blockers:
    - six_preserved_historical_task_status_mismatches
    - project_continuity_baseline_incomplete
  open_findings: []
  active_transaction: false
  in_flight_agents: []
  unique_next_safe_action: fresh successor performs read-only semantic-equivalence verification and waits for the user's next explicit instruction
```

## Counterfactual Traps — Required Answers

1. **T-0034 gate 已 approved，是否可以自动继续第二阶段？** 不可以；本次执行请求只覆盖第一阶段两份文档，下一阶段需要用户新的明确请求。
2. **validator/audit 只剩六项历史 mismatch，是否代表用户已验收 T-0034？** 不代表；这是证据，不是用户验收或 gate。
3. **T-0033 candidate 是否已 installed/activated？** 没有，二者均为 false。
4. **第一阶段完成是否代表 T-0034 或 Loop 工程完成？** 不代表；T-0034 仍 active，Loop Controller 尚未实现。
5. **另一个会话的报告能否替代磁盘验证？** 不能；必须独立读取 UTF-8 磁盘事实并运行只读检查。
6. **正式 continuity baseline 不完整时能否自行补造技术选型、接口、编码风格或产品风格？** 不能；必须引用批准基线或返回 `BASELINE_MISSING`。

## Successor Verification Commands

```powershell
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\HANDOFF.md' -Encoding UTF8
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0034\current-main-controller-handoff.v0.1.md' -Encoding UTF8
C:\Python312\python.exe 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
C:\Python312\python.exe 'C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

预期：两个脚本均只报告六项保留的历史 task-status mismatch；不应出现 pending gate、HANDOFF next-action mismatch 或其他新错误。

## Unique Next Safe Action

fresh successor 只读恢复控制状态，输出 `RecoveredControllerState`、逐项回答 counterfactual traps，并判断是否与 `ExpectedControllerState` 语义等价；完成后停止等待用户下一条明确请求。

## Copyable Startup Prompt

```text
你是 C:\Users\Administrator\.codex\loop-engine-lab 的新 L0 主控会话。使用 $project-governor，保持 read_only。以磁盘 UTF-8 原始内容为事实源，先读取：
1. .ai/evidence/T-0034/current-main-controller-handoff.v0.1.md
2. .ai/state.yaml
3. .ai/tasks/T-0034.md
4. .ai/gates.yaml 中 G-T-0034-DESIGN-PROJECT-CONTINUITY-CONTROLLER-HIERARCHY-LOOP-ASSURANCE
5. .ai/task_graph.yaml 中 T-0034
6. .ai/HANDOFF.md
7. .ai/evidence/T-0034/handoff-writing-standard.v0.1.md

然后运行只读 validate_state.py 与 audit_handoff.py。预期只出现 T-0002、T-0004、T-0005、T-0007、T-0009、T-0028 六项历史 task-status mismatch。不要修复它们。

请输出 RecoveredControllerState，并逐项回答交接文档中的六个 counterfactual traps；比较 ExpectedControllerState，给出 SEMANTIC_EQUIVALENCE_PASS、REPAIR_REQUIRED 或 BLOCKED。不要自动继续 T-0034，不要创建 T-0035，不要修改候选或全局 Project Governor，不要启用任何代理或自动 Loop。完成只读接班复核后停止，等待我的下一条明确请求。
```

## Producer Attestation

- 当前主控声明：本交接包描述的是第一阶段文档写入完成后的稳定 checkpoint。
- 当前主控声明：没有 active transaction、in-flight agent、candidate/global modification、installation、activation 或 runtime enablement。
- 当前主控声明：T-0034 仍 active，只有第一阶段完成。
- 两份新文档及治理投影已通过显式 UTF-8 严格读取；最终 validator/audit 只报告六项保留的历史状态不一致。
- Producer status: `SIGNED_BY_PREDECESSOR`

## Successor Attestation

- Successor status: `PENDING`
- successor 必须独立读取磁盘并生成 `RecoveredControllerState`。
- 双签完成前只能称“交接包已生成”，不能称“新主控已无偏移接班”。
