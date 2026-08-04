# T-0111 缺陷归类规则落地（design-common-weakness.md 3.3，报告制）

日期：2026-08-03
涉及文件：`loop_core/governance_metrics.py`（`classify_repair_event` /
`repair_classification`，纯函数零副作用）；报告：`design/repair-classification-report.md`

## 1. 归类规则（实现口径）

对 guard-events 中 check_type="repair" 事件，按 `failure_reason` 的
`fixed=<n>` 与 result 归类：

| 条件 | 归类 | 根因证据（design 3.3） |
|------|------|------------------------|
| fixed>0 | `unstable_generation` | 生成器（continuity_producer/写入工具）漏更新清单——修复确有物可修 |
| result=FAIL 且 fixed=0 | `over_strict` | 修复无物可修但校验仍失败——规则/白名单与真实写入路径不匹配 |
| 其余（含动态收尾 fixed=0、修复未执行/不可解析） | `benign` | 正常无漂移或环境性问题 |

**连续场景（AC-02 "fixed=0 连续场景"）**：`repair_classification` 额外计算
`over_strict_runs` —— 连续 ≥2 条 over_strict 事件的连续段数；连续复发是
校验过严的最强证据（人工检视规则的触发信号）。阈值语义：报告提示
over_strict 事件或连续段 ≥3/周期 时建议人工检视规则（**不自动阻断**）。

## 2. 报告制边界（硬约束落实）

- 归类函数只读输入、返回 dict，不写任何文件、不调用任何 gate 判定模块；
- `repair_trigger_rate` / `repair_classification` 未接入 `build_report` 的
  任何判定路径（MetricsReport 零改动，golden 等价基线保持）；
- 测试断言纯函数无副作用（两次调用输出一致）。

## 3. 测试（tests/test_repair_governance.py::TestRepairClassification）

| 用例 | 断言 |
|------|------|
| fixed=3 PASS → unstable_generation | 归类正确 |
| fixed=0 FAIL（nothing to fix）→ over_strict | 归类正确 |
| dynamic fixed=0 PASS → benign | 正常收尾不误报 |
| failure_reason 不可解析 FAIL → benign | 兜底不误报 |
| 连续场景：FAIL,FAIL,benign,FAIL → over_strict=3, runs=1 | 连续段检测 |
| 三类混合 → 计数 {1,1,1} + 逐条明细 | 汇总正确 |
| 无 repair 事件 → NOT_AVAILABLE | fail-closed 口径 |
| 纯函数无副作用 | 报告制不自动阻断 |

## 4. 样本与结论

分类报告（`design/repair-classification-report.md`）基于规则 + 三组代表
样本给出分布与解读；真实仓库当前 guard-events 无 repair 事件（3719 条
全为既有类型），`repair_trigger_rate = 0.0` —— 新事件类型自本任务起
由 validate_state/close_session 触发点写入，后续周期将积累真实样本。
