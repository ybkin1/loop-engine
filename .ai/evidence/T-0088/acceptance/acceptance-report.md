# T-0088 验收报告（acceptance-report）

> **T-0088: 上下文与路由升级 — U3 上下文预算压缩 + U5 路由粘性/任务帧 + U6 人工接管 resume | 2026-08-01**
> Gate: G-T-0088-REQUIREMENTS（user 批准，approval_text="批准 T-0088 需求"）
> 独立审查：GO（7/7 AC，无 P0/P1/P2，3 项 P3）

## AC 验收矩阵

| AC | 标准 | 结果 | 证据 |
|---|---|---|---|
| AC-01 | 压缩 token 预算触发 + 证据链完整性 | ✅ PASS | ContextCompressor（默认 2600/0.7，触发后 1147→162 token）；TestBudgetTrigger 6 项；SHA-256 证明零写原始证据文件 |
| AC-02 | 层级摘要（摘要的摘要） | ✅ PASS | summarize_text 每层严格收缩否则停止；max_levels 配置；关键字段（任务/gate/阶段/决策点）每层保留 |
| AC-03 | evidence 引用截断修复 | ✅ PASS | CitationResolver 4 形态恢复；AMBIGUOUS/NOT_FOUND → [UNRESOLVED: ...] 不猜测；roundtrip 测试 |
| AC-04 | 路由粘性 + 任务帧 + fail-safe | ✅ PASS | 粘性 4 类失效全覆盖；帧切分（时间状语不误切）+ to_task_dict 兼容；降级永不抛、保持现状、不猜新意图 |
| AC-05 | resume payload | ✅ PASS | 快照+恢复数据逐字取自权威文件；恢复校验六重；漂移抛 StateDriftError（含期望/实际值）；默认行为不变 |
| AC-06 | 全量测试无回归 | ✅ PASS | 3014 passed / 63 skipped / 12 xfailed / 0 failed（基线 2914 +100 = 新增 33+33+34） |
| AC-07 | 无约束被弱化 | ✅ PASS | 三模块纯增量（-20 行为 estimate_tokens 等价重构）；约束层（enforcement/hooks/C1-C11）零改动；压缩零写；fail-safe/resume 不猜测 |

## 交付物清单

1. `loop_core/context_loader.py`（+746/-20：ContextCompressor/summarize_text/CitationResolver/repair_truncated_references/estimate_tokens 模块级化）
2. `loop_core/intent_router.py`（+562 纯增量：route_upgrade/split_intents/detect_intent_switch/TaskFrame/ActiveTaskSnapshot）
3. `loop_core/human_review_packet.py`（+465 纯增量：ResumePayload/build_resume_payload/resume_from_payload）
4. `tests/test_context_compression.py`（33）+ `test_intent_router_upgrade.py`（33）+ `test_resume_payload.py`（34）= 100 新测试
5. `.ai/evidence/T-0088/`：approval/execution/compile-evidence + 三份 design.md + commands + acceptance

## 治理记录

- 任务登记：task_graph T-0088 + edge T-0087→T-0088；gates G-T-0088-REQUIREMENTS（用户消息批准）；state current_task_id=T-0088
- 启动证据：approval/execution/compile 全就位；T-0087 双 status 位遗留修复
- 派发记录：developer ×3 并行（U3/U5/U6）、independent-reviewer ×1（GO）
- 全程零越界写入（diff 审查）；约束层零改动

## 最终裁决

**GO**（独立审查 GO，7/7 AC 全 PASS）

## 已知遗留（P3，记录）

- P3-1: repair_truncated_references 子串替换边界（完整+丢前缀同文本场景）—— context_loader.py:595-603
- P3-2: 正常粘性路径不继承 active 任务 loop_mode（设计有意，模式不对称待评估）—— intent_router.py:1374-1404
- P3-3: _find_citation_tokens set 迭代次序非确定（仅输出次序）—— context_loader.py:242-249
