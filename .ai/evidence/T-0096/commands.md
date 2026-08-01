# T-0096 Commands

任务：知识/记忆服务（D3）
Gate：G-T-0096-REQUIREMENTS（approved 2026-08-02，approval_text="批准T-0095、96、97"）

## 登记与启动

1. 批量登记批次第 2 项；state 串行指向 T-0096
2. 创建 approval/execution-evidence.json；compile_gate 生成 compile-evidence.json
3. `repair_continuity.py` + `close_session.py` + `validate_state.py` — [ok] state is usable
4. 顺手修复：`.ai/tasks/T-0095.md` 双 status 位 → completed

## 实现（developer 子代理 agent_53f209c3）

5. 新增 `loop_core/knowledge_store.py`（551 行）— KnowledgeEntry schema v1 + 确定性 entry_id（去重键）+ put_entry 幂等（锁 + 原子写）+ 多维检索（by_task/by_gate/by_tag/search/query，上限 20）+ fail-closed 校验
6. 新增 `loop_core/memory_service.py`（439 行）— extract_memories（lessons/验收报告规则式提取，无 LLM）+ recall（组合过滤 + 上限 5）+ memories_to_context + MemoryExtractionReport
7. 修改 `loop_core/context_loader.py`（+82 纯增量）— include_memories=False 默认关闭 + memory_limit/memory_task_id
8. `tests/test_knowledge_memory.py`（73 测试）
9. 真实产物：.ai/evidence/knowledge/knowledge-store.yaml（55 条 T-0086~T-0095 派生；二跑 0 新增幂等验证）
10. 证据：.ai/evidence/T-0096/knowledge/design.md + evidence-manifest.v1.yaml

## 治理一致性修复（agent_b5c8eae2）

11. **T-0095 manifest 漂移修复**：execution-evidence.json 更新后 manifest 陈旧（2 测试失败预存基线）→ 脚本重算 sha256/ordered/semantic + manifest_id 更新（EM-T-0095-39D9BC24）→ test_manifest_t0095 4 passed → 全量 3594 passed / 0 failed

## 治理同步（主会话）

12. 独立审查（agent_95fb38f6）：CONDITIONAL_GO — 6/6 AC PASS；约束未弱化；数据流单向性成立（gate_feedback 零改动）；P1-1（HANDOFF checkpoint 块陈旧）+ P2-1（报告披露）+ P3-1（遗留）
13. P1-1 修复：close_session 重建 HANDOFF → [ok] state is usable
14. 落盘 commands.md + acceptance/acceptance-report.md

## 验收

15. 全量测试：3594 passed / 63 skipped / 12 xfailed / 0 failed（基线 3521 + 73）
16. 状态收敛（task_graph T-0096 completed + state idle）+ close_session
17. git 提交 v3.12.35

## 发现（P3 遗留，记录）

- 真实 store lessons 源为空（gate-lessons 尚无记录，extract 从验收报告派生为主）
- 非标准验收报告跳过计数（设计行为）
- store 追加式增长（与 gate-lessons 同策略）
