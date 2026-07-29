"""
artifact_integrity_validator.py — Check build output for zero-byte files and completeness.
"""
import json, sys
from pathlib import Path

def validate(r, ad="dist"):
    p = Path(r) / ad
    if not p.exists(): return {"status":"MISSING"}
    files = {}
    for f in p.rglob("*"):
        if f.is_file() and "__pycache__" not in str(f):
            files[str(f.relative_to(p)).replace("\\","/")] = f.stat().st_size
    zero = {k:v for k,v in files.items() if v==0}
    return {"status":"OK" if not zero else "FAIL","total":len(files),"zero_byte":list(zero.keys()),"zero_count":len(zero)}

if __name__=="__main__":
    print(json.dumps(validate(sys.argv[1] if len(sys.argv)>1 else ".", sys.argv[2] if len(sys.argv)>2 else "dist"), indent=2))
