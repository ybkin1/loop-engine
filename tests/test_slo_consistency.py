"""T-0100 (F-05): SLO 口径统一 + NOT_VERIFIED 语义细化。

- AC-04a: release_fee 计算收敛为 governance_metrics.release_fee_consumption
  单一函数（compute_error_budget 与 slo_gate 共用）—— 相同输入下
  build_report(...).budget 与 check_slo_gate(...).budget 输出一致。
- AC-04b: 未接线数据源（wave-2 ledger：phase_transitions/guard_decisions/
  runtime-events）逐项 advisory 标注；computed 项按实值判定；不因部分源
  未接线而整体 NOT_VERIFIED。
- AC-04c: fail-closed 语义保持 —— 已接线源（gates/task_graph/guard-events）
  缺失仍整体 NOT_VERIFIED（metrics）与 BLOCK（gate）；SKIP/advisory 均附原因。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from loop_core.governance_metrics import (
    NOT_AVAILABLE,
    REPORT_NOT_VERIFIED,
    REPORT_PASS,
    WAVE2_UNWIRED_SOURCES,
    build_report,
    compute_error_budget,
    release_fee_consumption,
)
from loop_core.slo_gate import (
    GATE_DECISION_BLOCK,
    GATE_DECISION_PASS,
    check_slo_gate,
)


# ── Fixture writers（与 test_governance_metrics / test_slo_gate 同风格）────


def _write_gates(root: Path, gates: list[dict]) -> Path:
    path = root / ".ai" / "gates.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "schema_version: 1\n" + "gates:\n"
        + "\n".join(f"- {json.dumps(g, ensure_ascii=False)}" for g in gates),
        encoding="utf-8",
    )
    return path


def _write_tasks(root: Path, tasks: list[dict]) -> Path:
    path = root / ".ai" / "task_graph.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "schema_version: 1\n" + "tasks:\n"
        + "\n".join(f"- {json.dumps(t, ensure_ascii=False)}" for t in tasks),
        encoding="utf-8",
    )
    return path


def _write_guard_events(root: Path, events: list[dict]) -> Path:
    path = root / ".ai" / "evidence" / "observability" / "guard-events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n",
        encoding="utf-8",
    )
    return path


def _write_executions(root: Path, records: list[dict]) -> Path:
    path = root / ".ai" / "ledger" / "executions.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
        encoding="utf-8",
    )
    return path


def _gate(gate_id: str, task_id: str = "T-X", status: str = "approved",
          requested: str | None = None, recorded: str | None = None,
          evidence: str | None = None) -> dict:
    gate: dict = {
        "id": gate_id, "task_id": task_id, "gate_type": "user-approval",
        "status": status, "decision": status,
    }
    if requested:
        gate["requested_at"] = requested
    if recorded:
        gate["recorded_at"] = recorded
    if evidence:
        gate["evidence"] = evidence
    return gate


def _pass_event(event_id: str) -> dict:
    return {
        "event_id": event_id, "guard_id": "g_alpha", "capability_id": None,
        "check_type": "death", "result": "PASS", "duration_ms": 5.0,
        "failure_reason": None, "timestamp": "2026-08-01T00:00:00+00:00",
        "source": "registry:t",
    }


@pytest.fixture
def wired_clean_project(tmp_path: Path) -> Path:
    """全部已接线源就绪（gates/task_graph/guard-events），未接线源缺失。

    各阶段均有 decided gate → 全部已接线 SLI 可 computed → 新语义下
    报告 PASS + advisories（不再整体 NOT_VERIFIED）。"""
    gates = [
        _gate(f"G-T-4000-{phase}-{i}", f"T-4{i}", requested="2026-07-01T09:00:00+08:00",
              recorded="2026-07-01T10:00:00+08:00", evidence=".ai/evidence/T-4/a.md")
        for i, phase in enumerate(["REQUIREMENTS", "REQUIREMENTS", "ARCHITECTURE",
                                   "ARCHITECTURE", "IMPLEMENTATION", "QUALITY",
                                   "DELIVERY"])
    ]
    tasks = [
        {"id": f"T-4{i}", "status": "completed", "phase": "S6-delivery",
         "created_at": "2026-07-01T00:00:00+08:00",
         "updated_at": "2026-07-03T00:00:00+08:00"}
        for i in range(7)
    ]
    events = [_pass_event("e1"), _pass_event("e2")]
    _write_gates(tmp_path, gates)
    _write_tasks(tmp_path, tasks)
    _write_guard_events(tmp_path, events)
    _write_executions(tmp_path, [
        {"execution_id": "x1", "status": "COMPLETED",
         "launched_at": "2026-07-01T00:00:00+00:00",
         "completed_at": "2026-07-01T00:05:00+00:00"},
    ])
    return tmp_path


# ── AC-04a: release_fee 口径一致 ─────────────────────────────────────────


class TestReleaseFeeConsistency:
    def test_release_fee_single_shared_function(self):
        """compute_error_budget 的 release 费用经 release_fee_consumption 计算。"""
        budget = compute_error_budget([], release_fee_units=5.0, releases=3)
        assert budget["release_consumption"] == release_fee_consumption(5.0, 3)
        assert budget["release_consumption"] == 15.0
        assert budget["consumed_units"] == 15.0
        # 0 次发布 → 不计费
        assert release_fee_consumption(5.0, 0) == 0.0

    def test_metrics_and_gate_budget_identical_for_same_inputs(
            self, wired_clean_project: Path):
        """build_report 与 check_slo_gate 在相同 (root, releases) 下预算一致。

        T-0099 发现的口径差异（metrics consumed 0.0 vs slo_gate 5.0）根因是
        调用点默认值不同（metrics CLI 默认 --releases 0，release.py check 传
        releases=1）；同一函数 + 相同输入下输出必须逐字段一致。"""
        for releases in (0, 1, 3):
            report_budget = build_report(
                wired_clean_project, releases=releases).budget
            gate_result = check_slo_gate(
                wired_clean_project, releases=releases)
            gate_budget = gate_result.budget
            assert gate_budget is not None
            for key in ("status", "consumed_units", "remaining_units",
                        "release_consumption", "breach_consumption",
                        "release_count", "total_units"):
                assert report_budget[key] == gate_budget[key], (
                    f"releases={releases} 口径不一致: {key} "
                    f"metrics={report_budget[key]} gate={gate_budget[key]}"
                )

    def test_gate_and_metrics_release_fee_agree(self, wired_clean_project: Path):
        report = build_report(wired_clean_project, releases=1)
        assert report.budget["release_consumption"] == 5.0
        assert report.budget["consumed_units"] == 5.0
        gate = check_slo_gate(wired_clean_project, releases=1)
        assert gate.budget["release_consumption"] == 5.0
        assert gate.budget["consumed_units"] == 5.0


# ── AC-04b: 未接线源 advisory 语义 ───────────────────────────────────────


class TestUnwiredSourceAdvisory:
    def test_unwired_sources_do_not_demote_status(self, wired_clean_project: Path):
        """已接线源完整 + 未接线源缺失 → status=PASS + 逐项 advisory。"""
        report = build_report(wired_clean_project)
        assert report.status == REPORT_PASS, (
            "未接线源（wave-2）缺失不得再导致整体 NOT_VERIFIED"
        )
        assert report.advisories, "未接线源应逐项标注 advisory"
        for rel in (".ai/ledger/phase_transitions.jsonl",
                    ".ai/ledger/guard_decisions.jsonl",
                    ".ai/ledger/runtime-events.jsonl"):
            assert any(Path(rel).name in a for a in report.advisories), rel
        # 汇总说明：部分源未接线，computed 项正常判定
        assert any("未接线" in n for n in report.notes)

    def test_unwired_sli_results_marked_advisory(self, wired_clean_project: Path):
        report = build_report(wired_clean_project)
        by_id = {r["sli_id"]: r for r in report.sli_eval}
        # 未接线源驱动的 SLI：NOT_AVAILABLE + advisory=True
        for sli_id in ("guard_block_rate", "drift_event_rate",
                       "delta_quality_pass_rate", "evidence_regeneration_rate",
                       "defect_fail_verdict_rate", "ac_invest_rate"):
            assert by_id[sli_id]["status"] == NOT_AVAILABLE
            assert by_id[sli_id]["advisory"] is True, sli_id
        # 已接线 SLI 正常 computed（按实值判定）
        assert by_id["req_gate_rejection_rate"]["status"] == "computed"
        assert by_id["guard_anomaly_rate"]["status"] == "computed"
        assert by_id["guard_anomaly_rate"]["advisory"] is False

    def test_wired_source_missing_still_not_verified(self, tmp_path: Path):
        """fail-closed 保持：已接线源（gates）缺失 → 仍 NOT_VERIFIED。"""
        _write_tasks(tmp_path, [{"id": "T-1", "status": "completed",
                                 "phase": "S6-delivery",
                                 "created_at": "2026-07-01T00:00:00+08:00",
                                 "updated_at": "2026-07-03T00:00:00+08:00"}])
        _write_guard_events(tmp_path, [_pass_event("e1")])
        report = build_report(tmp_path)
        assert report.status == REPORT_NOT_VERIFIED
        assert any("gates" in m for m in report.missing)

    def test_unparseable_wired_source_still_not_verified(self, tmp_path: Path):
        _write_gates(tmp_path, [_gate("G-T-4100-REQUIREMENTS")])
        (tmp_path / ".ai" / "gates.yaml").write_text("gates: [unclosed", encoding="utf-8")
        _write_tasks(tmp_path, [{"id": "T-1", "status": "completed",
                                 "phase": "S6-delivery",
                                 "created_at": "2026-07-01T00:00:00+08:00",
                                 "updated_at": "2026-07-03T00:00:00+08:00"}])
        _write_guard_events(tmp_path, [_pass_event("e1")])
        report = build_report(tmp_path)
        assert report.status == REPORT_NOT_VERIFIED

    def test_gate_fail_closed_semantics_unchanged(self, wired_clean_project: Path,
                                                  tmp_path: Path):
        """AC-07：SLO 门禁 fail-closed 语义不被弱化 ——
        已接线源缺失 → BLOCK（数据不足）；健康预算 → PASS（不因未接线源阻断）。"""
        assert check_slo_gate(wired_clean_project).decision == GATE_DECISION_PASS
        # 未接线源本来就是 gate 非输入（wave-2 项），不阻断 —— 语义不变
        assert check_slo_gate(wired_clean_project).missing == []
        # 已接线源缺失 → fail-closed BLOCK（原语义；独立空目录避免共享 fixture）
        empty_root = tmp_path / "empty"
        empty_root.mkdir()
        result = check_slo_gate(empty_root)
        assert result.decision == GATE_DECISION_BLOCK
        assert any("task graph" in m for m in result.missing)

    def test_unwired_source_constants_complete(self):
        """WAVE2_UNWIRED_SOURCES 覆盖 REPORT_SOURCE_FILES 中的 wave-2 三项。"""
        assert WAVE2_UNWIRED_SOURCES == {
            "phase_transitions.jsonl", "guard_decisions.jsonl", "runtime-events.jsonl",
        }

    def test_report_json_contains_advisories(self, wired_clean_project: Path):
        payload = build_report(wired_clean_project).to_dict()
        assert isinstance(payload["advisories"], list)
        assert payload["advisories"], "JSON 报告必须携带 advisories"
        assert payload["status"] == REPORT_PASS
        assert "missing" in payload
