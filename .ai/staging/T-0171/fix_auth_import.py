#!/usr/bin/env python3
"""fix_auth_import.py — authenticity.ts AI-03 用静态 import 替代 require/await"""
from pathlib import Path

AUTH = Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\src\core\authenticity.ts")

def main() -> int:
    t = AUTH.read_text(encoding="utf-8")
    old_imp = 'import { parseDocument } from "yaml";'
    new_imp = 'import { parseDocument } from "yaml";\nimport { checkAcImplementation } from "./oqa_patterns.js";'
    if 'from "./oqa_patterns.js"' not in t:
        assert t.count(old_imp) == 1, f"import anchor={t.count(old_imp)}"
        t = t.replace(old_imp, new_imp)
        print("[1] static import added")

    old_call = '    const { checkAcImplementation } = await import("./oqa_patterns.js");\n    const result = checkAcImplementation(root, files, contentMap, ctx.task_id);'
    new_call = '    const result = checkAcImplementation(root, files, contentMap, ctx.task_id);'
    assert t.count(old_call) == 1, f"call anchor={t.count(old_call)}"
    t = t.replace(old_call, new_call)
    print("[2] await removed")
    AUTH.write_text(t, encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
