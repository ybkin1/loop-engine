"""MCP Tool: Plan draft operations."""
import json, os, sys

def _get_root(): return os.environ.get("LOOP_PROJECT_ROOT", os.getcwd())
def _ok(data=None): return json.dumps({"success": True, "data": data}, ensure_ascii=False, indent=2)
def _err(msg): return json.dumps({"success": False, "error": msg}, ensure_ascii=False, indent=2)

def handle_generate(args):
    title = args.get("title", "").strip()
    desc = args.get("description", "").strip()
    rid = args.get("requirement_id", "")
    if not title: return _err("title is required")
    if not desc: return _err("description is required")
    try:
        from loop_core.planner import Planner
        draft = Planner(_get_root()).generate(title, desc, rid)
        return _ok(draft.to_dict())
    except Exception as e:
        return _err(str(e))

def handle_list(args):
    try:
        from loop_core.planner import Planner
        drafts = Planner(_get_root()).list_all(status=args.get("status"))
        return _ok([d.to_dict() for d in drafts])
    except Exception as e:
        return _err(str(e))

def handle_get(args):
    pid = args.get("plan_id", "").strip()
    if not pid: return _err("plan_id is required")
    try:
        from loop_core.planner import Planner
        return _ok(Planner(_get_root()).get(pid).to_dict())
    except Exception as e:
        return _err(str(e))

HANDLERS = {"planner_generate": handle_generate, "planner_list": handle_list, "planner_get": handle_get}

def main():
    try:
        req = json.loads(sys.stdin.read())
        h = HANDLERS.get(req.get("method", ""))
        if not h: return print(_err(f"Unknown method: {req.get('method')}"))
        print(h(req.get("params", {}) or {}))
    except Exception as e:
        print(_err(str(e)))

if __name__ == "__main__": main()
