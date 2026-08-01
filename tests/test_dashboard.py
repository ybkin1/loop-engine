"""T-0094 D4 AC-01..AC-04: AutoPlan dashboard visualization layer.

Covers:
- AC-01: task graph view — nodes (task_id/title/status/phase), dependency
  edges (explicit `edges` + `depends_on`), status summary, correct
  topological (dependency-chain) order; missing source renders
  NOT_AVAILABLE (never guessed).
- AC-02: gate view — pending/approved/rejected statistics plus decision
  records (gate_id / task / decision / approval_actor / recorded_at).
- AC-03: metrics + guard health view — error budget status, key DORA metric
  items from metrics-report.json (NOT_AVAILABLE passthrough), and
  guard-events.jsonl statistics (total / failures / avg duration).
- AC-04: snapshot report — text (markdown) + self-contained HTML (inline CSS,
  no JS, no external links); data sources are byte-identical (sha256) before
  and after snapshot generation (read-only proof).

Red line: the four data sources (task_graph.yaml / gates.yaml /
metrics-report.json / guard-events.jsonl) are never modified by the
dashboard — proven by the hash test and by writing snapshots only to
temporary directories in tests.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from loop_core.dashboard_views import (
    NOT_AVAILABLE,
    DashboardViews,
    write_snapshot_files,
)

ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT / "tools"
OBSERVABILITY_DIR = ROOT / ".ai" / "evidence" / "observability"

SOURCE_FILES = (
    ".ai/task_graph.yaml",
    ".ai/gates.yaml",
    ".ai/evidence/observability/metrics-report.json",
    ".ai/evidence/observability/guard-events.jsonl",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── Fixture writers ──────────────────────────────────────────────────────


def _write_task_graph(root: Path, tasks: list[dict], edges: list[dict] | None = None) -> Path:
    path = root / ".ai" / "task_graph.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = ["schema_version: 1", "tasks:"]
    for t in tasks:
        body.append("- " + json.dumps(t, ensure_ascii=False))
    if edges:
        body.append("edges:")
        for e in edges:
            body.append("- " + json.dumps(e, ensure_ascii=False))
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    return path


def _write_gates(root: Path, gates: list[dict]) -> Path:
    path = root / ".ai" / "gates.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = ["schema_version: 1", "gates:"]
    for g in gates:
        body.append("- " + json.dumps(g, ensure_ascii=False))
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    return path


def _write_metrics_report(root: Path, doc: dict) -> Path:
    path = root / ".ai" / "evidence" / "observability" / "metrics-report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return path


def _write_guard_events(root: Path, events: list[dict]) -> Path:
    path = root / ".ai" / "evidence" / "observability" / "guard-events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n",
        encoding="utf-8",
    )
    return path


def _fixture_root(tmp_path: Path) -> Path:
    """A complete fixture project root with all four data sources."""
    root = tmp_path / "project"
    _write_task_graph(root, [
        {"id": "T-100", "title": "First task", "status": "completed", "phase": "S1-requirements"},
        {"id": "T-101", "title": "Second task", "status": "in_progress", "phase": "S2-architecture",
         "depends_on": "T-100"},
        {"id": "T-102", "title": "Third task", "status": "pending", "phase": "S3-interface",
         "depends_on": ["T-101"]},
        {"id": "T-103", "title": "Leaf task", "status": "completed", "phase": "S4-implementation"},
    ], edges=[{"from": "T-103", "to": "T-102"}])
    _write_gates(root, [
        {"id": "G-1-PENDING", "task_id": "T-1", "gate_type": "user-approval", "status": "pending"},
        {"id": "G-2-APPROVED", "task_id": "T-2", "gate_type": "user-approval",
         "status": "approved", "decision": "approved", "approval_actor": "user",
         "recorded_at": "2026-07-01T10:00:00+08:00"},
        {"id": "G-3-REJECTED", "task_id": "T-3", "gate_type": "user-review",
         "status": "rejected", "decision": "rejected", "approval_actor": "user",
         "recorded_at": "2026-07-02T10:00:00+08:00"},
        {"id": "G-4-APPROVED-NO-TS", "task_id": "T-2", "gate_type": "user-approval",
         "status": "approved", "decision": "approved", "approval_actor": "user"},
    ])
    _write_metrics_report(root, {
        "status": "NOT_VERIFIED",
        "binding": {"task_id": "T-0090", "git_commit": "abc123", "timestamp": "2026-08-01T00:00:00+00:00"},
        "window": {"start": "2026-07-01", "end": "2026-08-01"},
        "error_budget": {"status": "HEALTHY", "total_units": 100.0,
                         "remaining_units": 100.0, "consumed_units": 0.0},
        "dora_metrics": {
            "gate_rejection_rate": {"status": "computed", "value": 0.0,
                                    "basis": "rejected / (approved + rejected)"},
            "gate_decision_coverage": {"status": "computed", "value": 0.5,
                                       "basis": "decided with evidence / decided"},
            "approval_latency": {"status": "computed",
                                 "value": {"p95_hours": 0.476, "mean_hours": 0.123},
                                 "basis": "requested_at -> recorded_at"},
            "task_cycle_time": {"status": "computed",
                                "value": {"mean_days": 0.084, "count": 3},
                                "basis": "created_at -> updated_at"},
            "phase_dwell_time": {"status": NOT_AVAILABLE, "value": NOT_AVAILABLE,
                                 "reason": "phase_transitions.jsonl absent"},
        },
    })
    _write_guard_events(root, [
        {"event_id": "e1", "guard_id": "bash_content_guard", "check_type": "health",
         "result": "PASS", "duration_ms": 100.0, "timestamp": "2026-08-01T00:00:01+00:00"},
        {"event_id": "e2", "guard_id": "bash_content_guard", "check_type": "health",
         "result": "PASS", "duration_ms": 200.0, "timestamp": "2026-08-01T00:00:02+00:00"},
        {"event_id": "e3", "guard_id": "gate_guard", "check_type": "death",
         "result": "PASS", "duration_ms": 300.0, "timestamp": "2026-08-01T00:00:03+00:00"},
        {"event_id": "e4", "guard_id": "content_guard", "check_type": "health",
         "result": "FAIL", "duration_ms": 400.0, "failure_reason": "blocked",
         "timestamp": "2026-08-01T00:00:04+00:00"},
    ])
    return root


# ── AC-01: task graph view ───────────────────────────────────────────────


class TestTaskGraphView:
    def test_nodes_edges_and_status_summary(self, tmp_path):
        root = _fixture_root(tmp_path)
        view = DashboardViews(root).task_graph_view()

        assert view["status"] == "available"
        ids = [n["task_id"] for n in view["nodes"]]
        assert ids == ["T-100", "T-101", "T-102", "T-103"]
        by_id = {n["task_id"]: n for n in view["nodes"]}
        assert by_id["T-101"]["title"] == "Second task"
        assert by_id["T-101"]["status"] == "in_progress"
        assert by_id["T-101"]["phase"] == "S2-architecture"

        # edges: explicit `edges` list merged with per-task `depends_on`
        edges = {(e["from"], e["to"]) for e in view["edges"]}
        assert ("T-100", "T-101") in edges      # depends_on (scalar)
        assert ("T-101", "T-102") in edges      # depends_on (list)
        assert ("T-103", "T-102") in edges      # explicit edges list
        assert len(edges) == 3

        s = view["summary"]
        assert s["total"] == 4
        assert s["completed"] == 2
        assert s["in_progress"] == 1
        assert s["pending"] == 1
        assert s["other"] == 0
        assert s["by_status"] == {"completed": 2, "in_progress": 1, "pending": 1}

    def test_topological_order_follows_dependency_chain(self, tmp_path):
        root = _fixture_root(tmp_path)
        view = DashboardViews(root).task_graph_view()

        order = view["topological_order"]
        assert view["unresolved_tasks"] == []
        # dependency chain T-100 -> T-101 -> T-102 must appear in that order
        assert order.index("T-100") < order.index("T-101") < order.index("T-102")
        # leaf T-103 must precede its dependent T-102
        assert order.index("T-103") < order.index("T-102")
        # ordered_nodes follow the same topological order
        node_order = [n["task_id"] for n in view["ordered_nodes"]]
        assert node_order.index("T-100") < node_order.index("T-101") < node_order.index("T-102")
        assert node_order.index("T-103") < node_order.index("T-102")

    def test_topological_order_reports_cycles(self, tmp_path):
        root = tmp_path / "project"
        _write_task_graph(root, [
            {"id": "T-200", "title": "Cycle A", "status": "completed", "depends_on": "T-201"},
            {"id": "T-201", "title": "Cycle B", "status": "completed", "depends_on": "T-200"},
            {"id": "T-202", "title": "Free", "status": "completed"},
        ])
        view = DashboardViews(root).task_graph_view()
        assert sorted(view["unresolved_tasks"]) == ["T-200", "T-201"]
        assert view["topological_order"] == ["T-202"]

    def test_missing_task_graph_is_not_available(self, tmp_path):
        view = DashboardViews(tmp_path).task_graph_view()
        assert view["status"] == NOT_AVAILABLE
        assert "missing" in view["reason"]

    def test_unparseable_task_graph_is_not_available(self, tmp_path):
        root = tmp_path / "project"
        path = root / ".ai" / "task_graph.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("tasks: [unclosed", encoding="utf-8")
        view = DashboardViews(root).task_graph_view()
        assert view["status"] == NOT_AVAILABLE
        assert "unparseable" in view["reason"]

    def test_real_repo_view_is_self_consistent(self):
        """The view must agree with the actual source file (no fabrication),
        independent of how many tasks the repo currently has."""
        import yaml

        view = DashboardViews(ROOT).task_graph_view()
        assert view["status"] == "available"
        doc = yaml.safe_load((ROOT / ".ai" / "task_graph.yaml").read_text(encoding="utf-8"))
        tasks = doc["tasks"]
        statuses = {}
        for t in tasks:
            status = str(t.get("status", "")).lower()
            statuses[status] = statuses.get(status, 0) + 1
        assert view["summary"]["total"] == len(tasks) == len(view["nodes"])
        assert view["summary"]["completed"] == statuses.get("completed", 0)
        assert view["summary"]["in_progress"] == statuses.get("in_progress", 0)
        # topological order is a permutation of all task ids
        assert sorted(view["topological_order"]) == sorted(n["task_id"] for n in view["nodes"])


# ── AC-02: gate view ─────────────────────────────────────────────────────


class TestGateView:
    def test_counts_pending_approved_rejected(self, tmp_path):
        root = _fixture_root(tmp_path)
        view = DashboardViews(root).gate_view()

        assert view["status"] == "available"
        c = view["counts"]
        assert c["total"] == 4
        assert c["pending"] == 1
        assert c["approved"] == 2
        assert c["rejected"] == 1
        assert c["other"] == 0
        assert view["by_status"] == {"approved": 2, "pending": 1, "rejected": 1}
        assert view["by_decision"] == {"approved": 2, "rejected": 1}

    def test_decision_records_fields_and_order(self, tmp_path):
        root = _fixture_root(tmp_path)
        view = DashboardViews(root).gate_view()

        records = view["decision_records"]
        # only decided gates carry decision records
        assert len(records) == 3
        ids = [r["gate_id"] for r in records]
        assert "G-1-PENDING" not in ids
        # recorded_at descending: newest first, missing timestamp last
        assert ids[0] == "G-3-REJECTED"
        assert ids[1] == "G-2-APPROVED"
        assert ids[2] == "G-4-APPROVED-NO-TS"
        r = records[0]
        assert r["task_id"] == "T-3"
        assert r["decision"] == "rejected"
        assert r["approval_actor"] == "user"
        assert r["recorded_at"] == "2026-07-02T10:00:00+08:00"
        assert r["gate_type"] == "user-review"

    def test_missing_gates_register_is_not_available(self, tmp_path):
        view = DashboardViews(tmp_path).gate_view()
        assert view["status"] == NOT_AVAILABLE
        assert "missing" in view["reason"]

    def test_real_repo_view_is_self_consistent(self):
        import yaml

        view = DashboardViews(ROOT).gate_view()
        assert view["status"] == "available"
        doc = yaml.safe_load((ROOT / ".ai" / "gates.yaml").read_text(encoding="utf-8"))
        gates = doc["gates"]
        assert view["counts"]["total"] == len(gates)
        decided = sum(1 for g in gates if str(g.get("status", "")).lower() in ("approved", "rejected"))
        assert len(view["decision_records"]) == decided
        assert sum(view["counts"][k] for k in ("pending", "approved", "rejected", "other")) == len(gates)


# ── AC-03: metrics + guard health view ───────────────────────────────────


class TestMetricsGuardHealthView:
    def test_metrics_view_budget_and_key_items(self, tmp_path):
        root = _fixture_root(tmp_path)
        view = DashboardViews(root).metrics_view()

        assert view["status"] == "available"
        assert view["report_status"] == "NOT_VERIFIED"
        assert view["error_budget"]["status"] == "HEALTHY"
        assert view["error_budget"]["remaining_units"] == 100.0
        assert view["error_budget"]["total_units"] == 100.0

        items = view["items"]
        assert items["gate_rejection_rate"]["status"] == "computed"
        assert items["gate_rejection_rate"]["value"] == 0.0
        assert items["gate_decision_coverage"]["value"] == 0.5
        # NOT_AVAILABLE items pass through with their reason, never guessed
        dwell = items["phase_dwell_time"]
        assert dwell["status"] == NOT_AVAILABLE
        assert dwell["value"] == NOT_AVAILABLE
        assert "absent" in dwell["reason"]
        # dict-valued items survive
        assert items["approval_latency"]["value"]["p95_hours"] == 0.476
        assert items["task_cycle_time"]["value"]["mean_days"] == 0.084

    def test_guard_health_stats(self, tmp_path):
        root = _fixture_root(tmp_path)
        view = DashboardViews(root).guard_health_view()

        assert view["status"] == "available"
        assert view["total_events"] == 4
        assert view["fail_count"] == 1
        assert view["avg_duration_ms"] == 250.0
        by_guard = {g["guard_id"]: g for g in view["by_guard"]}
        assert by_guard["bash_content_guard"]["total"] == 2
        assert by_guard["bash_content_guard"]["fail"] == 0
        assert by_guard["content_guard"]["fail"] == 1
        assert view["by_result"] == {"FAIL": 1, "PASS": 3}
        assert view["by_check_type"] == {"death": 1, "health": 3}

    def test_missing_metric_sources_are_not_available(self, tmp_path):
        root = tmp_path / "project"
        root.mkdir(parents=True, exist_ok=True)
        m = DashboardViews(root).metrics_view()
        assert m["status"] == NOT_AVAILABLE
        g = DashboardViews(root).guard_health_view()
        assert g["status"] == NOT_AVAILABLE

    def test_real_repo_views_are_self_consistent(self):
        view = DashboardViews(ROOT)
        m = view.metrics_view()
        assert m["status"] == "available"
        assert m["report_status"] in ("PASS", "NOT_VERIFIED")
        assert m["error_budget"]["status"] in ("HEALTHY", "CONSUMING", "FREEZE_RECOMMENDED")

        g = view.guard_health_view()
        assert g["status"] == "available"
        lines = [ln for ln in (OBSERVABILITY_DIR / "guard-events.jsonl")
                 .read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert g["total_events"] == len(lines)
        assert g["fail_count"] == sum(1 for ln in lines if '"result": "FAIL"' in ln)
        assert sum(x["total"] for x in g["by_guard"]) == g["total_events"]


# ── AC-04: snapshot report ───────────────────────────────────────────────


class TestSnapshotReport:
    def test_text_report_sections(self, tmp_path):
        root = _fixture_root(tmp_path)
        views = DashboardViews(root)
        snapshot = views.build_snapshot()
        text = views.render_text(snapshot)

        assert snapshot["status"] == "PASS"
        assert snapshot["not_available_views"] == []
        for heading in ("# AutoPlan Dashboard Snapshot", "## 1. Task graph",
                        "## 2. Gates", "## 3. Metrics", "## 4. Guard health",
                        "## Data source hashes (read-only proof)"):
            assert heading in text
        assert "| T-100 | First task | completed | S1-requirements |" in text
        assert "| G-3-REJECTED | T-3 | rejected | user |" in text
        assert "HEALTHY" in text
        assert "Avg duration (ms)" in text

    def test_text_report_marks_missing_data(self, tmp_path):
        views = DashboardViews(tmp_path)  # no data sources at all
        snapshot = views.build_snapshot()
        assert snapshot["status"] == "NOT_VERIFIED"
        assert sorted(snapshot["not_available_views"]) == [
            "gates", "guard_health", "metrics", "task_graph"]
        text = views.render_text(snapshot)
        assert "NOT_AVAILABLE" in text
        for rel in SOURCE_FILES:
            assert snapshot["source_hashes"][rel] is None

    def test_html_is_self_contained(self, tmp_path):
        root = _fixture_root(tmp_path)
        views = DashboardViews(root)
        html_out = views.render_html(views.build_snapshot())

        assert html_out.startswith("<!DOCTYPE html>")
        assert "<style>" in html_out and "</style>" in html_out
        for heading in ("Task graph", "Gates", "Metrics", "Guard health",
                        "Data source hashes (read-only proof)"):
            assert heading in html_out
        # self-contained: no JS, no external links, no images, no fonts
        for forbidden in ("<script", "src=", "href=", "http://", "https://",
                          "@import", "url(", "<img", "javascript:"):
            assert forbidden not in html_out
        # content is HTML-escaped
        assert "<table>" in html_out

    def test_snapshot_files_written_with_readonly_hash_proof(self, tmp_path):
        """AC-04 read-only: data sources are byte-identical before and after
        snapshot generation; recorded source_hashes match actual files."""
        before = {rel: _sha256(ROOT / rel) for rel in SOURCE_FILES}
        out_dir = tmp_path / "out"
        written = write_snapshot_files(ROOT, out_dir=out_dir)
        after = {rel: _sha256(ROOT / rel) for rel in SOURCE_FILES}

        assert before == after  # zero modification
        assert written["text"].exists() and written["html"].exists()
        assert written["text"].read_text(encoding="utf-8").startswith("# AutoPlan Dashboard Snapshot")

        snapshot = DashboardViews(ROOT).build_snapshot()
        for rel in SOURCE_FILES:
            assert snapshot["source_hashes"][rel] == before[rel]

    def test_snapshot_json_roundtrip(self, tmp_path):
        root = _fixture_root(tmp_path)
        views = DashboardViews(root)
        snapshot = views.build_snapshot()
        decoded = json.loads(json.dumps(snapshot, ensure_ascii=False))
        assert decoded["sections"]["task_graph"]["summary"]["total"] == 4
        assert decoded["sections"]["gates"]["counts"]["approved"] == 2


# ── CLI + MCP handlers ───────────────────────────────────────────────────


def _load_tool_module(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestCliAndMcp:
    def test_cli_text_json_html_stdout(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(ROOT)
        cli = _load_tool_module("loop_dashboard")
        assert cli.main(["--json"]) == 0
        out = capsys.readouterr().out
        assert json.loads(out)["report_type"] == "autoplan-dashboard-snapshot"

        assert cli.main(["--html"]) == 0
        html_out = capsys.readouterr().out
        assert html_out.startswith("<!DOCTYPE html>")
        assert "<script" not in html_out

        assert cli.main(["--text"]) == 0
        text_out = capsys.readouterr().out
        assert text_out.startswith("# AutoPlan Dashboard Snapshot")

    def test_cli_snapshot_writes_files(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(ROOT)
        cli = _load_tool_module("loop_dashboard")
        out_dir = tmp_path / "snap"
        assert cli.main(["--snapshot", "--out", str(out_dir)]) == 0
        assert (out_dir / "dashboard-snapshot.md").exists()
        assert (out_dir / "dashboard-snapshot.html").exists()
        assert "wrote" in capsys.readouterr().out

    def test_cli_snapshot_single_file(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(ROOT)
        cli = _load_tool_module("loop_dashboard")
        target = tmp_path / "single.md"
        assert cli.main(["--snapshot", "--out", str(target)]) == 0
        assert target.exists()
        assert target.read_text(encoding="utf-8").startswith("# AutoPlan Dashboard Snapshot")

    def test_mcp_handlers(self, monkeypatch):
        monkeypatch.setenv("LOOP_PROJECT_ROOT", str(ROOT))
        tool = _load_tool_module("tool_dashboard")

        resp = json.loads(tool.handle_task_graph({}))
        assert resp["success"] is True
        assert resp["data"]["status"] == "available"
        assert resp["data"]["summary"]["total"] >= 1

        resp = json.loads(tool.handle_gates({}))
        assert resp["success"] is True
        assert resp["data"]["counts"]["total"] >= 1

        resp = json.loads(tool.handle_guard_health({}))
        assert resp["success"] is True
        assert resp["data"]["metrics"]["status"] == "available"
        assert resp["data"]["guard_health"]["status"] == "available"

        resp = json.loads(tool.handle_snapshot({"format": "html"}))
        assert resp["success"] is True
        assert resp["data"]["html"].startswith("<!DOCTYPE html>")

        resp = json.loads(tool.handle_snapshot({"format": "json"}))
        assert resp["success"] is True
        assert resp["data"]["status"] in ("PASS", "NOT_VERIFIED")
