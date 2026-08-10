#!/usr/bin/env python3
"""fix_index_final.py — 清理 core/index.ts 中重复的 OQA 导出块

删除所有 OQA 导出块，重新插入唯一一份（带哨兵注释）。
"""
import re
from pathlib import Path

IDX = Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\src\core\index.ts")

OQA_BLOCK = """// ── Output Quality Engine (OQA-4D, T-0167) ──────────────────────────
export {
  OutputQualityEngine,
  renderReportSummary,
  DIMENSION_ORDER,
  ENGINE_VERSION,
} from "./output_quality.js";
export type {
  DimensionId,
  QualityFinding,
  QualityCheck,
  DimensionReport,
  OutputQualityReport,
  VerifyContext,
} from "./output_quality.js";
"""

def main() -> int:
    t = IDX.read_text(encoding="utf-8")
    n0 = t.count("from \"./output_quality.js\"")
    print(f"[info] found {n0} output_quality export reference(s)")

    # 删除所有 OQA 块（含注释行），保留最后一个文件尾换行结构
    pattern = re.compile(
        r"\n// ── Output Quality Engine \(OQA-4D, T-0167\) ──[─]*\nexport \{[\s\S]*?\} from \"./output_quality.js\";\nexport type \{[\s\S]*?\} from \"./output_quality.js\";\n",
    )
    t, n = pattern.subn("\n", t)
    print(f"[fix] removed {n} OQA export block(s)")

    # 在 loop_discovery 导出之后插入唯一一份
    anchor = "} from \"./loop_discovery.js\";"
    if anchor not in t:
        print("[err] loop_discovery anchor not found")
        return 1
    t = t.replace(anchor, anchor + "\n" + OQA_BLOCK, 1)
    IDX.write_text(t, encoding="utf-8")
    print("[fix] single OQA export block inserted after loop_discovery")

    # 校验
    t2 = IDX.read_text(encoding="utf-8")
    assert t2.count("from \"./output_quality.js\"") == 2, f"refs={t2.count('from \"./output_quality.js\"')}"
    assert t2.count("FindingSeverity") == 1, f"FindingSeverity={t2.count('FindingSeverity')}"
    print("[ok] validated: exactly one OQA export block, no duplicate FindingSeverity")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
