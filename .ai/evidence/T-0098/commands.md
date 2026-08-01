# T-0098 Commands

任务：D8 发布/产物体系 — 版本同步 + 构建产物 + release 流程 + 冒烟验证
Gate：G-T-0098-REQUIREMENTS（approved 2026-08-02，approval_text="D8 发布产物体系"）

## 登记与启动

1. 创建 `.ai/tasks/T-0098.md`（含 allowed_paths + pyproject.toml/CHANGELOG.md）
2. 更新 `.ai/task_graph.yaml` — 登记 T-0098 + edge T-0097→T-0098
3. 更新 `.ai/gates.yaml` — 登记 G-T-0098-REQUIREMENTS（用户消息即批准）
4. 更新 `.ai/state.yaml` — current_task_id=T-0098 + notes
5. 创建 approval/execution-evidence.json；compile_gate 生成 compile-evidence.json
6. `repair_continuity.py` + `close_session.py` + `validate_state.py` — [ok] state is usable
7. 顺手修复：`.ai/tasks/T-0097.md` 双 status 位 → completed

## 实现（developer 子代理 agent_f42a8a2d）

8. **版本同步**：pyproject 3.11.2→3.12.36 + CHANGELOG 补 v3.12.25~36（12 条）+ 版本载体同步（src/loop_engine/__init__.py、loop_core/__init__.py、README.md、.zcode-plugin/plugin.json、docs/06-delivery.md、.ai/version-manifest.yaml——范围偏差经独立审查判定合理必要，test_version_consistency 强制要求）+ pyproject [tool.setuptools] 显式包锁定（wheel 仅含 src/loop_engine + loop_core + loop_core.llm）
9. 新增 `scripts/release.py` — check（质量门前置）/build/manifest/release/smoke + --dry-run + 退出码 0/1/2
10. 新增 `tests/test_release.py`（19 测试）+ test_version_consistency 增补
11. 修复 HEAD 预存语法错误（scripts/role_checkers/review_coverage_checker.py 第 9 行裸换行）
12. 真实端到端：release.py release 跑通（check → 构建 → 清单 → 证据落盘 .ai/evidence/release/3.12.36/ 三件套）
13. 证据：.ai/evidence/T-0098/release/design.md + evidence-manifest

## 放行条件修复（agent_c9efb0aa，独立审查 CONDITIONAL_GO）

14. **P1-1 门禁盲区**：step_validate_state 接入真实校验器（subprocess，非 0 阻断）+ 新增 step_slo_gate（check 5→6 步）；全量测试保持子集的决策已写入 design.md §4
15. **P1-2 证据过期**：测试 fixture 隔离（tmp 构建不再污染 dist/）+ 重新生成 release 三件套（sha256sum -c 2/2 OK，双 manifest 逐项一致）
16. **P2 CRLF**：SHA256SUMS write_bytes（LF，sha256sum -c 兼容）+ 测试断言
17. 全量 3700 passed / 0 failed；check rc=0（6 步全 PASS）；dry-run 6 步列表

## 治理同步（主会话）

18. 独立审查（agent_643a08d4）：CONDITIONAL_GO — 范围偏差判定合理必要；AC-01/04/05/06 PASS；P1-1/P1-2/P2 修复后转 GO
19. 连续性漂移修复：validate_state --repair + close_session 重建 HANDOFF → [ok] state is usable
20. 落盘 commands.md + acceptance/acceptance-report.md

## 验收

21. 全量测试：3700 passed / 64 skipped / 12 xfailed / 0 failed（基线 3675 + 25）
22. 状态收敛（task_graph T-0098 completed + state idle）+ close_session
23. git 提交 v3.12.37

## 发现（P3 遗留，记录）

- manifest path 字段平台相关（Windows 反斜杠 dist\...）
- smoke 只安装 wheels[-1]
- HEAD 起动态 repair 不覆盖 version-manifest.yaml 的系统性缺口（后续任务跟进）
- 本机 Python 无 venv 模块 → smoke 如实 SKIP（--target 等价验证 PASS）
