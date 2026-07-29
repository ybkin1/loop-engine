"""MCP Tool: Inbox operations."""
import json, os, sys

def _get_root(): return os.environ.get("LOOP_PROJECT_ROOT", os.getcwd())
def _ok(data=None): return json.dumps({"success": True, "data": data}, ensure_ascii=False, indent=2)
def _err(msg): return json.dumps({"success": False, "error": msg}, ensure_ascii=False, indent=2)

def handle_submit(args):
    title = args.get("title", "").strip()
    desc = args.get("description", "").strip()
    if not title: return _err("title is required")
    if not desc: return _err("description is required")
    try:
        from loop_core.inbox import Inbox
        req = Inbox(_get_root()).submit(title, desc, args.get("source", "user"))
        return _ok(req.to_dict())
    except Exception as e:
        return _err(str(e))

def handle_list(args):
    try:
        from loop_core.inbox import Inbox
        reqs = Inbox(_get_root()).list_all(status=args.get("status"))
        return _ok([r.to_dict() for r in reqs])
    except Exception as e:
        return _err(str(e))

def handle_get(args):
    rid = args.get("requirement_id", "").strip()
    if not rid: return _err("requirement_id is required")
    try:
        from loop_core.inbox import Inbox
        return _ok(Inbox(_get_root()).get(rid).to_dict())
    except Exception as e:
        return _err(str(e))

def handle_summary(args):
    try:
        from loop_core.inbox import inbox_summary
        return _ok(inbox_summary(_get_root()))
    except Exception as e:
        return _err(str(e))

HANDLERS = {
    "inbox_submit": handle_submit, "inbox_list": handle_list,
    "inbox_get": handle_get, "inbox_summary": handle_summary,
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
