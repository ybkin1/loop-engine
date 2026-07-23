# Handoff

## Product Direction And Authority

<!-- PROJECT-GOVERNOR-PROJECT-CONTINUITY-BEGIN -->
```json
{
  "authorization_boundaries": {
    "allowed_effects": [
      "read",
      "write governance files"
    ],
    "current_gate_id": null,
    "forbidden_effects": [
      "deploy",
      "rollback",
      "database",
      "permission",
      "secret",
      "payment",
      "production_data",
      "migration"
    ]
  },
  "persisted_file_sha256": "FD12C5FDD8118EA2D7F5B0C5AC685C9709FAD0E3FB411A924726AF1E2F2E88BE",
  "product_identity": {
    "north_star": "每个非技术用户都能借助AI交付可用软件",
    "one_sentence_outcome": "帮助无代码能力的用户以Loop工程方式从需求到可交付软件",
    "project_id": "loop-engine",
    "success_signals": [
      "治理流程可被非技术用户理解",
      "gate机制有效阻断未授权操作",
      "证据链完整可审计"
    ]
  },
  "project_id": "loop-engine",
  "protected_decisions": [
    {
      "authority_ref": "user",
      "change_policy": "需用户显式gate批准",
      "decision_id": "MEANS_END_BOUNDARY",
      "rationale_ref": ".ai/DECISIONS.md",
      "statement": "AI负责手段，用户负责目标和gate批准"
    },
    {
      "authority_ref": "user",
      "change_policy": "不可变更",
      "decision_id": "USER_AUTHORITY",
      "rationale_ref": ".ai/DECISIONS.md",
      "statement": "只有用户能批准gate、拒绝gate、请求修复"
    },
    {
      "authority_ref": "user",
      "change_policy": "需用户显式gate批准",
      "decision_id": "CODEX_DELIVERY_RESPONSIBILITY",
      "rationale_ref": ".ai/DECISIONS.md",
      "statement": "AI负责在批准范围内完成交付"
    },
    {
      "authority_ref": "user",
      "change_policy": "不可变更",
      "decision_id": "EVIDENCE_ONLY_BOUNDARY",
      "rationale_ref": ".ai/DECISIONS.md",
      "statement": "reviewer PASS、测试通过、validator成功仅为evidence，不替代用户批准"
    }
  ],
  "schema": "ProjectContinuityProjection/v1",
  "semantic_sha256": "8F32DFDC8DF0D3B5F6BA4993193CD8DD0CEBC44294317B5A04DAA355C51A8847",
  "source_sha256": "17EB58373EE234058D5CBFAB013570D6097633A294FBD56774E3499A10765BF3",
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
  }
}
```
<!-- PROJECT-GOVERNOR-PROJECT-CONTINUITY-END -->

## Current Phase

S6-delivery

## Current Task

T-0034: P0-001 Runtime Controller + Approval Record + Agent Adapter Baseline

Status: `design`

## Current Gate

G-T-0034-DESIGN: approved (2026-07-23) — design documents produced

## Allowed Scope

- Continue only inside the approved structured Gate scope.

## Forbidden Scope

- No installation, activation, runtime enablement, downstream task, or real-project effect without a separate Gate.

## Recent Changes

- 2026-07-23: T-0034 created (P0-001 baseline). G-T-0034-DESIGN approved.
  4 design docs written: RuntimeController, ApprovalRecord+EvidenceEnvelope,
  AgentAdapter+ZCodeAdapter, gate_guard deadlock root cause analysis.
- P0-E deadlock discovered and analyzed: gate_guard:79-81 unconditionally
  appends current_gate_id to pending without cross-checking gates.yaml status.
- Previous: Hook 注册与缓存副本已同步，待真实 ZCode 会话 live-fire 验证。

## Verified

- none

## Unverified

- EVIDENCE_MANIFEST_REQUIRED
- FRESH_INDEPENDENT_REREVIEW_NOT_PERFORMED

## Evidence

- EvidenceManifest/v1 status: BOUNDED_OR_REQUIRED

## Integration Impact

- Production authority lifecycle available: false
- Installation eligibility: BLOCKED

## Pending Gates And Blockers

- TRANSACTION_REGISTRY_MISSING

## Structured Lifecycle

<!-- PROJECT-GOVERNOR-LIFECYCLE-BEGIN -->
```json
{
  "installation_eligibility": "BLOCKED",
  "not_authorized": [
    "INDEPENDENT_REREVIEW_AUTHORIZED",
    "INSTALLATION_AUTHORIZED",
    "ACTIVATION_AUTHORIZED",
    "RUNTIME_TOOL_ENABLEMENT_AUTHORIZED",
    "DOWNSTREAM_TASK_CREATION_AUTHORIZED",
    "REAL_PROJECT_ENTRY_AUTHORIZED"
  ],
  "not_performed": [
    "USER_ACCEPTANCE_NOT_PERFORMED",
    "PRODUCTION_AUTHORITY_LIFECYCLE_UNAVAILABLE"
  ],
  "schema": "ProjectLifecycleProjection/v1",
  "unverified": [
    "EVIDENCE_MANIFEST_REQUIRED",
    "FRESH_INDEPENDENT_REREVIEW_NOT_PERFORMED"
  ],
  "verified": []
}
```
<!-- PROJECT-GOVERNOR-LIFECYCLE-END -->

## Structured Next Action

<!-- PROJECT-GOVERNOR-NEXT-ACTION-BEGIN -->
```json
{
  "approved_execution_gate_id": null,
  "approved_execution_status": null,
  "current_gate_id": null,
  "current_task_id": null,
  "current_task_status": null,
  "lifecycle_revision": 0,
  "next_action": "USER_DECISION_REQUIRED",
  "schema": "ProjectGovernorNextAction/v2"
}
```
<!-- PROJECT-GOVERNOR-NEXT-ACTION-END -->

## Checkpoint

<!-- PROJECT-GOVERNOR-CHECKPOINT-BEGIN -->
```json
{
  "blockers": [
    "TRANSACTION_REGISTRY_MISSING"
  ],
  "checkpoint_status": "NOT_ESTABLISHED",
  "schema": "Checkpoint/v1.0"
}
```
<!-- PROJECT-GOVERNOR-CHECKPOINT-END -->

## Next Session First Step

USER_DECISION_REQUIRED

## Startup Prompt

Use $project-governor, validate structured state, and continue only inside the approved scope.
