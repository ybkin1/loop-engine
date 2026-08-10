#!/usr/bin/env python3
"""fix_f3_deployed.py — 直接在部署目标应用 F3（verifyTarget 越界校验）"""
from pathlib import Path

ENGINE = Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\src\core\output_quality.ts")

def main() -> int:
    t = ENGINE.read_text(encoding="utf-8")
    if "escapes project root" in t:
        print("[ok] F3 already applied")
        return 0

    old = """  verifyTarget(target: string, ctx: VerifyContext = {}): OutputQualityReport {
    const files = listFilesUnder(this.root, target);"""
    new = """  verifyTarget(target: string, ctx: VerifyContext = {}): OutputQualityReport {
    if (typeof target !== "string" || target.trim().length === 0) {
      throw new Error(`Invalid target: ${String(target)} — expected a non-empty path.`);
    }
    const resolvedTarget = resolve(this.root, target);
    const relCheck = relative(this.root, resolvedTarget);
    if (relCheck.startsWith("..")) {
      throw new Error(`Target escapes project root: ${target}`);
    }
    const files = listFilesUnder(this.root, target);"""
    assert t.count(old) == 1, f"anchor count={t.count(old)}"
    t = t.replace(old, new)
    ENGINE.write_text(t, encoding="utf-8")
    print("[F3] applied to deployed engine")

    staging = Path(r"C:\Users\Administrator\ZCodeProject\loop-engine\.ai\staging\T-0167\output_quality.ts")
    staging.write_text(t, encoding="utf-8")
    print("[sync] staging copy updated")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
