"""
implementation_design_diff.py — Compare code structure vs architecture design.
"""
import json, re, sys
from pathlib import Path

def diff(root):
    r = Path(root)
    arch = r / "docs/02-architecture.md"
    if not arch.exists(): return {"status":"NO_DESIGN"}
    text = arch.read_text(encoding="utf-8")
    designed = set()
    for m in re.finditer(r'`([a-zA-Z_][\w/]*\.py)`', text): designed.add(m.group(1))
    for m in re.finditer(r'`([a-zA-Z_][\w/]+/)`', text): designed.add(m.group(1))
    actual = set()
    for d in [r/"loop_core", r/"hooks", r/"tools", r/"src"]:
        if d.exists():
            for f in d.rglob("*.py"):
                if "__pycache__" not in str(f): actual.add(str(f.relative_to(r)).replace("\\","/"))
    only_designed = {d for d in designed if not any(a.startswith(d.rstrip("/")) for a in actual)}
    only_actual = {a for a in actual if not any(a.startswith(d.rstrip("/")) for d in designed)}
    return {"status":"DRIFT" if only_designed or only_actual else "OK","designed_but_missing":sorted(only_designed)[:10],"actual_but_undesigned":sorted(only_actual)[:10]}

if __name__=="__main__":
    print(json.dumps(diff(sys.argv[1] if len(sys.argv)>1 else "."), indent=2))
