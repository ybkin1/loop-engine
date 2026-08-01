# T-0093 Commands

任务：SLO 门禁 wave 2 — error budget 耗尽自动冻结发布
Gate：G-T-0093-REQUIREMENTS（approved 2026-08-01，approval_text="继续 T-0092/T-0093/T-0094"）

## 登记与启动

1. 批量登记（T-0092/93/94 三任务 + 三 gate + 边链）；state 串行指向
2. 创建 approval/execution-evidence.json；compile_gate 生成 compile-evidence.json
3. `repair_continuity.py` + `close_session.py` + `validate_state.py` — [ok] state is usable
4. T-0092 收尾提交 v3.12.31（8073149）后恢复 T-0093 active

## 实现（developer 子代理 agent_76cf934f）

5. 新增 `loop_core/slo_gate.py`（563 行）— check_slo_gate（HEALTHY→PASS / CONSUMING→PASS+warn / FREEZE→BLOCK ERROR_BUDGET_EXHAUSTED / 数据缺失→fail-closed BLOCK 列缺失源）+ SloGateResult + record_slo_exemption/load_exemptions（append-only 豁免账本）+ slo_gate_enabled（默认开，env LOOP_SLO_GATE_ENABLED > config）
6. 新增 `.ai/checkers/slo_gate_checker.py`（176 行）— compile_gate 同款 CLI（JSON + 退出码 0/1/2）
7. 修改 `hooks/scripts/loop_enforcement.py`（+47/-1 纯追加）— S6 分支追加 check_slo_gate_evidence（与 delivery/runtime/security 同级，仅新增阻断）
8. 修改 `hooks/scripts/hook_common.py`（+8）— DEFAULT_CONFIG 加 slo_gate.enabled
9. `tests/test_slo_gate.py`（40 测试：决策 12/开关 5/CLI 6/hook 接线 5/豁免 9/恢复 3/兼容 4）
10. 证据：`.ai/evidence/T-0093/slo-gate/design.md`

## P1 回归修复（agent_1979eb76，独立审查 CONDITIONAL_GO 条件）

11. **P1**：`slo_gate_checker` 注册进 capability_registry `_DEFAULT_MANIFEST`（live-repo 漂移测试回归修复）+ test_capability_registry 断言配套更新
12. **hook 运行时 import 修复**：check_slo_gate_evidence 先 `sys.path.insert(0, str(root))` + `sys.modules.pop("loop_core")`（插件缓存旧 loop_core 包已导入 sys.modules，包缓存优先于路径查找 —— 深层根因）；修复后从插件缓存模拟验证 → PASS；fail-closed 未放松（伪 root 仍阻断）
13. 修复文件同步进插件缓存；全量 3453 passed / 0 failed

## 治理同步（主会话）

14. 独立审查（agent_62598c65）：CONDITIONAL_GO → P1 修复复验转 GO（P2 本文件补齐）
15. 落盘 commands.md + acceptance/acceptance-report.md

## 验收

16. 全量测试：3453 passed / 63 skipped / 12 xfailed / 0 failed（基线 3413 + 40）
17. 状态收敛（task_graph T-0093 completed + state idle）+ close_session
18. git 提交 v3.12.32

## 发现（P3 遗留，记录）

- `.ai/slo.yaml` 不存在（门禁走 B2 内置默认 100 units/5 fee）—— 建议后续补充使预算配置显式化
- check_slo_gate 与 _check_with_config 各做一次 slo_gate_enabled 检查（冗余无害）
- 主会话 hook 场景实测：SLO 门禁真实生效（validate_state 通过即证明 HEALTHY 放行链路）
