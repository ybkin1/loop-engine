# T-0111 生成路径缺陷归类报告（repair-classification-report）

日期：2026-08-03
类型：报告制（不自动阻断）——本报告不触发任何 gate 判定/阻断语义
数据源：`.ai/evidence/observability/guard-events.jsonl` 的 `check_type="repair"`
事件（T-0111 起由 validate_state REPAIR_MODE / close_session 收尾触发点写入）
归类实现：`loop_core.governance_metrics.classify_repair_event` /
`repair_classification`（纯函数）

## 1. 归类规则（design-common-weakness.md 3.3 落地）

| 条件（failure_reason 含 `fixed=<n>`，result 为事件结果） | 归类 | 根因方向 |
|------|------|----------|
| fixed>0 | unstable_generation | 生成器（continuity_producer/写入工具）写入后未同步 manifest |
| result=FAIL 且 fixed=0 | over_strict | 修复无物可修但校验仍失败 → 规则/白名单与真实写入路径不匹配 |
| 其余（动态收尾 fixed=0、修复未执行、reason 不可解析） | benign | 正常无漂移 / 环境性 |

连续场景强化：连续 ≥2 条 over_strict 事件 = 1 个 `over_strict_runs` 连续段
（校验过严复发的最强证据）。阈值建议：任一周期内 over_strict 事件 ≥3 或
连续段 ≥1 时，人工检视 CONTINUITY 源清单与 allowed_paths 规则（提示用，
不改自动语义）。

## 2. 当前仓库基线（真实数据）

- guard-events 总事件数：3719
- repair 事件数：**0**（check_type="repair" 为本任务新引入，历史无样本）
- `repair_trigger_rate`：0.0（真实观测值）
- 读侧损坏行（D4-6）：0

结论：修复器现象在当前仓库尚未有可观测触发记录；新事件类型自本任务起
持续写入，下一 gate 周期可基于真实样本复核阈值。

## 3. 代表样本分类（规则实证，样本为规则行为展示）

样本事件（构造，时间戳统一）：

| # | result | failure_reason | 归类 |
|---|--------|----------------|------|
| 1 | FAIL | `SOURCE_DRIFT fixed=0 (auto-repair found nothing to fix)` | **over_strict** |
| 2 | FAIL | `SOURCE_DRIFT fixed=0 (auto-repair found nothing to fix)` | **over_strict** |
| 3 | PASS | `SOURCE_DRIFT fixed=3` | **unstable_generation** |
| 4 | PASS | `dynamic fixed=0` | **benign** |
| 5 | FAIL | `dynamic repair failed: boom` | **benign** |

`repair_classification` 汇总（实测输出）：

```json
{"status": "computed", "over_strict": 2, "unstable_generation": 1,
 "benign": 2, "over_strict_runs": 1}
```

解读：
- #1/#2 连续 fixed=0 且 FAIL → 1 个 over_strict 连续段：若真实周期内出现
  该形态，说明 CONTINUITY 源清单含非动态文件却被正常流程写改（或规则与
  实际写入路径不匹配），应人工检视清单构成——这是自动修复掩盖根因的
  主要风险面（修复 GO ≠ 长期有效）。
- #3 fixed=3 → 生成路径漏更新清单：优先排查最近写入 .ai/ 治理文件的
  工具/流程是否在写后未同步 manifest。
- #4 动态收尾 fixed=0 属正常（每次会话收尾都会触发一次），不构成信号。
- #5 修复尝试异常（如动态签名不支持）为环境性，不归类缺陷。

## 4. 分布建议口径

| 信号 | 建议动作 | 自动阻断 |
|------|----------|----------|
| over_strict ≥3/周期 或 over_strict_runs ≥1 | 人工检视 CONTINUITY 源清单与白名单 | 否 |
| unstable_generation 计数上升 | 排查写入路径 manifest 同步链（continuity_producer） | 否 |
| trigger_rate 持续 >0 | 结合 over/unstable 占比判断修复器是否为"常态化兜底" | 否 |

## 5. 边界（本任务硬约束）

- 归类为纯呈现：不进 gate 判定、不改变 fail-closed 语义（非 repair 模式
  SOURCE_DRIFT 仍 exit 2，AC-03 测试断言）。
- `repair_continuity.py` 零改动（语义哈希永不自动修复；dynamic_only 仅修
  三个动态条目——边界测试 `TestFallbackBoundaries` 5 项全绿）。
