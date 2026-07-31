# T-0088 Commands

任务：上下文与路由升级 — U3 上下文预算压缩 + U5 路由粘性/任务帧 + U6 人工接管 resume
Gate：G-T-0088-REQUIREMENTS（approved 2026-08-01，approval_text="批准 T-0088 需求"）

## 登记与启动

1. 创建 `.ai/tasks/T-0088.md`（含 allowed_paths: YAML 契约字段）
2. 更新 `.ai/task_graph.yaml` — 登记 T-0088（in_progress）+ edge T-0087→T-0088
3. 更新 `.ai/gates.yaml` — 登记 G-T-0088-REQUIREMENTS（用户消息即批准）
4. 更新 `.ai/state.yaml` — current_task_id=T-0088, current_gate_id=G-T-0088-REQUIREMENTS + notes
5. 创建 approval/execution-evidence.json；compile_gate 生成 compile-evidence.json
6. `repair_continuity.py` + `close_session.py` — 连续性/HANDOFF 同步
7. `validate_state.py` — [ok] state is usable
8. 顺手修复：`.ai/tasks/T-0087.md` 双 status 位 → completed（历史遗留 warn）

## 实现（developer 子代理 × 3 并行）

### U3 上下文预算压缩（agent_93a72f41）
9. `loop_core/context_loader.py`（+726/-20）— ContextCompressor（预算触发 estimate_tokens > budget×ratio，默认 2600/0.7；触发后每层严格收缩否则停止）+ summarize_text（确定性规则摘要，保留关键字段头/标题/决策点/evidence 引用 ≤8 行）+ CitationResolver/repair_truncated_references（4 形态唯一性恢复；多匹配 AMBIGUOUS/缺失 NOT_FOUND → 显式 [UNRESOLVED: ...]）+ estimate_tokens 模块级化
10. `tests/test_context_compression.py`（33 测试：预算触发/层级摘要/引用修复/证据链完整性 SHA-256 零写）
11. 证据：`.ai/evidence/T-0088/context-compression/design.md`

### U5 路由升级（agent_f36287fd）
12. `loop_core/intent_router.py`（+562 纯增量）— route_upgrade/route_user_input/split_intents/detect_intent_switch/ActiveTaskSnapshot/TaskFrame/RoutedIntent/IntentBrief；粘性四类失效（新任务/完成/引用他任务/mark-complete）；帧切分（分号/编号/中英连接词，时间状语不误切）；fail-safe 降级（永不抛、保持现状、不猜新意图、仅路由建议）
13. `tests/test_intent_router_upgrade.py`（33 测试：粘性 11/帧 11/降级 7/兼容 7）
14. 证据：`.ai/evidence/T-0088/router-upgrade/design.md`；附带修复 inbox.py 的 analyse_intent ImportError 兜底

### U6 resume payload（agent_f426bd20）
15. `loop_core/human_review_packet.py`（+465 纯增量）— ResumePayload/ResumeSnapshot/DecisionPoint/ResumeContext（schema v1）+ build_resume_payload（快照+恢复数据逐字取自 state/task_graph/gates，校验失败抛 ResumePayloadError）+ resume_from_payload（六重校验，漂移抛 StateDriftError 不猜测）+ HumanReviewPacket.resume_payload 可选字段（默认行为不变）
16. `tests/test_resume_payload.py`（34 测试：生成 5/恢复 3/漂移 8/兼容 5/fail-closed 13）
17. 证据：`.ai/evidence/T-0088/resume-payload/design.md`；真实状态实测（T-0088 gate 已 approved → resume 按设计拒绝）

## 治理同步（主会话）

18. 独立审查（agent_abc8605a）：GO — 7/7 AC PASS，diff 纯增量、约束层零改动、压缩零写原始文件、fail-safe/resume 不猜测；3 项 P3 记录遗留
19. 落盘 commands.md + acceptance/acceptance-report.md

## 验收

20. 全量测试：3014 passed / 63 skipped / 12 xfailed / 0 failed（基线 2914 + 100 = 新增测试 33+33+34）
21. 状态收敛（task_graph T-0088 completed + state idle）+ close_session 重建 HANDOFF
22. git 提交 v3.12.27

## 发现（P3 遗留，记录）

- P3-1: repair_truncated_references 子串替换边界（同文本含完整+丢前缀路径时可能双前缀）—— 建议防御性跳过"更长已解析 token 子串"（context_loader.py:595-603）
- P3-2: 正常粘性路径不继承 active 任务 loop_mode（仅降级路径继承）—— 设计有意为之，模式处理不对称待评估（intent_router.py:1374-1404）
- P3-3: _find_citation_tokens 长 token 排序依赖 set 迭代（跨运行非确定，仅影响输出次序）—— 无正确性影响（context_loader.py:242-249）
