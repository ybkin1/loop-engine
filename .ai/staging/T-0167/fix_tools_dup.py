#!/usr/bin/env python3
"""fix_tools_dup.py — 修复 tools.ts 中 OQA-4D handler 重复插入问题

1. 删除重复的 handler 块（保留一份）
2. 将 handler 移到 default 之前（switch 内正确位置）
3. 幂等：已修复则跳过
"""
import re
from pathlib import Path

TOOLS = Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\src\server\tools.ts")

HANDLER_BLOCK = r"""        case "loop_output_quality": {
          const { OutputQualityEngine, renderReportSummary } = await import("../core/output_quality.js");
          const engine = new OutputQualityEngine(root);
          const report = engine.verifyTarget(args!.target as string, {
            task_id: args?.task_id as string | undefined,
            phase: args?.phase as string | undefined,
            role: args?.role as string | undefined,
            dimensions: args?.dimensions as Array<"REQUIREMENTS" | "CODING" | "DESIGN" | "ENGINEERING"> | undefined,
          });
          return textReply(JSON.stringify(report, null, 2) + "\n\n" + renderReportSummary(report));
        }

        case "loop_quality_gate": {
          const { OutputQualityEngine } = await import("../core/output_quality.js");
          const engine = new OutputQualityEngine(root);
          const report = engine.verifyTarget(args!.target as string, {
            task_id: args?.task_id as string | undefined,
          });
          const gateable = report.overall !== "BLOCKED";
          return textReply(JSON.stringify({
            tool: "loop_quality_gate",
            target: report.target,
            overall: report.overall,
            gateable,
            blocked_by: report.blocked_by,
            content_hash: report.content_hash,
            evidence_ref: report.overall === "BLOCKED" ? null : `quality:${report.content_hash.slice(0, 12)}`,
          }, null, 2));
        }
"""

def main() -> int:
    text = TOOLS.read_text(encoding="utf-8")
    count = text.count('case "loop_output_quality":')
    if count == 1:
        # 已修复（或从未插入）——检查位置是否在 default 之前
        if 'case "loop_output_quality"' in text and text.index('case "loop_output_quality"') < text.index("default:"):
            print("[ok] single handler before default — no fix needed")
            return 0
    print(f"[fix] found {count} loop_output_quality case(s), normalizing...")

    # 1. 删除全部 OQA-4D handler 块（包括误插在 default 之后的）
    # 匹配从 case "loop_output_quality" 到其后的 case "loop_quality_gate" 块结束
    pattern = re.compile(
        r'        case "loop_output_quality": \{.*?\n        \}\n\n        case "loop_quality_gate": \{.*?\n        \}\n\n?',
        re.DOTALL,
    )
    text, n = pattern.subn("", text)
    print(f"[fix] removed {n} duplicated handler block(s)")

    # 2. 在 default 之前插入唯一 handler
    anchor = "        default:\n          return textReply(`Unknown tool: ${name}`);"
    if anchor not in text:
        print("[err] default anchor not found")
        return 1
    text = text.replace(anchor, HANDLER_BLOCK + "\n" + anchor, 1)
    TOOLS.write_text(text, encoding="utf-8")
    print("[fix] handler re-inserted before default")

    # 3. 校验
    text2 = TOOLS.read_text(encoding="utf-8")
    c = text2.count('case "loop_output_quality":')
    d = text2.count('case "loop_quality_gate":')
    assert c == 1 and d == 1, f"validation failed: cases={c},{d}"
    # 定位 switch 尾部（最后一个 default: 前的 case 位置）
    last_default = text2.rindex("default:")
    assert text2.rindex('case "loop_output_quality"') < last_default, "handler after default!"
    print(f"[ok] validated: 1×loop_output_quality, 1×loop_quality_gate, before default")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
