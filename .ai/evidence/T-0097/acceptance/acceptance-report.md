# T-0097 验收报告（acceptance-report）

> **T-0097: B2 学习回路补全 — incident + 复盘 + second-failure | 2026-08-02**
> Gate: G-T-0097-REQUIREMENTS（user 批量批准："批准T-0095、96、97"）
> 独立审查：GO（6/6 AC，约束零放松，无 task_graph 自动登记）

## AC 验收矩阵

| AC | 标准 | 结果 | 证据 |
|---|---|---|---|
| AC-01 | incident 记录（schema/幂等/落盘/检索） | ✅ PASS | IncidentRecord 全字段 + 确定性 IN-id + 幂等（同事件去重/异时刻分立）+ 四轴检索 + 12 线程并发不丢；19 测试 |
| AC-02 | 复盘（行动项 owner/deadline/status） | ✅ PASS | RT-id 关联 + 行动项强制 owner/ISO deadline + open→done→retro closed + closed 不可变；18 测试 |
| AC-03 | second-failure（复发→草稿 + 未解决阻断） | ✅ PASS | 复发指纹 + 草稿 [draft] + 未解决 BLOCK（明细）/有行动项 PASS/豁免/损坏 fail-closed/**默认关闭 opt-in**；33 测试 |
| AC-04 | gate_lessons 衔接 | ✅ PASS | register_gate_rejection_incident（≥2 拒绝 → incident，approved 不计，重跑幂等）；8 测试 |
| AC-05 | 全量测试无回归 | ✅ PASS | 3675 passed / 63 skipped / 12 xfailed / 0 failed（基线 3594 +81） |
| AC-06 | 无约束弱化 + 不自动登记 | ✅ PASS | 既有检查零修改（diff 审查）；second_failure 默认关闭只增阻断；grep 确认零 task_graph 写入 |

## 交付物清单

1. `loop_core/incidents.py` + `retrospectives.py` + `second_failure.py`（新）
2. `.ai/checkers/second_failure_checker.py`（新 CLI）
3. `hooks/scripts/loop_enforcement.py`（check_second_failure_gate_evidence + _import_loop_core_gate）+ `hook_common.py`（默认关闭）
4. `loop_core/capability_registry.py`（second_failure_checker 注册）
5. `tests/test_learning_loop.py`（81 测试）
6. `.ai/evidence/T-0097/`：approval/execution/compile-evidence + learning-loop/design.md + evidence-manifest + commands + acceptance
7. 既有缺陷修复：sys.modules.pop 精确化（_import_loop_core_gate）—— 修复跨测试顺序依赖 flake

## 治理记录

- 批量登记批次第 3 项（T-0095/96/97 全部完成）；T-0093 既有 import 缺陷修复（治理一致性）
- P2-1 修复：HANDOFF checkpoint 块重建 → [ok] state is usable
- 全程零越界写入；约束零放松；不自动登记任务（草稿需用户批准）

## 最终裁决

**GO**（独立审查 GO，6/6 AC 全 PASS）

## 已知遗留（P3，记录）

- record_second_failure docstring 表述不精确（语义无 bug）
- 闭环后复发回退旧闭环复盘放行（B2 §3.4 严格语义 wave-1 取舍）
