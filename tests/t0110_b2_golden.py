"""T-0110 批 B-2 golden 语料共享助手（human_review_packet / context_loader 拆分等价）。

本模块不被 pytest 直接收集（无 test_ 前缀），由两类消费者使用：
1. ``.ai/evidence/T-0110/golden/generate_golden_b2.py`` —— 拆分前/后各跑一次，
   产出 golden-b2-before.json / golden-b2-after.json（逐字节 diff 证据）；
2. ``tests/test_t0110_batch_b2.py`` —— 运行时重放语料，与内嵌基线逐字段断言。

全部捕获为确定性 JSON（复用 t0110_b1_golden 的 to_jsonable/norm_paths/try_exc）：
- 输入语料固定；build_resume_payload/resume_from_payload/builder 产物中的
  generated_at/resumed_at/expires_at/packet_id 归一化为固定标记
  （<GENERATED_AT>/<RESUMED_AT>/<EXPIRES_AT>/<PACKET_ID>）；
- 异常路径只记录 (type, message)，message 中的临时路径归一化为 <ROOT>；
- 枚举按 .value 序列化，datetime 按 isoformat，集合排序。
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from t0110_b1_golden import (  # noqa: F401 — 复用 B-1 归一化工具
    dump_json,
    module_dir_snapshot,
    norm_paths,
    to_jsonable,
    try_exc,
)

# ══════════════════════════════════════════════════════════════════════
# 归一化工具（B-2 专属：时间/包 ID 标记化）
# ══════════════════════════════════════════════════════════════════════

_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?")
_HRP_ID_RE = re.compile(r"HRP(?:-VETO)?-[0-9A-F]{8}")


def _mark_timestamps(obj: Any) -> Any:
    """把任意结构中的 ISO 时间戳字符串归一化为 <TS>（含 to_markdown 全文）。"""
    if isinstance(obj, str):
        return _TS_RE.sub("<TS>", obj)
    if isinstance(obj, dict):
        return {k: _mark_timestamps(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_mark_timestamps(x) for x in obj]
    return obj


def _mark_packet_ids(obj: Any) -> Any:
    """把 builder 生成的 HRP-xxxxxxxx / HRP-VETO-xxxxxxxx 归一化为 <PACKET_ID>。"""
    if isinstance(obj, str):
        return _HRP_ID_RE.sub("<PACKET_ID>", obj)
    if isinstance(obj, dict):
        return {k: _mark_packet_ids(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_mark_packet_ids(x) for x in obj]
    return obj


# ══════════════════════════════════════════════════════════════════════
# human_review_packet 固定夹具
# ══════════════════════════════════════════════════════════════════════

AUTHORITATIVE_STATE = {
    "current_task_id": "T-0110",
    "current_gate_id": "G-T-0110-DELIVERY",
    "current_phase": "S6-delivery",
}

TASK_GRAPH = {
    "tasks": [
        {
            "id": "T-0110", "title": "共同弱点治理", "status": "in_progress",
            "phase": "S6-delivery", "priority": "P1", "note": "五文件拆分",
            "depends_on": ["T-0109"],
            "gates": ["G-T-0110-DELIVERY"],
        },
        {
            "id": "T-0111", "title": "后续治理", "status": "pending",
            "phase": "S6-delivery", "priority": "P2",
        },
        {
            "id": "T-0112", "title": "已归档", "status": "completed",
            "phase": "S6-delivery", "priority": "P3",
        },
    ]
}

GATES_YAML = {
    "gates": [
        {
            "id": "G-T-0110-DELIVERY", "task_id": "T-0110",
            "gate_type": "delivery", "status": "pending",
            "decision": None, "recorded_at": None,
            "approval_actor": None, "approval_source": None, "evidence": [],
        },
    ]
}


def write_resume_fixture(root: Path, *, with_task_file: bool = False,
                         with_evidence_dir: bool = False) -> None:
    """构建权威治理状态树（state.yaml / task_graph.yaml / gates.yaml）。"""
    ai = root / ".ai"
    (ai / "evidence").mkdir(parents=True, exist_ok=True)
    (ai / "state.yaml").write_text(
        json.dumps(AUTHORITATIVE_STATE, ensure_ascii=False), encoding="utf-8")
    (ai / "task_graph.yaml").write_text(
        json.dumps(TASK_GRAPH, ensure_ascii=False), encoding="utf-8")
    (ai / "gates.yaml").write_text(
        json.dumps(GATES_YAML, ensure_ascii=False), encoding="utf-8")
    if with_task_file:
        (ai / "tasks").mkdir(parents=True, exist_ok=True)
        (ai / "tasks" / "T-0110.md").write_text("# T-0110\n", encoding="utf-8")
    if with_evidence_dir:
        (ai / "evidence" / "T-0110").mkdir(parents=True, exist_ok=True)


def _make_fixture_packet(**overrides: Any) -> Any:
    """构造确定性 HumanReviewPacket（固定 ID/时间，全节填充）。"""
    from loop_core.human_review_packet import (
        DecisionRequired,
        HumanReviewPacket,
        KeyChoice,
        PacketType,
        RiskItem,
    )

    base: dict[str, Any] = {
        "packet_id": "HRP-FIXEDID",
        "packet_type": PacketType.GATE_APPROVAL,
        "phase": "S6-delivery",
        "task_id": "T-0110",
        "what_we_did": "我们完成了交付阶段的全部产出并逐项检查。",
        "what_changed": "从计划推进到可评审的具体交付物。",
        "key_choices": [
            KeyChoice(
                question="How should we store user data?",
                option_a="A cloud-based database",
                option_b="Files saved on the server",
                why_a="Scales with the business",
                why_not_b="Becomes hard to keep consistent",
                risk_if_wrong="We may need to migrate later",
            ),
        ],
        "risks": [
            RiskItem(
                risk="SQL 注入风险",
                likelihood="High",
                impact="Unauthorised data access",
                analogy="Leaving the cash register unlocked",
                mitigation="All data requests are validated",
            ),
        ],
        "decision_required": DecisionRequired(
            question="Do you approve moving to the delivery phase?",
            options=["Approve", "Request changes", "Pause project"],
            recommendation="We recommend approving.",
            deadline="3 days from now",
        ),
        "evidence_summary": "- All checks passed\n- coverage: +",
        "who_reviewed": ["quality-engineer", "security-engineer"],
        "vetoes": ["scope drift detected"],
        "generated_at": "2026-08-03T00:00:00+00:00",
        "expires_at": "2026-08-10T00:00:00+00:00",
        "related_experience": "## 历史教训\n上次同一 gate 因证据缺失被拒。",
    }
    base.update(overrides)
    return HumanReviewPacket(**base)


def _resume_payload_fixture() -> Any:
    """构造确定性 ResumePayload（固定 generated_at，快照+恢复数据）。"""
    from loop_core.human_review_packet import (
        DecisionPoint,
        ResumePayload,
        ResumeSnapshot,
    )

    return ResumePayload(
        generated_at="2026-08-03T00:00:00+00:00",
        snapshot=ResumeSnapshot(
            task_id="T-0110",
            gate_id="G-T-0110-DELIVERY",
            phase="S6-delivery",
            decision_point=DecisionPoint(
                decision_type="gate_approval",
                presentation_version=1,
                packet_id="HRP-FIXEDID",
            ),
            context_pointers=[
                "<ROOT>/.ai/state.yaml",
                "<ROOT>/.ai/tasks/T-0110.md",
            ],
            sources={
                "state.yaml": "<ROOT>/.ai/state.yaml",
                "task_graph.yaml": "<ROOT>/.ai/task_graph.yaml",
            },
        ),
        recovery={
            "task": {"id": "T-0110", "status": "in_progress"},
            "gate": {"id": "G-T-0110-DELIVERY", "status": "pending"},
            "phase": "S6-delivery",
            "pending_tasks": [{"id": "T-0111", "status": "pending"}],
        },
    )


# ══════════════════════════════════════════════════════════════════════
# human_review_packet golden 捕获
# ══════════════════════════════════════════════════════════════════════


def capture_human_review_packet_golden(root: Path) -> dict[str, Any]:
    """human_review_packet 全量 golden 捕获（输出确定性 JSON 结构）。"""
    from loop_core import human_review_packet as hrp  # noqa: F401 — 统一入口壳

    out: dict[str, Any] = {}

    # ── 模块级常量 / 枚举 ─────────────────────────────────────────────
    out["constants"] = {
        "RESUME_PAYLOAD_SCHEMA": hrp.RESUME_PAYLOAD_SCHEMA,
        "RESUME_PAYLOAD_SCHEMA_VERSION": hrp.RESUME_PAYLOAD_SCHEMA_VERSION,
        "RESUME_PAYLOAD_PRESENTATION_VERSION": hrp.RESUME_PAYLOAD_PRESENTATION_VERSION,
        "PacketType_values": {p.value for p in hrp.PacketType},
        "ResumePayloadError_mro": [
            c.__name__ for c in hrp.ResumePayloadError.__mro__],
        "StateDriftError_mro": [
            c.__name__ for c in hrp.StateDriftError.__mro__],
    }

    # ── 数据模型默认值（dataclass 构造）───────────────────────────────
    out["model_defaults"] = {
        "KeyChoice": asdict(hrp.KeyChoice("q", "a", "b", "w", "n", "r")),
        "RiskItem": asdict(hrp.RiskItem("r", "M", "i", "an", "m")),
        "DecisionRequired": asdict(hrp.DecisionRequired("q", ["a"], "rec", None)),
        "DecisionPoint": asdict(hrp.DecisionPoint("gate_approval", 1)),
        "ResumeSnapshot": to_jsonable(
            asdict(hrp.ResumeSnapshot(
                task_id="T-1", gate_id="G-1", phase="S1",
                decision_point=hrp.DecisionPoint("x", 1)))),
        "ResumePayload": to_jsonable(asdict(hrp.ResumePayload(
            generated_at="2026-08-03T00:00:00+00:00",
            snapshot=hrp.ResumeSnapshot(
                task_id="T-1", gate_id="G-1", phase="S1",
                decision_point=hrp.DecisionPoint("x", 1))))),
        "ResumeContext_defaults": to_jsonable(
            asdict(hrp.ResumeContext(
                task_id="T", gate_id="G", phase="S", decision_point=None,
                task={}, gate={}, pending_tasks=[], context_pointers=[],
                sources={}, resumed_at="2026-08-03T00:00:00+00:00"))),
    }

    # ── 序列化往返（to/from_dict、to_json/from_json）──────────────────
    payload = _resume_payload_fixture()
    d = payload.to_dict()
    out["serialize"] = {
        "to_dict": to_jsonable(d),
        "from_dict_roundtrip": to_jsonable(
            asdict(hrp.ResumePayload.from_dict(d))),
        "to_json": _mark_timestamps(payload.to_json()),
        "from_json_roundtrip": to_jsonable(
            asdict(hrp.ResumePayload.from_json(payload.to_json()))),
        "snapshot_roundtrip": to_jsonable(
            asdict(hrp.ResumeSnapshot.from_dict(
                payload.snapshot.to_dict()))),
        "decision_point_roundtrip": to_jsonable(
            asdict(hrp.DecisionPoint.from_dict(
                payload.snapshot.decision_point.to_dict()))),
    }
    # 序列化失败路径（fail-closed）
    out["serialize_failures"] = {
        "payload_not_dict": try_exc(hrp.ResumePayload.from_dict, "nope"),
        "bad_schema": try_exc(hrp.ResumePayload.from_dict, {
            "schema": "other", "schema_version": 1, "snapshot": {}}),
        "bad_schema_version": try_exc(hrp.ResumePayload.from_dict, {
            "schema": hrp.RESUME_PAYLOAD_SCHEMA, "schema_version": 99,
            "snapshot": {}}),
        "missing_snapshot": try_exc(hrp.ResumePayload.from_dict, {
            "schema": hrp.RESUME_PAYLOAD_SCHEMA,
            "schema_version": hrp.RESUME_PAYLOAD_SCHEMA_VERSION}),
        "snapshot_not_dict": try_exc(hrp.ResumePayload.from_dict, {
            "schema": hrp.RESUME_PAYLOAD_SCHEMA,
            "schema_version": hrp.RESUME_PAYLOAD_SCHEMA_VERSION,
            "snapshot": "x"}),
        "snapshot_missing_field": try_exc(hrp.ResumeSnapshot.from_dict, {
            "task_id": "T"}),
        "snapshot_bad_dp": try_exc(hrp.ResumeSnapshot.from_dict, {
            "task_id": "T", "gate_id": "G", "phase": "S",
            "decision_point": None}),
        "dp_missing_fields": try_exc(hrp.DecisionPoint.from_dict, {
            "decision_type": "x"}),
        "dp_bad_version": try_exc(hrp.DecisionPoint.from_dict, {
            "decision_type": "x", "presentation_version": "1"}),
        "bad_json": try_exc(hrp.ResumePayload.from_json, "{not json"),
    }

    # ── build_resume_payload（成功 + 全部 fail-closed 路径）───────────
    ok_root = root / "r-ok"
    write_resume_fixture(ok_root, with_task_file=True, with_evidence_dir=True)
    built = hrp.build_resume_payload(
        ok_root, task_id="T-0110", gate_id="G-T-0110-DELIVERY",
        phase="S6-delivery", decision_type=hrp.PacketType.GATE_APPROVAL,
        presentation_version=1, packet_id="HRP-FIXEDID",
    )
    out["build_resume_payload_ok"] = norm_paths(
        _mark_timestamps(to_jsonable(asdict(built))), ok_root)

    empty_root = root / "r-empty"
    (empty_root / ".ai").mkdir(parents=True)
    out["build_failures"] = {
        "missing_state": try_exc(
            hrp.build_resume_payload, empty_root, task_id="T-0110",
            gate_id="G-T-0110-DELIVERY", phase="S6-delivery"),
    }
    missing_tg = root / "r-missing-tg"
    write_resume_fixture(missing_tg)
    (missing_tg / ".ai" / "task_graph.yaml").unlink()
    out["build_failures"]["missing_task_graph"] = try_exc(
        hrp.build_resume_payload, missing_tg, task_id="T-0110",
        gate_id="G-T-0110-DELIVERY", phase="S6-delivery")
    bad_yaml = root / "r-bad-yaml"
    write_resume_fixture(bad_yaml)
    (bad_yaml / ".ai" / "state.yaml").write_text(
        "{not yaml", encoding="utf-8")
    out["build_failures"]["unparseable_state"] = try_exc(
        hrp.build_resume_payload, bad_yaml, task_id="T-0110",
        gate_id="G-T-0110-DELIVERY", phase="S6-delivery")
    not_mapping = root / "r-not-mapping"
    write_resume_fixture(not_mapping)
    (not_mapping / ".ai" / "state.yaml").write_text("- 1\n- 2\n", encoding="utf-8")
    out["build_failures"]["state_not_mapping"] = try_exc(
        hrp.build_resume_payload, not_mapping, task_id="T-0110",
        gate_id="G-T-0110-DELIVERY", phase="S6-delivery")
    drift_task = root / "r-drift-task"
    write_resume_fixture(drift_task)
    out["build_failures"]["task_mismatch"] = try_exc(
        hrp.build_resume_payload, drift_task, task_id="T-9999",
        gate_id="G-T-0110-DELIVERY", phase="S6-delivery")
    drift_gate = root / "r-drift-gate"
    write_resume_fixture(drift_gate)
    out["build_failures"]["gate_mismatch"] = try_exc(
        hrp.build_resume_payload, drift_gate, task_id="T-0110",
        gate_id="G-T-9999", phase="S6-delivery")
    drift_phase = root / "r-drift-phase"
    write_resume_fixture(drift_phase)
    out["build_failures"]["phase_mismatch"] = try_exc(
        hrp.build_resume_payload, drift_phase, task_id="T-0110",
        gate_id="G-T-0110-DELIVERY", phase="S5-quality")
    no_task = root / "r-no-task"
    write_resume_fixture(no_task)
    (no_task / ".ai" / "task_graph.yaml").write_text(
        json.dumps({"tasks": []}), encoding="utf-8")
    out["build_failures"]["task_missing"] = try_exc(
        hrp.build_resume_payload, no_task, task_id="T-0110",
        gate_id="G-T-0110-DELIVERY", phase="S6-delivery")
    no_gate = root / "r-no-gate"
    write_resume_fixture(no_gate)
    (no_gate / ".ai" / "gates.yaml").write_text(
        json.dumps({"gates": []}), encoding="utf-8")
    out["build_failures"]["gate_missing"] = try_exc(
        hrp.build_resume_payload, no_gate, task_id="T-0110",
        gate_id="G-T-0110-DELIVERY", phase="S6-delivery")
    wrong_binding = root / "r-wrong-binding"
    write_resume_fixture(wrong_binding)
    (wrong_binding / ".ai" / "gates.yaml").write_text(json.dumps({
        "gates": [{"id": "G-T-0110-DELIVERY", "task_id": "T-OTHER",
                   "status": "pending"}]}), encoding="utf-8")
    out["build_failures"]["gate_wrong_task"] = try_exc(
        hrp.build_resume_payload, wrong_binding, task_id="T-0110",
        gate_id="G-T-0110-DELIVERY", phase="S6-delivery")
    out["build_failures"] = norm_paths(out["build_failures"], root)

    # ── 恢复字段辅助（直接调用）───────────────────────────────────────
    out["recovery_helpers"] = {
        "_task_recovery_record": hrp._task_recovery_record({
            "id": "T-0110", "title": "t", "status": "pending", "phase": "S1",
            "priority": "P1", "note": "n", "depends_on": ["T-1"],
            "gates": ["G-1"], "extra": "dropped"}),
        "_task_recovery_record_min": hrp._task_recovery_record({"id": "T"}),
        "_gate_recovery_record": hrp._gate_recovery_record({
            "id": "G-1", "task_id": "T-1", "gate_type": "delivery",
            "status": "pending", "decision": None, "recorded_at": "2026-01-01",
            "approval_actor": "user", "approval_source": "ui", "evidence": [],
            "extra": "dropped"}),
        "_gate_recovery_record_min": hrp._gate_recovery_record({"id": "G"}),
        "_pending_tasks": hrp._pending_tasks(TASK_GRAPH),
        "_pending_tasks_empty": hrp._pending_tasks({"tasks": []}),
        "_find_task_hit": hrp._find_task(TASK_GRAPH, "T-0111"),
        "_find_task_miss": hrp._find_task(TASK_GRAPH, "T-9999"),
        "_find_gate_hit": hrp._find_gate(GATES_YAML, "G-T-0110-DELIVERY"),
        "_find_gate_miss": hrp._find_gate(GATES_YAML, "G-9999"),
    }

    # ── resume_from_payload（成功 + 全 drift 路径）────────────────────
    ok2 = root / "r-resume-ok"
    write_resume_fixture(ok2)
    payload_ok = hrp.build_resume_payload(
        ok2, task_id="T-0110", gate_id="G-T-0110-DELIVERY",
        phase="S6-delivery", decision_type="gate_approval",
    )
    resumed = hrp.resume_from_payload(payload_ok, ok2)
    out["resume_ok"] = norm_paths(
        _mark_timestamps(to_jsonable(asdict(resumed))), ok2)
    # dict 形式 payload + 字符串 decision_type 变体
    payload_dict = payload_ok.to_dict()
    resumed_dict = hrp.resume_from_payload(payload_dict, ok2)
    out["resume_from_dict"] = norm_paths(
        _mark_timestamps(to_jsonable(asdict(resumed_dict))), ok2)

    def _mutate_state(r: Path, key: str, value: Any) -> Path:
        state_path = r / ".ai" / "state.yaml"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state[key] = value
        state_path.write_text(json.dumps(state), encoding="utf-8")
        return r

    drift_root = root / "r-drift"
    write_resume_fixture(drift_root)
    out["resume_failures"] = {
        "invalid_type": try_exc(hrp.resume_from_payload, "nope", drift_root),
        "no_snapshot": try_exc(
            hrp.resume_from_payload,
            hrp.ResumePayload(
                generated_at="2026-08-03T00:00:00+00:00", snapshot=None),
            drift_root),
    }
    for name, key, value in [
        ("state_task_drift", "current_task_id", "T-9999"),
        ("state_gate_drift", "current_gate_id", "G-9999"),
        ("state_phase_drift", "current_phase", "S5-quality"),
    ]:
        r = root / f"r-{name}"
        write_resume_fixture(r)
        p = hrp.build_resume_payload(
            r, task_id="T-0110", gate_id="G-T-0110-DELIVERY",
            phase="S6-delivery", decision_type="gate_approval")
        _mutate_state(r, key, value)
        out["resume_failures"][name] = try_exc(
            hrp.resume_from_payload, p, r)
    task_removed = root / "r-task-removed"
    write_resume_fixture(task_removed)
    p = hrp.build_resume_payload(
        task_removed, task_id="T-0110", gate_id="G-T-0110-DELIVERY",
        phase="S6-delivery", decision_type="gate_approval")
    (task_removed / ".ai" / "task_graph.yaml").write_text(
        json.dumps({"tasks": []}), encoding="utf-8")
    out["resume_failures"]["task_removed"] = try_exc(
        hrp.resume_from_payload, p, task_removed)
    gate_removed = root / "r-gate-removed"
    write_resume_fixture(gate_removed)
    p = hrp.build_resume_payload(
        gate_removed, task_id="T-0110", gate_id="G-T-0110-DELIVERY",
        phase="S6-delivery", decision_type="gate_approval")
    (gate_removed / ".ai" / "gates.yaml").write_text(
        json.dumps({"gates": []}), encoding="utf-8")
    out["resume_failures"]["gate_removed"] = try_exc(
        hrp.resume_from_payload, p, gate_removed)
    gate_decided = root / "r-gate-decided"
    write_resume_fixture(gate_decided)
    p = hrp.build_resume_payload(
        gate_decided, task_id="T-0110", gate_id="G-T-0110-DELIVERY",
        phase="S6-delivery", decision_type="gate_approval")
    (gate_decided / ".ai" / "gates.yaml").write_text(json.dumps({
        "gates": [{"id": "G-T-0110-DELIVERY", "task_id": "T-0110",
                   "status": "approved"}]}), encoding="utf-8")
    out["resume_failures"]["gate_decided"] = try_exc(
        hrp.resume_from_payload, p, gate_decided)
    gate_rebound = root / "r-gate-rebound"
    write_resume_fixture(gate_rebound)
    p = hrp.build_resume_payload(
        gate_rebound, task_id="T-0110", gate_id="G-T-0110-DELIVERY",
        phase="S6-delivery", decision_type="gate_approval")
    (gate_rebound / ".ai" / "gates.yaml").write_text(json.dumps({
        "gates": [{"id": "G-T-0110-DELIVERY", "task_id": "T-OTHER",
                   "status": "pending"}]}), encoding="utf-8")
    out["resume_failures"]["gate_rebound"] = try_exc(
        hrp.resume_from_payload, p, gate_rebound)
    out["resume_failures"] = norm_paths(out["resume_failures"], root)

    # ── 渲染（固定包 → to_markdown / to_plain_text 全文逐字节）────────
    full = _make_fixture_packet()
    out["render_full"] = {
        "markdown": full.to_markdown(),
        "plain": full.to_plain_text(),
    }
    minimal = _make_fixture_packet(
        key_choices=[], risks=[], decision_required=None,
        evidence_summary="", who_reviewed=[], vetoes=[],
        what_changed="", expires_at="", related_experience="",
    )
    out["render_minimal"] = {
        "markdown": minimal.to_markdown(),
        "plain": minimal.to_plain_text(),
    }
    veto_packet = _make_fixture_packet(
        packet_type=hrp.PacketType.VETO_ESCALATION,
        key_choices=[], risks=[],
        decision_required=hrp.DecisionRequired(
            "How to resolve?", ["Accept", "Override"], "Accept", None),
    )
    out["render_veto"] = veto_packet.to_markdown()

    # ── 渲染辅助（_phase_label / _format_ts）──────────────────────────
    out["_phase_label"] = [
        hrp._phase_label(p) for p in [
            "S0-init", "S1-requirements", "S2-architecture",
            "S3-interface", "S4-implementation", "S5-quality",
            "S6-delivery", "S7-integration", "S8-functional-test",
            "S9-fix-optimize", "S10-performance", "S11-maintenance",
            "unknown-phase", "",
        ]
    ]
    out["_phase_label_none"] = try_exc(hrp._phase_label, None)
    out["_format_ts"] = [
        hrp._format_ts(ts) for ts in [
            "2026-08-03T14:30:00+00:00", "2026-08-03T14:30:00Z",
            "2026-08-03T14:30:00.123456+08:00", "2026-08-03",
            "", None, "not-a-date",
        ]
    ]

    # ── Builder（确定性归一化后快照）──────────────────────────────────
    artifacts = {
        "architecture.md": "模块化设计文档",
        "api-spec.md": "接口契约 v2",
    }
    review_results = {
        "quality-engineer": "通过",
        "security-engineer": "1 项中危",
    }
    quality_report = {
        "pass": True,
        "checks": ["consistency: ok", "coverage: ok"],
        "warnings": ["Possible SQL injection in login form (critical)"],
    }
    built_packet = hrp.HumanReviewPacketBuilder.from_phase_completion(
        "S6-delivery", "T-0110", artifacts, review_results, quality_report)
    out["builder_phase"] = norm_paths(_mark_packet_ids(_mark_timestamps(
        to_jsonable(asdict(built_packet)))), root)

    no_artifacts = hrp.HumanReviewPacketBuilder.from_phase_completion(
        "S2-architecture", "T-0200", {}, {}, {"passed": True, "checks": {}})
    out["builder_phase_empty"] = _mark_packet_ids(_mark_timestamps(
        to_jsonable(asdict(no_artifacts))))

    warns_str = hrp.HumanReviewPacketBuilder.from_phase_completion(
        "S4-implementation", "T-0300",
        {"m1.py": "模块一"}, {"r1": "ok"},
        {"pass": "3/5", "checks": ["a"]})
    out["builder_phase_pass_str"] = _mark_packet_ids(_mark_timestamps(
        to_jsonable(asdict(warns_str))))

    vetoes = [
        {"vetoed_by": "quality-engineer", "reason": "证据不完整", "phase": "S5-quality"},
        {"vetoed_by": "security-engineer", "reason": "依赖漏洞", "phase": "S5-quality"},
    ]
    veto_built = hrp.HumanReviewPacketBuilder.from_veto_escalation(
        vetoes, "T-0400")
    out["builder_veto"] = _mark_packet_ids(_mark_timestamps(
        to_jsonable(asdict(veto_built))))
    veto_empty = hrp.HumanReviewPacketBuilder.from_veto_escalation([], "T-0500")
    out["builder_veto_empty"] = _mark_packet_ids(_mark_timestamps(
        to_jsonable(asdict(veto_empty))))
    veto_raw = hrp.HumanReviewPacketBuilder.from_veto_escalation(
        ["plain string veto"], "T-0600")
    out["builder_veto_raw"] = _mark_packet_ids(_mark_timestamps(
        to_jsonable(asdict(veto_raw))))

    out["translate_technical_risk"] = {
        "sql_critical": to_jsonable(asdict(
            hrp.HumanReviewPacketBuilder.translate_technical_risk(
                "Possible SQL injection in login form (critical)"))),
        "xss_minor": to_jsonable(asdict(
            hrp.HumanReviewPacketBuilder.translate_technical_risk(
                "minor XSS in search results"))),
        "race_medium": to_jsonable(asdict(
            hrp.HumanReviewPacketBuilder.translate_technical_risk(
                "race condition in billing"))),
        "generic": to_jsonable(asdict(
            hrp.HumanReviewPacketBuilder.translate_technical_risk(
                "mystery failure mode"))),
        "truncated": to_jsonable(asdict(
            hrp.HumanReviewPacketBuilder.translate_technical_risk(
                "x" * 200))),
    }

    out["_extract_key_choices"] = {
        "architecture": to_jsonable([
            asdict(c) for c in hrp.HumanReviewPacketBuilder._extract_key_choices(
                "S2-architecture", {"doc.md": "设计文档"})]),
        "implementation": to_jsonable([
            asdict(c) for c in hrp.HumanReviewPacketBuilder._extract_key_choices(
                "S4-implementation", {"m.py": "模块"})]),
        "generic": to_jsonable([
            asdict(c) for c in hrp.HumanReviewPacketBuilder._extract_key_choices(
                "S6-delivery", {"r.md": "报告"})]),
        "empty": to_jsonable([
            asdict(c) for c in hrp.HumanReviewPacketBuilder._extract_key_choices(
                "S6-delivery", {})]),
    }

    out = norm_paths(out, root)
    return out


# ══════════════════════════════════════════════════════════════════════
# context_loader 固定夹具
# ══════════════════════════════════════════════════════════════════════

ROLE_CONTRACT = """\
role_id: quality-engineer
identity:
  title: 资深质量工程师
fixed_stance:
  - "我的职责是找问题，不是证明没问题"
responsibilities:
  - 设计测试策略
  - 审查证据链
prohibitions:
  - 禁止凭空断言
veto_power:
  - 质量门禁否决权
"""

THINKING_FRAMEWORK_MD = """\
# 思考框架

## 概述

### Step 1: 质量全局视角
先看整体再看局部。

### Step 2: 证据优先
先收集证据再下结论。

## 其他章节
不应出现在摘要中。
"""

INTERNAL_LOOP_MD = """\
# 内部 Loop

- 合同合规自检
- 门禁证据自查
"""

ARCH_DOC = """\
# 架构文档

## Quality Gate
质量门禁说明，覆盖测试策略。

## Deployment
部署说明。

## API Design
接口设计。
"""

SUMMARY_CORPUS = """\
## 背景
本任务 T-0101 在 S4-implementation 阶段完成支付网关 G-T-0101-PAYMENT 的集成。
上一轮评审结论为 REJECTED：证据链缺失 .ai/evidence/T-0101/gate-requirements.md。
本次补充单元测试并重新提交，状态为 APPROVED。
task_id: T-0101
决策点：是否批准进入 S5-quality 阶段。
"""

CITATION_TEXT = """\
参考 .ai/evidence/T-0088/context-compression/design.md 与
…/T-0088/approval-evidence.json 及 evidence/T-0088/final.md。
另见 .ai/evidence/T-0088/context-compression/design.md（重复路径）。
"""


def write_loader_fixture(root: Path, *, with_memories: bool = False,
                         memories_n: int = 3) -> None:
    """构建角色目录 + 架构文档 + 可选知识库。"""
    role_dir = root / "agents" / "quality-engineer"
    role_dir.mkdir(parents=True, exist_ok=True)
    (role_dir / "CONTRACT.yaml").write_text(ROLE_CONTRACT, encoding="utf-8")
    (role_dir / "THINKING_FRAMEWORK.md").write_text(
        THINKING_FRAMEWORK_MD, encoding="utf-8")
    (role_dir / "INTERNAL_LOOP.md").write_text(
        INTERNAL_LOOP_MD, encoding="utf-8")
    (root / "architecture.md").write_text(ARCH_DOC, encoding="utf-8")
    if with_memories:
        from loop_core.knowledge_store import put_entry
        for i in range(memories_n):
            put_entry(
                root,
                kind="lesson",
                source_type="gate",
                source_id=f"G-T-0100-REVIEW-{i}",
                task_id="T-0100",
                tags=["gate", "rejected", "evidence"],
                content=f"Rejection reason number {i} for the closeout review.",
                recorded_at=f"2026-07-0{i + 1}T01:00:00+00:00",
            )


def _write_readme_routing(root: Path, routing: dict) -> None:
    ai = root / ".ai"
    ai.mkdir(parents=True, exist_ok=True)
    body = "---\n" + json.dumps(routing, ensure_ascii=False) + "\n---\n# 文档路由\n"
    (ai / "README.md").write_text(body, encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════
# context_loader golden 捕获
# ══════════════════════════════════════════════════════════════════════


def capture_context_loader_golden(root: Path) -> dict[str, Any]:
    """context_loader 全量 golden 捕获（输出确定性 JSON 结构）。"""
    from loop_core import context_loader as cl  # noqa: F401 — 统一入口壳

    out: dict[str, Any] = {}

    # ── 模块级常量 / 枚举 ─────────────────────────────────────────────
    out["constants"] = {
        "LoadLevel_values": [lv.value for lv in cl.LoadLevel],
        "DEFAULT_BUDGET_TOKENS": cl.DEFAULT_BUDGET_TOKENS,
        "DEFAULT_TRIGGER_RATIO": cl.DEFAULT_TRIGGER_RATIO,
        "DEFAULT_MAX_SUMMARY_LEVELS": cl.DEFAULT_MAX_SUMMARY_LEVELS,
        "UNRESOLVED_MARKER": cl.UNRESOLVED_MARKER,
        "DEFAULT_MEMORY_LIMIT": cl.DEFAULT_MEMORY_LIMIT,
        "CITATION_MAX_CHARS": cl.CITATION_MAX_CHARS,
        "CITATION_LINE_CAP": cl.CITATION_LINE_CAP,
        "MINIMAL_MAX": cl.MINIMAL_MAX,
        "STANDARD_MAX": cl.STANDARD_MAX,
        "regex_patterns": {
            "_TASK_ID_RE": cl._TASK_ID_RE.pattern,
            "_GATE_ID_RE": cl._GATE_ID_RE.pattern,
            "_PHASE_RE": cl._PHASE_RE.pattern,
            "_DECISION_RE": cl._DECISION_RE.pattern,
            "_HEADING_RE": cl._HEADING_RE.pattern,
            "_KEY_FIELD_LINE_RE": cl._KEY_FIELD_LINE_RE.pattern,
            "_CITATION_TOKEN_RE": cl._CITATION_TOKEN_RE.pattern,
            "_SENTENCE_SPLIT_RE": cl._SENTENCE_SPLIT_RE.pattern,
            "_ABBREV_RE": cl._ABBREV_RE.pattern,
        },
        "signature_defaults": {
            # T-0104 硬约束：include_memories 默认必须保持 False
            "load_role_context": {
                "include_memories": cl.ContextLoader.load_role_context.__kwdefaults__["include_memories"],
                "memory_limit": cl.ContextLoader.load_role_context.__kwdefaults__["memory_limit"],
                "memory_task_id": cl.ContextLoader.load_role_context.__kwdefaults__["memory_task_id"],
                "budget_tokens": cl.ContextLoader.load_role_context.__kwdefaults__["budget_tokens"],
                "trigger_ratio": cl.ContextLoader.load_role_context.__kwdefaults__["trigger_ratio"],
                "max_levels": cl.ContextLoader.load_role_context.__kwdefaults__["max_levels"],
            },
            "load_for_role": {
                "include_memories": cl.ContextLoader.load_for_role.__kwdefaults__["include_memories"],
                "memory_limit": cl.ContextLoader.load_for_role.__kwdefaults__["memory_limit"],
                "memory_task_id": cl.ContextLoader.load_for_role.__kwdefaults__["memory_task_id"],
                "budget_tokens": cl.ContextLoader.load_for_role.__kwdefaults__["budget_tokens"],
                "trigger_ratio": cl.ContextLoader.load_for_role.__kwdefaults__["trigger_ratio"],
                "max_levels": cl.ContextLoader.load_for_role.__kwdefaults__["max_levels"],
            },
        },
    }

    # ── 摘要级别/行选择辅助（含边界）─────────────────────────────────
    out["_level_line_params"] = {lv: cl._level_line_params(lv)
                                 for lv in (1, 2, 3, 4, 0, -1)}
    out["_level_body_cap"] = {lv: cl._level_body_cap(lv)
                              for lv in (1, 2, 3, 4, 0)}
    body_lines = [
        "decision: APPROVED for the gate",
        "plain earliest line one",
        "another body line two",
        "decision review needed here",
        "plain line three",
        "plain line four",
        "plain line five",
    ]
    out["_select_body_lines"] = {
        "cap2": cl._select_body_lines(body_lines, 2),
        "cap4": cl._select_body_lines(body_lines, 4),
        "cap0": cl._select_body_lines(body_lines, 0),
        "cap10": cl._select_body_lines(body_lines, 10),
        "empty": cl._select_body_lines([], 3),
    }
    out["_find_citation_tokens"] = {
        "text": cl._find_citation_tokens(CITATION_TEXT),
        "empty": cl._find_citation_tokens("no citations here"),
    }
    long_path = ".ai/evidence/T-0088/context-compression/hierarchical-summary/final-design.md"
    out["_truncate_citation"] = {
        "short": cl._truncate_citation(".ai/evidence/T-0088/a.md"),
        "long": cl._truncate_citation(long_path),
        "edge": cl._truncate_citation(".ai", 5),
    }
    out["_split_sentences"] = {
        "cn": cl._split_sentences("第一句。第二句！第三句？"),
        "latin": cl._split_sentences("First sentence. Second sentence! Third?"),
        "abbrev": cl._split_sentences("See e.g. .ai/evidence/T-0088/a.md for details. Next."),
        "single": cl._split_sentences("No punctuation here"),
    }
    out["_truncate_line"] = {
        "short": cl._truncate_line("short line"),
        "long2": cl._truncate_line("word " * 40, max_chars=60, keep_sentences=2),
        "long1": cl._truncate_line("word " * 40, max_chars=30, keep_sentences=1),
        "cn": cl._truncate_line("汉" * 100, max_chars=50, keep_sentences=2),
    }

    # ── 字段提取 / 摘要 ───────────────────────────────────────────────
    out["extract_key_fields"] = {
        "corpus": cl.extract_key_fields(SUMMARY_CORPUS),
        "empty": cl.extract_key_fields(""),
        "gates_not_tasks": cl.extract_key_fields(
            "G-T-0088-REQUIREMENTS approved in S3"),
    }
    fields = cl.extract_key_fields(SUMMARY_CORPUS)
    out["_format_key_fields"] = {
        "level1": cl._format_key_fields(fields, 1),
        "level3": cl._format_key_fields(fields, 3),
        "empty": cl._format_key_fields(
            {"task_ids": [], "gate_ids": [], "phases": [], "decisions": []}, 2),
    }
    out["summarize_text"] = {
        "l1": cl.summarize_text(SUMMARY_CORPUS, level=1),
        "l2": cl.summarize_text(SUMMARY_CORPUS, level=2),
        "l3": cl.summarize_text(SUMMARY_CORPUS, level=3),
        "empty": cl.summarize_text(""),
        "citation": cl.summarize_text(CITATION_TEXT, level=1),
    }
    out["estimate_tokens"] = {
        "empty": cl.estimate_tokens(""),
        "latin": cl.estimate_tokens("hello world this is a test"),
        "cjk": cl.estimate_tokens("中文测试字符"),
        "mixed": cl.estimate_tokens("混合 english 文本 with 中文"),
        "none": cl.estimate_tokens(None),
    }

    # ── CitationResolver（唯一匹配 / 歧义 / 不存在 / 前缀丢失）─────────
    cite_root = root / "r-citations"
    cite_ai = cite_root / ".ai" / "evidence" / "T-0088"
    (cite_ai / "context-compression").mkdir(parents=True)
    (cite_ai / "approval-evidence.json").write_text("{}", encoding="utf-8")
    (cite_ai / "final.md").write_text("# f", encoding="utf-8")
    (cite_ai / "context-compression" / "design.md").write_text(
        "# d", encoding="utf-8")
    (cite_ai / "context-compression" / "hierarchical-summary.md").write_text(
        "# h", encoding="utf-8")
    resolver = cl.CitationResolver(cite_root)
    out["citation_resolver"] = {
        "exact": to_jsonable(asdict(resolver.resolve(
            ".ai/evidence/T-0088/context-compression/design.md"))),
        "prefix_dropped": to_jsonable(asdict(resolver.resolve(
            "evidence/T-0088/context-compression/design.md"))),
        "truncated": to_jsonable(asdict(resolver.resolve(
            "…/T-0088/context-compression/design.md"))),
        "bare_name": to_jsonable(asdict(resolver.resolve("final.md"))),
        "ambiguous": to_jsonable(asdict(resolver.resolve("design.md"))),
        "not_found": to_jsonable(asdict(resolver.resolve(
            ".ai/evidence/T-0088/nope.md"))),
        "empty": to_jsonable(asdict(resolver.resolve(""))),
        "no_suffix": to_jsonable(asdict(resolver.resolve("…/"))),
        "is_resolved": resolver.resolve("final.md").is_resolved,
    }
    out["citation_resolver"] = norm_paths(out["citation_resolver"], cite_root)
    # search_roots 自定义
    custom_resolver = cl.CitationResolver(
        cite_root, search_roots=[cite_ai / "context-compression"])
    out["citation_resolver_custom_roots"] = to_jsonable(asdict(
        custom_resolver.resolve("design.md")))
    out["citation_resolver_custom_roots"] = norm_paths(
        out["citation_resolver_custom_roots"], cite_root)

    # ── repair_truncated_references（T-0095 子串守卫）──────────────────
    repair_text = (
        "见 .ai/evidence/T-0088/context-compression/design.md 与 "
        "…/T-0088/approval-evidence.json，另见 evidence/T-0088/final.md。"
    )
    repaired, resolutions = cl.repair_truncated_references(
        repair_text, cite_root)
    out["repair_truncated_references"] = {
        "text": repaired,
        "resolutions": [to_jsonable(asdict(r)) for r in resolutions],
    }
    out["repair_truncated_references"] = norm_paths(
        out["repair_truncated_references"], cite_root)
    # 子串守卫：全路径与其前缀丢失变体同现
    guard_text = (
        ".ai/evidence/T-0088/context-compression/design.md 与 "
        "evidence/T-0088/context-compression/design.md"
    )
    guarded, guard_res = cl.repair_truncated_references(guard_text, cite_root)
    out["repair_guard"] = {
        "text": guarded,
        "statuses": [r.status for r in guard_res],
    }
    out["repair_guard"] = norm_paths(out["repair_guard"], cite_root)
    # 无法恢复 → UNRESOLVED 包裹
    unres, unres_res = cl.repair_truncated_references(
        "参考 evidence/T-9999/missing-file.md", cite_root)
    out["repair_unresolved"] = {
        "text": unres,
        "statuses": [r.status for r in unres_res],
    }

    # ── ContextCompressor（触发/不触发/多级/参数校验/引用修复）────────
    compressor = cl.ContextCompressor(
        budget_tokens=2600, trigger_ratio=0.7, max_levels=2)
    out["compressor"] = {
        "under_budget": to_jsonable(asdict(compressor.compress_if_needed(
            "short text"))),
        "over_budget_l1": to_jsonable(asdict(
            cl.ContextCompressor(budget_tokens=50, trigger_ratio=1.0,
                                 max_levels=1).compress_if_needed(
                SUMMARY_CORPUS))),
        "over_budget_l2": to_jsonable(asdict(compressor.compress_if_needed(
            SUMMARY_CORPUS))),
        "overrides": to_jsonable(asdict(compressor.compress_if_needed(
            SUMMARY_CORPUS, budget_tokens=40, trigger_ratio=1.0,
            max_levels=3))),
        "invalid_budget": try_exc(compressor.compress_if_needed, "x",
                                  budget_tokens=0),
        "invalid_ratio": try_exc(compressor.compress_if_needed, "x",
                                 trigger_ratio=1.5),
        "invalid_levels": try_exc(compressor.compress_if_needed, "x",
                                  max_levels=0),
        "with_citation_repair": to_jsonable(asdict(
            cl.ContextCompressor(
                budget_tokens=60, trigger_ratio=1.0, max_levels=1,
                project_root=cite_root).compress_if_needed(CITATION_TEXT))),
    }
    out["compressor"]["with_citation_repair"] = norm_paths(
        out["compressor"]["with_citation_repair"], cite_root)
    out["_validate_budget_params"] = {
        "ok": try_exc(cl._validate_budget_params, 100, 0.7, 2),
        "bad_budget": try_exc(cl._validate_budget_params, 0, 0.7, 2),
        "bad_budget_type": try_exc(cl._validate_budget_params, 1.5, 0.7, 2),
        "bad_ratio_low": try_exc(cl._validate_budget_params, 100, 0.0, 2),
        "bad_ratio_high": try_exc(cl._validate_budget_params, 100, 1.1, 2),
        "bad_levels": try_exc(cl._validate_budget_params, 100, 0.7, 0),
    }

    # ── 复杂度 → 加载级别 ─────────────────────────────────────────────
    out["_complexity_to_level"] = {
        c: cl._complexity_to_level(c).value
        for c in (0.0, 0.29, 0.3, 0.5, 0.59, 0.6, 0.61, 0.99, 1.0)
    }

    # ── ContextLoader.load_role_context（各级别 + 失败路径）────────────
    ok_root = root / "r-loader"
    write_loader_fixture(ok_root)
    loader = cl.ContextLoader(ok_root)
    for lvl, cx in [("minimal", 0.1), ("standard", 0.5), ("full", 0.9)]:
        ctx = loader.load_role_context("quality-engineer", complexity=cx)
        out[f"load_{lvl}"] = {
            "level": ctx.level.value,
            "estimated_tokens": ctx.estimated_tokens,
            "loaded_sections": ctx.loaded_sections,
            "system_prompt": ctx.system_prompt,
            "compression": None if ctx.compression is None else to_jsonable(
                asdict(ctx.compression)),
        }
    out["load_failures"] = {
        "missing_role": try_exc(
            loader.load_role_context, "ghost-role", complexity=0.5),
        "missing_contract": try_exc(
            cl.ContextLoader(root / "r-no-contract").load_role_context,
            "quality-engineer", complexity=0.5),
        "not_mapping_contract": try_exc(
            cl.ContextLoader(root / "r-bad-contract").load_role_context,
            "quality-engineer", complexity=0.5),
    }
    no_contract = root / "r-no-contract"
    (no_contract / "agents" / "quality-engineer").mkdir(parents=True)
    bad_contract = root / "r-bad-contract"
    bd = bad_contract / "agents" / "quality-engineer"
    bd.mkdir(parents=True)
    (bd / "CONTRACT.yaml").write_text("- 1\n- 2\n", encoding="utf-8")
    out["load_failures"] = norm_paths(out["load_failures"], root)

    # 预算压缩生效路径（load_role_context + budget）
    compressed_ctx = loader.load_role_context(
        "quality-engineer", complexity=0.9,
        budget_tokens=100, trigger_ratio=1.0, max_levels=1)
    out["load_budget_compressed"] = {
        "level": compressed_ctx.level.value,
        "system_prompt": compressed_ctx.system_prompt,
        "compression": to_jsonable(asdict(compressed_ctx.compression)),
        "loaded_sections": compressed_ctx.loaded_sections,
    }

    # ── D3 记忆注入：默认 False 保持（含损坏存储 fail-closed 语义）────
    mem_root = root / "r-mem"
    write_loader_fixture(mem_root, with_memories=True, memories_n=3)
    mem_loader = cl.ContextLoader(mem_root)
    default_ctx = mem_loader.load_role_context("quality-engineer", complexity=0.9)
    off_ctx = mem_loader.load_role_context(
        "quality-engineer", complexity=0.9, include_memories=False)
    on_ctx = mem_loader.load_role_context(
        "quality-engineer", complexity=0.9, include_memories=True,
        memory_limit=5)
    limited_ctx = mem_loader.load_role_context(
        "quality-engineer", complexity=0.9, include_memories=True,
        memory_limit=2)
    filtered_ctx = mem_loader.load_role_context(
        "quality-engineer", complexity=0.9, include_memories=True,
        memory_limit=5, memory_task_id="T-0100")
    out["memory_injection"] = {
        "default_unchanged": {
            "same_as_off": default_ctx.system_prompt == off_ctx.system_prompt,
            "no_memory_section": "Related Memories"
            not in default_ctx.system_prompt,
            "loaded_sections": default_ctx.loaded_sections,
        },
        "on": {
            "has_section": "## 相关经验（Related Memories）" in on_ctx.system_prompt,
            "recalled": "[memories: 3 recalled]" in on_ctx.loaded_sections,
            "section": on_ctx.system_prompt.split("\n\n")[-1],
        },
        "limited2": {
            "recalled": "[memories: 2 recalled]" in limited_ctx.loaded_sections,
            "bullets": limited_ctx.system_prompt.count("\n- ("),
        },
        "task_filtered": {
            "recalled": "[memories: 3 recalled]" in filtered_ctx.loaded_sections,
        },
    }
    corrupt_mem = root / "r-mem-corrupt"
    write_loader_fixture(corrupt_mem, with_memories=True, memories_n=1)
    from loop_core.knowledge_store import knowledge_path as _kp
    corrupt_store = _kp(corrupt_mem)
    corrupt_store.write_text("{corrupt", encoding="utf-8")
    corrupt_loader = cl.ContextLoader(corrupt_mem)
    corrupt_default_ctx = corrupt_loader.load_role_context(
        "quality-engineer", complexity=0.9)
    out["memory_injection"]["corrupt_store_default_off"] = {
        "ok": True,
        "prompt_matches_pristine": (
            corrupt_default_ctx.system_prompt == default_ctx.system_prompt),
        "no_memory_section": "Related Memories"
        not in corrupt_default_ctx.system_prompt,
    }
    out["memory_injection"]["corrupt_store_on_fail_closed"] = try_exc(
        corrupt_loader.load_role_context, "quality-engineer", complexity=0.9,
        include_memories=True)

    # ── 文档索引 / 节加载 ─────────────────────────────────────────────
    idx = loader.build_document_index(str(ok_root / "architecture.md"))
    out["build_document_index"] = {
        "doc_path": idx.doc_path,
        "sections": idx.sections,
        "total_lines": idx.total_lines,
    }
    out["build_document_index"] = norm_paths(
        out["build_document_index"], ok_root)
    out["load_document_section"] = {
        "found": loader.load_document_section(
            str(ok_root / "architecture.md"), "Quality Gate"),
        "missing": loader.load_document_section(
            str(ok_root / "architecture.md"), "Nonexistent"),
    }
    out["doc_failures"] = {
        "missing_doc": try_exc(loader.build_document_index, "no-such-file.md"),
    }
    empty_doc = root / "r-empty-doc"
    empty_doc.mkdir(parents=True)
    (empty_doc / "empty.md").write_text("", encoding="utf-8")
    empty_idx = cl.ContextLoader(empty_doc).build_document_index(
        str(empty_doc / "empty.md"))
    out["doc_failures"]["empty_doc"] = {
        "sections": empty_idx.sections,
        "total_lines": empty_idx.total_lines,
    }
    subhead_doc = root / "r-subhead"
    subhead_doc.mkdir(parents=True)
    (subhead_doc / "d.md").write_text(
        "## H1\n### H1.1\n## H2\n", encoding="utf-8")
    sub_idx = cl.ContextLoader(subhead_doc).build_document_index(
        str(subhead_doc / "d.md"))
    out["doc_failures"]["subheading_not_section"] = {
        "sections": sub_idx.sections,
        "total_lines": sub_idx.total_lines,
    }

    # ── load_for_role（路由表 / 遗留启发 / 首 3 节兜底）────────────────
    routed_root = root / "r-routed"
    write_loader_fixture(routed_root)
    _write_readme_routing(routed_root, {
        "section_routing": {
            "quality-engineer": ["quality", "gate"],
            "default": ["design"],
        }
    })
    routed_loader = cl.ContextLoader(routed_root)
    routed_ctx = routed_loader.load_for_role(
        "quality-engineer", str(routed_root / "architecture.md"),
        complexity=0.9)
    out["load_for_role_routed"] = {
        "sections": [s for s in routed_ctx.loaded_sections
                     if "architecture.md" in s],
        "prompt_has_gate": "Quality Gate" in routed_ctx.system_prompt,
        "prompt_has_deployment": "Deployment" in routed_ctx.system_prompt,
        "estimated_tokens": routed_ctx.estimated_tokens,
    }
    legacy_loader = cl.ContextLoader(ok_root)
    legacy_ctx = legacy_loader.load_for_role(
        "quality-engineer", str(ok_root / "architecture.md"), complexity=0.9)
    out["load_for_role_legacy"] = {
        "sections": [s for s in legacy_ctx.loaded_sections
                     if "architecture.md" in s],
        "prompt_has_gate": "Quality Gate" in legacy_ctx.system_prompt,
        "estimated_tokens": legacy_ctx.estimated_tokens,
    }
    nobudget = routed_loader.load_for_role(
        "quality-engineer", str(routed_root / "architecture.md"),
        complexity=0.9, budget_tokens=50, trigger_ratio=1.0, max_levels=1)
    out["load_for_role_budget"] = {
        "compression": to_jsonable(asdict(nobudget.compression))
        if nobudget.compression else None,
    }

    # ── 内部辅助（_parse_yaml / 契约提取 / 框架标题）──────────────────
    out["_parse_yaml"] = {
        "yaml": cl._parse_yaml("a: 1\nb: [1, 2]\n"),
        "json": cl._parse_yaml('{"a": 1}'),
        "garbage": cl._parse_yaml("::: not parseable"),
    }
    contract = {
        "fixed_stance": ["A", "B"],
        "identity": {"title": "T"},
        "responsibilities": ["r1", "r2"],
        "prohibitions": ["p1"],
        "veto_power": ["v1", "v2"],
    }
    out["_extract_fixed_stance"] = {
        "list": cl._extract_fixed_stance(contract, "role-x"),
        "missing": cl._extract_fixed_stance({}, "role-x"),
        "identity_fallback": cl._extract_fixed_stance(
            {"identity": {"title": "自定义"}}, "role-x"),
        "identity_not_dict": cl._extract_fixed_stance(
            {"identity": "x"}, "role-x"),
    }
    out["_extract_contract_extras"] = {
        "all": cl._extract_contract_extras(contract),
        "none": cl._extract_contract_extras({}),
        "partial": cl._extract_contract_extras(
            {"responsibilities": ["only"]}),
        "not_lists": cl._extract_contract_extras(
            {"responsibilities": "x", "prohibitions": 1}),
    }
    fw_root = root / "r-fw"
    fw_root.mkdir(parents=True)
    (fw_root / "fw.md").write_text(
        "## Intro\n### Step 1: One\n### Step 2: Two\n## Later\n### Step 3: Three\n",
        encoding="utf-8")
    out["_extract_framework_titles"] = {
        "with_steps": cl._extract_framework_titles(fw_root / "fw.md"),
        "no_steps": None,  # 下方用真实文件覆盖
    }
    (fw_root / "nosteps.md").write_text(
        "## A\n### Not a step\n## B\n", encoding="utf-8")
    out["_extract_framework_titles"]["no_steps"] = (
        cl._extract_framework_titles(fw_root / "nosteps.md"))

    # ── 节选择（路由表 / 遗留 / 兜底 / 空索引）────────────────────────
    out["_select_relevant_sections"] = {
        "routed_match": cl._select_relevant_sections(
            "quality-engineer", idx, project_root=routed_root),
        "routed_default": cl._select_relevant_sections(
            "product-manager", idx, project_root=routed_root),
        "routed_no_keywords": cl._select_relevant_sections(
            "developer", idx, project_root=routed_root),
        "legacy_match": cl._select_relevant_sections(
            "quality-engineer", idx),
        "legacy_first3": cl._select_relevant_sections(
            "unknown-role", idx),
        "empty_index": cl._select_relevant_sections(
            "quality-engineer", cl.DocumentIndex("x.md")),
    }
    # 路由表缺失 → 遗留 + 警告（project_root 给定）
    out["_select_relevant_sections"]["routed_missing_legacy"] = (
        cl._select_relevant_sections(
            "quality-engineer", idx, project_root=ok_root))

    # ── front-matter / 路由表加载（含缓存语义）────────────────────────
    out["_parse_front_matter_yaml"] = {
        "valid": cl._parse_front_matter_yaml(
            "---\nkey: value\n---\nbody"),
        "no_front": cl._parse_front_matter_yaml("plain text"),
        "unclosed": cl._parse_front_matter_yaml("---\nkey: value\nbody"),
        "json_block": cl._parse_front_matter_yaml('---\n{"a": 1}\n---\n'),
        "garbage": cl._parse_front_matter_yaml("---\n::: bad\n---\n"),
    }
    out["_load_section_routing"] = {
        "valid": cl._load_section_routing(routed_root),
        "missing": cl._load_section_routing(ok_root),
        "none_root": cl._load_section_routing(None),
        "invalid_readme": cl._load_section_routing(root / "r-invalid"),
    }
    invalid_root = root / "r-invalid"
    (invalid_root / ".ai").mkdir(parents=True)
    (invalid_root / ".ai" / "README.md").write_text(
        "---\n::: bad yaml\n---\n", encoding="utf-8")
    # 缓存语义：第二次调用命中 _ROUTING_CACHE（值相同）
    out["_load_section_routing"]["cached_second_call"] = (
        cl._load_section_routing(routed_root))

    out = norm_paths(out, root)
    return out
