# T-0093 — SLO 门禁 wave 2：error budget 耗尽自动冻结发布（设计证据）

| | |
|---|---|
| **Task** | T-0093 — SLO 门禁 wave 2 接线（B2 §1.4/§1.5 `slo_budget_available`） |
| **Role** | developer |
| **Status** | implemented（AC-01..AC-06 全部验证） |
| **Basis** | docs/designs/loop-v4-slo-metrics-learning.md（B2）；loop_core/governance_metrics.py（T-0090 D2 advisory 核算）；T-0093 需求（approved） |
| **约束** | 只强化不弱化：本实现只**新增**阻断条件，不修改任何既有检查的判定逻辑 |

---

## 1. 接入点决策（为什么选 loop_enforcement S6 门 + 独立 checker CLI）

发布验证链现状（调研结论）：

- `hooks/scripts/loop_enforcement.py::check_phase_gate_enforcement(root, "S6-delivery")`
  是 PreToolUse hook 每次 S6 写入都会执行的发布证据链：`check_delivery_gate_evidence`
  （GO/NOGO）→ `check_runtime_quality_gate` → `check_security_gate_evidence`。
- `.ai/checkers/` 下的 checkers（compile_gate.py / run_governance_checks.py）是
  **独立可调用**的检查器：run_governance_checks.py 只校验 gate register，目前没有任何
  发布脚本接线它（grep 全仓确认）。

选择：

1. **主接线点 = loop_enforcement.py S6 分支**，新增 `check_slo_gate_evidence(root)`，
   与 `check_delivery_gate_evidence` 同级追加（T-0093 任务书明确要求"与现有 release
   证据链对齐（check_delivery_gate_evidence 同级）"）。改动为**纯追加**：
   - S6 分支新增一个调用 + 一条 return 消息追加 SLO 结果（消息文本变化，判定语义不变）；
   - 新增一个 wrapper 函数（约 30 行）；
   - 不触碰 `check_delivery_gate_evidence` / `check_runtime_quality_gate` /
     `check_security_gate_evidence` 的判定逻辑。
   - 该函数只可能**新增** EXIT_BLOCK 分支，不可能放松既有分支（AC-06）。
2. **工具入口 = `.ai/checkers/slo_gate_checker.py`**（compile_gate.py 同款 CLI：
   JSON 报告 + 退出码 0/1/2），供 release 脚本/质量门禁直接调用，与 hook 共享同一
   `loop_core/slo_gate.check_slo_gate` 代码路径。
3. `run_governance_checks.py` **不改动**（它的语义是 gate-register 校验，保持单一职责，
   避免向既有 checker 结果里混入新 fail-closed 检查导致语义漂移）。

测试证明接线成立（AC-02）：`check_phase_gate_enforcement(root, "S6-delivery")` 在
FREEZE 数据下返回阻断（含 `ERROR_BUDGET_EXHAUSTED`），HEALTHY 下放行，禁用后放行，
NOGO + HEALTHY 仍由既有检查阻断（AC-05）。

## 2. 门禁语义（AC-01）

`loop_core/slo_gate.py::check_slo_gate(project_root, budget=None, window=None, releases=0, now=None)`
返回 `SloGateResult`（decision PASS/BLOCK + reason + budget 明细 + missing/warnings/notes）：

| budget 状态（D2 核算） | 门禁决策 | reason |
|---|---|---|
| HEALTHY | PASS | error budget healthy — release allowed（含消费/总额） |
| CONSUMING | PASS + warning | within limits（附剩余单位警告） |
| FREEZE_RECOMMENDED | BLOCK | `ERROR_BUDGET_EXHAUSTED`: error budget exhausted — release frozen（含明细） |
| 数据不足（必需源缺失/不可解析） | BLOCK（fail-closed） | data insufficient (fail-closed)… 逐条列出缺失源 |
| 门禁禁用（config/env） | PASS + note | disabled by config/env — advisory-only mode |
| 有效豁免覆盖 FREEZE | PASS + note | exemption SLO-EX-xxxx in effect（approver/过期时间/原因） |

预算计算与 D2 **同一条代码路径**（复用 `load_slo_config` / `evaluate_sli` /
`compute_error_budget`），保证与 `build_report` 的 budget 逐字段一致
（有测试：`test_precomputed_budget_param` 用 `build_report().budget` 直接喂门禁）。

### 2.1 数据完备性策略（fail-closed 的精确边界）

门禁判定所需**必需源**（预算消费型 SLI 的输入）：

- `.ai/gates.yaml`（S1/S2/S5/S6 rejection + approval_latency SLI）
- `.ai/task_graph.yaml`（rework_cycle_rate SLI）
- `.ai/evidence/observability/guard-events.jsonl`（guard_anomaly_rate SLI）

任一缺失/不可解析 → BLOCK，原因列出该源（**绝不猜测、绝不静默零**，B2 §2.5）。

明确**不阻断**的两类 NOT_AVAILABLE（列入 warnings，不消耗预算——与 D2
`compute_error_budget` 只累计 computed 消费的行为一致）：

1. 源存在但数据集为空（如某 phase 无已决 gate："no decided gates for phase…"）；
2. 文档化的 wave-2 未接线源（`guard_decisions.jsonl`、`phase_transitions.jsonl`、
   `runtime-events.jsonl` 及未记录的 SLI）。若把它们当作必需源，门禁将**永久死锁**
   （任何仓库都无法放行），与 B2 §1.4"预算可重建、耗尽即冻结"的设计意图相悖；
   这些 SLI 以 `sli:xxx NOT_AVAILABLE — …(not budget-consumed)` 形式透明呈现。

这一策略在 design 中明示，作为 B2 §2.5 fail-closed 的**门禁侧实现细则**：门禁在
"能判定预算"与"不能判定预算"之间划界，不能判定（必需源缺失）→ BLOCK；
能判定（按 D2 同路径核算）→ 按状态决策。

### 2.2 窗口与恢复（AC-04）

窗口解析：显式 `window` 参数 > `.ai/slo.yaml` 的 `window_start/window_end` > 全部数据
（D2 默认）。窗口化预算 = 只统计窗口内 gate（`load_gates(since=start)` + 上界过滤）与
guard 事件。因此**窗口滚动 → 预算重置 → 门禁自动放行**（B2 §1.4 unfreeze: window
rollover）。D2 报告（build_report）的 window 是元数据标签，门禁的窗口是**核算边界**——
两者在 design 中显式区分（门禁接线是 wave 2 的细化，不改 D2 报告行为）。

## 3. 豁免机制（AC-03）

- 记录：`record_slo_exemption(project_root, reason, expires_at, approver)` → 追加到
  `.ai/evidence/observability/slo-exemptions.json`（**append-only**：已有记录永不修改/
  删除；新记录追加，id 单调递增 `SLO-EX-NNNN`）。
- 校验：reason 非空、approver 非空（缺失 → ValueError 拒绝）、expires_at 可解析
  （ISO-8601；过去时间允许记录但立即失效——这就是过期可观察的方式）。
- 判定：豁免有效 ⇔ `expires_at > now` 且 `approver` 非空。有效豁免把 FREEZE 决策翻转为
  PASS（reason 含豁免 id/approver/过期时间）；过期豁免失效 → 基础决策恢复（重新 BLOCK，
  warning 注明过期）。
- 失败方向：豁免文件**不可解析 → 视为无有效豁免**（不可读的覆盖不能覆盖冻结），
  且门禁从不写该文件（有字节级只读测试）。

## 4. 开关（AC-02）

默认**启用**（B2 wave 2 enforced）。禁用通道：

1. 环境变量 `LOOP_SLO_GATE_ENABLED=0|false|off|no`（显式值优先，双向覆盖 config）；
2. `.zcode/skills/loop-governance/config.yaml` → `slo_gate: {enabled: false}`
   （`hook_common.DEFAULT_CONFIG` 新增同名节，`_merge` 机制天然支持项目覆盖）。

禁用时门禁返回 PASS + note（advisory 模式），hook 放行并注明。

## 5. 不改动的既有行为（AC-05 / AC-06）

- `check_delivery_gate_evidence`（NOGO/缺 owners/deadline 等）语义零改动（有测试：
  NOGO + HEALTHY 预算仍阻断，且阻断消息仍是 NOGO 原因）。
- S5/S7/S8-S11 分支未触碰（有测试：S5 全证据放行、S7 缺证据仍阻断——SLO 门禁仅 S6）。
- `hook_common.load_config` / `DEFAULT_CONFIG`：只**新增**一个 `slo_gate.enabled` 键
  （默认 True），既有键值不动。
- 门禁模块加载/执行异常 → fail-closed 阻断（T-0083 AC-06 姿态），绝不 fail-open。

## 6. 文件清单（diff 摘要）

| 文件 | 变更 |
|---|---|
| `loop_core/slo_gate.py` | **新增** ~490 行：check_slo_gate / SloGateResult / record_slo_exemption / load_exemptions / slo_gate_enabled / 窗口化预算 |
| `.ai/checkers/slo_gate_checker.py` | **新增** ~200 行：CLI（JSON + 退出码 0/1/2，compile_gate 同款） |
| `hooks/scripts/loop_enforcement.py` | **+38 行**：新增 check_slo_gate_evidence；S6 分支追加 1 个调用；return 消息追加 SLO 结果（纯追加） |
| `hooks/scripts/hook_common.py` | **+9 行**：DEFAULT_CONFIG 新增 `slo_gate: {enabled: True}` |
| `tests/test_slo_gate.py` | **新增** 40 个测试（AC-01..AC-05） |
| `.ai/evidence/T-0093/slo-gate/design.md` | 本文档 |

## 7. 验收对照

| AC | 证据（测试） | 结果 |
|---|---|---|
| AC-01 | TestSloGateDecision（HEALTHY PASS / FREEZE BLOCK / CONSUMING PASS+warn / 缺失 fail-closed BLOCK 带明细 / 不可解析源 BLOCK / 预计算 budget） | 12 passed |
| AC-02 | TestSloGateToggle（默认启用/环境变量禁用/config 禁用/env 优先）+ TestSloGateCheckerCli（退出码 0/1/2/禁用）+ TestSloGateHookWiring（S6 门接线：FREEZE 阻断、HEALTHY 放行、禁用放行、缺数据 fail-closed） | 14 passed |
| AC-03 | TestSloExemption（记录/append-only/有效豁免覆盖/过期失效/approver 缺失拒绝/不可读账本无法覆盖/无批准人条目无效） | 9 passed |
| AC-04 | TestSloRecovery（全量 FREEZE → 窗口滚动恢复 HEALTHY PASS；slo.yaml 窗口默认生效） | 3 passed |
| AC-05 | TestSloGateBackwardCompat（NOGO 仍阻断 / 全证据放行 / 只增阻断 / 非 S6 阶段不受影响）+ 全量回归 | 4 passed + 全量 3413+ |

门禁对真实仓库现状：`.ai/` 必需源齐全 → budget HEALTHY → PASS（S6 发布链可正常放行，
不产生死锁）；三个 wave-2 未接线源以 warning 呈现。
