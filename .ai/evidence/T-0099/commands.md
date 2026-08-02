# T-0099 Commands

任务：Loop 工程自身质量验收 — 全能力端到端验收（dogfooding）
Gate：G-T-0099-REQUIREMENTS（approved 2026-08-02，approval_text="把loop工程自己当作一个项目治理，该项目目前已经完成开发需要做质量验收"）

## 登记与启动

1. 创建 `.ai/tasks/T-0099.md`（含 allowed_paths: YAML 契约字段）
2. 更新 `.ai/task_graph.yaml` — 登记 T-0099 + edge T-0098→T-0099
3. 更新 `.ai/gates.yaml` — 登记 G-T-0099-REQUIREMENTS（用户消息即批准）
4. 更新 `.ai/state.yaml` — current_task_id=T-0099 + notes
5. 创建 approval/execution-evidence.json；compile_gate 生成 compile-evidence.json
6. `repair_continuity.py` + `close_session.py` + `validate_state.py` — [ok] state is usable
7. 顺手修复：`.ai/tasks/T-0098.md` 双 status 位 → completed

## 质量验收执行（quality-engineer agent_10c65932，四组 13 项）

### 组 1 静态门禁（AC-01，5/5 PASS）
8. G1-1 validate_state [ok] usable；G1-2 compile 68/68；G1-3 version_consistency 7/7；G1-4 registry missing/drift 0（--json 崩溃 F-01）；G1-5 guard 5/5 ALIVE

### 组 2 动态质量（AC-02，2 PASS / 1 FAIL）
9. G2-6 全量测试 2 failed / 3698 passed（F-02 manifest 瞬时 + F-03 版本漂移）→ FAIL；G2-7 eval 6/6 PASS；G2-8 conformance gate PASS

### 组 3 治理质量（AC-03，3 PASS* / 1 FAIL）
10. G3-9 SLO HEALTHY 但 NOT_VERIFIED（F-05 数据源缺失）；G3-10 second_failure PASS（DISABLED）；G3-11 安全扫描 BLOCKED（F-04 环境 + 误报）；G3-12 self_audit PASS

### 组 4 发布就绪（AC-04，FAIL）
11. G4-13 release check 第 1 步 version_sync 阻断（F-03，fail-closed 正确触发）；逐步隔离 5/6 PASS

### 产出
12. 逐项证据 .ai/evidence/T-0099/quality/（15 文件）；统一报告 acceptance/quality-acceptance-report.md + summary.json；dashboard 快照更新

## 独立验证（agent_ca33bd1a）

13. 8 项关键抽查独立复现全部一致；F-01~F-06 全部真实无误报；报告如实记录（FAIL 未掩饰）；验证裁决：验收执行可信；3 处 P3 表述瑕疵

## 收尾修复（agent_7dc0a418）

14. T-0099 evidence-manifest 生成（EM-T-0099-B0B9CA47，官方校验通过）→ F-02 自愈
15. 报告 3 处勘误（版本来源表述/计数口径/pip-audit 退出码）

## 治理同步（主会话）

16. 落盘 commands.md + acceptance/acceptance-report.md

## 验收

17. 状态收敛（task_graph T-0099 completed + state idle）+ close_session
18. git 提交 v3.12.38

## Findings（记录不修复，修复需用户发起）

- **F-03（P1）** 版本漂移：pyproject 3.12.36 vs git HEAD v3.12.37 → release check 阻断
- **F-01（P2）** tool_registry_status --json UnboundLocalError 'death'（L82）
- **F-04（P2）** pip-audit 环境不可用（Python 缺 venv）→ 依赖 CVE 无法本地验证
- **F-05（P2）** 14 个 ledger 数据源缺失 → SLO NOT_VERIFIED；metrics/slo_gate 口径差异
- **F-02（P3）** manifest 测试瞬时变红（已自愈）
- **F-06（P3）** 安全扫描器无白名单（自指/夹具误报）
