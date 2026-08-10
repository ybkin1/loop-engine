#!/usr/bin/env python3
"""fix_index_idempotent.py — 最终幂等修复：core/index.ts 只保留一份 OQA 导出块

- 删除所有 output_quality 导出块
- 重新插入唯一一份（哨兵注释与 deploy 脚本检查串一致："OQA-4D Output Quality Engine"）
"""
import re
from pathlib import Path

IDX = Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\src\core\index.ts")

SENTINEL = "OQA-4D Output Quality Engine"

OQA_BLOCK = f"""// ── {SENTINEL} ──────────────────────────
export {{
  OutputQualityEngine,
  renderReportSummary,
  DIMENSION_ORDER,
  ENGINE_VERSION,
}} from "./output_quality.js";
export type {{
  DimensionId,
  QualityFinding,
  QualityCheck,
  DimensionReport,
  OutputQualityReport,
  VerifyContext,
}} from "./output_quality.js";
"""

def main() -> int:
    t = IDX.read_text(encoding="utf-8")
    n0 = t.count("from \"./output_quality.js\"")
    print(f"[info] found {n0} output_quality export reference(s)")

    # 删除所有块（匹配两种注释写法）
    pattern = re.compile(
        r"\n// ── (?:OQA-4D Output Quality Engine|Output Quality Engine \(OQA-4D, T-0167\)) ──[─]*\nexport \{[\s\S]*?\} from \"./output_quality.js\";\nexport type \{[\s\S]*?\} from \"./output_quality.js\";\n",
    )
    t, n = pattern.subn("\n", t)
    print(f"[fix] removed {n} OQA export block(s)")

    if SENTINEL not in t:
        anchor = "} from \"./loop_discovery.js\";"
        if anchor not in t:
            print("[err] loop_discovery anchor not found")
            return 1
        t = t.replace(anchor, anchor + "\n" + OQA_BLOCK, 1)
        print("[fix] inserted single OQA export block")
    IDX.write_text(t, encoding="utf-8")

    t2 = IDX.read_text(encoding="utf-8")
    assert t2.count("from \"./output_quality.js\"") == 2, f"refs={t2.count('from \"./output_quality.js\"')}"
    assert t2.count(SENTINEL) == 1, f"sentinel={t2.count(SENTINEL)}"
    print("[ok] validated: exactly one OQA export block")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
