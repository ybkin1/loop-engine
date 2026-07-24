# Handoff

## Product Direction And Authority

<!-- PROJECT-GOVERNOR-PROJECT-CONTINUITY-BEGIN -->
```json
{
  "schema": "ProjectContinuityProjection/v1",
  "project_id": "loop-engine",
  "user_origin": {
    "audience": "单人AI辅助软件研发",
    "capability_assumptions": [
      "用户无代码能力",
      "用户无项目管理背景"
    ],
    "user_authorities": [
      "批准gate",
      "拒绝gate",
      "请求修复",
      "提出目标"
    ]
  },
  "product_identity": {
    "project_id": "loop-engine",
    "one_sentence_outcome": "帮助无代码能力的用户以Loop工程方式从需求到可交付软件",
    "north_star": "每个非技术用户都能借助AI交付可用软件",
    "success_signals": [
      "治理流程可被非技术用户理解",
      "gate机制有效阻断未授权操作",
      "证据链完整可审计"
    ]
  },
  "protected_decisions": [
    {
      "decision_id": "MEANS_END_BOUNDARY",
      "statement": "AI负责手段，用户负责目标和gate批准",
      "rationale_ref": ".ai/DECISIONS.md",
      "authority_ref": "user",
      "change_policy": "需用户显式gate批准"
    },
    {
      "decision_id": "USER_AUTHORITY",
      "statement": "只有用户能批准gate、拒绝gate、请求修复",
      "rationale_ref": ".ai/DECISIONS.md",
      "authority_ref": "user",
      "change_policy": "不可变更"
    },
    {
      "decision_id": "CODEX_DELIVERY_RESPONSIBILITY",
      "statement": "AI负责在批准范围内完成交付",
      "rationale_ref": ".ai/DECISIONS.md",
      "authority_ref": "user",
      "change_policy": "需用户显式gate批准"
    },
    {
      "decision_id": "EVIDENCE_ONLY_BOUNDARY",
      "statement": "reviewer PASS、测试通过、validator成功仅为evidence，不替代用户批准",
      "rationale_ref": ".ai/DECISIONS.md",
      "authority_ref": "user",
      "change_policy": "不可变更"
    }
  ],
  "authorization_boundaries": {
    "allowed_effects": [
      "read",
      "write governance files"
    ],
    "forbidden_effects": [
      "deploy",
      "rollback",
      "database",
      "permission",
      "secret",
      "payment",
      "production_data",
      "migration"
    ],
    "current_gate_id": "G-T-0047-HARDENING"
  },
  "source_sha256": "8487009BC9649F1CD7A540AC9426507B5CC7C6854E30FC9083C8915D2DD27FB3",
  "semantic_sha256": "AC02D495F90485360E5435B639AB9FFF81B8A38590C89E1452403B804324ADC4",
  "persisted_file_sha256": "8EA9530E729868FEB3F53F533A35F240E96C5E2E14D797CFFFE8BB6B39A7CCA2"
}
```
<!-- PROJECT-GOVERNOR-PROJECT-CONTINUITY-END -->

## Current Phase

S6-delivery

## Current Task

T-0048: Finalize — Atomic Write + Hook Split Completion + Status Marking + Vertical Slice

Status: `in_progress`

## Current Gate

G-T-0048-FINALIZE: approved+in_progress (2026-07-24)

## Recent Changes

- **2026-07-24: T-0048 — 收尾修复**
  - executor.py 原子写入（.tmp + os.replace）
  - Hook 拆分补全：_hook_state.py, _hook_path.py, _hook_config.py, _hook_sync.py
  - T-0043（角色能力认证）→ completed
  - T-0044（Qoder 借鉴点移植）→ completed
  - T-0041 垂直切片证据：23 tests pass, S0→S6 governance trail documented

- **2026-07-24: T-0047 — 治理关键路径硬化**
  - 修复 Core 层 fail-open → fail-closed（enforcement_hub.py）
    - `_read_state()`, `_read_gates()`, `_read_tasks()` 损坏/缺失时记录错误
    - `should_allow_write()`, `should_allow_phase_advance()`, `quick_check()` 检测后 FAIL CLOSED
  - 修复 role_isolation.py fail-open → fail-closed + 新增 8 个测试
    - state.yaml 损坏 → exit 2（原是 exit 0 静默通过）
    - `tests/test_role_isolation.py`：正常路径 + self-review 阻断 + corruption 路径全覆盖
  - 新增 12 个 enforcement_hub 负面路径测试（corruption/missing/healthy 回归守卫）
  - 总计新增 20 个测试，全部通过

- **2026-07-24: T-0040 — approved → completed**
  - 用户审查 v3.0.0 交付结果后批准
  - 状态从 active 更新为 completed

- **2026-07-23: T-0040 completed — v3.0.0 核心交付**
  - 新增 `loop_core/enforcement_hub.py` — Hook↔Core 治理决策桥梁
    - `should_allow_write()` — C4+C3+C7+phase 约束统一检查
    - `should_allow_phase_advance()` — 阶段推进前置条件验证
    - `check_role_isolation_enforcement()` — HARD 级自评自审阻断
    - `check_evidence_freshness_enforcement()` — C8 证据新鲜度检查
    - `quick_check()` — 轻量整体校验
    - `EnforcementDecision.to_hook_output()` — 标准 hook JSON 输出
    - `EnforcementLevel` 枚举 — HARD/PARTIAL/ADVISORY 能力声明
  - 升级 `hooks/scripts/role_isolation.py` → v2.0 HARD 阻断
    - FULL mode: 自评自审 → `permissionDecision: "deny"` + `exit 2`
    - LIGHTWEIGHT/STANDARD: 保持 WARN-only 向后兼容
  - 新增 `tests/test_enforcement_hub.py` — 39 测试覆盖全 API
  - 注册 gate `G-T-0040-IMPLEMENT` 定义实现范围

## Verified

- 2116 tests passed (0 regression from v2.0.0 baseline)
- 39 new enforcement_hub tests all pass
- role_isolation.py v2.0 logic verified via code review
- EnforcementHub reads .ai/state.yaml, gates.yaml, task_graph.yaml correctly

## Unverified

- role_isolation.py HARD blocking live-fire (needs real ZCode session with distinct agent IDs)
- EnforcementHub hook integration live-fire (needs hook reload)
- External vertical slice (T-0041) — deferred to v3.1

## Evidence

- `loop_core/enforcement_hub.py` — 390 lines, full EnforcementHub implementation
- `hooks/scripts/role_isolation.py` — upgraded to v2.0 with HARD blocking
- `tests/test_enforcement_hub.py` — 39 tests, all passing
- Full regression: 2116 passed, 61 skipped, 18 xfailed

## Pending

- T-0041: 外部垂直切片验证 — 用 loop-engine 交付真实 CLI 工具
- T-0044: 角色能力认证框架 (role_capability.py)
- T-0045: 全 11 角色 CONTRACT.yaml 补齐
- Live-fire verification of hook HARD enforcement


## Allowed Scope

```yaml
allowed_effects:
  - read
  - write governance files (.ai/, hooks/scripts/, .zcode/tools/)
  - update evidence and test files
forbidden_effects:
  - deploy
  - rollback
  - database changes
  - permission changes
  - secret handling
  - payment actions
  - production data modifications
  - migrations
  - modify AGENTS.md
  - install or enable skill/MCP/agent/automation/protocol
  - enter real business project
```

## Forbidden Scope

See Allowed Scope above. Any action not explicitly listed in allowed_effects is forbidden.

## Integration Impact

- gate_guard.py: Gate lifecycle logic fixed (T-0046)
- governor_lib.py: Gate lifecycle semantics aligned
- validate_state.py: Legacy error classification added
- Version consistency: All files aligned to v3.0.0
- Role contracts: test-engineer completed

## Structured Lifecycle

```
current_phase: S6-delivery
current_task: T-0047
current_gate: G-T-0047-HARDENING (approved, in_progress)
task_status: in_progress
```

## Structured Next Action

T-0047 execution: Complete governance hardening, run full regression, record evidence.

## Checkpoint

- Core layer fail-closed: IMPLEMENTED
- role_isolation.py fail-closed: IMPLEMENTED
- Negative path test coverage: 20 new tests added
- Gate lifecycle deadlock: RESOLVED (T-0046)
- Version consistency: RESOLVED (T-0046)
- Historical task mismatches: CLASSIFIED AS LEGACY (T-0046)

## Next Session First Step

USER_DECISION_REQUIRED — 审查 v3.0.0 T-0040 交付结果，决定是否批准 / 要求修复 / 进入下一阶段

## Startup Prompt

Use $project-governor, validate structured state, and continue only inside the approved scope.

<!-- PROJECT-GOVERNOR-NEXT-ACTION-BEGIN -->
```json
{
  "schema": "ProjectGovernorNextAction/v2",
  "current_task_id": "T-0048",
  "current_task_status": "in_progress",
  "current_gate_id": "G-T-0048-FINALIZE",
  "approved_execution_gate_id": "G-T-0048-FINALIZE",
  "approved_execution_status": "in_progress",
  "lifecycle_revision": 0,
  "next_action": "CONTINUE_APPROVED_EXECUTION"
}
```
<!-- PROJECT-GOVERNOR-NEXT-ACTION-END -->

<!-- PROJECT-GOVERNOR-LIFECYCLE-BEGIN -->
```json
{
  "schema": "ProjectLifecycleProjection/v1",
  "verified": [],
  "unverified": [
    "EVIDENCE_MANIFEST_REQUIRED",
    "FRESH_INDEPENDENT_REREVIEW_NOT_PERFORMED"
  ],
  "not_performed": [
    "USER_ACCEPTANCE_NOT_PERFORMED",
    "PRODUCTION_AUTHORITY_LIFECYCLE_UNAVAILABLE"
  ],
  "not_authorized": [
    "INDEPENDENT_REREVIEW_AUTHORIZED",
    "INSTALLATION_AUTHORIZED",
    "ACTIVATION_AUTHORIZED",
    "RUNTIME_TOOL_ENABLEMENT_AUTHORIZED",
    "DOWNSTREAM_TASK_CREATION_AUTHORIZED",
    "REAL_PROJECT_ENTRY_AUTHORIZED"
  ],
  "installation_eligibility": "BLOCKED"
}
```
<!-- PROJECT-GOVERNOR-LIFECYCLE-END -->

<!-- PROJECT-GOVERNOR-CHECKPOINT-BEGIN -->
```json
{
  "schema": "Checkpoint/v1.0",
  "checkpoint_status": "NOT_ESTABLISHED",
  "blockers": [
    "TRANSACTION_REGISTRY_MISSING"
  ]
}
```
<!-- PROJECT-GOVERNOR-CHECKPOINT-END -->
