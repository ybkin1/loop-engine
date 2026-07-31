# T-0087 验收报告（acceptance-report）

> **T-0087: 运行时契约化 — U1 checkers/guards 注册表化 + U2 vertical_slice 契约平面化 | 2026-08-01**
> Gate: G-T-0087-REQUIREMENTS（user 批准，approval_text="批准 T-0087 需求"）
> 独立审查：GO（7/7 AC，无 P0/P1/P2）

## AC 验收矩阵

| AC | 标准 | 结果 | 证据 |
|---|---|---|---|
| AC-01 | 注册表 seal 不可变 + 快照确定性指纹 | ✅ PASS | capability_registry.py：seal 后 register 抛 RuntimeError；canonical_json 键排序 → sha256 snapshot_id；MappingProxyType 只读；4 测试 + CLI 实跑复现同指纹 |
| AC-02 | guard_health 三类检测（dead/missing/drift） | ✅ PASS | missing_detection/drift_detection 为 report 级（test_missing_drift_are_report_level_and_never_flip_overall）；death 保持 fail-closed（test_death_detection_stays_fail_closed） |
| AC-03 | 重水合 fail-closed | ✅ PASS | rehydrate：版本/契约不匹配 → ValueError；未知 → LookupError；篡改 snapshot_id → ValueError；6 测试全过 |
| AC-04 | 契约平面 ≥4 + conformance + 门禁双分支 | ✅ PASS | planes.yaml 4 平面 + VS-GS-001~004 每场景 4 平面断言 + conformance.py 门禁；篡改真实证据 final_decision→NOGO → gate FAIL（真实性证明）；PASS/FAIL 双分支有测试 |
| AC-05 | 需求注册表落盘 | ✅ PASS | 12 条需求 VS-REQ-001..012（ID/描述/plane/covered_by/status）+ 证据镜像 byte 一致（防漂移测试） |
| AC-06 | 全量测试无回归 | ✅ PASS | 2914 passed / 63 skipped / 12 xfailed / 0 failed（基线 2856 +58 = 新增测试） |
| AC-07 | 无约束被弱化 | ✅ PASS | hooks/ 零改动；enforcement/hard_constraints/state_machine 零改动；guard_health diff 纯增量（overall 仍由 death 驱动）；conformance 门禁为收紧方向 |

## 交付物清单

1. `loop_core/capability_registry.py`（新，~300 行）
2. `loop_core/guard_health.py`（+130 行：missing/drift/integrity_check）
3. `tools/tool_registry_status.py`（新 CLI）
4. `tests/test_capability_registry.py`（新，21 测试）
5. `tests/vertical_slice/conformance.py` + `test_contract_planes.py`（新，37 测试）
6. `tests/vertical_slice/contract_planes/`：planes.yaml + 2 JSON Schema + 4 golden 场景 + requirement-registry.yaml（12 条）
7. `.ai/evidence/T-0087/`：approval/execution/compile-evidence + capability-registry/（design + status.json）+ contract-planes/（design + 注册表镜像 + conformance-report.json）+ commands + acceptance

## 治理记录

- 任务登记：task_graph T-0087 + edge T-0086→T-0087；gates G-T-0087-REQUIREMENTS（用户消息批准）；state current_task_id=T-0087
- 启动证据：approval/execution/compile 全就位；T-0083 双 status 位遗留修复
- 派发记录：developer ×2 并行（U1/U2）、independent-reviewer ×1（GO）
- 全程零越界写入（diff 审查）；约束层零改动

## 最终裁决

**GO**（独立审查 GO，7/7 AC 全 PASS）

## 已知遗留（P3，记录）

- 死导入 F401（guard_health.py hashlib/CapabilityBinding；capability_registry.py field）—— content_guard lint 门连锁拦截，建议子代理或后续任务清理
- lint 风格项（UP045 等 12 项）与仓库基线一致
- 全量测试 STALE_GATE_REFERENCE 警告为既有测试故意行为
