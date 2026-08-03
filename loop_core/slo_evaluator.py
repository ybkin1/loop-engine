"""
Governance metrics — SLI/SLO 评估与 error-budget 记账（T-0110 批 B-1 拆分产物）。

从 loop_core/governance_metrics.py 外提（design-common-weakness.md 1.2 边界：
"SLI/SLO 评估（load_slo_config/evaluate_sli/compute_error_budget/_metric/
_not_available）:663-1008" + 同族的哨兵常量 / 默认 SLO 表 / 接线状态表 /
release_fee_consumption —— SLO 域常量唯一归属）。

语义必须保持（拆分硬门槛）：
- ``load_slo_config`` 的 fail-closed 校验（T-0095：无效配置抛
  DataSourceUnavailableError，绝不部分应用/静默降级）；
- ``DataSourceUnavailableError`` 语义（slo_gate.py 依赖）；
- ``release_fee_consumption`` 单一共享实现（T-0100 F-05：metrics 记账与
  SLO 门禁同口径）；
- NOT_AVAILABLE 哨兵绝不与真实零混淆（B2 §2.5）。

依赖：governance_aggregations（叶子）→ governance_loaders（叶子）→
本模块。public 面由 governance_metrics 壳 re-export 保持。
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

from loop_core.governance_aggregations import (
    _DECIDED_STATUSES,
    SliContext,
    _over_target,
    _parse_dt,
    approval_latencies,
    approval_latency_stats,
    guard_anomaly_rates,
)
from loop_core.governance_loaders import DataSourceUnavailableError
from loop_core.schemas.evidence_state import (  # T-0109 F1 (advisory)
    DEFAULT_SCORE_CAPS,
    score_cap_for_state,
)

# ── Availability sentinel ────────────────────────────────────────────────
# A metric value that cannot be computed from the available data sources.
# Never conflated with a real zero (B2 §2.5 — missing data is NOT_VERIFIED,
# never a silent zero).
NOT_AVAILABLE = "NOT_AVAILABLE"

# ── Report / budget statuses ─────────────────────────────────────────────
BUDGET_HEALTHY = "HEALTHY"                      # nothing consumed
BUDGET_CONSUMING = "CONSUMING"                  # consumption > 0, budget remains
BUDGET_FREEZE_RECOMMENDED = "FREEZE_RECOMMENDED"  # remaining units <= 0 (advisory only)
REPORT_PASS = "PASS"
REPORT_NOT_VERIFIED = "NOT_VERIFIED"

# ── SLO severity classes (B2 §1.3) ───────────────────────────────────────
SEVERITY_BUDGET = "error-budget-slo"   # breaches consume error budget
SEVERITY_HARD_GATE = "hard-gate"       # not budget-consuming
SEVERITY_INFO = "informational"        # not budget-consuming


# ── SLO configuration ────────────────────────────────────────────────────
# Default targets from B2 §1.2 (proposal).  An .ai/slo.yaml (B2 §1.3) may
# override any of them; when absent the defaults apply and the report says so.

DEFAULT_SLOS: tuple[dict[str, Any], ...] = (
    {"sli_id": "req_gate_rejection_rate", "phase": "S1-requirements",
     "description": "S1 gate rejections / (approvals + rejections)",
     "target": {"op": "<=", "value": 0.35}, "severity": SEVERITY_BUDGET,
     "budget_share": 1.0, "source": ".ai/gates.yaml (S1 gates, phase-classified)"},
    {"sli_id": "design_review_rejection_rate", "phase": "S2-architecture",
     "description": "design review rejections / decisions",
     "target": {"op": "<=", "value": 0.30}, "severity": SEVERITY_BUDGET,
     "budget_share": 1.0, "source": ".ai/gates.yaml (S2 gates, phase-classified)"},
    {"sli_id": "quality_gate_rejection_rate", "phase": "S5-quality",
     "description": "S5 rejections / decisions",
     "target": {"op": "<=", "value": 0.30}, "severity": SEVERITY_BUDGET,
     "budget_share": 1.0, "source": ".ai/gates.yaml (S5 gates, phase-classified)"},
    {"sli_id": "delivery_gate_rejection_rate", "phase": "S6-delivery",
     "description": "S6 rejections (incl. NOGO) / decisions",
     "target": {"op": "<=", "value": 0.20}, "severity": SEVERITY_BUDGET,
     "budget_share": 1.0, "source": ".ai/gates.yaml (S6 gates, phase-classified)"},
    {"sli_id": "rework_cycle_rate", "phase": "S4-implementation",
     "description": "rework cycles (rejected gates or S4<->S5 bounces) / completed tasks",
     "target": {"op": "<=", "value": 0.25}, "severity": SEVERITY_BUDGET,
     "budget_share": 1.0,
     "source": ".ai/gates.yaml rejected gates (or .ai/ledger/phase_transitions.jsonl)"},
    {"sli_id": "guard_block_rate", "phase": "S4-implementation",
     "description": "guard blocks / (blocks + passes) across hooks (false-positive proxy)",
     "target": {"op": "<=", "value": 0.05}, "severity": SEVERITY_BUDGET,
     "budget_share": 1.0,
     "source": ".ai/ledger/guard_decisions.jsonl (hook decision log — not yet wired)"},
    {"sli_id": "guard_anomaly_rate", "phase": "S4-implementation",
     "description": "guard check anomalies (FAIL events) / total guard-check events — "
                    "wave-1 computable proxy for guard_block_rate (U8 guard-events.jsonl)",
     "target": {"op": "<=", "value": 0.05}, "severity": SEVERITY_BUDGET,
     "budget_share": 1.0,
     "source": ".ai/evidence/observability/guard-events.jsonl"},
    {"sli_id": "approval_latency_p95", "phase": "S6-delivery",
     "description": "p95 of gate requested_at -> recorded_at (hours)",
     "target": {"op": "<=", "value": 24.0, "unit": "h"}, "severity": SEVERITY_BUDGET,
     "budget_share": 1.0, "source": ".ai/gates.yaml requested_at/recorded_at"},
    {"sli_id": "gate_decision_coverage", "phase": "All",
     "description": "gates decided with evidence dossier / decided",
     "target": {"op": ">=", "value": 1.0}, "severity": SEVERITY_HARD_GATE,
     "budget_share": 0.0, "source": ".ai/gates.yaml evidence fields"},
    {"sli_id": "drift_event_rate", "phase": "S11-maintenance",
     "description": "governance drift events per window",
     "target": {"op": "<=", "value": 2}, "severity": SEVERITY_INFO,
     "budget_share": 0.0,
     "source": ".ai/ledger/runtime-events.jsonl (drift source — not yet wired)"},
    {"sli_id": "delta_quality_pass_rate", "phase": "S4-implementation",
     "description": "tasks passing delta gates (no new regressions on the diff)",
     "target": {"op": ">=", "value": 1.0}, "severity": SEVERITY_HARD_GATE,
     "budget_share": 0.0, "source": "delta gate results (not yet recorded)"},
    {"sli_id": "evidence_regeneration_rate", "phase": "S5-quality",
     "description": "evidence regeneration events / tasks",
     "target": {"op": "<=", "value": 0.10}, "severity": SEVERITY_BUDGET,
     "budget_share": 1.0, "source": "evidence re-run tracking (not yet recorded)"},
    {"sli_id": "defect_fail_verdict_rate", "phase": "S5-quality",
     "description": "tasks with FAIL verdicts (warning class)",
     "target": {"op": "<=", "value": 0.20}, "severity": SEVERITY_BUDGET,
     "budget_share": 1.0, "source": "FAIL verdict store (not yet recorded)"},
    {"sli_id": "ac_invest_rate", "phase": "S1-requirements",
     "description": "acceptance criteria meeting INVEST/verifiable shape",
     "target": {"op": ">=", "value": 1.0}, "severity": SEVERITY_HARD_GATE,
     "budget_share": 0.0, "source": "DoD gate acceptance-criteria check (T-0089 scope)"},
)

DEFAULT_BUDGET_TOTAL_UNITS = 100.0
DEFAULT_RELEASE_FEE_UNITS = 5.0

# ── Data-source wiring status (T-0100 F-05) ──────────────────────────────
# REPORT_SOURCE_FILES 中的三项是文档化 wave-2 接线项（B2 §2.2）：
# 缺失/未接线 → 逐项 advisory 标注（不因它们整体 NOT_VERIFIED）；
# 其余源（gates/task_graph/guard-events/executions）为已接线源 ——
# 缺失即 NOT_AVAILABLE 且报告 NOT_VERIFIED（fail-closed，语义不变）。
WAVE2_UNWIRED_SOURCES: frozenset[str] = frozenset({
    "phase_transitions.jsonl",
    "guard_decisions.jsonl",
    "runtime-events.jsonl",
})

# 依赖未接线源或尚未落盘的 SLI：其 NOT_AVAILABLE 属于 advisory 类别
# （evaluate_sli 逐分支标注 advisory=True），不驱动整体 NOT_VERIFIED。
UNWIRED_SLI_IDS: frozenset[str] = frozenset({
    "guard_block_rate",       # guard_decisions.jsonl（wave-2）
    "drift_event_rate",       # runtime-events.jsonl（wave-2）
    "delta_quality_pass_rate",      # 尚未记录
    "evidence_regeneration_rate",   # 尚未记录
    "defect_fail_verdict_rate",     # 尚未记录
    "ac_invest_rate",               # 尚未记录
})


def release_fee_consumption(release_fee_units: float, releases: int) -> float:
    """Release-fee consumption: ``releases * release_fee_units``.

    单一共享实现（T-0100 F-05）：metrics 记账（compute_error_budget）与 SLO
    门禁（loop_core.slo_gate 经 compute_error_budget 引用）使用同一函数，
    保证口径一致 —— 相同输入必然得到相同 release_consumption。
    """
    if not releases:
        return 0.0
    return round(releases * release_fee_units, 3)


def load_slo_config(root: str | Path, slo_path: str | Path | None = None) -> dict[str, Any]:
    """Merge .ai/slo.yaml (B2 §1.3) over the B2 §1.2 defaults.

    - Absent slo.yaml -> defaults apply; ``source`` says so.
    - Present but unparseable -> DataSourceUnavailableError (an explicit config
      that cannot be read must not silently fall back to defaults).
    - Per-SLI overrides are matched by sli_id; unknown sli_ids are appended.
    - T-0095 fail-closed validation: an explicit slo.yaml that is semantically
      invalid (non-numeric budget units, malformed target/severity/budget_share,
      half-set or unparseable window bounds) raises DataSourceUnavailableError
      with the field named — the config is never partially applied and never
      silently downgraded to defaults.
    """
    path = Path(slo_path) if slo_path is not None else Path(root) / ".ai" / "slo.yaml"

    def _invalid(message: str) -> DataSourceUnavailableError:
        return DataSourceUnavailableError(f"slo config invalid ({message}): {path}")

    slos: list[dict[str, Any]] = [dict(d) for d in DEFAULT_SLOS]
    by_id = {s["sli_id"]: s for s in slos}
    if not path.exists():
        return {
            "source": "defaults (B2 §1.2 table); .ai/slo.yaml absent",
            "slo_path": str(path),
            "slos": slos,
            "budget_total_units": DEFAULT_BUDGET_TOTAL_UNITS,
            "release_fee_units": DEFAULT_RELEASE_FEE_UNITS,
            "window": None,
            "score_caps": dict(DEFAULT_SCORE_CAPS),  # T-0109 F1 (advisory)
        }
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise DataSourceUnavailableError(f"slo config unparseable: {path}: {exc}") from exc
    if not isinstance(doc, dict):
        raise DataSourceUnavailableError(f"slo config not a mapping: {path}")

    # ── T-0095: budget units validation (fail-closed) ────────────────────
    for key, minimum, exclusive in (
        ("budget_total_units", 0.0, True),
        ("release_fee_units", 0.0, False),
    ):
        if key in doc:
            raw = doc[key]
            try:
                value = float(raw)
            except (TypeError, ValueError):
                raise _invalid(f"'{key}' must be numeric, got {raw!r}") from None
            if not math.isfinite(value) or value < minimum or (exclusive and value == minimum):
                comparator = f"> {minimum:g}" if exclusive else f">= {minimum:g}"
                raise _invalid(f"'{key}' must be a finite number {comparator}, got {raw!r}")

    # ── T-0095: window bounds validation (fail-closed) ───────────────────
    # A window is honored only when both bounds are set; a half-set or
    # unparseable window would previously be *silently ignored* (treated as
    # "no window") — that ambiguity now fails closed with the field named.
    window_start = doc.get("window_start")
    window_end = doc.get("window_end")
    if (window_start or window_end) and not (window_start and window_end):
        raise _invalid(
            "'window_start' and 'window_end' must be set together "
            f"(got start={window_start!r}, end={window_end!r})"
        )
    for key in ("window_start", "window_end"):
        value = doc.get(key)
        if value and _parse_dt(value) is None:
            raise _invalid(f"'{key}' is not an ISO-8601 timestamp: {value!r}")

    raw_slos = doc.get("slos", [])
    if not isinstance(raw_slos, list):
        raise DataSourceUnavailableError(f"slo config 'slos' not a list: {path}")
    for raw in raw_slos:
        if not isinstance(raw, dict) or "sli_id" not in raw:
            raise DataSourceUnavailableError(f"slo config entry lacks sli_id: {path}")
        sli_id = str(raw["sli_id"])

        # ── T-0095: per-SLI semantic validation (fail-closed) ────────────
        target = raw.get("target")
        if target is not None:
            if not isinstance(target, dict) or "op" not in target or "value" not in target:
                raise _invalid(
                    f"entry '{sli_id}' target must be a mapping with 'op' and 'value'"
                )
            if str(target.get("op")) not in ("<=", ">=", "=="):
                raise _invalid(
                    f"entry '{sli_id}' target op must be <= | >= | ==, "
                    f"got {target.get('op')!r}"
                )
            try:
                target_value = float(target["value"])
            except (TypeError, ValueError):
                raise _invalid(
                    f"entry '{sli_id}' target value must be numeric, "
                    f"got {target.get('value')!r}"
                ) from None
            if not math.isfinite(target_value):
                raise _invalid(
                    f"entry '{sli_id}' target value must be finite, "
                    f"got {target.get('value')!r}"
                )
        severity = raw.get("severity")
        if severity is not None and severity not in (
            SEVERITY_BUDGET, SEVERITY_HARD_GATE, SEVERITY_INFO,
        ):
            raise _invalid(f"entry '{sli_id}' has unknown severity: {severity!r}")
        share = raw.get("budget_share")
        if share is not None:
            try:
                share_value = float(share)
            except (TypeError, ValueError):
                raise _invalid(
                    f"entry '{sli_id}' budget_share must be numeric, got {share!r}"
                ) from None
            if not math.isfinite(share_value) or share_value < 0:
                raise _invalid(
                    f"entry '{sli_id}' budget_share must be finite and >= 0, "
                    f"got {share!r}"
                )

        entry = by_id.get(sli_id)
        if entry is None:
            entry = {
                "sli_id": sli_id, "phase": raw.get("phase"),
                "description": raw.get("description", ""),
                "target": {"op": "<=", "value": 0.0},
                "severity": SEVERITY_BUDGET, "budget_share": 1.0,
                "source": str(path),
            }
            by_id[sli_id] = entry
            slos.append(entry)
        for key in ("target", "severity", "budget_share", "phase", "description"):
            if key in raw:
                entry[key] = raw[key]
    # ── T-0109 F1: score_caps 评分上限表（advisory-only）──────────────────
    # 显式化评分上限（对齐 slo.yaml 配置外置模式）。校验 fail-closed：
    # 非 mapping / 状态名非法 / 上限非有限正数 → DataSourceUnavailableError，
    # 绝不部分应用。缺失 → 默认表（DEFAULT_SCORE_CAPS）。
    score_caps = dict(DEFAULT_SCORE_CAPS)
    raw_caps = doc.get("score_caps")
    if raw_caps is not None:
        if not isinstance(raw_caps, dict):
            raise _invalid("'score_caps' must be a mapping of state -> cap")
        for state, cap in raw_caps.items():
            try:
                cap_value = float(cap)
            except (TypeError, ValueError):
                raise _invalid(
                    f"'score_caps.{state}' must be numeric, got {cap!r}"
                ) from None
            if not math.isfinite(cap_value) or cap_value < 0:
                raise _invalid(
                    f"'score_caps.{state}' must be a finite number >= 0, got {cap!r}"
                )
            try:
                score_cap_for_state(str(state), score_caps)
            except ValueError as exc:
                raise _invalid(f"'score_caps' 非法状态名: {state!r}") from exc
            score_caps[str(state)] = int(round(cap_value))

    return {
        "source": str(path),
        "slo_path": str(path),
        "slos": slos,
        "budget_total_units": float(doc.get("budget_total_units", DEFAULT_BUDGET_TOTAL_UNITS)),
        "release_fee_units": float(doc.get("release_fee_units", DEFAULT_RELEASE_FEE_UNITS)),
        "window": (doc.get("window_start"), doc.get("window_end")),
        "score_caps": score_caps,  # T-0109 F1 (advisory)
    }


# ── SLI evaluation ───────────────────────────────────────────────────────


def evaluate_sli(sli: dict[str, Any], ctx: SliContext) -> dict[str, Any]:
    """Evaluate one SLO spec against the data context.

    Returns a record with status computed|NOT_AVAILABLE, value, over_target,
    breach_events and consumed_units (breach_events * budget_share for
    error-budget SLOs; B2 §1.4 v1 rule — one breach event = 1 unit)."""
    sli_id = sli["sli_id"]
    severity = sli.get("severity", SEVERITY_BUDGET)
    budget_share = float(sli.get("budget_share", 1.0))
    target = dict(sli.get("target", {"op": "<=", "value": 0.0}))
    value: float | None = None
    breach_events: int | None = None
    reason: str | None = None
    # T-0100 F-05: advisory=True 表示 NOT_AVAILABLE 源于文档化未接线数据源
    # （wave-2）或尚未落盘的 SLI —— 逐项标注，不驱动整体 NOT_VERIFIED。
    # guard_block_rate / drift_event_rate 的 advisory 仅在"源缺失（未接线）"
    # 分支成立；若源已存在但无数据，则属真实数据情形（非 advisory）。
    advisory = sli_id in UNWIRED_SLI_IDS - {"guard_block_rate", "drift_event_rate"}

    if sli_id in ("req_gate_rejection_rate", "design_review_rejection_rate",
                  "quality_gate_rejection_rate", "delivery_gate_rejection_rate"):
        phase = sli.get("phase")
        if ctx.gates is None:
            reason = "gates register unavailable"
        else:
            decided = [g for g in ctx.gates
                       if g.status in _DECIDED_STATUSES and g.phase == phase]
            if not decided:
                reason = f"no decided gates for phase {phase}"
            else:
                rejected = sum(1 for g in decided if g.status == "rejected")
                value = rejected / len(decided)
                breach_events = rejected
    elif sli_id == "rework_cycle_rate":
        if ctx.gates is None:
            reason = "gates register unavailable"
        elif ctx.completed_tasks == 0:
            reason = "no completed tasks in task graph"
        else:
            value = ctx.rework_total / ctx.completed_tasks
            breach_events = ctx.rework_total
    elif sli_id == "guard_block_rate":
        if ctx.guard_decisions is None:
            reason = ("guard_decisions.jsonl absent (hook decision log not yet "
                      "wired — B2 §2.2 wave 1)")
            advisory = True  # 未接线源缺失 → advisory
        else:
            decided = [d for d in ctx.guard_decisions
                       if d.get("decision") in ("block", "pass")]
            if not decided:
                reason = "no block/pass decisions in guard_decisions.jsonl"
            else:
                blocks = sum(1 for d in decided if d.get("decision") == "block")
                value = blocks / len(decided)
                breach_events = blocks
    elif sli_id == "guard_anomaly_rate":
        if ctx.guard_events is None:
            reason = "guard-events.jsonl unavailable"
        elif not ctx.guard_events:
            reason = "guard-events.jsonl contains no events"
        else:
            rates = guard_anomaly_rates(ctx.guard_events)
            if rates["anomaly_rate"] is None:
                reason = "no guard events recorded"
            else:
                value = rates["anomaly_rate"]
                breach_events = int(rates["by_result"].get("FAIL", 0))
    elif sli_id == "approval_latency_p95":
        if ctx.gates is None:
            reason = "gates register unavailable"
        else:
            stats = approval_latency_stats(ctx.gates)
            if stats is None:
                reason = "no gate with both requested_at and recorded_at"
            else:
                value = stats["p95_hours"]
                breach_events = sum(
                    1 for s in approval_latencies(ctx.gates) if s > 24.0 * 3600.0
                )
    elif sli_id == "gate_decision_coverage":
        if ctx.gates is None:
            reason = "gates register unavailable"
        else:
            decided = [g for g in ctx.gates if g.status in _DECIDED_STATUSES]
            if not decided:
                reason = "no decided gates"
            else:
                with_evidence = sum(1 for g in decided if g.evidence)
                value = with_evidence / len(decided)
                breach_events = len(decided) - with_evidence
    elif sli_id == "drift_event_rate":
        if ctx.drift_events is None:
            reason = "runtime-events.jsonl absent (drift source not yet wired)"
            advisory = True  # 未接线源缺失 → advisory
        else:
            value = float(len(ctx.drift_events))
            breach_events = len(ctx.drift_events)
    elif sli_id == "delta_quality_pass_rate":
        reason = "delta gate results not yet recorded"
    elif sli_id == "evidence_regeneration_rate":
        reason = "evidence re-run tracking not yet recorded"
    elif sli_id == "defect_fail_verdict_rate":
        reason = "FAIL verdict store not yet recorded"
    elif sli_id == "ac_invest_rate":
        reason = "DoD gate acceptance-criteria check not yet recorded"
    else:
        reason = f"unknown SLI id: {sli_id}"

    if value is None:
        status = NOT_AVAILABLE
        over_target: bool | None = None
    else:
        status = "computed"
        over_target = _over_target(target, value)

    consumed = 0.0
    if severity == SEVERITY_BUDGET and breach_events is not None:
        consumed = round(breach_events * budget_share, 3)

    return {
        "sli_id": sli_id,
        "phase": sli.get("phase"),
        "description": sli.get("description", ""),
        "severity": severity,
        "budget_share": budget_share,
        "target": target,
        "status": status,
        "value": value if status == "computed" else NOT_AVAILABLE,
        "reason": reason,
        "over_target": over_target,
        "breach_events": breach_events,
        "consumed_units": consumed,
        "source": sli.get("source", ""),
        "advisory": advisory,
    }


def compute_error_budget(sli_results: Sequence[dict[str, Any]],
                         total_units: float = DEFAULT_BUDGET_TOTAL_UNITS,
                         release_fee_units: float = DEFAULT_RELEASE_FEE_UNITS,
                         releases: int = 0) -> dict[str, Any]:
    """Error budget accounting (B2 §1.4).

    consumed = sum(breach_events * budget_share) over budget-consuming SLOs,
    plus ``releases * release_fee_units`` when a release count is supplied
    (release fee via the shared ``release_fee_consumption`` — identical for
    metrics accounting and the SLO gate, T-0100 F-05).
    Status: HEALTHY (nothing consumed) / CONSUMING (within budget) /
    FREEZE_RECOMMENDED (remaining <= 0 — advisory only in wave 1; release
    blocking is a wave-2 wiring item and is NOT applied here)."""
    consumed = round(sum(float(r.get("consumed_units", 0.0)) for r in sli_results), 3)
    release_units = release_fee_consumption(release_fee_units, releases)
    total_consumed = round(consumed + release_units, 3)
    remaining = round(total_units - total_consumed, 3)
    if remaining <= 0:
        status = BUDGET_FREEZE_RECOMMENDED
    elif total_consumed > 0:
        status = BUDGET_CONSUMING
    else:
        status = BUDGET_HEALTHY
    return {
        "total_units": total_units,
        "consumed_units": total_consumed,
        "breach_consumption": consumed,
        "release_fee_units": release_fee_units,
        "release_count": releases,
        "release_consumption": release_units,
        "remaining_units": remaining,
        "status": status,
        "note": ("advisory only (wave 1): budget exhaustion is reported, "
                 "no release path is blocked by this module"),
    }


# ── DORA metric builders (shared helpers) ────────────────────────────────


def _metric(value: Any, status: str = "computed", **extra: Any) -> dict[str, Any]:
    return {"status": status, "value": value, **extra}


def _not_available(reason: str, advisory: bool = False) -> dict[str, Any]:
    """NOT_AVAILABLE 指标。advisory=True：源于文档化未接线源（wave-2）——
    逐项标注，不驱动整体 NOT_VERIFIED（T-0100 F-05）。"""
    return {
        "status": NOT_AVAILABLE, "value": NOT_AVAILABLE,
        "reason": reason, "advisory": advisory,
    }
