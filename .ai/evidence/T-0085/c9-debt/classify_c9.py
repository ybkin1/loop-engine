"""C9 finding classifier — T-0085 research.

Re-scans the repo exactly like check_c9_import_validity(root='.', scan_paths=['.']),
then classifies each violation per-site using the actual AST node:
  TYPE-A1: relative import (node.level > 0) misdetected as undeclared
  TYPE-A2: declared package whose import name != package name (yaml -> pyyaml)
  TYPE-A3: project-local module nested under a non-root dir (hooks/, tools/, ...)
  TYPE-B : genuinely undeclared third-party import
  TYPE-C : optional/lazy/guarded third-party import
Also buckets findings whose importing file lives under archive/ (scan-scope note).
"""
import ast
import collections
import os
import sys
from pathlib import Path

sys.path.insert(0, ".")
from loop_core.import_checker import ImportChecker  # noqa: E402

ROOT = Path(".")
LIVE_SOURCE_DIRS = ("loop_core", "hooks", "tools", "src", "loop_engine",
                    "scripts", "agents", "tests", "demo")

res = ImportChecker.check_directory(root=ROOT, scan_paths=[ROOT])

# Cache: parse each file once, map lineno -> node
node_cache: dict[str, dict[int, ast.AST]] = {}


def node_at(file_path: str, lineno: int):
    if file_path not in node_cache:
        node_cache[file_path] = {}
        try:
            tree = ast.parse(Path(file_path).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    node_cache[file_path][node.lineno] = node
        except (OSError, SyntaxError):
            pass
    return node_cache[file_path].get(lineno)


def local_module_exists(top: str) -> bool:
    """True if a dir or .py file named `top` exists anywhere under a live source
    dir (recursive, any depth) or under archive/ (project content)."""
    for d in LIVE_SOURCE_DIRS + ("archive",):
        base = Path(d)
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if not x.startswith(".") and x != "__pycache__"]
            if os.path.basename(dirpath) == top:
                return True
            if f"{top}.py" in filenames:
                return True
    return False


DECLARED = ImportChecker._collect_declared_deps(ROOT)
KNOWN_MAPPINGS = {"yaml": "pyyaml", "dateutil": "python-dateutil", "bs4": "beautifulsoup4",
                  "sklearn": "scikit-learn", "PIL": "pillow", "cv2": "opencv-python"}

buckets: dict[str, list[dict]] = collections.defaultdict(list)
stdlib_missed = set()

for v in res.violations:
    node = node_at(v.file_path, v.line_number)
    top = v.import_name.split(".")[0]
    entry = {"file": v.file_path, "line": v.line_number, "import": v.import_name,
             "top": top}
    if isinstance(node, ast.ImportFrom) and node.level and node.level > 0:
        buckets["A1-relative-import-bug"].append(entry)
    elif top.lower() in KNOWN_MAPPINGS and KNOWN_MAPPINGS[top.lower()] in DECLARED:
        buckets["A2-package-name-mapping"].append(entry)
    elif local_module_exists(top):
        buckets["A3-nested-project-local"].append(entry)
    elif top == "playwright":
        buckets["C-optional-lazy-thirdparty"].append(entry)
    elif top in __import__("sys").stdlib_module_names:
        stdlib_missed.add(top)
        buckets["A4-stdlib-missed"].append(entry)
    else:
        buckets["B-real-debt"].append(entry)

total = 0
for key in sorted(buckets):
    rows = buckets[key]
    total += len(rows)
    mods = collections.Counter(r["top"] for r in rows)
    files = collections.Counter(r["file"].replace("\\", "/") for r in rows)
    under_archive = sum(1 for r in rows if "/archive/" in r["file"].replace("\\", "/"))
    print(f"{key}: {len(rows)}")
    print(f"   top-level modules: {dict(mods.most_common(12))}")
    print(f"   files: {dict(files.most_common(6))}")
    if under_archive:
        print(f"   of which under archive/: {under_archive}")
print("TOTAL:", total, "| expected 237 | stdlib missed:", sorted(stdlib_missed))

# examples per bucket
import json
out = {k: rows[:8] for k, rows in buckets.items()}
json.dump({k: {"count": len(rows), "examples": rows[:10]} for k, rows in buckets.items()},
          open(".ai/evidence/T-0085/c9-debt/c9-buckets.json", "w"), indent=1)
print("saved c9-buckets.json")
