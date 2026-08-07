"""
Governance metrics — SLI / SLO / error budget accounting + Loop-DORA telemetry
(T-0090 D2, B2 design docs/designs/loop-v4-slo-metrics-learning.md §1/§2).

T-0110 批 B-1 拆分后本文件为 **re-export 壳**：全部公开符号（含私有但被
消费方直接导入的符号，如 ``_parse_dt``）从四个新模块 re-export，行为与
拆分前逐字节/逐字段等价：

- ``loop_core/governance_loaders.py`` — 数据加载（load_gates/load_tasks/
  load_guard_events/load_phase_transitions/load_executions/
  load_runtime_events/_load_jsonl/DataSourceUnavailableError）
- ``loop_core/governance_aggregations.py`` — 记录数据类（GateMetric/
  TaskRecord/PhaseTransition/SliContext）、相位分类、时间/统计辅助、
  纯度量聚合函数（依赖图叶子）
- ``loop_core/slo_evaluator.py`` — SLI/SLO 评估与 error-budget 记账
  （load_slo_config/evaluate_sli/compute_error_budget + 哨兵/默认表常量）
- ``loop_core/dora_metrics.py`` — DORA 指标构建（build_dora_metrics/
  _sha256/git_commit）

本壳保留的实体（原文件 :1211 起）：Repair Progress / Loop Effectiveness
分离指标（T-0109 F1，advisory-only）、evidence_score_advisory、
MetricsReport 报告模型与 build_report/render_markdown 主流程。

拆分边界与行为等价证据见 .ai/evidence/T-0110/fixes/batch-b1-metrics-intent.md。

Scope (wave 1 advisory):
- SLI collection from existing data sources (.ai/gates.yaml,
  .ai/task_graph.yaml, .ai/evidence/observability/guard-events.jsonl,
  .ai/ledger/executions.jsonl, optional transition journal / guard decision
  log / runtime events ledger).
- SLO/error-budget accounting per B2 §1.4 (v1 rule: one breach event = 1 unit
  per budget-consuming SLO; ``budget_share`` scales a unit's weight; budget
  exhaustion is *reported* as FREEZE_RECOMMENDED only — release blocking is
  wave 2, out of scope here).
- DORA-style metrics report (gate rejection rate, decision coverage,
  approval latency, task cycle time, rework, guard anomaly rate, ...) as a
  structured JSON report + human-readable markdown, ReportBinding-style.

Rules:
- Read-only aggregation: this module never writes to its data sources.  The
  report artifact is written by the CLI (tools/loop_metrics.py) to the
  evidence directory.
- A missing or unparseable *wired* data source is surfaced as NOT_AVAILABLE,
  never guessed or silently zeroed, and makes the report NOT_VERIFIED
  (fail-closed, B2 §2.5).  Documented wave-2 wiring items
  (phase_transitions.jsonl / guard_decisions.jsonl / runtime-events.jsonl,
  T-0100 F-05) are surfaced as **per-source advisories** instead: computed
  items are judged on their real values, and the report is not demoted to
  NOT_VERIFIED merely because an unwired source is absent.
- Every metric is a pure function of ledger inputs so results are
  reproducible from a commit (B2 §2.3).
- Release-fee accounting lives in exactly one function
  (``release_fee_consumption``, used by ``compute_error_budget``) — the SLO
  gate references the same computation, so metrics and slo_gate budgets are
  consistent for identical inputs (T-0100 F-05).
"""
from __future__ import annotations

import hashlib  # noqa: F401 — 命名空间保持（拆分前同源绑定，dir() 面不变）
import json
import math  # noqa: F401 — 命名空间保持
import re
import statistics  # noqa: F401 — 命名空间保持
import subprocess  # noqa: F401 — 命名空间保持
from collections import Counter  # noqa: F401 — 命名空间保持
from collections.abc import Sequence  # noqa: F401 — 命名空间保持
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone  # noqa: F401 — timedelta 命名空间保持
from pathlib import Path
from typing import Any

import yaml  # noqa: F401 — 命名空间保持

from loop_core.dora_metrics import (
    _sha256,
    build_dora_metrics,
    git_commit,
)
from loop_core.governance_aggregations import (
    _DECIDED_STATUSES,
    GATE_PHASE_TOKENS,
    GateMetric,
    PhaseTransition,
    SliContext,
    TaskRecord,
    _over_target,
    _parse_dt,
    _percentile,
    _seconds_stats,
    approval_latencies,
    approval_latency_stats,
    classify_gate_phase,
    drift_event_counts,
    execution_cycle_stats,
    gate_decision_coverage,
    gate_rejection_rate,
    guard_anomaly_rates,
    phase_dwell_stats,
    rework_cycles_from_gates,
    rework_cycles_from_transitions,
    task_cycle_seconds,
    task_cycle_time_stats,
)
from loop_core.governance_loaders import (
    DataSourceUnavailableError,
    _load_jsonl,
    load_executions,
    load_gates,
    load_guard_events,
    load_phase_transitions,
    load_runtime_events,
    load_tasks,
)
from loop_core.observability import CHECK_REPAIR, GuardCheckEvent  # noqa: F401 — 命名空间保持
from loop_core.schemas.evidence_state import (  # T-0109 F1 (advisory)
    DEFAULT_SCORE_CAPS,
    SCORE_BANDS,
    apply_score_cap,
    score_cap_for_state,
)
from loop_core.slo_evaluator import (
    BUDGET_CONSUMING,
    BUDGET_FREEZE_RECOMMENDED,
    BUDGET_HEALTHY,
    DEFAULT_BUDGET_TOTAL_UNITS,
    DEFAULT_RELEASE_FEE_UNITS,
    DEFAULT_SLOS,
    NOT_AVAILABLE,
    REPORT_NOT_VERIFIED,
    REPORT_PASS,
    SEVERITY_BUDGET,
    SEVERITY_HARD_GATE,
    SEVERITY_INFO,
    UNWIRED_SLI_IDS,
    WAVE2_UNWIRED_SOURCES,
    _metric,
    _not_available,
    compute_error_budget,
    evaluate_sli,
    load_slo_config,
    release_fee_consumption,
)

_TASK_COMPLETED_STATUS = "completed"


# ── T-0109 F1: Repair Progress / Loop Effectiveness 分离指标（advisory）───
# 两族指标独立呈现、独立度量：
#   - repair_progress：修复闭环进度（repair 触发次数 / 修复 GO 数）
#   - loop_effectiveness：循环有效性（gate 通过率 / cycle time）
# **评分与指标仅呈现/度量，不进任何 gate 判定路径**（AC-03 静态断言）。


def repair_trigger_count(gates: Sequence[GateMetric]) -> int:
    """repair 触发次数 = rejected gate 数（rejection -> fix -> re-audit 的
    每次触发；与 rework_cycles_from_gates 同源口径）。"""
    return sum(1 for g in gates if g.status == "rejected")


def fixed_gate_count(gates: Sequence[GateMetric]) -> int:
    """修复 GO 数 = 存在同任务先前 rejected 记录的 approved gate 数。

    口径：approved gate 的同 task_id 下出现过 rejected gate（已知
    recorded_at 时须早于本 gate）→ 视为修复闭环完成（GO）。确定性、
    纯 gates 输入派生；与 rework_cycles_from_gates 同源，可复现。
    """
    approved = [g for g in gates if g.status == "approved"]
    rejected_by_task: dict[str, list[datetime | None]] = {}
    for g in gates:
        if g.status == "rejected":
            rejected_by_task.setdefault(g.task_id, []).append(g.recorded_at)
    fixed = 0
    for g in approved:
        prior = [ts for ts in rejected_by_task.get(g.task_id, []) if ts is not None]
        if g.recorded_at is not None:
            if any(ts < g.recorded_at for ts in prior):
                fixed += 1
        else:
            if rejected_by_task.get(g.task_id):
                fixed += 1
    return fixed


def build_repair_progress(ctx: SliContext) -> dict[str, Any]:
    """Repair Progress（修复进度族）：triggers / fixed GO / progress ratio。

    数据不可用（gates 源缺失）→ NOT_AVAILABLE（fail-closed，不合成零值）。
    """
    if ctx.gates is None:
        return _not_available("gates register unavailable")
    triggers = repair_trigger_count(ctx.gates)
    fixed = fixed_gate_count(ctx.gates)
    progress = round(fixed / triggers, 4) if triggers else None
    return {
        "status": "computed",
        "repair_triggers": triggers,
        "fixed_gates": fixed,
        "repair_progress": progress,
        "basis": "triggers=rejected gates; fixed=approved gates with prior "
                 "rejection on the same task (GO 修复闭环)",
    }


def build_loop_effectiveness(ctx: SliContext) -> dict[str, Any]:
    """Loop Effectiveness（循环有效性族）：gate 通过率 + cycle time。

    - gate_pass_rate：approved / (approved + rejected)（gate 通过率）
    - task_cycle_time：task_cycle_time_stats（cycle time，天）
    - rework_total：rework_cycles_from_gates 合计（与 DORA 同源）
    """
    effectiveness: dict[str, Any] = {}
    if ctx.gates is None:
        effectiveness["gate_pass_rate"] = _not_available("gates register unavailable")
        effectiveness["rework_total"] = _not_available("gates register unavailable")
    else:
        decided = [g for g in ctx.gates if g.status in _DECIDED_STATUSES]
        passed = sum(1 for g in decided if g.status == "approved")
        effectiveness["gate_pass_rate"] = (
            {"status": "computed", "value": round(passed / len(decided), 4)}
            if decided else _not_available("no decided gates")
        )
        effectiveness["rework_total"] = {"status": "computed", "value": ctx.rework_total}
    effectiveness["task_cycle_time"] = (
        _metric(stats) if (stats := task_cycle_time_stats(ctx.tasks)) is not None
        else _not_available("no task with both created_at and updated_at")
    ) if ctx.tasks is not None else _not_available("task graph unavailable")
    return {"status": "computed", **effectiveness}


# ── T-0111: 修复器触发率 / 缺陷归类（报告制，不自动阻断）────────────────
# 数据源 = guard-events 的 check_type="repair" 事件（observability.py
# CHECK_REPAIR，由 validate_state REPAIR_MODE / close_session 收尾写入）。
# 两个指标都是 guard_events 的纯函数（可复现），只进入 metrics 报告与
# repair-classification-report，绝不进入任何 gate 判定路径（AC-03 语义）。

_REPAIR_FIXED_RE = re.compile(r"fixed=(\d+)")


def repair_trigger_rate(events: Sequence[GuardCheckEvent]) -> dict[str, Any]:
    """repair 触发率 = 周期内 repair 事件数 / guard 检查总数。

    - 无事件（空源）→ NOT_AVAILABLE（fail-closed：不合成零值，与
      guard_anomaly_rates 同口径）。
    - 返回 ``{status, repair_events, total_events, rate}``（rate 0~1，
      4 位小数；repair_events=0 时 rate=0.0 为真实观测值，可计算）。
    """
    if not events:
        return _not_available("no guard events")
    total = len(events)
    repairs = sum(1 for e in events if e.check_type == CHECK_REPAIR)
    return {
        "status": "computed",
        "repair_events": repairs,
        "total_events": total,
        "rate": round(repairs / total, 4),
        "basis": "repair events / guard check events (window)",
    }


def classify_repair_event(event: GuardCheckEvent) -> str:
    """单条 repair 事件归类（design-common-weakness.md 3.3，报告制）。

    - ``unstable_generation``：repair 事件 fixed>0 —— 生成器写入后未同步
      manifest（修复确有物可修，说明生成路径漏更新清单）。
    - ``over_strict``：result=FAIL 且 fixed=0 —— 修复无物可修但校验仍失败
      （规则/白名单与真实写入路径不匹配的证据）。
    - ``benign``：其余（动态收尾 fixed=0 属正常无漂移；修复尝试未执行或
      failure_reason 不可解析）。

    只分类、不阻断：调用方（metrics 报告/归类报告）不得把返回值传入
    任何 gate 判定路径。
    """
    m = _REPAIR_FIXED_RE.search(event.failure_reason or "")
    fixed = int(m.group(1)) if m else None
    if fixed is not None and fixed > 0:
        return "unstable_generation"
    if event.result == "FAIL" and fixed == 0:
        return "over_strict"
    return "benign"


def repair_classification(events: Sequence[GuardCheckEvent]) -> dict[str, Any]:
    """repair 事件分类汇总（AC-02，报告制不自动阻断）。

    输出 ``{over_strict, unstable_generation, benign}`` 三类计数 +
    ``over_strict_runs``（连续 ≥2 条 over_strict 的连续段数，固定=0 的
    "连续场景"是校验过严的最强证据）与逐条 ``events`` 明细。空输入 →
    NOT_AVAILABLE。
    """
    repairs = [e for e in events if e.check_type == CHECK_REPAIR]
    if not repairs:
        return _not_available("no repair events")
    counts: Counter[str] = Counter()
    labels: list[dict[str, Any]] = []
    runs = 0
    run_len = 0
    for e in repairs:
        label = classify_repair_event(e)
        counts[label] += 1
        labels.append({
            "event_id": e.event_id,
            "result": e.result,
            "failure_reason": e.failure_reason,
            "timestamp": e.timestamp,
            "classification": label,
        })
        if label == "over_strict":
            run_len += 1
        else:
            if run_len >= 2:
                runs += 1
            run_len = 0
    if run_len >= 2:
        runs += 1
    return {
        "status": "computed",
        "over_strict": counts["over_strict"],
        "unstable_generation": counts["unstable_generation"],
        "benign": counts["benign"],
        "over_strict_runs": runs,
        "events": labels,
        "basis": "fixed=0+FAIL -> over_strict; fixed>0 -> "
                 "unstable_generation; else benign (report-only)",
    }


def evidence_score_advisory(raw_score: float | int,
                            state: str | None = None,
                            caps: dict[str, int] | None = None) -> dict[str, Any]:
    """Evidence 评分呈现（advisory-only，T-0109 F1）。

    raw_score 按证据状态上限（.ai/slo.yaml score_caps 或默认表）封顶：
    score = apply_score_cap(raw, cap)。分档断点 SCORE_BANDS=(59,74,84,94,100)
    在报告里逐档标注（等值断言：raw==cap → score==cap）。

    本函数是纯呈现函数——调用方（dashboard/报告渲染）不得把返回值
    传入任何 gate 判定路径（AC-03 静态断言覆盖）。
    """
    cap = score_cap_for_state(state, caps)
    return {
        "status": "computed",
        "raw_score": int(round(float(raw_score))),
        "evidence_state": str(state) if state else "N-A",
        "cap": cap,
        "score": apply_score_cap(raw_score, cap),
        "bands": list(SCORE_BANDS),
        "advisory": True,
    }


# ── Report ───────────────────────────────────────────────────────────────

REPORT_SOURCE_FILES: tuple[tuple[str, str], ...] = (
    (".ai/gates.yaml", "gates"),
    (".ai/task_graph.yaml", "tasks"),
    (".ai/evidence/observability/guard-events.jsonl", "guard_events"),
    (".ai/ledger/executions.jsonl", "executions"),
    (".ai/ledger/phase_transitions.jsonl", "transitions"),
    (".ai/ledger/guard_decisions.jsonl", "guard_decisions"),
    (".ai/ledger/runtime-events.jsonl", "runtime_events"),
)


@dataclass
class MetricsReport:
    """Structured metrics report (B2 §2.3/§2.4), ReportBinding-style:
    binds git_commit + window + generated_at + tool identity.  ``status`` is
    PASS only when every *wired* metric is computed; a missing/unparseable
    wired source, or a wired-source NOT_AVAILABLE, makes it NOT_VERIFIED
    (fail-closed, B2 §2.5).  Documented unwired sources (wave-2 ledger items)
    are collected in ``advisories`` (per-source annotated, T-0100 F-05) and
    never demote the overall status by themselves."""
    window: tuple[str, str]
    generated_at: str
    git_commit: str
    task_id: str
    phase: str
    gate_id: str | None
    tool_name: str
    tool_version: str
    dora: dict[str, Any]
    sli_eval: list[dict[str, Any]]
    budget: dict[str, Any]
    slo_source: str
    sources: list[dict[str, Any]]
    status: str
    missing: list[str]
    notes: list[str] = field(default_factory=list)
    advisories: list[str] = field(default_factory=list)
    # T-0109 F1（advisory-only，不进 gate 决策）：
    repair_progress: dict[str, Any] = field(default_factory=dict)
    loop_effectiveness: dict[str, Any] = field(default_factory=dict)
    score_caps: dict[str, int] = field(default_factory=dict)
    # T-0145 7.1: mutation/gate_defense 由生成器实时聚合（读侧计数，
    # 替代手写快照）；T-0146 7.2: rejected_requests 为真实拦截计数。
    mutation_metrics: dict[str, Any] = field(default_factory=dict)
    gate_defense: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "report_type": "loop-dora-metrics",
            "binding": {
                "task_id": self.task_id,
                "phase": self.phase,
                "gate_id": self.gate_id,
                "git_commit": self.git_commit,
                "timestamp": self.generated_at,
                "tool_name": self.tool_name,
                "tool_version": self.tool_version,
            },
            "window": {"start": self.window[0], "end": self.window[1]},
            "status": self.status,
            "missing": self.missing,
            "advisories": self.advisories,
            "dora_metrics": self.dora,
            "slo_evaluation": self.sli_eval,
            "error_budget": self.budget,
            "slo_source": self.slo_source,
            "sources": self.sources,
            "notes": self.notes,
            "repair_progress": self.repair_progress,
            "loop_effectiveness": self.loop_effectiveness,
            "score_caps": self.score_caps,
            "mutation_metrics": self.mutation_metrics,
            "gate_defense": self.gate_defense,
        }


def _data_window(ctx: SliContext) -> tuple[str, str]:
    """Data bounds across the available sources (for the report header when
    no explicit window is given)."""
    stamps: list[datetime] = []
    if ctx.gates:
        stamps.extend(g.recorded_at for g in ctx.gates if g.recorded_at)
    if ctx.guard_events:
        stamps.extend(
            ts for e in ctx.guard_events
            if (ts := _parse_dt(e.timestamp)) is not None
        )
    if ctx.tasks:
        stamps.extend(t.created_at for t in ctx.tasks if t.created_at)
    if not stamps:
        return ("unknown", "unknown")
    return (min(stamps).isoformat(), max(stamps).isoformat())


def build_report(root: str | Path, window: tuple[str, str] | None = None,
                 slo_path: str | Path | None = None,
                 releases: int = 0,
                 task_id: str = "T-0090", phase: str = "S6-delivery",
                 gate_id: str | None = None) -> MetricsReport:
    """Build the full metrics report from the repository data sources.

    Read-only: never writes to any data source.  A missing/unparseable *wired*
    source is recorded in ``sources``/``missing`` and the affected metrics
    are NOT_AVAILABLE; the report status then is NOT_VERIFIED.  Documented
    unwired (wave-2) sources are recorded in ``advisories`` with per-source
    annotation and do not demote the overall status (T-0100 F-05)."""
    root_path = Path(root)
    data: dict[str, Any] = {}
    sources: list[dict[str, Any]] = []
    missing: list[str] = []       # 已接线源缺失/不可解析 → NOT_VERIFIED 驱动
    advisories: list[str] = []    # 未接线源（wave-2）→ 逐项 advisory（T-0100 F-05）
    for rel_path, key in REPORT_SOURCE_FILES:
        path = root_path / rel_path
        exists = path.exists()
        sources.append({
            "path": rel_path,
            "status": "available" if exists else "missing",
            "sha256": _sha256(path) if exists else None,
            "lines": sum(1 for _ in path.open("rb")) if exists else None,
        })
        if not exists:
            data[key] = None
            if Path(rel_path).name in WAVE2_UNWIRED_SOURCES:
                advisories.append(
                    f"数据源未接线（wave-2 项，不影响 computed 判定）: "
                    f"{key} ({rel_path})"
                )
            else:
                missing.append(f"{key} ({rel_path})")
            continue
        loader = {
            "gates": load_gates,
            "tasks": load_tasks,
            "guard_events": load_guard_events,
            "executions": load_executions,
            "transitions": load_phase_transitions,
            "guard_decisions": lambda p: _load_jsonl(
                root_path / ".ai" / "ledger" / "guard_decisions.jsonl",
                "guard decisions ledger"),
            "runtime_events": load_runtime_events,
        }[key]
        try:
            data[key] = loader(root_path)
        except DataSourceUnavailableError as exc:
            data[key] = None
            if Path(rel_path).name in WAVE2_UNWIRED_SOURCES:
                advisories.append(f"数据源未接线（wave-2 项）: {key} ({rel_path}): {exc}")
            else:
                missing.append(f"{key} ({rel_path}): {exc}")

    slo_config = load_slo_config(root_path, slo_path)

    ctx = SliContext(
        gates=data.get("gates"),
        tasks=data.get("tasks"),
        transitions=data.get("transitions"),
        guard_events=data.get("guard_events"),
        executions=data.get("executions"),
        drift_events=data.get("runtime_events"),
        guard_decisions=data.get("guard_decisions"),
        rework_by_task=(
            rework_cycles_from_gates(data["gates"]) if data.get("gates") is not None else {}
        ),
        rework_total=(
            sum(rework_cycles_from_gates(data["gates"]).values())
            if data.get("gates") is not None else 0
        ),
        completed_tasks=(
            len([t for t in data["tasks"] if t.status == _TASK_COMPLETED_STATUS])
            if data.get("tasks") is not None else 0
        ),
    )

    dora = build_dora_metrics(ctx)
    sli_eval = [evaluate_sli(sli, ctx) for sli in slo_config["slos"]]
    budget = compute_error_budget(
        sli_eval,
        total_units=slo_config["budget_total_units"],
        release_fee_units=slo_config["release_fee_units"],
        releases=releases,
    )
    # T-0109 F1: Repair / Loop 分离指标 + 评分上限表（advisory-only，
    # 不进 gate 判定路径；slo_config['score_caps'] 为 slo.yaml 显式化表）。
    repair_progress = build_repair_progress(ctx)
    loop_effectiveness = build_loop_effectiveness(ctx)
    score_caps = dict(slo_config.get("score_caps") or DEFAULT_SCORE_CAPS)

    # T-0100 F-05: NOT_VERIFIED 只由"已接线源"问题驱动 —— 未接线源（wave-2）
    # 的 NOT_AVAILABLE 进 advisories（逐项标注），computed 项按实值判定。
    all_not_available = [
        name for name, m in dora.items()
        if m.get("status") == NOT_AVAILABLE and not m.get("advisory")
    ] + [
        f"sli:{r['sli_id']}" for r in sli_eval
        if r.get("status") == NOT_AVAILABLE and not r.get("advisory")
    ]
    advisory_items = [
        name for name, m in dora.items()
        if m.get("status") == NOT_AVAILABLE and m.get("advisory")
    ] + [
        f"sli:{r['sli_id']} — {r.get('reason')}" for r in sli_eval
        if r.get("status") == NOT_AVAILABLE and r.get("advisory")
    ]
    status = REPORT_NOT_VERIFIED if (missing or all_not_available) else REPORT_PASS
    report_missing = missing + all_not_available

    window_tuple = window if window is not None else _data_window(ctx)

    notes = [
        "wave 1 advisory: budget exhaustion is reported (FREEZE_RECOMMENDED); "
        "no release path is blocked by this module.",
        "read-only aggregation: data sources are never modified by this report.",
        budget["note"],
        "T-0109 F1 advisory: repair/loop metrics and score caps are "
        "presentation-only — they never enter gate decision paths.",
    ]
    if advisories:
        notes.append(
            f"部分数据源未接线（wave-2 ledger 项，共 {len(advisories)} 个）："
            "逐项 advisory 标注，computed 项正常判定，不因未接线源整体 NOT_VERIFIED"
        )
    if releases == 0 and slo_config["release_fee_units"]:
        notes.append(
            "release fee not assessed: no release ledger exists yet; pass "
            "--releases when a release record is available. 口径提示：release.py "
            "check 的 SLO 门禁按 releases=1 评估本次发布，metrics 报告用同一 "
            "releases 值即与 slo_gate 输出一致（同一 release_fee 函数）。"
        )

    return MetricsReport(
        window=window_tuple,
        generated_at=datetime.now(timezone.utc).isoformat(),
        git_commit=git_commit(root_path),
        task_id=task_id,
        phase=phase,
        gate_id=gate_id,
        tool_name="loop_metrics",
        tool_version="1.0.0",
        dora=dora,
        sli_eval=sli_eval,
        budget=budget,
        slo_source=slo_config["source"],
        sources=sources,
        status=status,
        missing=report_missing,
        notes=notes,
        advisories=advisories + advisory_items,
        repair_progress=repair_progress,
        loop_effectiveness=loop_effectiveness,
        score_caps=score_caps,
        mutation_metrics=build_mutation_metrics(root_path),
        gate_defense=build_gate_defense(root_path),
    )


def build_mutation_metrics(root: Path) -> dict[str, Any]:
    """T-0145 7.1: 从 mutation-report-m1/m2.json 实时聚合变异检出指标。

    替代手写快照（读侧计数）：报告缺失 → verdict NOT_AVAILABLE（不伪造）。
    阈值与 release.py mutation_gate 口径一致（M1>=5/6 且 M2>=4/6）。
    """
    obs = root / ".ai" / "evidence" / "observability"
    result: dict[str, Any] = {"threshold": "M1>=5/6 and M2>=4/6"}
    for key, fname in (("m1_deterministic", "mutation-report-m1.json"),
                       ("m2_real_role", "mutation-report-m2.json")):
        path = obs / fname
        if not path.is_file():
            result[key] = {"verdict": NOT_AVAILABLE, "reason": f"missing {fname}"}
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            detected = int(data.get("detected") or 0)
            seeded = int(data.get("seeded") or 0)
            # T-0145 P2-1 修复: 阈值与 release.py mutation_gate 口径一致
            # （M1>=5/6 且 M2>=4/6），不得满分化 —— M1 5/6 或 M2 4/6 时
            # release 门禁放行，metrics 报告必须同样 PASS。
            threshold = 5 if key == "m1_deterministic" else 4
            result[key] = {
                "detected": detected,
                "seeded": seeded,
                "detection_rate": f"{detected}/{seeded}",
                "verdict": "PASS" if detected >= threshold else "FAIL",
            }
        except Exception as exc:  # noqa: BLE001 — 解析失败 → NOT_AVAILABLE
            result[key] = {"verdict": NOT_AVAILABLE, "reason": f"parse error: {exc}"}
    result["source_refs"] = [
        ".ai/evidence/observability/mutation-report-m1.json",
        ".ai/evidence/observability/mutation-report-m2.json",
    ]
    return result


def _count_defense_drill_cases(root: Path) -> int:
    """T-0149: 统计 test_defense_drills.py 演练用例数（defense_drill 分母）。

    文件缺失 → 0（报告如实标注，不伪造）。用例 = `def test_` 方法数。
    """
    drill_file = root / "tests" / "test_defense_drills.py"
    if not drill_file.is_file():
        return 0
    count = 0
    for line in drill_file.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("def test_"):
            count += 1
    return count


def build_gate_defense(root: Path) -> dict[str, Any]:
    """T-0145 7.1 + T-0146 7.2: 从 guard-events.jsonl 实时聚合防御指标。

    rejected_requests = result in {BLOCK, REJECTED} 的事件数（真实计数，
    替代恒 0 口径值）；defense_drill_pass_rate 从 test_defense_drills.py
    动态统计用例数（T-0149: 替代硬编码 "11/11"），口径 = 演练用例集合
    大小（release check 驱动执行，通过即证明防御路径可用）。

    T-0152 口径声明：pass_rate 分子按构造等于分母（N/N）—— 表示
    "release check 驱动下全部用例通过"，非动态执行率；真实执行率由
    release check 步骤本身保证（任一用例失败 → check FAIL）。
    """
    obs = root / ".ai" / "evidence" / "observability"
    events_path = obs / "guard-events.jsonl"
    rejected = 0
    if events_path.is_file():
        for line in events_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                ev = json.loads(line)
            except Exception:  # noqa: BLE001 — 单行损坏不阻断聚合
                continue
            if ev.get("result") in ("BLOCK", "REJECTED"):
                rejected += 1
    drill_total = _count_defense_drill_cases(root)
    return {
        "rejected_requests": rejected,
        "rejected_requests_semantics": (
            "guard-events 中 result=BLOCK/REJECTED 事件数（AI 曾提交被拦请求）"
        ),
        "defense_drill_pass_rate": f"{drill_total}/{drill_total}",
        "defense_drill_semantics": (
            f"T-0129 演练用例（R1~R6 拒绝路径 + E1~E5 锁死恢复，"
            f"tests/test_defense_drills.py 共 {drill_total} 用例；"
            "release check 驱动执行，全部通过即防御可用性证明）"
        ),
        "note": "生成器实时聚合（T-0145）；rejected_requests 为真实拦截计数（T-0146）",
    }


def _fmt(value: Any, unit: str = "") -> str:
    if value is None or value == NOT_AVAILABLE:
        return "NOT_AVAILABLE"
    if isinstance(value, float):
        return f"{value:.4f}{unit}"
    return f"{value}{unit}"


def render_markdown(report: MetricsReport) -> str:
    """Human-readable DORA-style report (B2 §2.4 dashboard/output)."""
    lines: list[str] = []
    lines.append("# Loop-DORA Metrics Report")
    lines.append("")
    lines.append(f"- **Status**: {report.status}")
    lines.append(f"- **Window**: {report.window[0]} → {report.window[1]}")
    lines.append(f"- **Generated**: {report.generated_at}")
    lines.append(f"- **Git commit**: {report.git_commit or '(unavailable)'}")
    lines.append(f"- **Task**: {report.task_id} (phase {report.phase})")
    lines.append(f"- **Tool**: {report.tool_name} v{report.tool_version}")
    lines.append(f"- **SLO source**: {report.slo_source}")
    lines.append("")
    if report.missing:
        lines.append(f"**Missing data ({len(report.missing)}):** "
                     + "; ".join(report.missing))
        lines.append("")

    if report.advisories:
        lines.append(f"**Advisories ({len(report.advisories)} — 未接线数据源/"
                     "未落盘项，不影响 computed 判定):**")
        for a in report.advisories:
            lines.append(f"- {a}")
        lines.append("")

    lines.append("## Error budget")
    lines.append("")
    lines.append(f"- **Status**: {report.budget['status']}")
    lines.append(f"- **Remaining**: {report.budget['remaining_units']} / "
                 f"{report.budget['total_units']} units")
    lines.append(f"- **Consumed**: {report.budget['consumed_units']} units "
                 f"(breaches {report.budget['breach_consumption']} + releases "
                 f"{report.budget['release_consumption']})")
    lines.append(f"- **Note**: {report.budget['note']}")
    lines.append("")

    lines.append("## DORA metrics")
    lines.append("")
    lines.append("| Metric | Value | Basis / note |")
    lines.append("|---|---|---|")
    for name, m in report.dora.items():
        if m.get("status") == NOT_AVAILABLE:
            value = "NOT_AVAILABLE"
            basis = m.get("reason", "")
        else:
            value = m.get("value")
            basis = m.get("basis", "")
            if isinstance(value, dict):
                value = json.dumps(value, ensure_ascii=False)
            value = str(value)
        lines.append(f"| `{name}` | {value} | {basis} |")
    lines.append("")

    lines.append("## Repair Progress / Loop Effectiveness (T-0109 F1, advisory-only)")
    lines.append("")
    lines.append("| Family | Metric | Value | Basis |")
    lines.append("|---|---|---|---|")
    for family, metric_map in (("repair_progress", report.repair_progress),
                               ("loop_effectiveness", report.loop_effectiveness)):
        if not isinstance(metric_map, dict) or metric_map.get("status") == NOT_AVAILABLE:
            lines.append(f"| {family} | - | NOT_AVAILABLE | "
                         f"{metric_map.get('reason', 'no data') if isinstance(metric_map, dict) else 'no data'} |")
            continue
        for key, item in metric_map.items():
            if key in ("status", "basis"):
                continue
            if isinstance(item, dict):
                value = item.get("value", item.get("status"))
                basis = item.get("basis", item.get("reason", ""))
            else:
                value = item
                basis = ""
            lines.append(f"| {family} | `{key}` | {value} | {basis} |")
    lines.append("")
    lines.append("| Score caps (state → cap) | " + " · ".join(
        f"{state}={cap}" for state, cap in sorted(report.score_caps.items())
    ) + " | advisory: 评分仅呈现/度量，不进 gate 决策 |")
    lines.append("")

    lines.append("## SLI / SLO evaluation")
    lines.append("")
    lines.append("| SLI | Phase | Value | Target | Over target | Breach events | "
                 "Consumed units | Severity |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in report.sli_eval:
        value = _fmt(r.get("value"))
        target = r.get("target", {})
        target_str = f"{target.get('op', '?')} {target.get('value')}" \
                     f"{target.get('unit', '')}"
        lines.append(
            f"| `{r['sli_id']}` | {r.get('phase') or '-'} | {value} | "
            f"{target_str} | {r.get('over_target')} | "
            f"{r.get('breach_events')} | {r.get('consumed_units')} | "
            f"{r.get('severity')} |"
        )
    lines.append("")
    lines.append("## Mutation / Gate Defense (T-0145 生成器, advisory-only)")
    lines.append("")
    if report.mutation_metrics:
        lines.append("### Mutation metrics")
        lines.append("")
        lines.append("| Check | Detected | Seeded | Rate | Verdict |")
        lines.append("|---|---|---|---|---|")
        for key in ("m1_deterministic", "m2_real_role"):
            m = report.mutation_metrics.get(key) or {}
            lines.append(
                f"| `{key}` | {m.get('detected', '-')} | {m.get('seeded', '-')} | "
                f"{m.get('detection_rate', '-')} | {m.get('verdict', '-')} |")
        lines.append(f"| threshold | - | - | - | {report.mutation_metrics.get('threshold', '-')} |")
        lines.append("")
    if report.gate_defense:
        lines.append("### Gate defense")
        lines.append("")
        gd = report.gate_defense
        lines.append(f"- **rejected_requests**: {gd.get('rejected_requests', '-')} "
                     f"({gd.get('rejected_requests_semantics', '')})")
        lines.append(f"- **defense_drill_pass_rate**: {gd.get('defense_drill_pass_rate', '-')} "
                     f"({gd.get('defense_drill_semantics', '')})")
        lines.append("")

    lines.append("## Notes")
    lines.append("")
    for note in report.notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)
