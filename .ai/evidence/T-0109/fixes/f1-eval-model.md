# T-0109 F1 评估模型 — 修复证据（AC-03）

日期：2026-08-03
范围：证据七态枚举 / GateLesson evidence 字段 / 评分上限表 59-74-84-94-100 /
Repair Progress 与 Loop Effectiveness 分离指标 / **advisory-only 静态断言**

## 改动

### 1. `loop_core/schemas/evidence_state.py`（新增，零依赖）
- `EvidenceState` 枚举七态：Present / Wired / Exercised / Outcome-supported /
  Missing / Unobserved / N-A（str-Enum，可直接序列化）。
- `coerce(value)`：大小写/连字符/空值规整；空值 → N-A；未知值 → ValueError
  （fail-closed，绝不静默猜测）。
- 评分上限表（代码默认值 `DEFAULT_SCORE_CAPS` + `SCORE_BANDS=(59,74,84,94,100)`）：
  Missing/Unobserved/N-A → 59，Present → 74，Wired → 84，Exercised → 94，
  Outcome-supported → 100；`apply_score_cap(raw, cap)=min(round(raw), cap)`；
  `score_cap_for_state` 支持注入 .ai/slo.yaml 显式化配置。
- 模块内不含任何 gate 判定函数（设计约束：七态仅描述验证结果，不替代
  evidence_chain/execution_ledger 哈希校验；Missing/Unobserved 不得自动通过门禁）。

### 2. `loop_core/gate_feedback.py`
- `GateLesson` 新增 `evidence_state` 字段（默认 N-A；advisory 呈现）。
- `to_dict` 恒输出规整七态值；`from_dict` 缺字段 → N-A（**旧记录向后兼容**，
  GATE_LESSONS_SCHEMA_VERSION 保持 1）；非法值 fail-closed 拒绝。
- `record_gate_lesson` 新增 `evidence_state` 关键字参数（缺省 N-A）。
- 判定语义零改动：decision/reason_category 校验、幂等 dedup、_RECORD_LOCK
  串行写均原样。

### 3. `loop_core/governance_metrics.py`
- `load_slo_config` 解析 `.ai/slo.yaml` 新增 `score_caps` 节（配置外置模式）：
  mapping 校验 fail-closed（非 mapping / 非法状态名 / 非有限非负数 →
  DataSourceUnavailableError）；缺失 → 代码默认表。
- 新增分离指标族（advisory-only）：
  - `build_repair_progress(ctx)`：repair_triggers（rejected gate 数）/
    fixed_gates（同任务 prior rejected 的 approved gate 数，即修复 GO）/
    repair_progress 比率。
  - `build_loop_effectiveness(ctx)`：gate_pass_rate（approved/(approved+rejected)）/
    task_cycle_time（task_cycle_time_stats 复用）/ rework_total
    （rework_cycles_from_gates 同源）。
  - `evidence_score_advisory(raw, state, caps)`：纯呈现函数（cap/score/bands）。
- `MetricsReport` 新增 `repair_progress` / `loop_effectiveness` / `score_caps`
  字段（to_dict 输出）；`build_report` 计算；`render_markdown` 新增
  「Repair Progress / Loop Effectiveness」节 + score caps 行。

### 4. `.ai/slo.yaml`
- 新增 `score_caps:` 节（七态 → 上限，与代码默认表一致），对齐既有配置
  外置模式（T-0095：改配置即生效，无需改代码）。

### 5. `loop_core/subagent_evidence_verifier.py`：零改动
design-bh-integration.md F1 列其为映射消费方，但不在 T-0109 任务卡
allowed_paths（写路径仅限任务卡）——验证结果映射七态留待后续任务
（已记入遗留）。本任务提供 `EvidenceState.coerce` 作为统一映射入口。

## 测试（tests/test_t0109_f1_eval_model.py，29 passed）

- **TestEvidenceStateEnum**：七态值域精确断言；coerce 往返/变体规整/空值；
  非法值 ValueError（fail-closed）。
- **TestGateLessonEvidenceState**：record round-trip；默认 N-A；旧记录缺字段
  → N-A（向后兼容实证）；非法值 InvalidLessonError。
- **TestScoreCapTable（AC-03 分档边界）**：SCORE_BANDS 精确；
  state→cap 七态映射；**59/74/84/94/100 各档等值断言**（raw==cap → score==cap，
  parametrize 5 档）；raw 超上限 → 压档；低于上限保持；slo.yaml 显式化解析
  与默认一致；slo.yaml 覆盖生效 + 非法（未知状态/-5）fail-closed。
- **TestRepairLoopSeparation**：repair_triggers/fixed_gates/progress 计数断言；
  Loop Effectiveness gate_pass_rate/rework_total 独立字段；NOT_AVAILABLE
  fail-closed；cycle time 字段存在。
- **TestAdvisoryStaticAssertions（AC-03 静态断言）**：
  - AST 扫描 7 个 gate 判定模块（state_machine / hooks gate_guard /
    enforcement / hard_constraints / guard_health / slo_gate / approval_ledger）
    源码不含任何 advisory 符号（score_cap/score_band/evidence_score/
    apply_score_cap/evidence_state/EvidenceState）。
  - 函数级断言：state_machine.can_approve_gate / can_transition_phase 函数体
    无评分符号。
  - hooks/ 目录全仓无 advisory 符号（hook 零改动门禁补充）。

## 约束自查

| 硬约束 | 实证 |
|--------|------|
| 评分仅呈现/度量不进 gate 决策 | 静态断言测试全绿（7 模块 AST 零符号 + 函数级断言）；governance_metrics 中 evaluate_sli/compute_error_budget 未引用评分函数 |
| 防篡改哈希链不动 | evidence_chain/execution_ledger 未触碰；七态仅描述验证结果 |
| Missing/Unobserved 不得自动通过 | 评分函数无判定语义；无 gate 路径引用 |
| 审批闭环零改动 | approval_ledger/state_machine 判定未触碰（state_machine 的 diff 仅为 F2-2 刷新调用，见 f2-write-convergence.md） |
| 写路径限 allowed_paths | schemas/evidence_state.py、gate_feedback.py、governance_metrics.py、.ai/slo.yaml、tests/ |
| 版本文件不改 | pyproject/CHANGELOG 未触碰（bump 主会话） |

## 回归

- test_gate_feedback / test_governance_metrics / test_slo_consistency /
  test_t0109_f1_eval_model：全绿（93 passed 批次内）。
- governance_metrics 报告构建 + render_markdown 冒烟正常（含新节）。

## 遗留

1. `subagent_evidence_verifier.py` 的验证结果 → 七态映射消费（不在本任务
   allowed_paths）：建议 T-0110/T-0111 接入 `EvidenceState.coerce`（统一入口
   已就绪）。
2. 评分上限表 slo.yaml 显式化已完成；M-16（slo.yaml 上限表常量集中）在
   T-0110 范围（roadmap 已排布），本任务不重复落地。
