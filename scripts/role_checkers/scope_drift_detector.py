"""scope_drift_detector.py — Detect scope drift: changed files vs allowed_paths."""
import json, sys, subprocess
from pathlib import Path

def detect(project_root, task_id):
    root = Path(project_root)
    try: import yaml
    except: yaml = None
    if not yaml: return {"error": "yaml not available"}
    tg = yaml.safe_load((root / ".ai/task_graph.yaml").read_text()) or {}
    task = next((t for t in tg.get("tasks",[]) if t.get("id")==task_id), None)
    if not task: return {"error": f"Task {task_id} not found"}
    allowed = set(task.get("allowed_paths", []))
    if not allowed: return {"status":"OK","reason":"No allowed_paths defined"}
    r = subprocess.run(["git","diff","--name-only","HEAD~1"], capture_output=True, text=True, cwd=str(root))
    changed = set(f.strip() for f in r.stdout.split("\n") if f.strip())
    violations = [f for f in changed if not any(f.startswith(a.rstrip("/")) for a in allowed)]
    return {"status":"SCOPE_DRIFT" if violations else "OK","violations":violations,"count":len(violations)}

if __name__ == "__main__":
    print(json.dumps(detect(sys.argv[1] if len(sys.argv)>1 else ".", sys.argv[2] if len(sys.argv)>2 else ""), indent=2))
