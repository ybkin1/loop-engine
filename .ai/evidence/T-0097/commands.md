# T-0097 Commands

任务：B2 学习回路补全 — incident + 复盘 + second-failure 自动任务
Gate：G-T-0097-REQUIREMENTS（approved 2026-08-02，approval_text="批准T-0095、96、97"）

## 登记与启动

1. 批量登记批次第 3 项；state 串行指向 T-0097
2. 创建 approval/execution-evidence.json；compile_gate 生成 compile-evidence.json
3. `repair_continuity.py` + `close_session.py` + `validate_state.py` — [ok] state is usable
4. 顺手修复：`.ai/tasks/T-0096.md` 双 status 位 → completed

## 实现（developer 子代理 agent_8711a039）

5. 新增 `loop_core/incidents.py` — IncidentRecord（确定性 IN-id/类别/severity/时间线/状态/来源）+ 幂等（同事件去重，异时刻分立）+ 落盘（追加式原子写 + 锁）+ 检索四轴 + register_gate_rejection_incident（gate_lessons ≥2 拒绝 → incident）
6. 新增 `loop_core/retrospectives.py` — Retrospective（RT-id 关联 incident）+ ActionItem（owner/deadline/status，open→done→retro closed，closed 不可变）
7. 新增 `loop_core/second_failure.py` — 复发指纹（类别+来源+归一化根因）+ detect_second_failure（第 2+ 次 → SecondFailureRecord + 任务草稿 [draft]）+ second_failure_block（未解决 BLOCK / 有行动项 PASS / 豁免 / 损坏证据 fail-closed / **默认关闭 opt-in**）
8. 新增 `.ai/checkers/second_failure_checker.py`（compile_gate 同款 CLI 0/1/2 + --detect 维护模式）
9. 修改 `hooks/scripts/loop_enforcement.py` — check_second_failure_gate_evidence（S6 分支 SLO 门禁后追加，默认关闭）+ `_import_loop_core_gate` 精确 import 辅助；`hook_common.py` — second_failure_gate.enabled: false
10. `loop_core/capability_registry.py` + 测试 — 注册 second_failure_checker（6 项期望）
11. `tests/test_learning_loop.py`（81 测试：AC-01 19/AC-02 18/AC-03 22+CLI 7+S6 接线 4/AC-04 8 + 并发）
12. 证据：`.ai/evidence/T-0097/learning-loop/design.md` + evidence-manifest.v1.yaml

## 既有缺陷修复（agent_e28e34a3）

13. **sys.modules.pop("loop_core") 破坏子模块 flake**（T-0093 既有模式）：_import_loop_core_gate 精确处理（临时前置 __path__ + finally 恢复，不替换包对象）→ test_slo_gate+test_observability 顺序依赖修复 → 全量 3675 passed / 0 failed

## 治理同步（主会话）

14. 独立审查（agent_34586cc0）：GO — 6/6 AC PASS；约束零放松；second-failure 默认关闭；无 task_graph 自动登记；P2-1（HANDOFF checkpoint）+ P2-2（证据收尾）
15. P2-1 修复：close_session 重建 HANDOFF → [ok] state is usable
16. 落盘 commands.md + acceptance/acceptance-report.md

## 验收

17. 全量测试：3675 passed / 63 skipped / 12 xfailed / 0 failed（基线 3594 + 81）
18. 状态收敛（task_graph T-0097 completed + state idle）+ close_session
19. git 提交 v3.12.36

## 发现（P3 遗留，记录）

- record_second_failure docstring 表述不精确（created_flags 与 detected 列表对齐，非 all_records）—— 语义无 bug
- 闭环后复发回退旧闭环复盘放行（与 B2 §3.4 严格语义略有出入，wave-1 取舍）
