# T-0092 验收报告（acceptance-report）

> **T-0092: AI-agent eval 栈（B1 设计落地）| 2026-08-01**
> Gate: G-T-0092-REQUIREMENTS（user 批量批准："继续 T-0092/T-0093/T-0094"）
> 独立审查：GO（6/6 AC，约束零弱化，2 项 P2 已补）

## AC 验收矩阵

| AC | 标准 | 结果 | 证据 |
|---|---|---|---|
| AC-01 | eval schema 完整 + 校验拒绝非法 | ✅ PASS | EvalCase 8 字段 + 14 项校验测试（缺失/未知断言/非法 severity/坏正则/重复 id 全拒绝，无静默修正） |
| AC-02 | 运行器（≥3 断言 + LLM 可选 SKIPPED + 异常隔离） | ✅ PASS | 4 种规则断言（text_contains/text_matches/json_equals/exit_code）双测；LLM fail-safe 6 路径 SKIP 不阻断；单用例崩溃隔离 |
| AC-03 | 报告 ReportBinding 风格 | ✅ PASS | 完整 binding 字段 + stats/by_severity/明细 + validate fail-closed；实测报告 6/6 PASS |
| AC-04 | 内置样例 ≥4（guard 正/负） | ✅ PASS | 6 例（正 2/负 4）+ aligns:GC-* 与 guard_health 对照电池**逐字对齐**（GC-002/003/004/006/007/008） |
| AC-05 | 全量测试无回归 | ✅ PASS | 3413 passed / 63 skipped / 12 xfailed / 0 failed（基线 3365 +48） |
| AC-06 | 无约束被弱化 | ✅ PASS | hooks/enforcement/hard_constraints/guard_health 零改动；eval 零接线（仅自身 CLI 引用）；LLM 全 mock |

## 交付物清单

1. `loop_core/evals.py`（EvalCase/EvalRunner/EvalReport/内置样例）
2. `tools/tool_eval.py`（CLI）
3. `tests/test_evals.py`（48 测试）
4. `.ai/evidence/T-0092/`：approval/execution/compile-evidence + evals/design.md + builtin-cases.yaml + commands + acceptance
5. `.ai/evidence/observability/eval-report.json`（实测报告）

## 治理记录

- 批量登记：T-0092/93/94 三任务 + 三 gate（用户一次批准）+ 边链 T-0091→92→93→94
- 启动证据：approval/execution/compile 全就位；T-0091 双 status 位遗留修复
- 派发记录：developer ×1、independent-reviewer ×1（GO）
- 全程零越界写入；eval 纯评测不接线；安全扫描回归已修复（fake secret → 运行时拼接）

## 最终裁决

**GO**（独立审查 GO，6/6 AC 全 PASS）

## 已知遗留（P3，记录）

- HANDOFF.md 引用 evidence-manifest.v1.yaml 实际不存在（模板性引用，历史任务同款）
