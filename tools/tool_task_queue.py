"""MCP Tool: Task queue analysis."""
import json, os, sys

def _get_root(): return os.environ.get("LOOP_PROJECT_ROOT", os.getcwd())
def _ok(data=None): return json.dumps({"success": True, "data": data}, ensure_ascii=False, indent=2)
def _err(msg): return json.dumps({"success": False, "error": msg}, ensure_ascii=False, indent=2)

def handle_analysis(args):
    try:
        from loop_core.task_queue import TaskQueue
        return _ok(TaskQueue(_get_root()).to_dict())
    except Exception as e:
        return _err(str(e))

def handle_ready(args):
    try:
        from loop_core.task_queue import TaskQueue
        return _ok({"ready": TaskQueue(_get_root()).ready_tasks()})
    except Exception as e:
        return _err(str(e))

HANDLERS = {"task_queue_analysis": handle_analysis, "task_queue_ready": handle_ready}

def main():
    try:
        req = json.loads(sys.stdin.read())
        h = HANDLERS.get(req.get("method", ""))
        if not h: return print(_err(f"Unknown method: {req.get('method')}"))
        print(h(req.get("params", {}) or {}))
    except Exception as e:
        print(_err(str(e)))

if __name__ == "__main__": main()
