"""T-0110 批 B-1 golden 语料共享助手（governance_metrics / intent_router 拆分等价）。

本模块不被 pytest 直接收集（无 test_ 前缀），由两类消费者使用：
1. ``.ai/evidence/T-0110/golden/generate_golden.py`` —— 拆分前/后各跑一次，
   产出 golden-before.json / golden-after.json（逐字节 diff 证据）；
2. ``tests/test_t0110_batch_b1.py`` —— 运行时重放语料，与内嵌 golden 逐字段断言。

全部捕获为确定性 JSON：
- 输入语料固定（无随机、无时钟依赖）；build_report 的 generated_at / git_commit
  归一化为固定标记（<GENERATED_AT> / <GIT_COMMIT>）；
- 异常路径只记录 (type, message)，message 中的临时路径归一化为 <ROOT>；
- 枚举按 .value 序列化，datetime 按 isoformat，集合排序。
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

# ══════════════════════════════════════════════════════════════════════
# 归一化工具
# ══════════════════════════════════════════════════════════════════════


def to_jsonable(value: Any) -> Any:
    """深度转换为 JSON 可序列化结构（枚举→value、datetime→isoformat、集合→排序列表）。"""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, set):
        return sorted(to_jsonable(v) for v in value)
    if isinstance(value, (tuple, list)):
        return [to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, Path):
        return str(value)
    return value


def norm_paths(obj: Any, root: Path) -> Any:
    """把 obj 中出现的 root 路径（正/反斜杠两种写法）归一化为 <ROOT>。"""
    root_s = str(root)
    root_posix = root.as_posix()

    def _walk(v: Any) -> Any:
        if isinstance(v, str):
            return v.replace(root_s, "<ROOT>").replace(root_posix, "<ROOT>")
        if isinstance(v, dict):
            return {k: _walk(val) for k, val in v.items()}
        if isinstance(v, list):
            return [_walk(x) for x in v]
        return v

    return _walk(obj)


def dump_json(data: Any) -> str:
    """确定性 JSON 文本（sort_keys + ensure_ascii=False + 统一换行结尾）。"""
    return json.dumps(to_jsonable(data), sort_keys=True, ensure_ascii=False, indent=1) + "\n"


def try_exc(fn: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
    """执行 fn，成功返回 {ok: True, value}，异常返回 {ok: False, type, message}。"""
    try:
        return {"ok": True, "value": fn(*args, **kwargs)}
    except Exception as exc:  # noqa: BLE001 — golden 语料需要捕获所有异常路径
        return {"ok": False, "type": type(exc).__name__, "message": str(exc)}


# ══════════════════════════════════════════════════════════════════════
# governance_metrics 固定夹具（.ai 数据源树）
# ══════════════════════════════════════════════════════════════════════

GATES_YAML = [
    {"id": "G-T-0001-REQUIREMENTS", "task_id": "T-0001", "gate_type": "requirements",
     "status": "approved", "decision": "GO",
     "requested_at": "2026-01-05T09:00:00Z", "recorded_at": "2026-01-05T10:30:00Z",
     "evidence": ".ai/evidence/T-0001/gate-requirements.md"},
    {"id": "G-T-0001-REQUIREMENTS-R2", "task_id": "T-0001", "gate_type": "requirements",
     "status": "rejected", "decision": "NOGO",
     "requested_at": "2026-01-04T09:00:00Z", "recorded_at": "2026-01-04T11:00:00Z",
     "evidence": ""},
    {"id": "G-T-0002-ARCHITECTURE", "task_id": "T-0002", "gate_type": "design",
     "status": "approved", "decision": "GO",
     "requested_at": "2026-01-06T08:00:00Z", "recorded_at": "2026-01-06T12:00:00Z",
     "evidence": ".ai/evidence/T-0002/gate-design.md"},
    {"id": "G-T-0003-DESIGN", "task_id": "T-0003", "gate_type": "design",
     "status": "rejected", "decision": "NOGO",
     "requested_at": "2026-01-07T09:00:00Z", "recorded_at": "2026-01-07T10:00:00Z",
     "evidence": ".ai/evidence/T-0003/rev1.md"},
    {"id": "G-T-0003-IMPLEMENTATION", "task_id": "T-0003", "gate_type": "implementation",
     "status": "approved", "decision": "GO",
     "requested_at": "2026-01-08T09:00:00Z", "recorded_at": "2026-01-08T11:00:00Z",
     "evidence": ".ai/evidence/T-0003/impl.md"},
    {"id": "G-T-0004-QUALITY", "task_id": "T-0004", "gate_type": "quality",
     "status": "approved", "decision": "GO",
     "requested_at": "2026-01-09T09:00:00Z", "recorded_at": "2026-01-09T09:30:00Z",
     "evidence": ".ai/evidence/T-0004/quality.md"},
    {"id": "G-T-0005-DELIVERY", "task_id": "T-0005", "gate_type": "delivery",
     "status": "rejected", "decision": "NOGO",
     "requested_at": "2026-01-10T09:00:00Z", "recorded_at": "2026-01-10T10:00:00Z",
     "evidence": ".ai/evidence/T-0005/delivery-rev1.md"},
    {"id": "G-T-0006-UNMAPPED", "task_id": "T-0006", "gate_type": "custom",
     "status": "approved", "decision": "GO", "evidence": "x.md"},
    {"id": "G-T-0007-REQUIREMENT", "task_id": "T-0007", "gate_type": "requirements",
     "status": "in_progress", "decision": None,
     "requested_at": "2026-01-11T09:00:00Z"},
]

TASKS_YAML = [
    {"id": "T-0001", "status": "completed", "phase": "S6-delivery",
     "created_at": "2026-01-02T08:00:00Z", "updated_at": "2026-01-06T16:00:00Z"},
    {"id": "T-0002", "status": "active", "phase": "S4-implementation",
     "created_at": "2026-01-03T09:00:00Z", "updated_at": "2026-01-07T09:00:00Z"},
    {"id": "T-0003", "status": "in_progress", "phase": "S5-quality",
     "created_at": "2026-01-04T10:00:00Z", "updated_at": "2026-01-09T10:00:00Z"},
    {"id": "T-0004", "status": "completed", "phase": "S6-delivery",
     "created_at": "2026-01-05T08:00:00Z", "updated_at": "2026-01-10T08:00:00Z"},
    {"id": "T-0005", "status": "planned", "phase": "S0-init",
     "created_at": "2026-01-06T08:00:00Z"},
    {"id": "T-0006", "status": "completed", "phase": "S6-delivery",
     "created_at": "2026-01-07T08:00:00Z", "updated_at": "2026-01-08T08:00:00Z"},
]

GUARD_EVENTS_JSONL = [
    {"event_id": "ev-0001", "guard_id": "g1", "capability_id": "c1",
     "check_type": "health", "result": "PASS", "duration_ms": 12.5,
     "failure_reason": None, "timestamp": "2026-01-08T09:00:01Z", "source": "registry-a"},
    {"event_id": "ev-0002", "guard_id": "g1", "capability_id": "c1",
     "check_type": "health", "result": "FAIL", "duration_ms": 8.0,
     "failure_reason": "probe timeout", "timestamp": "2026-01-08T09:05:01Z", "source": "registry-a"},
    {"event_id": "ev-0003", "guard_id": "g2", "capability_id": "c2",
     "check_type": "drift", "result": "FAIL", "duration_ms": 3.0,
     "failure_reason": "source drift", "timestamp": "2026-01-08T09:10:01Z", "source": "registry-b"},
    {"event_id": "ev-0004", "guard_id": "g2", "capability_id": "c2",
     "check_type": "drift", "result": "PASS", "duration_ms": 2.5,
     "failure_reason": None, "timestamp": "2026-01-08T09:15:01Z", "source": "registry-b"},
    {"event_id": "ev-0005", "guard_id": "g2", "capability_id": "c2",
     "check_type": "drift", "result": "PASS", "duration_ms": 2.0,
     "failure_reason": None, "timestamp": "2026-01-08T09:20:01Z", "source": "registry-b"},
    {"event_id": "ev-0006", "guard_id": "g3", "capability_id": None,
     "check_type": "integrity", "result": "REPORT", "duration_ms": 20.0,
     "failure_reason": "manifest mismatch", "timestamp": "2026-01-08T09:25:01Z", "source": "registry-c"},
]

EXECUTIONS_JSONL = [
    {"status": "COMPLETED", "launched_at": "2026-01-08T09:00:00Z",
     "completed_at": "2026-01-08T09:12:30Z", "tool": "test"},
    {"status": "completed", "launched_at": "2026-01-09T09:00:00Z",
     "completed_at": "2026-01-09T09:30:00Z", "tool": "test"},
    {"status": "RUNNING", "launched_at": "2026-01-10T09:00:00Z", "tool": "test"},
]

PHASE_TRANSITIONS_JSONL = [
    {"task_id": "T-0003", "from_phase": "S2-architecture",
     "to_phase": "S4-implementation", "at": "2026-01-05T09:00:00Z"},
    {"task_id": "T-0003", "from_phase": "S4-implementation",
     "to_phase": "S5-quality", "at": "2026-01-06T09:00:00Z"},
    {"task_id": "T-0003", "from_phase": "S5-quality",
     "to_phase": "S4-implementation", "at": "2026-01-07T09:00:00Z"},
    {"task_id": "T-0003", "from_phase": "S4-implementation",
     "to_phase": "S5-quality", "at": "2026-01-08T09:00:00Z"},
]

GUARD_DECISIONS_JSONL = [
    {"decision": "block", "guard_id": "g1", "at": "2026-01-08T09:00:00Z"},
    {"decision": "pass", "guard_id": "g1", "at": "2026-01-08T09:05:00Z"},
    {"decision": "pass", "guard_id": "g2", "at": "2026-01-08T09:10:00Z"},
    {"decision": "report", "guard_id": "g3", "at": "2026-01-08T09:15:00Z"},
]

RUNTIME_EVENTS_JSONL = [
    {"event_type": "drift_source", "at": "2026-01-08T09:00:00Z", "detail": "a"},
    {"type": "drift_target", "at": "2026-01-08T10:00:00Z", "detail": "b"},
]

SLO_YAML = """\
budget_total_units: 80
release_fee_units: 4
window_start: "2026-01-01T00:00:00Z"
window_end: "2026-01-31T23:59:59Z"
slos:
- sli_id: req_gate_rejection_rate
  target: {op: ">=", value: 0.9}
- sli_id: custom_sli_xyz
  description: "custom sli from slo.yaml"
score_caps:
  "Outcome-supported": 95
"""


def write_metrics_fixture(root: Path, *, with_slo: bool = True) -> None:
    """构建完整 .ai 数据源树（含 slo.yaml 覆盖配置）。"""
    ai = root / ".ai"
    (ai / "evidence" / "observability").mkdir(parents=True, exist_ok=True)
    (ai / "ledger").mkdir(parents=True, exist_ok=True)

    (ai / "gates.yaml").write_text(
        "schema_version: 1\n" + "gates:\n"
        + "\n".join(f"- {json.dumps(g, ensure_ascii=False)}" for g in GATES_YAML),
        encoding="utf-8",
    )
    (ai / "task_graph.yaml").write_text(
        "schema_version: 1\n" + "tasks:\n"
        + "\n".join(f"- {json.dumps(t, ensure_ascii=False)}" for t in TASKS_YAML),
        encoding="utf-8",
    )
    (ai / "evidence" / "observability" / "guard-events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in GUARD_EVENTS_JSONL) + "\n",
        encoding="utf-8",
    )
    (ai / "ledger" / "executions.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in EXECUTIONS_JSONL) + "\n",
        encoding="utf-8",
    )
    (ai / "ledger" / "phase_transitions.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in PHASE_TRANSITIONS_JSONL) + "\n",
        encoding="utf-8",
    )
    (ai / "ledger" / "guard_decisions.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in GUARD_DECISIONS_JSONL) + "\n",
        encoding="utf-8",
    )
    (ai / "ledger" / "runtime-events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in RUNTIME_EVENTS_JSONL) + "\n",
        encoding="utf-8",
    )
    if with_slo:
        (ai / "slo.yaml").write_text(SLO_YAML, encoding="utf-8")


def empty_root(root: Path) -> Path:
    """空 .ai 根（仅建目录，不写任何数据源）。"""
    (root / ".ai").mkdir(parents=True, exist_ok=True)
    return root


def capture_governance_metrics_golden(root: Path) -> dict[str, Any]:
    """governance_metrics 全量 golden 捕获（输出确定性 JSON 结构）。"""
    from loop_core import governance_metrics as gm  # noqa: F401 — 统一入口壳
    from loop_core.observability import GuardCheckEvent

    write_metrics_fixture(root)
    out: dict[str, Any] = {}

    # ── 模块级常量（值级快照）─────────────────────────────────────────
    out["constants"] = {
        "NOT_AVAILABLE": gm.NOT_AVAILABLE,
        "BUDGET_HEALTHY": gm.BUDGET_HEALTHY,
        "BUDGET_CONSUMING": gm.BUDGET_CONSUMING,
        "BUDGET_FREEZE_RECOMMENDED": gm.BUDGET_FREEZE_RECOMMENDED,
        "REPORT_PASS": gm.REPORT_PASS,
        "REPORT_NOT_VERIFIED": gm.REPORT_NOT_VERIFIED,
        "SEVERITY_BUDGET": gm.SEVERITY_BUDGET,
        "SEVERITY_HARD_GATE": gm.SEVERITY_HARD_GATE,
        "SEVERITY_INFO": gm.SEVERITY_INFO,
        "GATE_PHASE_TOKENS": list(gm.GATE_PHASE_TOKENS),
        "DEFAULT_BUDGET_TOTAL_UNITS": gm.DEFAULT_BUDGET_TOTAL_UNITS,
        "DEFAULT_RELEASE_FEE_UNITS": gm.DEFAULT_RELEASE_FEE_UNITS,
        "WAVE2_UNWIRED_SOURCES": sorted(gm.WAVE2_UNWIRED_SOURCES),
        "UNWIRED_SLI_IDS": sorted(gm.UNWIRED_SLI_IDS),
        "REPORT_SOURCE_FILES": list(gm.REPORT_SOURCE_FILES),
        "DEFAULT_SLOS": gm.DEFAULT_SLOS,
    }

    # ── 相位分类 / 时间解析 / 统计辅助（含边界）──────────────────────
    out["classify_gate_phase"] = [
        gm.classify_gate_phase(g) for g in [
            "G-T-0001-REQUIREMENTS", "G-T-0001-REQUIREMENT", "G-T-0002-ARCHITECTURE",
            "G-T-0003-DESIGN", "G-T-0004-IMPLEMENTATION", "G-T-0004-IMPL",
            "G-T-0005-QUALITY", "G-T-0006-DELIVERY", "G-T-0007-UNMAPPED",
            "", None,
        ]
    ]
    out["_parse_dt"] = {
        "z_naive": gm._parse_dt("2026-01-05T09:00:00Z"),
        "tz": gm._parse_dt("2026-01-05T09:00:00+08:00"),
        "bare": gm._parse_dt("2026-01-05"),
        "none": gm._parse_dt(None),
        "empty": gm._parse_dt(""),
        "garbage": gm._parse_dt("not-a-date"),
    }
    out["_percentile"] = {
        "empty": gm._percentile([], 50.0),
        "single": gm._percentile([42.0], 95.0),
        "mid": gm._percentile([1.0, 2.0, 3.0], 50.0),
        "p95": gm._percentile([1.0, 2.0, 3.0, 4.0], 95.0),
        "p100": gm._percentile([1.0, 2.0, 3.0], 100.0),
    }
    out["_seconds_stats"] = {
        "empty": gm._seconds_stats([]),
        "sample": gm._seconds_stats([1800.0, 3600.0, 7200.0]),
    }
    out["_over_target"] = {
        "le_ok": gm._over_target({"op": "<=", "value": 0.35}, 0.2),
        "le_over": gm._over_target({"op": "<=", "value": 0.35}, 0.5),
        "ge_ok": gm._over_target({"op": ">=", "value": 1.0}, 1.0),
        "ge_over": gm._over_target({"op": ">=", "value": 1.0}, 0.9),
        "eq_ok": gm._over_target({"op": "==", "value": 0.5}, 0.5),
        "eq_over": gm._over_target({"op": "==", "value": 0.5}, 0.500000001),
    }

    # ── 加载器（正常路径 + since 过滤）────────────────────────────────
    gates = gm.load_gates(root)
    out["load_gates"] = [asdict(g) for g in gates]
    out["load_gates_since"] = [
        asdict(g) for g in gm.load_gates(
            root, since=datetime(2026, 1, 5, 0, 0, 0, tzinfo=timezone.utc))
    ]
    out["load_tasks"] = [asdict(t) for t in gm.load_tasks(root)]
    out["load_guard_events"] = [
        to_jsonable(asdict(e)) for e in gm.load_guard_events(root)]
    out["load_phase_transitions"] = [
        asdict(t) for t in gm.load_phase_transitions(root)]
    out["load_executions"] = gm.load_executions(root)
    out["load_runtime_events"] = gm.load_runtime_events(root)

    # ── 加载器失败路径（fail-closed，message 路径归一化）───────────────
    out["loader_failures"] = {
        "missing_gates": try_exc(gm.load_gates, empty_root(root / "r-missing-gates")),
        "missing_events": try_exc(
            gm.load_guard_events, empty_root(root / "r-missing-events")),
        "missing_transitions": try_exc(
            gm.load_phase_transitions, empty_root(root / "r-missing-transitions")),
        "missing_executions": try_exc(
            gm.load_executions, empty_root(root / "r-missing-executions")),
        "missing_runtime": try_exc(
            gm.load_runtime_events, empty_root(root / "r-missing-runtime")),
    }
    corrupt_root = root / "r-corrupt"
    write_metrics_fixture(corrupt_root)
    (corrupt_root / ".ai" / "evidence" / "observability" / "guard-events.jsonl").write_text(
        '{"guard_id": "g1", "check_type": "health", "result": "PASS"}\n'
        "not-json-line\n",
        encoding="utf-8",
    )
    out["loader_failures"]["corrupt_event_line"] = try_exc(
        gm.load_guard_events, corrupt_root)
    bad_result_root = root / "r-bad-result"
    write_metrics_fixture(bad_result_root)
    (bad_result_root / ".ai" / "evidence" / "observability" / "guard-events.jsonl").write_text(
        '{"guard_id": "g1", "check_type": "health", "result": "MAYBE"}\n',
        encoding="utf-8",
    )
    out["loader_failures"]["unknown_event_result"] = try_exc(
        gm.load_guard_events, bad_result_root)
    bad_key_root = root / "r-bad-key"
    write_metrics_fixture(bad_key_root)
    (bad_key_root / ".ai" / "evidence" / "observability" / "guard-events.jsonl").write_text(
        '{"guard_id": "g1", "check_type": "health"}\n',  # 缺 result
        encoding="utf-8",
    )
    out["loader_failures"]["event_missing_key"] = try_exc(
        gm.load_guard_events, bad_key_root)
    no_gates_list_root = root / "r-no-gates-list"
    (no_gates_list_root / ".ai").mkdir(parents=True)
    (no_gates_list_root / ".ai" / "gates.yaml").write_text(
        "schema_version: 1\n", encoding="utf-8")
    out["loader_failures"]["no_gates_list"] = try_exc(
        gm.load_gates, no_gates_list_root)

    # ── 纯度量函数（完整 ctx 派生）────────────────────────────────────
    def _build_ctx() -> Any:
        guard_events = [GuardCheckEvent.from_dict(d) for d in GUARD_EVENTS_JSONL]
        from loop_core.governance_metrics import SliContext
        return SliContext(
            gates=gm.load_gates(root),
            tasks=gm.load_tasks(root),
            transitions=gm.load_phase_transitions(root),
            guard_events=guard_events,
            executions=gm.load_executions(root),
            drift_events=gm.load_runtime_events(root),
            guard_decisions=[{"decision": d["decision"]} for d in GUARD_DECISIONS_JSONL],
            rework_by_task=gm.rework_cycles_from_gates(gm.load_gates(root)),
            rework_total=sum(
                gm.rework_cycles_from_gates(gm.load_gates(root)).values()),
            completed_tasks=len(
                [t for t in gm.load_tasks(root) if t.status == "completed"]),
        )

    ctx = _build_ctx()
    out["metric_functions"] = {
        "gate_rejection_rate": gm.gate_rejection_rate(ctx.gates or []),
        "gate_rejection_rate_s1": gm.gate_rejection_rate(ctx.gates or [], phase="S1-requirements"),
        "gate_rejection_rate_s4": gm.gate_rejection_rate(ctx.gates or [], phase="S4-implementation"),
        "gate_rejection_rate_empty": gm.gate_rejection_rate([]),
        "gate_decision_coverage": gm.gate_decision_coverage(ctx.gates or []),
        "approval_latencies": gm.approval_latencies(ctx.gates or []),
        "approval_latency_stats": gm.approval_latency_stats(ctx.gates or []),
        "task_cycle_seconds": gm.task_cycle_seconds(ctx.tasks or []),
        "task_cycle_time_stats": gm.task_cycle_time_stats(ctx.tasks or []),
        "phase_dwell_stats": gm.phase_dwell_stats(ctx.transitions or []),
        "rework_cycles_from_gates": gm.rework_cycles_from_gates(ctx.gates or []),
        "rework_cycles_from_transitions": gm.rework_cycles_from_transitions(ctx.transitions or []),
        "guard_anomaly_rates": gm.guard_anomaly_rates(ctx.guard_events or []),
        "guard_anomaly_rates_empty": gm.guard_anomaly_rates([]),
        "execution_cycle_stats": gm.execution_cycle_stats(ctx.executions or []),
        "drift_event_counts": gm.drift_event_counts(ctx.drift_events or []),
        "drift_event_counts_empty": gm.drift_event_counts([]),
    }

    # ── SLO 配置（缺省 / 覆盖 / 各类 fail-closed 无效配置）────────────
    out["slo_absent"] = gm.load_slo_config(empty_root(root / "r-slo-absent"))
    out["slo_override"] = gm.load_slo_config(root)
    invalid_roots: dict[str, str] = {
        "invalid_budget": "budget_total_units: abc\n",
        "half_window": "window_start: \"2026-01-01T00:00:00Z\"\n",
        "bad_target_op": "slos:\n- sli_id: x1\n  target: {op: \"<\", value: 1}\n",
        "bad_target_shape": "slos:\n- sli_id: x1\n  target: {value: 1}\n",
        "bad_severity": "slos:\n- sli_id: x1\n  severity: severe\n",
        "bad_share": "slos:\n- sli_id: x1\n  budget_share: -1\n",
        "bad_score_caps_state": "score_caps:\n  nonexistent_state: 90\n",
        "bad_score_caps_type": "score_caps: [1, 2]\n",
        "unparseable": "::: not yaml\n",
        "not_mapping": "- 1\n- 2\n",
        "entry_no_sli_id": "slos:\n- description: x\n",
    }
    out["slo_invalid"] = {}
    for name, content in invalid_roots.items():
        r = root / f"r-slo-{name}"
        (r / ".ai").mkdir(parents=True)
        (r / ".ai" / "slo.yaml").write_text(content, encoding="utf-8")
        out["slo_invalid"][name] = try_exc(gm.load_slo_config, r)
    out["slo_invalid"] = norm_paths(out["slo_invalid"], root)

    # ── SLI 评估（默认表 × 完整 ctx；budget 记账）──────────────────────
    out["sli_eval_default"] = [gm.evaluate_sli(sli, ctx) for sli in gm.DEFAULT_SLOS]
    out["release_fee_consumption"] = {
        "zero_releases": gm.release_fee_consumption(5.0, 0),
        "two_releases": gm.release_fee_consumption(5.0, 2),
        "rounding": gm.release_fee_consumption(0.5, 3),
    }
    out["compute_error_budget"] = {
        "releases0": gm.compute_error_budget(
            out["sli_eval_default"], total_units=80.0, release_fee_units=4.0, releases=0),
        "releases2": gm.compute_error_budget(
            out["sli_eval_default"], total_units=80.0, release_fee_units=4.0, releases=2),
        "healthy": gm.compute_error_budget([]),
        "exhausted": gm.compute_error_budget(
            out["sli_eval_default"], total_units=5.0, release_fee_units=4.0, releases=0),
    }

    # ── DORA / Repair / LoopEffectiveness / 评分呈现 ───────────────────
    out["dora"] = gm.build_dora_metrics(ctx)
    out["repair_progress"] = gm.build_repair_progress(ctx)
    out["repair_trigger_count"] = gm.repair_trigger_count(ctx.gates or [])
    out["fixed_gate_count"] = gm.fixed_gate_count(ctx.gates or [])
    out["loop_effectiveness"] = gm.build_loop_effectiveness(ctx)
    out["evidence_score_advisory"] = {
        "with_state": gm.evidence_score_advisory(88.0, state="Exercised"),
        "no_state": gm.evidence_score_advisory(12.4),
        "capped": gm.evidence_score_advisory(
            96.0, state="Outcome-supported", caps={"Outcome-supported": 95}),
        "float_round": gm.evidence_score_advisory(88.6, state="Wired"),
    }
    out["_metric"] = gm._metric(1.0, status="computed", basis="b")
    out["_not_available"] = {
        "plain": gm._not_available("reason"),
        "advisory": gm._not_available("reason", advisory=True),
    }

    # ── 报告（显式窗口 + 数据窗口；generated_at/git_commit 归一化）────
    report1 = gm.build_report(
        root, window=("2026-01-01T00:00:00", "2026-01-31T23:59:59"),
        releases=2, task_id="T-0110", phase="S6-delivery", gate_id="G-T-0110-DELIVERY",
    )
    d1 = report1.to_dict()
    d1["binding"]["timestamp"] = "<GENERATED_AT>"
    d1["binding"]["git_commit"] = "<GIT_COMMIT>"
    out["report_explicit_window"] = d1
    md1 = gm.render_markdown(report1)
    md1 = re.sub(r"\*\*Generated\*\*: .*", "**Generated**: <GENERATED_AT>", md1)
    md1 = re.sub(r"\*\*Git commit\*\*: .*", "**Git commit**: <GIT_COMMIT>", md1)
    out["report_markdown"] = md1

    report2 = gm.build_report(root)  # 数据窗口 + releases=0
    d2 = report2.to_dict()
    d2["binding"]["timestamp"] = "<GENERATED_AT>"
    d2["binding"]["git_commit"] = "<GIT_COMMIT>"
    out["report_data_window"] = d2

    out = norm_paths(out, root)
    return out


# ══════════════════════════════════════════════════════════════════════
# intent_router 固定语料
# ══════════════════════════════════════════════════════════════════════

INTENT_CORPUS: list[str] = [
    # 基础域
    "Build a simple web app with html and css",
    "Create a mobile app for iOS using flutter",
    "Set up a REST API backend with PostgreSQL",
    "Write a CLI tool in python to parse logs",
    "Deploy a kubernetes cluster on AWS",
    "Train an LLM model with pytorch",
    # 高风险
    "Build a payment gateway with stripe and subscription billing",
    "Add authentication with jwt and oauth to the login flow",
    "Handle production data migration for customer records",
    "Fix the sql injection vulnerability in the search endpoint",
    "Add pii compliance for gdpr and hipaa",
    # 否定语境
    "Remove the database and the auth module",
    "Create the payment module without any secrets",
    "Delete the caching layer",
    "Stop using the old api and remove mysql",
    "Add caching without any database",
    # 中风险
    "Refactor the module into multiple packages for the monorepo",
    "Integrate with a third-party REST API",
    "Set up CI/CD pipeline and deploy to production",
    "Add caching and async concurrency for performance",
    # 规模/复杂度
    "Build a high-availability microservice platform with real-time streaming",
    "Migrate the legacy monolith to event-driven architecture",
    "Build a scalable enterprise system with feature flags and canary releases",
    "Add zero-downtime blue-green deployment with rollback",
    "Set up observability with monitoring and alerting",
    # 轻量提示
    "Fix a typo in the readme",
    "Add docstring to the util module and rename a variable",
    "Update the changelog",
    # 不确定
    "maybe build a small tool for experiments",
    "I am not sure, explore some options for a poc",
    "Something about web stuff",
    # 中文变更类型
    "修复登录页面的 bug，补充单元测试",
    "新增用户管理功能，重构权限模块",
    "需求变更：改成 v2 接口",
    "帮我写一个数据管道，然后部署到服务器",
    # 多意图
    "Build a web app; then add payment integration",
    "1. fix the login bug 2. add unit tests for the api",
    "创建一个 CLI 工具，然后部署到服务器",
    "Refactor the module. 修复崩溃问题",
    "Add feature A；同时优化性能",
    # 任务引用 / 完成信号
    "Continue working on T-0123 and finish the remaining tests",
    "mark T-0100 complete and start a new task",
    "T-0123 is done, switch to T-0456",
    "帮我收尾 T-0100，然后开始 T-0123",
    # 杂项
    "Set up a data pipeline with etl and analytics",
    "Build a raspberry pi iot sensor with mqtt",
    "Write terraform for infrastructure and helm charts",
    "Add a feature flag for the new checkout flow",
]

INTENT_CONTEXTS: list[dict | None] = [
    None,
    {"file_count": 3, "module_count": 1},
    {"file_count": 50, "module_count": 12, "team_size": 4},
    {"is_existing_project": True},
]


def capture_intent_router_golden() -> dict[str, Any]:
    """intent_router 全量 golden 捕获（输出确定性 JSON 结构）。"""
    from loop_core import intent_router as ir  # noqa: F401 — 统一入口壳
    from loop_core.router import LoopMode

    out: dict[str, Any] = {}

    # ── 词表/常量表（值级快照）────────────────────────────────────────
    out["keywords"] = {
        "DOMAIN_KEYWORDS": ir.DOMAIN_KEYWORDS,
        "LIGHTWEIGHT_KEYWORDS": ir.LIGHTWEIGHT_KEYWORDS,
        "HIGH_RISK_KEYWORDS": ir.HIGH_RISK_KEYWORDS,
        "MEDIUM_RISK_KEYWORDS": ir.MEDIUM_RISK_KEYWORDS,
        "SCALE_INDICATORS": [[p, i] for p, i in ir.SCALE_INDICATORS],
        "MAX_COMPLEXITY": ir.MAX_COMPLEXITY,
        "MIN_COMPLEXITY": ir.MIN_COMPLEXITY,
        "BUG_FIX_KEYWORDS": ir.BUG_FIX_KEYWORDS,
        "FEATURE_ADD_KEYWORDS": ir.FEATURE_ADD_KEYWORDS,
        "REFACTOR_KEYWORDS": ir.REFACTOR_KEYWORDS,
        "REQUIREMENT_CHANGE_KEYWORDS": ir.REQUIREMENT_CHANGE_KEYWORDS,
        "QUALITY_FIX_KEYWORDS": ir.QUALITY_FIX_KEYWORDS,
        "INTENT_SWITCH_KEYWORDS": ir.INTENT_SWITCH_KEYWORDS,
        "_COMPLETION_VERBS": ir._COMPLETION_VERBS,
        "_NEGATION_PATTERNS": ir._NEGATION_PATTERNS,
        "_MAX_TASK_FRAMES": ir._MAX_TASK_FRAMES,
        "_TASK_ID_RE": ir._TASK_ID_RE.pattern,
        "_INTENT_SPLIT_RE": ir._INTENT_SPLIT_RE.pattern,
        "CHANGE_TYPE_TO_ENTRY_PHASE": {
            k.value: v for k, v in ir.CHANGE_TYPE_TO_ENTRY_PHASE.items()},
        "CHANGE_TYPE_MIN_PHASES": {
            k.value: v for k, v in ir.CHANGE_TYPE_MIN_PHASES.items()},
        "router_knobs": {
            "LIGHTWEIGHT_COMPLEXITY_MAX": ir.IntentRouter.LIGHTWEIGHT_COMPLEXITY_MAX,
            "STANDARD_COMPLEXITY_MAX": ir.IntentRouter.STANDARD_COMPLEXITY_MAX,
            "LOW_CONFIDENCE_THRESHOLD": ir.IntentRouter.LOW_CONFIDENCE_THRESHOLD,
            "MEDIUM_RISK_ESCALATION_MIN": ir.IntentRouter.MEDIUM_RISK_ESCALATION_MIN,
            "DOMAIN_WEIGHT": ir.IntentRouter.DOMAIN_WEIGHT,
            "KEYWORD_WEIGHT": ir.IntentRouter.KEYWORD_WEIGHT,
            "SCALE_WEIGHT": ir.IntentRouter.SCALE_WEIGHT,
        },
    }

    # ── 变更类型检测 ───────────────────────────────────────────────────
    out["_detect_change_type"] = [
        ir._detect_change_type(d) for d in [
            "fix a bug in login", "新增用户管理功能", "重构权限模块",
            "需求变了，改成 v2", "测试没过，补一下单元测试",
            "build a web app", "修复崩溃并加测试",
        ]
    ]

    # ── 检测/评分辅助（直接调用）───────────────────────────────────────
    out["_detect_domains"] = [
        sorted(ir._detect_domains(d.lower())) for d in [
            "build a web app with react and bootstrap",
            "create a mobile app for ios with flutter",
            "set up a rest api backend with postgresql",
            "write a cli tool using argparse",
            "train an llm with pytorch and jupyter",
            "maintain the ai infra on aws",  # "ai" 词边界（不误命中 maintain）
            "build a thing with no keywords at all",
        ]
    ]
    out["_extract_risk_factors"] = [
        ir._extract_risk_factors(d.lower()) for d in [
            "build a payment gateway with stripe and billing",
            "add auth with jwt and oauth",
            "migrate production data and pii",
            "remove the database and the auth module",
            "deploy to production with ci/cd pipeline",
            "maybe add async caching",
            "add monitoring and rollback support",
        ]
    ]
    out["_is_negated"] = {
        "remove_db": ir._is_negated("remove the database", "database"),
        "without_auth": ir._is_negated("create the module without any auth", "auth"),
        "do_not_need": ir._is_negated("we do not need the cache", "cache"),
        "plain": ir._is_negated("add a database", "database"),
    }
    out["_set_if_match"] = []
    for desc in ["remove the database", "add a database", "with mysql only"]:
        factors = {"has_database": False}
        ir._set_if_match(factors, "has_database", desc,
                         ["database", "sql", "mysql"])
        out["_set_if_match"].append(factors)
    out["_compute_complexity"] = [
        ir._compute_complexity(
            d, ir._detect_domains(d), ir._extract_risk_factors(d),
            ir.IntentRouter.DOMAIN_WEIGHT, ir.IntentRouter.KEYWORD_WEIGHT,
            ir.IntentRouter.SCALE_WEIGHT, ctx)
        for d, ctx in [
            ("build a payment gateway with postgresql", {}),
            ("fix a typo and update the readme", {}),
            ("build a high-availability microservice with real-time streaming", {}),
            ("add caching to the web app", {"file_count": 50, "module_count": 12}),
            ("refactor the monorepo", {}),
        ]
    ]
    out["_build_reasoning"] = ir._build_reasoning(
        {"web", "api"}, 0.42, {"has_external_api": True}, LoopMode.STANDARD,
        True, "Multiple medium-risk factors (1): escalating.", 0.7)

    # ── IntentRouter.analyze × 语料 × 上下文 ───────────────────────────
    router = ir.IntentRouter()
    out["analyze"] = []
    for desc in INTENT_CORPUS:
        for ctx in INTENT_CONTEXTS:
            analysis = router.analyze(desc, ctx)
            out["analyze"].append({
                "desc": desc,
                "ctx": ctx,
                "result": to_jsonable(asdict(analysis)),
            })

    # 自定义阈值路由实例
    custom = ir.IntentRouter(LIGHTWEIGHT_COMPLEXITY_MAX=0.5,
                             MEDIUM_RISK_ESCALATION_MIN=2)
    out["analyze_custom_knobs"] = to_jsonable(
        asdict(custom.analyze("Build a simple api with auth")))

    # ── should_escalate / route ────────────────────────────────────────
    out["should_escalate"] = {
        "high_risk": ir.IntentRouter.should_escalate(
            {"has_payments": True, "has_database": True}, LoopMode.LIGHTWEIGHT),
        "medium_3": ir.IntentRouter.should_escalate(
            {"has_external_api": True, "has_multiple_modules": True,
             "requires_deployment": True}, LoopMode.STANDARD),
        "medium_2": ir.IntentRouter.should_escalate(
            {"has_external_api": True, "has_multiple_modules": True},
            LoopMode.LIGHTWEIGHT),
        "already_full": ir.IntentRouter.should_escalate(
            {"has_external_api": True, "has_multiple_modules": True,
             "requires_deployment": True}, LoopMode.FULL),
        "low_conf_analysis": ir.IntentRouter.should_escalate(
            analysis=router.analyze("something vague")),
        "none": ir.IntentRouter.should_escalate(),
    }
    out["route"] = [
        to_jsonable(asdict(router.route(router.analyze(d))))
        for d in ["fix a typo", "build a web api", "handle production data migration"]
    ]
    out["_phases_for_mode"] = {
        m.value: ir._phases_for_mode(m)
        for m in (LoopMode.LIGHTWEIGHT, LoopMode.STANDARD, LoopMode.FULL)
    }
    out["_analysis_to_profile"] = to_jsonable(vars(
        ir._analysis_to_profile(router.analyze("build a payment gateway"))))

    # ── 意图切分 / 切换信号 ────────────────────────────────────────────
    out["split_intents"] = [
        ir.split_intents(d) for d in [
            "Build a web app; then add payment integration",
            "1. fix the login bug 2. add unit tests for the api",
            "创建一个 CLI 工具，然后部署到服务器",
            "Refactor the module. 修复崩溃问题",
            "Add feature A；同时优化性能",
            "登录之后修改设置",               # 时态引用不切分
            "Build a web app",               # 单意图
            "", None, 123,                   # 空/非法输入 → []
            "a; b; c; d; e; f; g",           # 超 max_frames（默认 5）
        ]
    ]
    out["split_intents_max2"] = [
        ir.split_intents(d, max_frames=2) for d in [
            "Build a web app; then add payment; finally deploy",
            "x",
        ]
    ]
    out["detect_intent_switch"] = [
        ir.detect_intent_switch(d) for d in [
            "start a new task: build a cli",
            "mark T-0100 complete and start a new task",
            "继续当前任务",                    # 无标记
            "任务完成，切换到另一个任务",
            "build a web app",
            "switch to T-0456",
        ]
    ]
    out["_other_task_refs"] = {
        "other_id": ir._other_task_refs("continue working on t-0123", "T-0100"),
        "same_id": ir._other_task_refs("work on T-0100", "T-0100"),
        "two_ids": ir._other_task_refs("T-0123 and T-0456", "T-0100"),
        "case_dup": ir._other_task_refs("T-0123 and t-0123", "T-0100"),
    }
    out["_active_task_completion_signal"] = {
        "complete": ir._active_task_completion_signal(
            "please mark T-0100 complete when done", "T-0100"),
        "done": ir._active_task_completion_signal(
            "T-0100 is done", "T-0100"),
        "cancel": ir._active_task_completion_signal(
            "cancel the task T-0100", "T-0100"),
        "far_away": ir._active_task_completion_signal(
            "continue the work on T-0100 and then later when finished maybe complete", "T-0100"),
        "no_ref": ir._active_task_completion_signal(
            "mark complete please", "T-0100"),
        "other_task": ir._active_task_completion_signal(
            "T-0123 is done", "T-0100"),
    }

    # ── U5 路由主流程（sticky / switch / degraded / 多帧）──────────────
    active_full = ir.ActiveTaskSnapshot(
        task_id="T-0100", status="active", title="web app",
        domain="web", description="existing web app",
        loop_mode=LoopMode.FULL)
    active_done = ir.ActiveTaskSnapshot(
        task_id="T-0100", status="completed", title="web app",
        domain="web", description="existing web app",
        loop_mode=LoopMode.STANDARD)
    active_from_task = ir.ActiveTaskSnapshot.from_task({
        "id": "T-0200", "status": "in_progress", "title": "cli",
        "domain": "cli", "description": "a cli tool",
        "loop_mode": "standard",
    })
    active_from_task_unknown = ir.ActiveTaskSnapshot.from_task({
        "task_id": "T-0300", "mode": "bogus",
    })

    upgrade_cases: list[tuple[str, Any, dict | None]] = [
        ("Build a web app with react", active_full, None),
        ("switch to a new task: build a cli tool", active_full, None),
        ("mark T-0100 complete", active_full, None),
        ("continue T-0123 please", active_full, None),
        ("fix the api bug; add tests for it", active_full, None),
        ("add a feature to the cli", active_from_task, None),
        ("add a feature", active_done, None),
        ("add a feature", active_from_task_unknown, None),
        ("build a web app", None, None),
        (123, active_full, None),
        ("build a web app", active_full, {"file_count": 2}),
    ]
    out["route_user_input"] = []
    for desc, act, ctx in upgrade_cases:
        result = ir.route_user_input(desc, act, ctx)
        out["route_user_input"].append(to_jsonable(asdict(result)))
    out["analyse_intent"] = [
        to_jsonable(asdict(ir.analyse_intent(d))) for d in [
            "build a payment gateway",
            "fix a typo",
            "set up a data pipeline",
        ]
    ]
    return out


# ══════════════════════════════════════════════════════════════════════
# 模块公开面快照（dir() 全量，用于 re-export 完整性断言）
# ══════════════════════════════════════════════════════════════════════


def module_dir_snapshot(module_name: str) -> list[str]:
    """返回模块 dir() 全量排序快照（含私有名，覆盖 import * 与直接私有导入）。"""
    import importlib
    return sorted(dir(importlib.import_module(module_name)))
