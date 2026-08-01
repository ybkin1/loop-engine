"""
review_coverage_checker.py — Verify review covered all changed files.
"""
import json, sys, subprocess
from pathlib import Path

def check(project_root, evidence_path):
    r = subprocess.run(["git","diff","--name-only","HEAD~1"], capture_output=True, text=True, cwd=project_root)
    changed = set(f.strip() for f in r.stdout.split("\n") if f.strip())
    ep = Path(evidence_path)
    if not ep.exists(): return {"status":"MISSING","changed":sorted(changed)}
    try: ev = json.loads(ep.read_text())
    except: return {"status":"INVALID"}
    reviewed = set(ev.get("files_reviewed",[]))
    missing = changed - reviewed
    return {"status":"INCOMPLETE" if missing else "OK","changed":len(changed),"reviewed":len(reviewed),"missing":sorted(missing),"coverage_pct":round(len(reviewed & changed)/len(changed)*100,1) if changed else 100}

if __name__=="__main__":
    print(json.dumps(check(sys.argv[1] if len(sys.argv)>1 else ".", sys.argv[2] if len(sys.argv)>2 else ""), indent=2))
