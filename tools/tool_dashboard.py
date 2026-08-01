"""MCP Tool: Project status dashboard."""
import json, os, sys

def _get_root(): return os.environ.get("LOOP_PROJECT_ROOT", os.getcwd())
def _ok(data=None): return json.dumps({"success": True, "data": data}, ensure_ascii=False, indent=2)
def _err(msg): return json.dumps({"success": False, "error": msg}, ensure_ascii=False, indent=2)

def handle_status(args):
    try:
        from loop_core.status_dashboard import Dashboard
        dashboard = Dashboard(_get_root())
        status = dashboard.generate()
        fmt = args.get("format", "json")
        if fmt == "markdown":
            return _ok({"markdown": dashboard.to_markdown(status)})
        return _ok(dashboard.to_dict(status))
    except Exception as e:
        return _err(str(e))

def handle_task_graph(args):
    """T-0094 AC-01: task graph view (nodes/edges/status summary/topology)."""
    try:
        from loop_core.dashboard_views import DashboardViews
        return _ok(DashboardViews(_get_root()).task_graph_view())
    except Exception as e:
        return _err(str(e))

def handle_gates(args):
    """T-0094 AC-02: gate view (pending/approved/rejected + decision records)."""
    try:
        from loop_core.dashboard_views import DashboardViews
        return _ok(DashboardViews(_get_root()).gate_view())
    except Exception as e:
        return _err(str(e))

def handle_guard_health(args):
    """T-0094 AC-03: metrics + guard health view (metrics-report + guard events)."""
    try:
        from loop_core.dashboard_views import DashboardViews
        views = DashboardViews(_get_root())
        return _ok({
            "metrics": views.metrics_view(),
            "guard_health": views.guard_health_view(),
        })
    except Exception as e:
        return _err(str(e))

def handle_snapshot(args):
    """T-0094 AC-04: full snapshot; format json|markdown|html."""
    try:
        from loop_core.dashboard_views import DashboardViews
        views = DashboardViews(_get_root())
        snapshot = views.build_snapshot()
        fmt = args.get("format", "json")
        if fmt == "markdown":
            return _ok({"markdown": views.render_text(snapshot)})
        if fmt == "html":
            return _ok({"html": views.render_html(snapshot)})
        return _ok(snapshot)
    except Exception as e:
        return _err(str(e))

HANDLERS = {
    "dashboard_status": handle_status,
    "dashboard_task_graph": handle_task_graph,
    "dashboard_gates": handle_gates,
    "dashboard_guard_health": handle_guard_health,
    "dashboard_snapshot": handle_snapshot,
}

def main():
    try:
        req = json.loads(sys.stdin.read())
        h = HANDLERS.get(req.get("method", ""))
        if not h: return print(_err(f"Unknown method: {req.get('method')}"))
        print(h(req.get("params", {}) or {}))
    except Exception as e:
        print(_err(str(e)))

if __name__ == "__main__": main()
