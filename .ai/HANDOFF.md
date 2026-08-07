# Handoff

> **权威层级**: state.yaml > gates.yaml > task_graph.yaml > HANDOFF.md
> HANDOFF 是连续性辅助信息，不得重新定义状态。所有状态以机器可读文件为准。

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
  "persisted_file_sha256": "0A28A67840E75774388448D9B8B1F16F2C18281FF609146E1BAD410F6471EBA3",
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
  "semantic_sha256": "4A628D77A09C427695A4CADA20E21A8E91A5C311CCB92D278B4990B0A1D4DE9C",
  "source_sha256": "944B2A6D2170A4AC710C3B46E095A55038E4B4979BB24F01B823B053264A7D15",
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

T-0155

Status: `completed`

## Current Gate

pending_gate_status: none (no pending decision required)
active_gate: G-T-0155-REQUIREMENTS
active_gate_status: approved / completed

current_gate_id is null because no pending decision is required.
G-T-0155-REQUIREMENTS is approved and execution is in progress.

## Allowed Scope

Defined by the active gate's allowed_paths in gates.yaml.

## Forbidden Scope

Defined by the active gate's forbidden_actions in gates.yaml.

## Verified

- STRUCTURED_STATE_HASHES_VERIFIED

## Unverified

- FRESH_INDEPENDENT_REREVIEW_NOT_PERFORMED

## Evidence

Evidence manifest: .ai/evidence/T-0155/evidence-manifest.v1.yaml.

## Integration Impact

Checkpoint status: PENDING_SUCCESSOR_ACK.
Blockers: none.

## Next Session First Step

TASK_COMPLETED_AWAIT_NEXT

## Startup Prompt

Use $project-governor, validate structured state, and continue only inside the approved scope.

提醒：reviewer PASS / validator / 测试通过均为 evidence，不等于用户批准。

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
    "FRESH_INDEPENDENT_REREVIEW_NOT_PERFORMED"
  ],
  "verified": [
    "STRUCTURED_STATE_HASHES_VERIFIED"
  ]
}
```
<!-- PROJECT-GOVERNOR-LIFECYCLE-END -->

## Structured Next Action

<!-- PROJECT-GOVERNOR-NEXT-ACTION-BEGIN -->
```json
{
  "approved_execution_gate_id": "G-T-0155-REQUIREMENTS",
  "approved_execution_status": "completed",
  "current_gate_id": "G-T-0155-REQUIREMENTS",
  "current_task_id": "T-0155",
  "current_task_status": "completed",
  "lifecycle_revision": 0,
  "next_action": "TASK_COMPLETED_AWAIT_NEXT",
  "schema": "ProjectGovernorNextAction/v2"
}
```
<!-- PROJECT-GOVERNOR-NEXT-ACTION-END -->

## Checkpoint

<!-- PROJECT-GOVERNOR-CHECKPOINT-BEGIN -->
```json
{
  "authority_hash": "1A0EC6C0F3CA91CDF181697A46FE61EDB870D3F87FE41F2687DFF5F4026E37AA",
  "blockers": [],
  "checkpoint_id": "CP-354AA95FC72E83D8769F60E0",
  "checkpoint_status": "PENDING_SUCCESSOR_ACK",
  "contract_id": "PCC-2026-07-16-R1",
  "controller_generation": 1,
  "evidence_manifest_hashes": {
    "file_count": 3,
    "manifest_file_sha256": "03CCC546BB5BCE6B224DFF3693E4006D40FB5269B758A1B39F9E6BB95015184F",
    "ordered_entries_sha256": "0C02F19B12D131C58A72C241FF284692CA3E9E11D440C73AC6033F05DDA1059E",
    "semantic_sha256": "3D18C57980023BA6DDC6B58F7B9CA24962CB1620CB7604AB128A3173560FC437",
    "total_bytes": 911
  },
  "fixture_only": false,
  "project_continuity_hashes": {
    "file_sha256": "0A28A67840E75774388448D9B8B1F16F2C18281FF609146E1BAD410F6471EBA3",
    "semantic_sha256": "4A628D77A09C427695A4CADA20E21A8E91A5C311CCB92D278B4990B0A1D4DE9C",
    "source_sha256": "944B2A6D2170A4AC710C3B46E095A55038E4B4979BB24F01B823B053264A7D15"
  },
  "recovered_state_sha256": "834A414861C62D804E7356BA0220B89800E9372048226752B4675C24D0468EDB",
  "requirements_revision": "T-0034-REQ-2026-07-16-R1",
  "schema": "Checkpoint/v1.0",
  "task_scope_hash": "2B1D6DD348ADF755C0A3EAAD8AF1D8FFAE193FCA08B5E49AD70414038D32AC92",
  "transaction_registry_hashes": {
    "checkpoint_semantic_sha256": "5C99D5C2425154741AE25217E824B17AFD734D3AA776286F4ED7A94647901BCE",
    "file_sha256": "0D99CF029CBF0D360725195E8B0825832E019976EEF988A9EFFDD2F7B01301CE",
    "semantic_sha256": "2CF3351B01F4A75E5114D8EEED9B0C418079516C0CDD264A4579ED4299A7F555",
    "source_sha256": "CBCD552B56BA77B10A11A38257B965B0009162F67E0F196B6824CFD44AC06262"
  }
}
```
<!-- PROJECT-GOVERNOR-CHECKPOINT-END -->
