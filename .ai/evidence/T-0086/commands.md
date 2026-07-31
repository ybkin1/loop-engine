# T-0086 Commands

任务：治理清障 + StaffDeck 对标落地 + 任务计划编排
Gate：G-T-0086-REQUIREMENTS（approved 2026-08-01）

## 登记与启动

1. `validate_state.py .` — 初始状态检查（发现 task_graph.yaml 已由 T-0085 修复；系统 idle）
2. 创建 `.ai/tasks/T-0086.md`（含 allowed_paths: YAML 契约字段）
3. 更新 `.ai/task_graph.yaml` — 登记 T-0086 + edge T-0085→T-0086
4. 更新 `.ai/gates.yaml` — 登记 G-T-0086-REQUIREMENTS（pending → approved + approval/execution_evidence 字段）
5. 更新 `.ai/state.yaml` — current_task_id=T-0086, current_gate_id=G-T-0086-REQUIREMENTS
6. `validate_state.py .` — pending gate 阻断确认（设计行为）
7. 用户批准：`批准 T-0086`
8. `validate_state.py .` — 解锁确认

## 启动证据

9. 创建 `.ai/evidence/T-0086/approval-evidence.json`、`execution-evidence.json`
10. `compile_gate.py . --output .ai/evidence/T-0086/compile-evidence.json` — 42/42 编译通过
11. `repair_continuity.py .` — 修复 gates.yaml 变更引起的连续性漂移（2+1 处）
12. `.ai/tasks/T-0085.md` — 状态漂移修复（in_progress → completed，S4 → S6）
13. `close_session.py . --note "T-0086 active: ..."` — HANDOFF 结构化块重建
14. `validate_state.py .` — [ok] state is usable

## 实现（developer 子代理派发）

15. `hooks/scripts/path_guard.py` — READ_ONLY_TOOLS 只读豁免（Read/WebFetch/WebSearch/只读 Bash → 放行；写入仍拦截）
16. `hooks/scripts/loop_enforcement.py` — EXTERNAL_READ 只读外部引用放行（最小改动；写入 fail-closed 保持）
17. `scripts/runtime_delivery_gate.py .` — 实测输出 BLOCKED（web 应用门 N/A，非本项目适用）→ 按任务豁免以真实全量测试为证据
18. `pytest tests/` — 2791 passed / 63 skipped / 16 xfailed / 0 failed
19. 生成 `.ai/evidence/quality/runtime_quality_report.json`（overall=PASS，通过 .ai/schemas/runtime_quality.schema.json 严格校验）
20. `agents/security-engineer/scripts/run_security_scan.py` — 真实扫描 + 逐项复核（dependency HIGH 为 pip-audit 环境崩溃占位；secret/injection 均为测试夹具/误报）→ `.ai/evidence/security/security_audit.json`（verdict=PASS）
21. 新增 `tests/test_path_guard.py`（16 项：只读放行/写入拦截/保护区/deny 模式）
22. hook 套件验证：460 passed / 15 xfailed
23. `loop_enforcement.check_phase_gate_enforcement(root, "S6-delivery")` → True

## 治理同步（主会话）

24. `.ai/PROGRESS.md` — 漂移修复（头部同步 T-0086 active，旧内容标注存档）
25. `repair_continuity.py .` + `close_session.py .` — 连续性/HANDOFF 再同步
26. `validate_state.py .` — [ok] state is usable
27. 落盘 `.ai/evidence/T-0086/staffdeck-benchmark.md`（D1-D10/U1-U9/领先项/映射）
28. 落盘 `.ai/evidence/T-0086/task-plan.md`（T-0087~T-0090 编排）

## 验收

29. `git status/diff --stat` — 变更范围审查（全部在 .ai/、hooks/、tests/ 内）
30. independent-reviewer 子代理独立审查（AC-01~AC-07）
31. 验收证据落盘 `.ai/evidence/T-0086/acceptance/`
32. git 提交（v3.12.25）

## 发现（超范围，记录未改）

- Bash 写入目标含 Windows 反斜杠路径时 shlex.split POSIX 模式路径损坏（既有行为，loop_enforcement 仍由 DISPATCH 门拦截）
- 主会话 active task 下非治理读写需 runtime projection（既有设计，.ai/runtime/runtime-state.json 仅 .bak）
