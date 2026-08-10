#!/usr/bin/env python3
"""fix_f4_correct.py — 修正 F4：只剥离注释，保留字符串（import 路径不能被剥掉）"""
from pathlib import Path

ENGINE = Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\src\core\output_quality.ts")

def main() -> int:
    t = ENGINE.read_text(encoding="utf-8")
    old = """      // 剥离注释与字符串字面量后再匹配 import，防注释/常量误报（F4）
      const codeOnly = c
        .replace(/\\/\\*[\\s\\S]*?\\*\\//g, "")
        .replace(/\\/\\/[^\\n]*/g, "")
        .replace(/\"[^\"]*\"/g, "")
        .replace(/'[^']*'/g, "");"""
    new = """      // 只剥离注释后再匹配 import：字符串字面量必须保留（import 路径本身是字符串），
      // 但注释中的 `from "./x"` 文本会产生假依赖边（F4）。
      const codeOnly = c
        .replace(/\\/\\*[\\s\\S]*?\\*\\//g, "")
        .replace(/\\/\\/[^\\n]*/g, "");"""
    assert t.count(old) == 1, f"anchor count={t.count(old)}"
    t = t.replace(old, new)
    ENGINE.write_text(t, encoding="utf-8")
    print("[F4] corrected: strip comments only, keep strings")

    # 同步 staging
    Path(r"C:\Users\Administrator\ZCodeProject\loop-engine\.ai\staging\T-0167\output_quality.ts").write_text(t, encoding="utf-8")
    print("[sync] staging updated")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
