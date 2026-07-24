# Handoff

## Product Direction And Authority

<!-- PROJECT-GOVERNOR-PROJECT-CONTINUITY-BEGIN -->
```json
{
  "authorization_boundaries": {
    "allowed_effects": ["read", "write governance files"],
    "current_gate_id": "G-T-0040-IMPLEMENT",
    "forbidden_effects": ["deploy", "rollback", "database", "permission", "secret", "payment", "production_data", "migration"]
  },
  "persisted_file_sha256": "FD12C5FDD8118EA2D7F5B0C5AC685C9709FAD0E3FB411A924726AF1E2F2E88BE",
  "product_identity": {
    "north_star": "每个非技术用户都能借助AI交付可用软件",
    "one_sentence_outcome": "帮助无代码能力的用户以Loop工程方式从需求到可交付软件",
    "project_id": "loop-engine",
    "success_signals": ["治理流程可被非技术用户理解", "gate机制有效阻断未授权操作", "证据链完整可审计"]
  },
  "project_id": "loop-engine",
  "protected_decisions": [
    {"authority_ref": "user", "change_policy": "需用户显式gate批准", "decision_id": "MEANS_END_BOUNDARY", "rationale_ref": ".ai/DECISIONS.md", "statement": "AI负责手段，用户负责目标和gate批准"},
    {"authority_ref": "user", "change_policy": "不可变更", "decision_id": "USER_AUTHORITY", "rationale_ref": ".ai/DECISIONS.md", "statement": "只有用户能批准gate、拒绝gate、请求修复"},
    {"authority_ref": "user", "change_policy": "需用户显式gate批准", "decision_id": "CODEX_DELIVERY_RESPONSIBILITY", "rationale_ref": ".ai/DECISIONS.md", "statement": "AI负责在批准范围内完成交付"},
    {"authority_ref": "user", "change_policy": "不可变更", "decision_id": "EVIDENCE_ONLY_BOUNDARY", "rationale_ref": ".ai/DECISIONS.md", "statement": "reviewer PASS、测试通过、validator成功仅为evidence，不替代用户批准"}
  ],
  "schema": "ProjectContinuityProjection/v1",
  "semantic_sha256": "8F32DFDC8DF0D3B5F6BA4993193CD8DD0CEBC44294317B5A04DAA355C51A8847",
  "source_sha256": "17EB58373EE234058D5CBFAB013570D6097633A294FBD56774E3499A10765BF3",
  "user_origin": {"audience": "单人AI辅助软件研发", "capability_assumptions": ["用户无代码能力", "用户无项目管理背景"], "user_authorities": ["批准gate", "拒绝gate", "请求修复", "提出目标"]}
}
```
<!-- PROJECT-GOVERNOR-PROJECT-CONTINUITY-END -->

## Current Phase

S6-delivery

## Current Task

T-0040: P0 消除模型自觉依赖 — EnforcementHub + Hook 增强 + 角色隔离 HARD 阻断

Status: `completed`

## Current Gate

G-T-0040-IMPLEMENT: approved (2026-07-23)

## Recent Changes

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

## Next Session First Step

USER_DECISION_REQUIRED — 审查 v3.0.0 T-0040 交付结果，决定是否批准 / 要求修复 / 进入下一阶段

## Startup Prompt

Use $project-governor, validate structured state, and continue only inside the approved scope.
