#!/usr/bin/env python3
"""
repair_continuity.py — Official tool to repair ProjectContinuity hash drift.

Usage: python .zcode/tools/repair_continuity.py <project_root>

When governance files are modified through normal operations, the source_manifest
hashes in project_continuity.yaml become stale. This tool recalculates all hashes
and updates the manifest atomically (.tmp + os.replace).
"""
import hashlib, os, sys, json
from pathlib import Path

def _canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def repair_continuity(root: Path) -> dict:
    pc_path = root / ".ai" / "project_continuity.yaml"
    if not pc_path.exists():
        return {"fixed": 0, "errors": ["project_continuity.yaml not found"]}
    try:
        import yaml as _y
        with open(pc_path, "r", encoding="utf-8") as f:
            data = _y.safe_load(f)
    except Exception as e:
        return {"fixed": 0, "errors": [f"YAML error: {e}"]}
    sm = data.get("source_manifest", [])
    if not isinstance(sm, list):
        return {"fixed": 0, "errors": ["invalid manifest"]}
    fixed, errors = 0, []
    for item in sm:
        if not isinstance(item, dict) or "path" not in item: continue
        subject = root / item["path"]
        if not subject.exists():
            errors.append(f"missing: {item['path']}"); continue
        try:
            ah = hashlib.sha256(subject.read_bytes()).hexdigest().upper()
            sz = subject.stat().st_size
        except OSError as e:
            errors.append(f"read error: {item['path']}: {e}"); continue
        if item.get("sha256") != ah or item.get("size") != sz:
            item["sha256"] = ah; item["size"] = sz; fixed += 1
    data["source_sha256"] = hashlib.sha256(_canonical_json(sm).encode()).hexdigest().upper()
    hash_payload = {k: v for k, v in data["project_continuity"].items() if k != "lifecycle"}
    data["semantic_sha256"] = hashlib.sha256(_canonical_json(hash_payload).encode()).hexdigest().upper()
    import yaml as __y
    tmp = pc_path.with_suffix(".yaml.tmp")
    tmp.write_text(__y.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False), encoding="utf-8")
    os.replace(str(tmp), str(pc_path))
    return {"fixed": fixed, "errors": errors}

def main():
    if len(sys.argv) < 2:
        print("Usage: python repair_continuity.py <project_root>"); sys.exit(1)
    root = Path(sys.argv[1]).resolve()
    if not root.is_dir():
        print(f"ERROR: not a directory: {root}"); sys.exit(1)
    result = repair_continuity(root)
    if result["fixed"] > 0:
        print(f"[repair_continuity] Fixed {result['fixed']} drifted hash(es).")
    else:
        print("[repair_continuity] No hash drift detected.")
    for err in result.get("errors", []):
        print(f"[repair_continuity] WARNING: {err}")
    sys.exit(0 if not result["errors"] else 1)

if __name__ == "__main__":
    main()
