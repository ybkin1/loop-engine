#!/usr/bin/env python3
"""fix_auth_types.py — 修复 authenticity.ts AI-03 类型问题"""
from pathlib import Path

AUTH = Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\src\core\authenticity.ts")

def main() -> int:
    t = AUTH.read_text(encoding="utf-8")
    old = '    const { checkAcImplementation } = require("./oqa_patterns.js");\n    const result = checkAcImplementation(root, files, contentMap, ctx.task_id);'
    new = '    const { checkAcImplementation } = await import("./oqa_patterns.js");\n    const result = checkAcImplementation(root, files, contentMap, ctx.task_id);'
    assert t.count(old) == 1, f"require anchor={t.count(old)}"
    t = t.replace(old, new)

    old2 = "      findings: result.findings.map(f => ({"
    new2 = "      findings: result.findings.map((f: { severity: string; message: string; evidence: string; remediation: string }) => ({"
    assert t.count(old2) == 1, f"map anchor={t.count(old2)}"
    t = t.replace(old2, new2)
    AUTH.write_text(t, encoding="utf-8")
    print("[fix] authenticity.ts AI-03 types fixed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
