# T-0087 Commands

任务：运行时契约化 — checkers/guards 注册表化（U1）+ vertical_slice 契约平面化（U2）
Gate：G-T-0087-REQUIREMENTS（approved 2026-08-01，approval_text="批准 T-0087 需求"）

## 登记与启动

1. 创建 `.ai/tasks/T-0087.md`（含 allowed_paths: YAML 契约字段）
2. 更新 `.ai/task_graph.yaml` — 登记 T-0087（in_progress）+ edge T-0086→T-0087
3. 更新 `.ai/gates.yaml` — 登记 G-T-0087-REQUIREMENTS（用户消息即批准，直接记录 approved）
4. 更新 `.ai/state.yaml` — current_task_id=T-0087, current_gate_id=G-T-0087-REQUIREMENTS
5. 创建 `.ai/evidence/T-0087/approval-evidence.json`、`execution-evidence.json`
6. `compile_gate.py . --output .ai/evidence/T-0087/compile-evidence.json`
7. `repair_continuity.py .` + `close_session.py .` — 连续性/HANDOFF 同步
8. `validate_state.py .` — [ok] state is usable
9. 顺手修复：`.ai/tasks/T-0083.md` 双 status 位（表格 + ## Status 段）→ completed（历史遗留 warn 消除）

## 实现（developer 子代理 × 2 并行）

### U1 能力注册表化（agent_88b7df4a）
10. 新增 `loop_core/capability_registry.py`（~300 行）— CapabilityBinding（frozen + implementation_hash）/ CapabilityRegistry（register/seal/require/snapshot/rehydrate）/ CapabilitySnapshot（MappingProxyType 只读 + canonical_json + sha256 snapshot_id）/ build_default_registry（内容寻址版本：__version__ 常量或文件 sha256 前缀）
11. 新增 `tools/tool_registry_status.py` — 注册表状态 CLI（exit 0=健康 / 1=仅 report 级 / 2=guard 死亡 fail-closed）
12. 新增 `tests/test_capability_registry.py`（21 测试：seal 不可变/快照确定性/rehydrate fail-closed 6 例/missing/drift/death 语义）
13. 修改 `loop_core/guard_health.py`（+130 行纯增量）— registry 注入 + missing_detection（MISSING report）+ drift_detection（DRIFT report）+ integrity_check（overall 仅由 death 驱动，死亡 fail-closed 保持）
14. 证据：`.ai/evidence/T-0087/capability-registry/design.md` + `status.json`（snapshot_id 116fd5bc…，4 绑定，missing 0 / drift 0，overall PASS）

### U2 契约平面化（agent_8385dd38）
15. `tests/vertical_slice/` 新增 9 文件：conformance.py（9 类断言 + 需求状态计算 + 报告 + fail-closed 门禁 CLI 退出码 0/1）+ test_contract_planes.py（37 测试）+ contract_planes/planes.yaml（4 平面）+ scenario.schema.json + registry.schema.json + golden_scenarios/VS-GS-001~004.json（正向端到端/负向 gate 拒绝/状态机合法性/7 角色裁决收敛）+ requirement-registry.yaml（12 条需求 VS-REQ-001..012）
16. 证据：`.ai/evidence/T-0087/contract-planes/design.md` + requirement-registry.yaml（镜像，byte 一致防漂移测试）+ conformance-report.json（12/12 implemented，4/4 场景，gate PASS）
17. 门禁真实性：开发中 gate 曾真实 FAIL 两次（count_equals 用于 dict、S2→S4 直跳非法）→ 修复后 PASS

## 治理同步（主会话）

18. 独立审查（agent_c6885266）：GO — 7/7 AC PASS，约束层零改动，无 P0/P1/P2，仅 3 项 P3
19. P3-1 死导入清理尝试被 content_guard lint 门拦截（F401/F821 连锁）→ 记录遗留，后续任务处理
20. 落盘 `.ai/evidence/T-0087/commands.md` + `acceptance/acceptance-report.md`

## 验收

21. 全量测试：2914 passed / 63 skipped / 12 xfailed / 0 failed（较 T-0086 基线 2856 增量 +58 = 新增测试数）
22. 状态收敛（task_graph T-0087 completed + state idle）+ close_session 重建 HANDOFF
23. git 提交 v3.12.26

## 发现（P3 遗留，记录）

- 死导入：guard_health.py L28 hashlib / L39 CapabilityBinding；capability_registry.py L30 field（ruff F401）—— content_guard lint 门阻止主会话直接清理（连锁 lint），建议子代理或后续任务处理
- 证据目录规范：.ai/evidence/T-0087/ 无 commands.md/acceptance/ 时执行中（现已补）；execution-evidence 完成标记已更新
- 既有 UP045 等 lint 风格项与仓库基线一致，非回归
- 全量测试 STALE_GATE_REFERENCE 警告来自既有测试故意传假 gate id（test_state_machine_enhanced.py:224），与 T-0087 无关
