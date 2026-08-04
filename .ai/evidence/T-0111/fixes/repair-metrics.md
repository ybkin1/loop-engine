# T-0111 修复器度量落地（design-common-weakness.md 3.2 + D4-6）

日期：2026-08-03
涉及文件：`loop_core/observability.py`、`loop_core/governance_metrics.py`、
`.zcode/tools/validate_state.py`、`.zcode/tools/close_session.py`（判定零改动）

## 1. guard-events 事件类型扩展：check_type="repair"

`observability.py` 新增常量 `CHECK_REPAIR = "repair"`（check_type 枚举向后
兼容——既有消费者只按已知 check_type 过滤/计数，未知类型不影响其判定；
`load_guard_events` strict-parse 不校验 check_type 值，repair 事件可正常
加载，由测试 `test_repair_events_loadable_by_existing_consumers` 断言）。

事件字段约定（PASS/FAIL 两分支）：

| 触发点 | result | failure_reason 格式 | 语义 |
|--------|--------|---------------------|------|
| validate_state REPAIR_MODE + SOURCE_DRIFT，repair fixed>0 且重新校验通过 | PASS | `SOURCE_DRIFT fixed=<n>` | 修复闭环成功 |
| validate_state REPAIR_MODE，repair fixed=0（无物可修） | FAIL | `SOURCE_DRIFT fixed=0 (auto-repair found nothing to fix)` | 修复后校验仍失败 → over_strict 证据 |
| validate_state REPAIR_MODE，repair/重新校验抛错 | FAIL | `SOURCE_DRIFT auto-repair failed: <err>` | 修复器异常 |
| close_session 收尾 dynamic_only 修复完成 | PASS | `dynamic fixed=<n>` | 收尾动态修复（fixed=0 属正常） |
| close_session 收尾修复被跳过/失败 | FAIL | `dynamic repair failed: ...` 等 | 环境/异常 |

- guard_id 恒为 `"repair_continuity"`；source 标记 `tool:<脚本名>`。
- PASS 分支写入点在**重新校验通过之后**（重新校验抛错 → 只写 FAIL），
  保证 PASS 事件语义 = "修复 + 重新校验通过"（design 3.3 口径）。
- 写入为观测侧旁路：`_record_repair_event` 全程 try/except 吞错；优先走
  `loop_core.observability.GuardEventRecorder`（同 schema），loop_core
  不可导入时降级为等价最小 JSONL 追加（子进程运行环境实证路径）。
- **判定零改动**：validate_state/close_session 仅新增事件写入语句，无任何
  既有判定/exit code/控制流变更（`git diff` 复核 + AC-03 测试断言）。

## 2. 指标：repair_trigger_rate / repair_classification

`governance_metrics.py` 新增三个纯函数（guard_events 输入 → 可复现输出，
**报告制，不进入任何 gate 判定路径**）：

- `repair_trigger_rate(events)`：`rate = repair 事件数 / guard 检查总数`；
  空源 → NOT_AVAILABLE（fail-closed 不合成零值）；无 repair → 0.0（真实观测）。
- `classify_repair_event(event)`：单事件归类
  - `unstable_generation`：fixed>0（生成器写入后未同步 manifest）
  - `over_strict`：result=FAIL 且 fixed=0（规则/白名单与真实写入路径不匹配）
  - `benign`：其余（动态收尾 fixed=0 正常；修复尝试未执行/不可解析）
- `repair_classification(events)`：三类计数 + `over_strict_runs`（连续 ≥2
  条 over_strict 的连续段数——fixed=0 连续场景是校验过严最强证据，AC-02）
  + 逐条事件明细。

**设计决策（与 golden 基线的兼容）**：指标以独立函数形式落地，**不**改动
`MetricsReport`/`build_report`/`render_markdown`/`to_dict`——T-0110 拆分
golden 的逐字节等价基线（`test_golden_metrics_byte_identical`）保持不变；
指标由 `repair-classification-report.md` 与后续 dashboard 消费。

**golden dir() 表面基线更新（有意漂移，已文档化）**：上述新增使
`governance_metrics` 模块表面 +6 名（`CHECK_REPAIR`、`_REPAIR_FIXED_RE`、
`classify_repair_event`、`re`、`repair_classification`、`repair_trigger_rate`），
`test_reexport_surface_governance_metrics`（dir() == 拆分前基线）随之失败。
已用官方生成器重生成 `.ai/evidence/T-0110/golden/golden-before.json`：
`git diff` 验证仅 `dir_snapshots.governance_metrics` +6 行、其余全部
逐字节一致。这是任务卡要求的特性新增（非拆分漂移），T-0110 拆分行为
等价证据不受影响（golden 的度量/intent 捕获输出零变化）。

## 3. D4-6：读侧损坏行计数（同文件同批）

`observability.py` `GuardEventRecorder`：

- 新增 `read_corrupt_lines` 进程内累计计数器（与写侧 `failures` 对称）；
- `_read_file` 改为**逐行**容错：损坏行计数 + `logger.warning` 后跳过，
  不再整文件 abort——可读前缀与后缀全部保留（旧实现中段损坏会丢弃后缀）；
- `summary()` 新增 `read_corrupt_lines` 键上报。

测试（tests/test_observability.py::TestT0111ReadCorruptCounting）：
主文件损坏计数 / 中段损坏后缀保留 / 轮转归档内损坏计数 / summary 上报。

## 4. 测试

- `tests/test_repair_governance.py`（新增 20 项）：AC-01 事件两分支
  （validate_state PASS/FAIL + close_session 收尾 + 既有消费者兼容）、
  AC-02 归类规则（含连续段）、AC-03 兜底边界、trigger_rate、
  端到端集成（REPAIR_MODE 运行 → guard-events → 指标）。
- 既有消费者集全绿（metrics/b1 golden/manifest/doc-link/guard_health/
  self_audit/f5/batch3），基线既有 3 项失败另列（commands.md 遗留事项）。

## 5. 证据链

- AC-01 实测：`tests/test_repair_governance.py::TestRepairEvents`（PASS 分支
  exit 0 + 事件 PASS fixed=1；FAIL 分支 exit 2 + 事件 FAIL fixed=0）。
- 兜底边界：`TestFallbackBoundaries`（dynamic_only 哈希不重算可观测断言：
  semantic_sha256 与 source_sha256 值均不变；全量模式对照组 source_sha256
  变化——证明"不重算"是可区分行为）。
