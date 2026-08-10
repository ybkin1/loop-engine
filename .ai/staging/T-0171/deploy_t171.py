#!/usr/bin/env python3
"""deploy_t171.py — T-0171 部署：oqa_patterns.ts + MCP 工具 + 引擎接线"""
from pathlib import Path

LAB = Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab")
STAGING = Path(r"C:\Users\Administrator\ZCodeProject\loop-engine\.ai\staging\T-0171")

def main() -> int:
    dst = LAB / "src/core/oqa_patterns.ts"
    src = STAGING / "oqa_patterns.ts"
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    print("[copy] src/core/oqa_patterns.ts")

    idx = LAB / "src/core/index.ts"
    t = idx.read_text(encoding="utf-8")
    if "loadOqaPatterns" not in t:
        block = "\n// ── OQA Patterns + AI-03 (T-0171) ──────────────────────────────────\nexport { loadOqaPatterns, scanWithPatterns, checkAcImplementation } from \"./oqa_patterns.js\";\nexport type { OqaPattern, AcImplementationResult } from \"./oqa_patterns.js\";\n"
        idx.write_text(t.rstrip() + "\n" + block, encoding="utf-8")
        print("[patch] core/index.ts exports appended")
    else:
        print("[same] core/index.ts already wired")

    tools = LAB / "src/server/tools.ts"
    tt = tools.read_text(encoding="utf-8")
    if "loop_oqa_patterns" not in tt:
        reg = """
      { name: "loop_oqa_patterns", description: "Query or add OQA pattern-library entries (laziness/hallucination/fabrication patterns).", inputSchema: { type: "object", properties: { action: { type: "string", description: "list | add" }, project_root: { type: "string" }, pattern_id: { type: "string" }, pattern_yaml: { type: "string", description: "YAML pattern entry (for add)" } }, required: ["action"] } },
"""
        anchor_reg = '      { name: "loop_prompt",'
        assert tt.count(anchor_reg) == 1, "tools reg anchor"
        tt = tt.replace(anchor_reg, reg + '      { name: "loop_prompt",', 1)

        handler = """
        case "loop_oqa_patterns": {
          const { loadOqaPatterns } = await import("../core/oqa_patterns.js");
          const action = args?.action as string;
          if (action === "list") {
            const patterns = loadOqaPatterns(root);
            return textReply(JSON.stringify(patterns.map(p => ({ id: p.id, dimension: p.dimension, severity: p.severity, pattern_count: p.patterns.length })), null, 2));
          }
          if (action === "add") {
            const patternYaml = args?.pattern_yaml as string;
            if (!patternYaml) return textReply("loop_oqa_patterns add: pattern_yaml required.");
            const { writeFileSync, existsSync } = await import("node:fs");
            const { join } = await import("node:path");
            const { parseDocument, stringify } = await import("yaml");
            const { readFileSync } = await import("node:fs");
            const pFile = join(root, ".ai", "oqa-patterns.yaml");
            let data: { modes?: unknown[] } = { modes: [] };
            if (existsSync(pFile)) {
              const parsed = parseDocument(readFileSync(pFile, "utf-8")).toJSON() as { modes?: unknown[] };
              if (parsed?.modes) data = parsed;
            }
            const entry = parseDocument(patternYaml).toJSON();
            if (!entry || typeof entry !== "object") return textReply("loop_oqa_patterns add: invalid YAML.");
            data.modes = data.modes ?? [];
            data.modes.push(entry);
            writeFileSync(pFile, stringify(data), "utf-8");
            return textReply(`Pattern added to ${pFile}.`);
          }
          return textReply("loop_oqa_patterns: action must be list | add.");
        }

"""
        anchor_h = "        default:\n          return textReply(`Unknown tool: ${name}`);"
        assert tt.count(anchor_h) == 1, "tools handler anchor"
        tt = tt.replace(anchor_h, handler + anchor_h, 1)
        tools.write_text(tt, encoding="utf-8")
        print("[patch] tools.ts loop_oqa_patterns registered")
    else:
        print("[same] tools.ts already wired")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
