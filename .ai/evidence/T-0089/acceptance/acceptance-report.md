# T-0089 验收报告（acceptance-report）

> **T-0089: 学习回路与工程化 — U4 反馈回路 + U7 evidence 可靠投递 + U8 可观测性 + U9 生命周期 | 2026-08-01**
> Gate: G-T-0089-REQUIREMENTS（user 批准，approval_text="批准 T-0089 需求"）
> 独立审查：GO（6/6 AC，三条红线验证通过，3 项 P3）

## AC 验收矩阵

| AC | 标准 | 结果 | 证据 |
|---|---|---|---|
| AC-01 | 反馈回路（gate 拒绝/修复经验沉淀） | ✅ PASS | GateLesson 结构化（schema v1）+ 确定性幂等 lesson_id + 5 类检索 + human_review_packet related_experience 集成（默认不变）；43 测试 |
| AC-02 | evidence 幂等 + 退避重试 + 卡死重置 | ✅ PASS | transactional_write_texts 三参数默认关闭；幂等表防重复；指数退避超上限重抛；陈旧 journal 双重前置检查重置；18 测试 |
| AC-03 | 观测事件落盘 + 异常不阻断业务 | ✅ PASS | GuardEventRecorder JSONL append-only；record 永不抛错；红线测试（观测失败不吞安全 BLOCK、三态裁决签名一致）；13 测试 |
| AC-04 | 生命周期脚本 | ✅ PASS | scripts/dev.py up/down/status + pid/port 原子写 + 三探针 + Windows 兼容 + status 三态；38 测试 |
| AC-05 | 全量测试无回归 | ✅ PASS | 3126 passed / 63 skipped / 12 xfailed / 0 failed（基线 3014 +112 = 43+18+13+38） |
| AC-06 | 无约束被弱化 | ✅ PASS | 三条红线验证：enforcement_hub/hard_constraints/hooks 零改动；默认行为逐字节兼容；历史记录零修改（gate-lessons/events 均为独立追加文件） |

## 交付物清单

1. `loop_core/gate_feedback.py`（新，~449 行）+ `human_review_packet.py`（+42 纯增量）
2. `.zcode/tools/governor_lib.py`（+262/-6：idempotent/retry/stale_timeout + RetryPolicy/TransactionResult）
3. `loop_core/observability.py`（新，~200 行）+ `guard_health.py`（+162 纯增量，含死导入清理）
4. `scripts/dev.py`（新，~700 行）
5. `tests/`：test_gate_feedback（43）+ test_reliable_delivery（18）+ test_observability（13）+ test_lifecycle（38）= 112 新测试
6. `.ai/evidence/T-0089/`：approval/execution/compile-evidence + 4 份 design.md + commands + acceptance
7. `.ai/evidence/observability/guard-events.jsonl`（真实运行事件）

## 治理记录

- 任务登记：task_graph T-0089 + edge T-0088→T-0089；gates G-T-0089-REQUIREMENTS（用户消息批准）；state current_task_id=T-0089
- 启动证据：approval/execution/compile 全就位；T-0088 双 status 位遗留修复
- 派发记录：developer ×4 并行（U4/U7/U8/U9）、independent-reviewer ×1（GO）
- 全程零越界写入（diff 审查）；三条红线（安全裁决/默认兼容/历史零修改）验证通过

## 最终裁决

**GO**（独立审查 GO，6/6 AC 全 PASS）

## 已知遗留（P3，记录）

- record_gate_lesson 无锁 read-modify-write（单用户低风险，建议后续复用事务机制）
- guard-events.jsonl 持续增长（建议 T-0090+ 轮转/上限）
- scripts/dev.py POSIX 分支未在真实 POSIX 主机验证（本机 win32，monkeypatch 覆盖）
