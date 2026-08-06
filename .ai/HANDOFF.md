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
  "persisted_file_sha256": "CD1D613057DBC6C174525F461DB2FD008A2E5511E55EC33868F0259A2FF4D56E",
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
  "source_sha256": "AC2BE1EA963836366725D830BA0A7C858AAF8098747D9FDB2FE47D4B537018BD",
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

T-0125

Status: `completed`

## Current Gate

pending_gate_status: none (no pending decision required)
active_gate: G-T-0125-REQUIREMENTS
active_gate_status: approved / approved_not_started

current_gate_id is null because no pending decision is required.
G-T-0125-REQUIREMENTS is approved and execution is in progress.

## Allowed Scope

Defined by the active gate's allowed_paths in gates.yaml.

## Forbidden Scope

Defined by the active gate's forbidden_actions in gates.yaml.

## Verified

- STRUCTURED_STATE_HASHES_VERIFIED

## Unverified

- FRESH_INDEPENDENT_REREVIEW_NOT_PERFORMED

## Evidence

Evidence manifest: .ai/evidence/T-0125/evidence-manifest.v1.yaml.

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
  "approved_execution_gate_id": "G-T-0125-REQUIREMENTS",
  "approved_execution_status": "approved_not_started",
  "current_gate_id": "G-T-0125-REQUIREMENTS",
  "current_task_id": "T-0125",
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
  "authority_hash": "AD84BDA636591BD50C2FE316F345ED46616CC094CE3B252C6981538D105360C3",
  "blockers": [],
  "checkpoint_id": "CP-F672775464EE7E8E7C8A9336",
  "checkpoint_status": "PENDING_SUCCESSOR_ACK",
  "contract_id": "PCC-2026-07-16-R1",
  "controller_generation": 1,
  "evidence_manifest_hashes": {
    "file_count": 5,
    "manifest_file_sha256": "EAC1854E047D6B664B99A8CEC7AE09E8D98AC3ECB127FA3F6D33015B430E46C7",
    "ordered_entries_sha256": "1C476AC50FB25FE928FF6D7416747A3A05039B1EAEA0ABAC1489BAA8783C19C5",
    "semantic_sha256": "133F61E5D748BB7EA3F9C9A2D04DF2CDF3B140CF47A830C690D211E0E2FEC25F",
    "total_bytes": 5801
  },
  "fixture_only": false,
  "project_continuity_hashes": {
    "file_sha256": "CD1D613057DBC6C174525F461DB2FD008A2E5511E55EC33868F0259A2FF4D56E",
    "semantic_sha256": "4A628D77A09C427695A4CADA20E21A8E91A5C311CCB92D278B4990B0A1D4DE9C",
    "source_sha256": "AC2BE1EA963836366725D830BA0A7C858AAF8098747D9FDB2FE47D4B537018BD"
  },
  "recovered_state_sha256": "35C6B20208DDF8BFB8A6540ABD39DEAA6FB8E5F841626163366F10207CAF50FA",
  "requirements_revision": "T-0034-REQ-2026-07-16-R1",
  "schema": "Checkpoint/v1.0",
  "task_scope_hash": "4845BBE3E15AEAE1167ED39BBC550508CF4124CAEC97EA9398557D300C03D802",
  "transaction_registry_hashes": {
    "checkpoint_semantic_sha256": "5C99D5C2425154741AE25217E824B17AFD734D3AA776286F4ED7A94647901BCE",
    "file_sha256": "0D99CF029CBF0D360725195E8B0825832E019976EEF988A9EFFDD2F7B01301CE",
    "semantic_sha256": "2CF3351B01F4A75E5114D8EEED9B0C418079516C0CDD264A4579ED4299A7F555",
    "source_sha256": "CBCD552B56BA77B10A11A38257B965B0009162F67E0F196B6824CFD44AC06262"
  }
}
```
<!-- PROJECT-GOVERNOR-CHECKPOINT-END -->
