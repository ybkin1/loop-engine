#!/usr/bin/env python3
"""fix_tools_final.py — 彻底修复 tools.ts OQA handler（审查 F1，P1）

问题：handler 被重复插入多份（当前 5 份），default 被放在重复块之前。
修复：
  1. 删除全部 OQA handler 块（case loop_output_quality + loop_quality_gate 成对块）
  2. 将唯一 handler 插入 switch 内、default 之前
  3. 移除 T-0167 注册表重复项（保留 1 份注册）
  4. 重建 dist（由外部 npm run build 完成）
幂等：已修复则跳过。
"""
import re
from pathlib import Path

TOOLS = Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\src\server\tools.ts")

# 单个 handler 块的精确形态（成对：loop_output_quality + loop_quality_gate）
HANDLER_BLOCK = r'''        case "loop_output_quality": {
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
'''

def main() -> int:
    t = TOOLS.read_text(encoding="utf-8")
    n_cases = t.count('case "loop_output_quality":')
    print(f"[info] current loop_output_quality cases: {n_cases}")

    if n_cases == 1:
        # 校验 default 是否在 handler 之后（正确位置）
        idx_case = t.index('case "loop_output_quality"')
        last_default = t.rindex("default:")
        if idx_case < last_default:
            print("[ok] already fixed — single handler before default")
            return 0

    # 1. 删除所有 OQA handler 成对块（含前导注释行，若存在）
    pattern = re.compile(
        r'(?:\n        // ── T-0167 OQA-4D handlers ──)?\n        case "loop_output_quality": \{[^{}]*\{[^{}]*\}[^{}]*\{[^{}]*\}[^{}]*\{[^{}]*\}[^{}]*\}[^{}]*\n        \}\n\n        case "loop_quality_gate": \{[\s\S]*?\n        \}\n',
    )
    t, n = pattern.subn("\n", t)
    print(f"[fix] removed {n} duplicated handler block(s)")

    # 2. 若仍有残留（宽松匹配），逐行清理
    if t.count('case "loop_output_quality":') > 0:
        lines = t.split("\n")
        out: list[str] = []
        i = 0
        removed = 0
        while i < len(lines):
            line = lines[i]
            if 'case "loop_output_quality":' in line:
                # 跳过到 loop_quality_gate 块结束
                removed += 1
                while i < len(lines) and 'case "loop_quality_gate":' not in lines[i]:
                    i += 1
                while i < len(lines) and not lines[i].strip() == "}":
                    i += 1
                i += 1  # 跳过闭合 }
                # 跳过后续空行
                while i < len(lines) and lines[i].strip() == "":
                    i += 1
                continue
            out.append(line)
            i += 1
        t = "\n".join(out)
        print(f"[fix] line-level cleanup removed {removed} block(s)")

    # 3. 移除注册表重复项（保留 1 份 loop_output_quality 注册）
    reg_count = t.count('name: "loop_output_quality"')
    if reg_count > 1:
        # 保留第一份，删除其余（成对删除 loop_output_quality + loop_quality_gate 注册行）
        lines = t.split("\n")
        out: list[str] = []
        i = 0
        kept = False
        removed = 0
        while i < len(lines):
            line = lines[i]
            if 'name: "loop_output_quality"' in line:
                if kept:
                    # 删除本行 + 下一行 loop_quality_gate
                    removed += 1
                    i += 1
                    while i < len(lines) and 'name: "loop_quality_gate"' not in lines[i]:
                        i += 1
                    i += 1  # 跳过 gate 注册行
                    continue
                kept = True
            out.append(line)
            i += 1
        t = "\n".join(out)
        print(f"[fix] registration cleanup removed {removed} duplicate(s)")

    # 4. 插入唯一 handler 到 default 之前
    anchor = '        default:\n          return textReply(`Unknown tool: ${name}`);'
    if anchor not in t:
        print("[err] default anchor not found")
        return 1
    t = t.replace(anchor, HANDLER_BLOCK + "\n" + anchor, 1)

    TOOLS.write_text(t, encoding="utf-8")

    # 5. 校验
    t2 = TOOLS.read_text(encoding="utf-8")
    c = t2.count('case "loop_output_quality":')
    g = t2.count('case "loop_quality_gate":')
    r = t2.count('name: "loop_output_quality"')
    assert c == 1 and g == 1 and r == 1, f"validation failed: cases={c},{g},regs={r}"
    assert t2.index('case "loop_output_quality"') < t2.rindex("default:"), "handler after default!"
    print(f"[ok] validated: cases={c}, gates={g}, regs={r}, handler before default")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
