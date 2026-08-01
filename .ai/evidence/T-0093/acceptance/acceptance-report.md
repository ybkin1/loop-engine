# T-0093 验收报告（acceptance-report）

> **T-0093: SLO 门禁 wave 2 — error budget 耗尽自动冻结发布 | 2026-08-01**
> Gate: G-T-0093-REQUIREMENTS（user 批量批准："继续 T-0092/T-0093/T-0094"）
> 独立审查：CONDITIONAL_GO → P1 修复复验转 GO

## AC 验收矩阵

| AC | 标准 | 结果 | 证据 |
|---|---|---|---|
| AC-01 | SLO 门禁检查器（HEALTHY/FREEZE/缺失 fail-closed） | ✅ PASS | check_slo_gate：HEALTHY→PASS / FREEZE→BLOCK（ERROR_BUDGET_EXHAUSTED + 明细）/ CONSUMING→PASS+warn / 缺失源逐条列出 fail-closed BLOCK；12 测试 |
| AC-02 | 接入发布链（S6 门，开关可配） | ✅ PASS | hook S6 分支追加 check_slo_gate_evidence（与既有三检查同级，仅新增阻断）；env/config 双开关；CLI 退出码 0/1/2；16 测试 |
| AC-03 | 豁免机制（有效 PASS/过期失效/approver 缺失拒绝） | ✅ PASS | append-only 豁免账本；有效豁免翻转 FREEZE→PASS；过期重 BLOCK；9 测试 |
| AC-04 | 恢复机制（窗口滚动自动放行） | ✅ PASS | 7 月 FREEZE→8 月 HEALTHY PASS；slo.yaml 窗口默认生效；3 测试 |
| AC-05 | 全量测试无回归 | ✅ PASS | 3453 passed / 63 skipped / 12 xfailed / 0 failed（P1 修复后全绿） |
| AC-06 | 约束只强化不弱化 | ✅ PASS | hook +47/-1 纯追加（既有三检查函数体零触碰）；SLO 门禁仅 S6 分支；fail-closed 语义保持（伪 root 仍阻断） |

## P1 修复记录（CONDITIONAL_GO 条件）

| 问题 | 修复 | 验证 |
|---|---|---|
| slo_gate_checker 未注册 registry → live-repo 漂移测试失败 | capability_registry _DEFAULT_MANIFEST 注册 + 测试断言配套 | 全量 3453 passed 0 failed |
| hook 插件缓存运行 import loop_core.slo_gate 失败（sys.modules 缓存旧包） | sys.path.insert(root) + sys.modules.pop("loop_core") 强制从项目根解析 | 插件缓存模拟验证 PASS；fail-closed 未放松 |

## 交付物清单

1. `loop_core/slo_gate.py`（新，563 行）+ `.ai/checkers/slo_gate_checker.py`（新，176 行）
2. `hooks/scripts/loop_enforcement.py`（+47/-1 纯追加 S6 门）+ `hook_common.py`（+8 配置）
3. `loop_core/capability_registry.py`（slo_gate_checker 注册）+ `tests/test_capability_registry.py`（配套）
4. `tests/test_slo_gate.py`（40 测试）
5. `.ai/evidence/T-0093/`：approval/execution/compile-evidence + slo-gate/design.md + commands + acceptance

## 治理记录

- 批量登记批次第 2 项；P1 修复经独立复验；主会话 hook 场景实测（SLO 门禁真实生效）
- 全程零越界写入；约束只强化（SLO 门禁为新增 fail-closed 检查）

## 最终裁决

**GO**（CONDITIONAL_GO 的 P1 已修复复验；6/6 AC 达成）

## 已知遗留（P3，记录）

- `.ai/slo.yaml` 不存在（走 B2 内置默认 100 units/5 fee）—— 建议后续补充显式化
- check_slo_gate 双重复用检查（冗余无害）
