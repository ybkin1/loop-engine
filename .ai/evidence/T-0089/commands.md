# T-0089 Commands

任务：学习回路与工程化 — U4 gate 决策反馈回路 + U7 evidence 可靠投递 + U8 可观测性分层 + U9 生命周期
Gate：G-T-0089-REQUIREMENTS（approved 2026-08-01，approval_text="批准 T-0089 需求"）

## 登记与启动

1. 创建 `.ai/tasks/T-0089.md`（含 allowed_paths: YAML 契约字段）
2. 更新 `.ai/task_graph.yaml` — 登记 T-0089（in_progress）+ edge T-0088→T-0089
3. 更新 `.ai/gates.yaml` — 登记 G-T-0089-REQUIREMENTS（用户消息即批准）
4. 更新 `.ai/state.yaml` — current_task_id=T-0089, current_gate_id=G-T-0089-REQUIREMENTS + notes
5. 创建 approval/execution-evidence.json；compile_gate 生成 compile-evidence.json
6. `repair_continuity.py` + `close_session.py` — 连续性/HANDOFF 同步
7. `validate_state.py` — [ok] state is usable
8. 顺手修复：`.ai/tasks/T-0088.md` 双 status 位 → completed（历史遗留 warn）

## 实现（developer 子代理 × 4 并行）

### U4 gate 决策反馈回路（agent_af279a83）
9. 新增 `loop_core/gate_feedback.py`（~449 行）— GateLesson（schema v1）/make_lesson_id（确定性 SHA-256）/record_gate_lesson（追加式原子写，同指纹幂等）/检索（by_gate_id/by_reason_category/recent/search/suggest_related_lessons）/fail-closed 校验
10. 修改 `loop_core/human_review_packet.py`（+42 纯增量）— related_experience 可选字段，非空才渲染 "Related Past Experience" 小节
11. `tests/test_gate_feedback.py`（43 测试）
12. 证据：`.ai/evidence/T-0089/feedback-loop/design.md`

### U7 evidence 可靠投递（agent_d17b671a）
13. 修改 `.zcode/tools/governor_lib.py`（+262/-6）— transactional_write_texts 三新参数默认关闭：idempotent（内容指纹幂等表 .project-governor-idempotency.json）/retry（RetryPolicy 指数退避，超上限重抛不静默）/stale_timeout_seconds（陈旧 journal 双重前置检查后重置，并发写者拒绝）；新增 RetryPolicy/TransactionResult
14. `tests/test_reliable_delivery.py`（18 测试，AC-02a/b/c/d）
15. 证据：`.ai/evidence/T-0089/reliable-delivery/design.md`

### U8 可观测性分层（agent_31f2a729）
16. 新增 `loop_core/observability.py`（~200 行）— GuardCheckEvent + GuardEventRecorder（JSONL append-only，record 永不抛错，可开关，read_events/summary）
17. 修改 `loop_core/guard_health.py`（+162 纯增量）— 观测挂点（health/death/missing/drift/integrity 事件）；裁决逻辑零语义变化；顺带清理 hashlib/CapabilityBinding 死导入（T-0087 P3-1 遗留）
18. `tests/test_observability.py`（13 测试，红线：观测失败不吞安全 BLOCK、开关不影响裁决）
19. 证据：`.ai/evidence/T-0089/observability/design.md` + 真实事件 `.ai/evidence/observability/guard-events.jsonl`

### U9 生命周期（agent_efd0fe9c）
20. 新增 `scripts/dev.py`（~700 行）— up/down/status + --detach/--port/--target/--health-url；pid/port/status JSON 原子写 `.ai/runtime/`；三探针（HttpProbe/StdioPingProbe/AliveProbe）；Windows 兼容（tasklist/taskkill /F /T 升级）；status 三态（running/stopped/stale）
21. `tests/test_lifecycle.py`（38 测试，fake 目标命令，不启动真实长驻服务）
22. 证据：`.ai/evidence/T-0089/lifecycle/design.md`

## 治理同步（主会话）

23. 独立审查（agent_1dcc7617）：GO — 6/6 AC PASS，三条红线（安全裁决零改动/默认兼容/历史零修改）验证通过；3 项 P3 记录遗留
24. 落盘 commands.md + acceptance/acceptance-report.md

## 验收

25. 全量测试：3126 passed / 63 skipped / 12 xfailed / 0 failed（基线 3014 + 112 = 43+18+13+38）
26. 状态收敛（task_graph T-0089 completed + state idle）+ close_session 重建 HANDOFF
27. git 提交 v3.12.28

## 发现（P3 遗留，记录）

- record_gate_lesson 去重为无锁 read-modify-write（单用户场景低风险；建议后续复用事务机制）
- guard-events.jsonl 运行产物持续增长（建议 T-0090+ 增加轮转/上限）
- U7/U9 全量运行中两次瞬时失败均为并行子代理 in-flight 文件竞态（单独重跑通过），非回归
- scripts/dev.py POSIX 分支经 monkeypatch 单测覆盖，未在真实 POSIX 主机验证（本机 win32）
