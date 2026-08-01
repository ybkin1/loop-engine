"""
AutoPlan dashboard visualization layer (T-0094 D4 — StaffDeck-style front
product layer, no React stack).

Reads the governance data sources and renders four visualizable views plus a
self-contained snapshot report:

- ``task_graph_view``   — nodes (task_id/title/status/phase), dependency
  edges (``edges`` list + per-task ``depends_on``), status summary and a
  deterministic topological order of the dependency chain (AC-01).
- ``gate_view``         — pending/approved/rejected statistics plus decision
  records (gate_id / task / decision / approval_actor / recorded_at) (AC-02).
- ``metrics_view``      — key items of ``metrics-report.json`` (D2): error
  budget status, gate rejection rate, decision coverage, approval latency,
  task cycle time, guard anomaly rate (AC-03).
- ``guard_health_view`` — guard-events.jsonl (U8) statistics: total events,
  failures, average check duration, per-guard / per-result / per-check-type
  breakdown (AC-03).
- ``build_snapshot`` / ``render_text`` / ``render_html`` — snapshot report
  as text (markdown) and as a single self-contained HTML file (inline CSS,
  no JavaScript, no external links) (AC-04).

Rules:
- Read-only: data sources (task_graph.yaml / gates.yaml / metrics-report.json
  / guard-events.jsonl) are never modified; ``source_hashes`` in the snapshot
  records their sha256 so a reader (or test) can prove byte-identity.
- Fail-closed: a missing or unparseable source renders as NOT_AVAILABLE for
  that view — never guessed, never silently zeroed.
- Deterministic: views sort by stable keys so snapshots are reproducible
  from the same sources.
"""
from __future__ import annotations

import hashlib
import html
import json
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

# Availability sentinel — mirrors loop_core/governance_metrics.NOT_AVAILABLE
NOT_AVAILABLE = "NOT_AVAILABLE"

TOOL_NAME = "loop_dashboard"
TOOL_VERSION = "1.0.0"

# (relative path, loader kind) — the four data sources the dashboard reads.
SOURCE_FILES: tuple[tuple[str, str], ...] = (
    (".ai/task_graph.yaml", "yaml"),
    (".ai/gates.yaml", "yaml"),
    (".ai/evidence/observability/metrics-report.json", "json"),
    (".ai/evidence/observability/guard-events.jsonl", "jsonl"),
)

DECIDED_STATUSES = ("approved", "rejected")
GATE_STATUS_ORDER = ("pending", "approved", "rejected")
TASK_STATUS_ORDER = ("completed", "in_progress", "pending")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit(root: Path) -> str:
    import subprocess

    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def _load_yaml(path: Path, what: str) -> tuple[Any, str | None]:
    """Load a YAML source; returns (data, None) or (None, reason)."""
    if not path.exists():
        return None, f"{what} missing: {path}"
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return None, f"{what} unparseable: {path}: {exc}"
    return doc, None


def _load_json(path: Path, what: str) -> tuple[Any, str | None]:
    if not path.exists():
        return None, f"{what} missing: {path}"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"{what} unparseable: {path}: {exc}"
    return doc, None


def _load_jsonl(path: Path, what: str) -> tuple[list[dict], str | None]:
    """Strict JSONL load: a corrupt line makes the source NOT_AVAILABLE."""
    if not path.exists():
        return None, f"{what} missing: {path}"
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"{what} unreadable: {path}: {exc}"
    records: list[dict] = []
    for i, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            return None, f"{what} unparseable line {i}: {path}: {exc}"
        if not isinstance(data, dict):
            return None, f"{what} non-object line {i}: {path}"
        records.append(data)
    return records, None


def _not_available(reason: str) -> dict[str, Any]:
    return {"status": NOT_AVAILABLE, "reason": reason}


# ── View 1: task graph ───────────────────────────────────────────────────


def _topological_order(
    task_ids: set[str], edges: list[tuple[str, str]]
) -> tuple[list[str], list[str]]:
    """Kahn's algorithm over the dependency edges restricted to known tasks.

    Returns (ordered_ids, unresolved_ids).  ``unresolved_ids`` collects tasks
    that could not be fully ordered (cycle / self-loop) — they are appended at
    the end instead of being dropped.  Order is deterministic: candidates are
    popped in lexicographic task-id order.
    """
    present = [e for e in edges if e[0] in task_ids and e[1] in task_ids]
    dependents: dict[str, list[str]] = {t: [] for t in task_ids}
    indegree: dict[str, int] = {t: 0 for t in task_ids}
    for from_id, to_id in present:
        dependents[from_id].append(to_id)
        indegree[to_id] += 1
    queue = deque(sorted(t for t, d in indegree.items() if d == 0))
    ordered: list[str] = []
    while queue:
        node = queue.popleft()
        ordered.append(node)
        for dep in sorted(dependents[node]):
            indegree[dep] -= 1
            if indegree[dep] == 0:
                queue.append(dep)
    unresolved = sorted(t for t, d in indegree.items() if d > 0)
    return ordered, unresolved


class DashboardViews:
    """AutoPlan dashboard views over the repository governance data."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)

    # -- data source helpers ----------------------------------------------

    def _source_path(self, rel: str) -> Path:
        return self._root / rel

    # -- View 1: task graph (AC-01) ---------------------------------------

    def task_graph_view(self) -> dict[str, Any]:
        """Nodes + dependency edges + status summary + topological order."""
        path = self._source_path(".ai/task_graph.yaml")
        doc, err = _load_yaml(path, "task graph")
        if err is not None:
            return _not_available(err)

        raw_tasks = doc.get("tasks") if isinstance(doc, dict) else None
        if not isinstance(raw_tasks, list):
            return _not_available(f"task graph has no 'tasks' list: {path}")

        nodes: list[dict[str, str]] = []
        statuses: Counter[str] = Counter()
        for raw in raw_tasks:
            if not isinstance(raw, dict):
                continue
            task_id = str(raw.get("id", ""))
            status = str(raw.get("status", "")).lower()
            statuses[status] += 1
            nodes.append({
                "task_id": task_id,
                "title": str(raw.get("title", "")),
                "status": status,
                "phase": raw.get("phase") if raw.get("phase") else None,
            })

        # edges: explicit `edges` list + per-task `depends_on`
        edge_set: set[tuple[str, str]] = set()
        raw_edges = doc.get("edges") if isinstance(doc, dict) else None
        if isinstance(raw_edges, list):
            for e in raw_edges:
                if isinstance(e, dict) and e.get("from") and e.get("to"):
                    edge_set.add((str(e["from"]), str(e["to"])))
        for raw in raw_tasks:
            if not isinstance(raw, dict):
                continue
            deps = raw.get("depends_on") or []
            if not isinstance(deps, list):
                deps = [deps]
            for dep in deps:
                if dep:
                    edge_set.add((str(dep), str(raw.get("id", ""))))
        edges = sorted(
            [{"from": f, "to": t} for f, t in edge_set],
            key=lambda e: (e["from"], e["to"]),
        )

        task_ids = {n["task_id"] for n in nodes}
        ordered, unresolved = _topological_order(
            task_ids, {(e["from"], e["to"]) for e in edges}
        )
        order_index = {tid: i for i, tid in enumerate(ordered)}
        ordered_nodes = sorted(
            nodes, key=lambda n: order_index.get(n["task_id"], len(order_index))
        )

        summary: dict[str, Any] = {"total": len(nodes)}
        for status in TASK_STATUS_ORDER:
            summary[status] = statuses.get(status, 0)
        summary["other"] = sum(
            n for s, n in statuses.items() if s not in TASK_STATUS_ORDER
        )
        summary["by_status"] = dict(sorted(statuses.items()))

        return {
            "status": "available",
            "source": ".ai/task_graph.yaml",
            "nodes": nodes,
            "ordered_nodes": ordered_nodes,
            "edges": edges,
            "summary": summary,
            "topological_order": ordered,
            "unresolved_tasks": unresolved,
        }

    # -- View 2: gates (AC-02) ---------------------------------------------

    def gate_view(self) -> dict[str, Any]:
        """Pending/approved/rejected statistics + decision records."""
        path = self._source_path(".ai/gates.yaml")
        doc, err = _load_yaml(path, "gates register")
        if err is not None:
            return _not_available(err)

        raw_gates = doc.get("gates") if isinstance(doc, dict) else None
        if not isinstance(raw_gates, list):
            return _not_available(f"gates register has no 'gates' list: {path}")

        by_status: Counter[str] = Counter()
        by_decision: Counter[str] = Counter()
        decision_records: list[dict[str, Any]] = []
        for raw in raw_gates:
            if not isinstance(raw, dict):
                continue
            status = str(raw.get("status", "")).lower()
            decision = raw.get("decision")
            by_status[status] += 1
            if decision is not None:
                by_decision[str(decision).lower()] += 1
            if status in DECIDED_STATUSES:
                decision_records.append({
                    "gate_id": str(raw.get("id", "")),
                    "task_id": str(raw.get("task_id", "")),
                    "gate_type": str(raw.get("gate_type", "")),
                    "status": status,
                    "decision": str(decision) if decision is not None else None,
                    "approval_actor": raw.get("approval_actor"),
                    "recorded_at": raw.get("recorded_at"),
                })

        counts: dict[str, int] = {"total": len(raw_gates)}
        for status in GATE_STATUS_ORDER:
            counts[status] = by_status.get(status, 0)
        counts["other"] = sum(
            n for s, n in by_status.items() if s not in GATE_STATUS_ORDER
        )

        # deterministic order: recorded_at descending (most recent first),
        # records without a timestamp last (sorted by gate_id)
        decision_records.sort(
            key=lambda r: (r["recorded_at"] is None, str(r["recorded_at"] or ""),
                           r["gate_id"])
        )
        with_ts = [r for r in decision_records if r["recorded_at"]]
        without_ts = [r for r in decision_records if not r["recorded_at"]]
        decision_records = with_ts[::-1] + without_ts

        return {
            "status": "available",
            "source": ".ai/gates.yaml",
            "counts": counts,
            "by_status": dict(sorted(by_status.items())),
            "by_decision": dict(sorted(by_decision.items())),
            "decision_records": decision_records,
        }

    # -- View 3: metrics (AC-03) -------------------------------------------

    @staticmethod
    def _pick(metric: dict[str, Any]) -> dict[str, Any]:
        """Collapse one dora metric entry to {status, value, basis/reason}."""
        if not isinstance(metric, dict):
            return {"status": NOT_AVAILABLE, "value": NOT_AVAILABLE}
        if metric.get("status") == NOT_AVAILABLE:
            return {
                "status": NOT_AVAILABLE,
                "value": NOT_AVAILABLE,
                "reason": metric.get("reason"),
            }
        return {
            "status": metric.get("status", "computed"),
            "value": metric.get("value"),
            "basis": metric.get("basis"),
        }

    def metrics_view(self) -> dict[str, Any]:
        """Key metrics-report.json items (D2) — read only, pass through."""
        path = self._source_path(".ai/evidence/observability/metrics-report.json")
        doc, err = _load_json(path, "metrics report")
        if err is not None:
            return _not_available(err)

        dora = doc.get("dora_metrics") if isinstance(doc, dict) else None
        if not isinstance(dora, dict):
            dora = {}
        key_items = [
            "gate_rejection_rate",
            "gate_rejection_rate_by_phase",
            "gate_decision_coverage",
            "approval_latency",
            "task_cycle_time",
            "phase_dwell_time",
            "task_rework_cycles",
            "guard_anomaly_rate",
            "guard_events_summary",
            "execution_cycle_time",
        ]
        items = {name: self._pick(dora.get(name)) for name in key_items}

        budget = doc.get("error_budget") if isinstance(doc, dict) else None
        binding = doc.get("binding") if isinstance(doc, dict) else None
        window = doc.get("window") if isinstance(doc, dict) else None

        return {
            "status": "available",
            "source": ".ai/evidence/observability/metrics-report.json",
            "report_status": doc.get("status") if isinstance(doc, dict) else None,
            "binding": {
                "task_id": (binding or {}).get("task_id"),
                "git_commit": (binding or {}).get("git_commit"),
                "timestamp": (binding or {}).get("timestamp"),
            } if isinstance(binding, dict) else None,
            "window": window if isinstance(window, dict) else None,
            "error_budget": {
                "status": budget.get("status") if isinstance(budget, dict) else None,
                "total_units": budget.get("total_units") if isinstance(budget, dict) else None,
                "remaining_units": budget.get("remaining_units") if isinstance(budget, dict) else None,
                "consumed_units": budget.get("consumed_units") if isinstance(budget, dict) else None,
            } if isinstance(budget, dict) else NOT_AVAILABLE,
            "items": items,
        }

    # -- View 4: guard health (AC-03) --------------------------------------

    def guard_health_view(self) -> dict[str, Any]:
        """guard-events.jsonl statistics computed directly from the file."""
        path = self._source_path(".ai/evidence/observability/guard-events.jsonl")
        events, err = _load_jsonl(path, "guard events")
        if err is not None:
            return _not_available(err)

        by_guard: dict[str, dict[str, Any]] = {}
        by_result: Counter[str] = Counter()
        by_check_type: Counter[str] = Counter()
        durations: list[float] = []
        for e in events:
            guard_id = str(e.get("guard_id", ""))
            result = str(e.get("result", ""))
            by_result[result] += 1
            by_check_type[str(e.get("check_type", ""))] += 1
            g = by_guard.setdefault(guard_id, {"total": 0, "fail": 0})
            g["total"] += 1
            if result == "FAIL":
                g["fail"] += 1
            try:
                durations.append(float(e.get("duration_ms", 0.0) or 0.0))
            except (TypeError, ValueError):
                pass

        per_guard = [
            {"guard_id": gid, **g}
            for gid, g in sorted(by_guard.items())
        ]
        failures = by_result.get("FAIL", 0)
        return {
            "status": "available",
            "source": ".ai/evidence/observability/guard-events.jsonl",
            "total_events": len(events),
            "fail_count": failures,
            "avg_duration_ms": (
                round(sum(durations) / len(durations), 3) if durations else None
            ),
            "by_guard": per_guard,
            "by_result": dict(sorted(by_result.items())),
            "by_check_type": dict(sorted(by_check_type.items())),
        }

    # -- Snapshot (AC-04) --------------------------------------------------

    def build_snapshot(self) -> dict[str, Any]:
        """Full dashboard snapshot: four views + source hashes + binding."""
        views = {
            "task_graph": self.task_graph_view(),
            "gates": self.gate_view(),
            "metrics": self.metrics_view(),
            "guard_health": self.guard_health_view(),
        }
        source_hashes: dict[str, Any] = {}
        for rel, _kind in SOURCE_FILES:
            path = self._source_path(rel)
            source_hashes[rel] = _sha256(path) if path.exists() else None

        not_available = [
            name for name, view in views.items()
            if view.get("status") == NOT_AVAILABLE
        ]
        return {
            "schema_version": 1,
            "report_type": "autoplan-dashboard-snapshot",
            "binding": {
                "tool_name": TOOL_NAME,
                "tool_version": TOOL_VERSION,
                "task_id": "T-0094",
                "phase": "S6-delivery",
                "git_commit": _git_commit(self._root),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            "status": "NOT_VERIFIED" if not_available else "PASS",
            "not_available_views": not_available,
            "sections": views,
            "source_hashes": source_hashes,
        }

    # -- Text rendering -----------------------------------------------------

    def render_text(self, snapshot: dict[str, Any] | None = None) -> str:
        """Render the snapshot as human-readable markdown (text report)."""
        if snapshot is None:
            snapshot = self.build_snapshot()
        lines: list[str] = []
        binding = snapshot.get("binding", {})
        lines.append("# AutoPlan Dashboard Snapshot")
        lines.append("")
        lines.append(f"- **Status**: {snapshot.get('status')}")
        lines.append(f"- **Generated**: {binding.get('generated_at')}")
        lines.append(f"- **Git commit**: {binding.get('git_commit') or '(unavailable)'}")
        lines.append(f"- **Tool**: {binding.get('tool_name')} v{binding.get('tool_version')}")
        if snapshot.get("not_available_views"):
            lines.append("")
            lines.append(f"**NOT_AVAILABLE views ({len(snapshot['not_available_views'])}):** "
                         + ", ".join(snapshot["not_available_views"]))
        lines.append("")
        lines.append("## 1. Task graph")
        lines.append("")
        lines.extend(self._render_task_graph_text(snapshot.get("sections", {}).get("task_graph")))
        lines.append("## 2. Gates")
        lines.append("")
        lines.extend(self._render_gates_text(snapshot.get("sections", {}).get("gates")))
        lines.append("## 3. Metrics")
        lines.append("")
        lines.extend(self._render_metrics_text(snapshot.get("sections", {}).get("metrics")))
        lines.append("## 4. Guard health")
        lines.append("")
        lines.extend(self._render_guard_health_text(snapshot.get("sections", {}).get("guard_health")))
        lines.append("## Data source hashes (read-only proof)")
        lines.append("")
        for rel in sorted(snapshot.get("source_hashes", {})):
            digest = snapshot["source_hashes"][rel]
            lines.append(f"- `{rel}`: {digest if digest else NOT_AVAILABLE}")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _render_task_graph_text(view: dict[str, Any] | None) -> list[str]:
        if view is None or view.get("status") == NOT_AVAILABLE:
            return [f"- {NOT_AVAILABLE}: {view.get('reason', 'no data')}", ""]
        s = view["summary"]
        lines = [
            f"| Status | Count |",
            f"|---|---|",
            f"| Total | {s['total']} |",
            f"| Completed | {s['completed']} |",
            f"| In progress | {s['in_progress']} |",
            f"| Pending | {s['pending']} |",
            f"| Other | {s['other']} |",
            "",
        ]
        lines.append(f"**Topological order** ({len(view['topological_order'])} tasks):")
        lines.append("")
        lines.append(", ".join(view["topological_order"]) or "(empty)")
        lines.append("")
        if view["unresolved_tasks"]:
            lines.append(f"**Unresolved (cycle/self-loop):** "
                         + ", ".join(view["unresolved_tasks"]))
            lines.append("")
        lines.append(f"**Dependency edges** ({len(view['edges'])}):")
        lines.append("")
        lines.append("| From | To |")
        lines.append("|---|---|")
        for e in view["edges"]:
            lines.append(f"| {e['from']} | {e['to']} |")
        lines.append("")
        lines.append(f"**Nodes** ({len(view['nodes'])}):")
        lines.append("")
        lines.append("| Task | Title | Status | Phase |")
        lines.append("|---|---|---|---|")
        for n in view["ordered_nodes"]:
            lines.append(f"| {n['task_id']} | {n['title'] or '-'} | "
                         f"{n['status']} | {n['phase'] or '-'} |")
        lines.append("")
        return lines

    @staticmethod
    def _render_gates_text(view: dict[str, Any] | None) -> list[str]:
        if view is None or view.get("status") == NOT_AVAILABLE:
            return [f"- {NOT_AVAILABLE}: {view.get('reason', 'no data')}", ""]
        c = view["counts"]
        lines = [
            f"| Status | Count |",
            f"|---|---|",
            f"| Pending | {c['pending']} |",
            f"| Approved | {c['approved']} |",
            f"| Rejected | {c['rejected']} |",
            f"| Other | {c['other']} |",
            f"| Total | {c['total']} |",
            "",
            f"**Decision records** ({len(view['decision_records'])}):",
            "",
            "| Gate | Task | Decision | Actor | Recorded at |",
            "|---|---|---|---|---|",
        ]
        for r in view["decision_records"]:
            lines.append(f"| {r['gate_id']} | {r['task_id']} | "
                         f"{r['decision'] or '-'} | {r['approval_actor'] or '-'} | "
                         f"{r['recorded_at'] or '-'} |")
        lines.append("")
        return lines

    @staticmethod
    def _render_metrics_text(view: dict[str, Any] | None) -> list[str]:
        if view is None or view.get("status") == NOT_AVAILABLE:
            return [f"- {NOT_AVAILABLE}: {view.get('reason', 'no data')}", ""]
        lines = [f"- **Report status**: {view.get('report_status') or '-'}"]
        budget = view.get("error_budget")
        if isinstance(budget, dict):
            lines.append(f"- **Error budget**: {budget.get('status') or '-'} — "
                         f"{budget.get('remaining_units')} / {budget.get('total_units')} "
                         f"units remaining (consumed {budget.get('consumed_units')})")
        lines.append("")
        lines.append("| Metric | Status | Value | Basis / note |")
        lines.append("|---|---|---|---|")
        for name, item in view.get("items", {}).items():
            if item.get("status") == NOT_AVAILABLE:
                value = NOT_AVAILABLE
                basis = item.get("reason", "")
            else:
                value = item.get("value")
                basis = item.get("basis", "")
                if isinstance(value, dict):
                    value = json.dumps(value, ensure_ascii=False)
                value = str(value)
            lines.append(f"| `{name}` | {item.get('status')} | {value} | {basis} |")
        lines.append("")
        return lines

    @staticmethod
    def _render_guard_health_text(view: dict[str, Any] | None) -> list[str]:
        if view is None or view.get("status") == NOT_AVAILABLE:
            return [f"- {NOT_AVAILABLE}: {view.get('reason', 'no data')}", ""]
        lines = [
            f"- **Total events**: {view['total_events']}",
            f"- **Failures (FAIL)**: {view['fail_count']}",
            f"- **Avg duration (ms)**: {view['avg_duration_ms']}",
            "",
            "| Guard | Checks | Failures |",
            "|---|---|---|",
        ]
        for g in view["by_guard"]:
            lines.append(f"| {g['guard_id'] or '(unnamed)'} | {g['total']} | {g['fail']} |")
        lines.append("")
        lines.append(f"**By result**: {view['by_result']}")
        lines.append("")
        lines.append(f"**By check type**: {view['by_check_type']}")
        lines.append("")
        return lines

    # -- HTML rendering (self-contained) ------------------------------------

    def render_html(self, snapshot: dict[str, Any] | None = None) -> str:
        """Self-contained HTML: inline CSS only, no JS, no external links."""
        if snapshot is None:
            snapshot = self.build_snapshot()
        binding = snapshot.get("binding", {})
        esc = html.escape

        def table(headers: list[str], rows: list[list[str]]) -> str:
            thead = "".join(f"<th>{esc(h)}</th>" for h in headers)
            body = "".join(
                "<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>"
                for row in rows
            )
            return (f"<table><thead><tr>{thead}</tr></thead>"
                    f"<tbody>{body}</tbody></table>")

        parts: list[str] = []
        parts.append(f"<h1>AutoPlan Dashboard Snapshot</h1>")
        parts.append("<div class=\"meta\">")
        parts.append(f"<p><strong>Status:</strong> {esc(str(snapshot.get('status')))}</p>")
        parts.append(f"<p><strong>Generated:</strong> {esc(str(binding.get('generated_at')))}</p>")
        parts.append(f"<p><strong>Git commit:</strong> {esc(str(binding.get('git_commit') or '(unavailable)'))}</p>")
        parts.append(f"<p><strong>Tool:</strong> {esc(str(binding.get('tool_name')))} v{esc(str(binding.get('tool_version')))}</p>")
        if snapshot.get("not_available_views"):
            parts.append(f"<p class=\"warn\"><strong>NOT_AVAILABLE views:</strong> "
                         f"{esc(', '.join(snapshot['not_available_views']))}</p>")
        parts.append("</div>")

        views = snapshot.get("sections", {})
        tg = views.get("task_graph")
        parts.append("<h2>1. Task graph</h2>")
        if not tg or tg.get("status") == NOT_AVAILABLE:
            parts.append(f"<p class=\"na\">NOT_AVAILABLE: {esc(str((tg or {}).get('reason', 'no data')))}</p>")
        else:
            s = tg["summary"]
            parts.append(table(
                ["Status", "Count"],
                [["Total", str(s["total"])], ["Completed", str(s["completed"])],
                 ["In progress", str(s["in_progress"])], ["Pending", str(s["pending"])],
                 ["Other", str(s["other"])]],
            ))
            parts.append(f"<h3>Topological order ({len(tg['topological_order'])} tasks)</h3>")
            parts.append(f"<p>{esc(', '.join(tg['topological_order']) or '(empty)')}</p>")
            if tg["unresolved_tasks"]:
                parts.append(f"<p class=\"warn\">Unresolved (cycle/self-loop): "
                             f"{esc(', '.join(tg['unresolved_tasks']))}</p>")
            parts.append(f"<h3>Dependency edges ({len(tg['edges'])})</h3>")
            parts.append(table(
                ["From", "To"],
                [[e["from"], e["to"]] for e in tg["edges"]],
            ))
            parts.append(f"<h3>Nodes ({len(tg['nodes'])})</h3>")
            parts.append(table(
                ["Task", "Title", "Status", "Phase"],
                [[n["task_id"], n["title"] or "-", n["status"],
                  str(n["phase"] or "-")] for n in tg["ordered_nodes"]],
            ))

        gv = views.get("gates")
        parts.append("<h2>2. Gates</h2>")
        if not gv or gv.get("status") == NOT_AVAILABLE:
            parts.append(f"<p class=\"na\">NOT_AVAILABLE: {esc(str((gv or {}).get('reason', 'no data')))}</p>")
        else:
            c = gv["counts"]
            parts.append(table(
                ["Status", "Count"],
                [["Pending", str(c["pending"])], ["Approved", str(c["approved"])],
                 ["Rejected", str(c["rejected"])], ["Other", str(c["other"])],
                 ["Total", str(c["total"])]],
            ))
            parts.append(f"<h3>Decision records ({len(gv['decision_records'])})</h3>")
            parts.append(table(
                ["Gate", "Task", "Decision", "Actor", "Recorded at"],
                [[r["gate_id"], r["task_id"], str(r["decision"] or "-"),
                  str(r["approval_actor"] or "-"), str(r["recorded_at"] or "-")]
                 for r in gv["decision_records"]],
            ))

        mv = views.get("metrics")
        parts.append("<h2>3. Metrics</h2>")
        if not mv or mv.get("status") == NOT_AVAILABLE:
            parts.append(f"<p class=\"na\">NOT_AVAILABLE: {esc(str((mv or {}).get('reason', 'no data')))}</p>")
        else:
            budget = mv.get("error_budget")
            parts.append(f"<p>Report status: {esc(str(mv.get('report_status') or '-'))}"
                         + (f" — Error budget: {esc(str(budget.get('status') or '-'))} — "
                            f"{esc(str(budget.get('remaining_units') or '-'))} / "
                            f"{esc(str(budget.get('total_units') or '-'))} units remaining"
                            if isinstance(budget, dict) else "")
                         + "</p>")
            rows = []
            for name, item in mv.get("items", {}).items():
                if item.get("status") == NOT_AVAILABLE:
                    value, basis = NOT_AVAILABLE, item.get("reason", "")
                else:
                    value = item.get("value")
                    if isinstance(value, dict):
                        value = json.dumps(value, ensure_ascii=False)
                    basis = item.get("basis", "")
                rows.append([name, str(item.get("status")), str(value), str(basis)])
            parts.append(table(["Metric", "Status", "Value", "Basis / note"], rows))

        gh = views.get("guard_health")
        parts.append("<h2>4. Guard health</h2>")
        if not gh or gh.get("status") == NOT_AVAILABLE:
            parts.append(f"<p class=\"na\">NOT_AVAILABLE: {esc(str((gh or {}).get('reason', 'no data')))}</p>")
        else:
            parts.append(f"<p>Total events: {gh['total_events']} — Failures: "
                         f"{gh['fail_count']} — Avg duration (ms): "
                         f"{esc(str(gh['avg_duration_ms']))}</p>")
            parts.append(table(
                ["Guard", "Checks", "Failures"],
                [[g["guard_id"] or "(unnamed)", str(g["total"]), str(g["fail"])]
                 for g in gh["by_guard"]],
            ))
            parts.append(f"<p>By result: {esc(str(gh['by_result']))}</p>")
            parts.append(f"<p>By check type: {esc(str(gh['by_check_type']))}</p>")

        parts.append("<h2>Data source hashes (read-only proof)</h2>")
        parts.append("<ul>")
        for rel in sorted(snapshot.get("source_hashes", {})):
            digest = snapshot["source_hashes"][rel]
            parts.append(f"<li><code>{esc(rel)}</code>: "
                         f"{esc(digest) if digest else esc(NOT_AVAILABLE)}</li>")
        parts.append("</ul>")

        css = (
            "body{font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,"
            "sans-serif;margin:2rem auto;max-width:960px;padding:0 1rem;"
            "color:#1a1a1a;line-height:1.5}"
            "h1{border-bottom:3px solid #2563eb;padding-bottom:.4rem}"
            "h2{margin-top:2rem;border-bottom:1px solid #ddd;padding-bottom:.3rem}"
            "table{border-collapse:collapse;width:100%;margin:.6rem 0 1.2rem;"
            "font-size:.9rem}"
            "th,td{border:1px solid #ccc;padding:.35rem .55rem;text-align:left}"
            "th{background:#eef2ff;font-weight:600}"
            "code{background:#f3f4f6;padding:.1rem .3rem;border-radius:3px;"
            "font-size:.85em}"
            ".meta{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;"
            "padding:.6rem 1rem;margin-bottom:1rem}"
            ".warn{color:#92400e;background:#fffbeb;border:1px solid #fcd34d;"
            "border-radius:4px;padding:.4rem .7rem}"
            ".na{color:#7f1d1d;background:#fef2f2;border:1px solid #fecaca;"
            "border-radius:4px;padding:.4rem .7rem}"
        )
        return (
            "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
            "<meta charset=\"utf-8\">\n"
            f"<title>AutoPlan Dashboard Snapshot</title>\n"
            f"<style>{css}</style>\n"
            "</head>\n<body>\n" + "\n".join(parts) + "\n</body>\n</html>\n"
        )


# ── Snapshot file writer (AC-04) ─────────────────────────────────────────

SNAPSHOT_MD_NAME = "dashboard-snapshot.md"
SNAPSHOT_HTML_NAME = "dashboard-snapshot.html"
SNAPSHOT_JSON_NAME = "dashboard-snapshot.json"


def write_snapshot_files(
    root: str | Path,
    out_dir: str | Path | None = None,
    include_json: bool = False,
) -> dict[str, Path]:
    """Write the text + self-contained HTML snapshot (optionally JSON).

    Default output directory: ``<root>/.ai/evidence/observability/``.
    Returns the written file paths.  Data sources are never modified.
    """
    root_path = Path(root)
    target_dir = (
        Path(out_dir) if out_dir is not None
        else root_path / ".ai" / "evidence" / "observability"
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    views = DashboardViews(root_path)
    snapshot = views.build_snapshot()
    written: dict[str, Path] = {}
    md_path = target_dir / SNAPSHOT_MD_NAME
    md_path.write_text(views.render_text(snapshot), encoding="utf-8")
    written["text"] = md_path
    html_path = target_dir / SNAPSHOT_HTML_NAME
    html_path.write_text(views.render_html(snapshot), encoding="utf-8")
    written["html"] = html_path
    if include_json:
        json_path = target_dir / SNAPSHOT_JSON_NAME
        json_path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        written["json"] = json_path
    return written
