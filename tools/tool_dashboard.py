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

HANDLERS = {"dashboard_status": handle_status}

def main():
    try:
        req = json.loads(sys.stdin.read())
        h = HANDLERS.get(req.get("method", ""))
        if not h: return print(_err(f"Unknown method: {req.get('method')}"))
        print(h(req.get("params", {}) or {}))
    except Exception as e:
        print(_err(str(e)))

if __name__ == "__main__": main()
