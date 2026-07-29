"""
cross_layer_consistency.py — Architecture doc vs actual code structure.
"""
import json, re, sys
from pathlib import Path

def check(r):
    root = Path(r)
    results = {"checks":[], "consistent":True}
    arch = root / "docs/02-architecture.md"
    if arch.exists():
        text = arch.read_text(encoding="utf-8")
        arch_mods = set()
        for m in re.finditer(r'`([a-zA-Z_][\w/]+)\.py`', text): arch_mods.add(m.group(1).split("/")[0])
        actual = set(d.name for d in root.iterdir() if d.is_dir() and d.name[0] not in "._." and d.name not in ("docs","tests","scripts","agents","skills","dist",".git",".ai",".zcode","node_modules","__pycache__"))
        missing = arch_mods - actual
        extra = actual - arch_mods
        results["checks"].append({"check":"arch_vs_dirs","missing":sorted(missing),"extra":sorted(extra)})
        if missing or extra: results["consistent"] = False
    return results

if __name__=="__main__":
    print(json.dumps(check(sys.argv[1] if len(sys.argv)>1 else "."), indent=2))
