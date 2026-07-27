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
  "persisted_file_sha256": "0D2770473D03BE9F2566EC8FF0C30262BD6C2B37DFCB1920D8203DA08D33D30D",
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
  "source_sha256": "3DEAB75E885138A6B8D049F9E569214E9A9DA098FDDA8395B5DE654794423271",
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

T-0052

Status: `in_progress`

## Current Gate

pending_gate_status: none (no pending decision required)
active_gate: G-T-0052-COMPREHENSIVE-REMEDIATION
active_gate_status: approved / in_progress

current_gate_id is null because no pending decision is required.
G-T-0052-COMPREHENSIVE-REMEDIATION is approved and execution is in progress.

## Allowed Scope

Defined by the active gate's allowed_paths in gates.yaml.

## Forbidden Scope

Defined by the active gate's forbidden_actions in gates.yaml.

## Verified

See Structured Lifecycle block below.

## Unverified

See Structured Lifecycle block below.

## Evidence

Evidence is recorded in .ai/evidence/<task_id>/ and verified via evidence-manifest.

## Integration Impact

No integration impact assessed. See checkpoint block below.

## Next Session First Step

CONTINUE_APPROVED_EXECUTION

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
  "approved_execution_gate_id": "G-T-0052-COMPREHENSIVE-REMEDIATION",
  "approved_execution_status": "in_progress",
  "current_gate_id": "G-T-0052-COMPREHENSIVE-REMEDIATION",
  "current_task_id": "T-0052",
  "current_task_status": "in_progress",
  "lifecycle_revision": 0,
  "next_action": "CONTINUE_APPROVED_EXECUTION",
  "schema": "ProjectGovernorNextAction/v2"
}
```
<!-- PROJECT-GOVERNOR-NEXT-ACTION-END -->

## Checkpoint

<!-- PROJECT-GOVERNOR-CHECKPOINT-BEGIN -->
```json
{
  "authority_hash": "2337C69A376EF942A0249978571E61B1BCAB58F34037DDAA88E14B5109EE6FC3",
  "blockers": [],
  "checkpoint_id": "CP-3C9E731E405DA5A37E6FB44A",
  "checkpoint_status": "PENDING_SUCCESSOR_ACK",
  "contract_id": "PCC-2026-07-16-R1",
  "controller_generation": 1,
  "evidence_manifest_hashes": {
    "file_count": 6,
    "manifest_file_sha256": "9E16DEC7C8350C8DDB5E4270CE0B2D2E7C0B0966876A55707887FF06C458BEFC",
    "ordered_entries_sha256": "0A13AABEC2EB4A58D9F25DD8381B8C14DA5D705BBEA286FAB08FDF5EDD061D52",
    "semantic_sha256": "C2159D158CB80BD4615D90FA2CD699AA295FE37CDE31BBCE0F98BAA1EC4FB220",
    "total_bytes": 7593
  },
  "fixture_only": false,
  "project_continuity_hashes": {
    "file_sha256": "0D2770473D03BE9F2566EC8FF0C30262BD6C2B37DFCB1920D8203DA08D33D30D",
    "semantic_sha256": "4A628D77A09C427695A4CADA20E21A8E91A5C311CCB92D278B4990B0A1D4DE9C",
    "source_sha256": "3DEAB75E885138A6B8D049F9E569214E9A9DA098FDDA8395B5DE654794423271"
  },
  "recovered_state_sha256": "C979FDBFD77D2C99D15B271707BCD812A86505DDB3FD9F221A7C3961F1279AEB",
  "requirements_revision": "T-0034-REQ-2026-07-16-R1",
  "schema": "Checkpoint/v1.0",
  "task_scope_hash": "387F12B9F31D5D0F307498E063C27A45AA8CB08A5C1D2208096B88B556EF84BE",
  "transaction_registry_hashes": {
    "checkpoint_semantic_sha256": "5C99D5C2425154741AE25217E824B17AFD734D3AA776286F4ED7A94647901BCE",
    "file_sha256": "0D99CF029CBF0D360725195E8B0825832E019976EEF988A9EFFDD2F7B01301CE",
    "semantic_sha256": "2CF3351B01F4A75E5114D8EEED9B0C418079516C0CDD264A4579ED4299A7F555",
    "source_sha256": "CBCD552B56BA77B10A11A38257B965B0009162F67E0F196B6824CFD44AC06262"
  }
}
```
<!-- PROJECT-GOVERNOR-CHECKPOINT-END -->
