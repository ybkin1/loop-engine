#!/usr/bin/env python3
"""fix_tools_reg.py — 修复 tools.ts 中 OQA-4D 工具注册位置

当前错误：工具注册被插到了 tools 数组的 `],` 之后（数组外）。
修复：删除数组外的注册行，重新插到 loop_prompt 注册行之后（数组内）。
幂等：已修复则跳过。
"""
from pathlib import Path

TOOLS = Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\src\server\tools.ts")

REG_BLOCK = """      // ── T-0167 OQA-4D Output Quality tools ──
      { name: "loop_output_quality", description: "Four-dimension output quality verification (REQUIREMENTS/CODING/DESIGN/ENGINEERING). Returns structured report with BLOCKER/WARNING/INFO findings.", inputSchema: { type: "object", properties: { project_root: { type: "string" }, target: { type: "string", description: "File or directory to verify (relative to project_root)" }, task_id: { type: "string", description: "Task ID for requirement binding (from state.yaml)" }, phase: { type: "string" }, role: { type: "string" }, dimensions: { type: "array", items: { type: "string" } } }, required: ["target"] } },
      { name: "loop_quality_gate", description: "Gate decision for an artifact: true when overall != BLOCKED. Call before gate advance / role handoff.", inputSchema: { type: "object", properties: { project_root: { type: "string" }, target: { type: "string", description: "File or directory to verify" }, task_id: { type: "string" } }, required: ["target"] } },
"""

def main() -> int:
    text = TOOLS.read_text(encoding="utf-8")

    # 1. 检查当前是否已正确（loop_prompt 行之后紧跟 OQA 注册，再跟 ],）
    prompt_line = '      { name: "loop_prompt", description: "Generate a four-quadrant'
    if prompt_line in text:
        after_prompt = text[text.index(prompt_line):]
        if after_prompt.startswith(prompt_line) and "OQA-4D Output Quality tools" in after_prompt.split("],")[0]:
            print("[ok] registration already inside tools array — no fix needed")
            return 0

    # 2. 删除数组外的注册块（在 ], 之后、Handle tool calls 之前的）
    import re
    bad_pattern = re.compile(
        r'    \],\n  \}\)\);\n      // ── T-0167 OQA-4D Output Quality tools ──\n      \{ name: "loop_output_quality".*?\n      \{ name: "loop_quality_gate".*?\n\n',
        re.DOTALL,
    )
    text, n = bad_pattern.subn(lambda m: m.group(0).split("// ── T-0167")[0] + "\n", text)
    if n > 0:
        print(f"[fix] removed {n} misplaced registration block(s)")
    else:
        # 尝试宽松模式：删除所有 OQA 注册行（不含注释）
        lines = text.split("\n")
        out = []
        skip = False
        removed = 0
        for line in lines:
            if '// ── T-0167 OQA-4D Output Quality tools ──' in line:
                skip = True
                removed += 1
                continue
            if skip and 'name: "loop_output_quality"' in line:
                removed += 1
                continue
            if skip and 'name: "loop_quality_gate"' in line:
                skip = False
                removed += 1
                continue
            out.append(line)
        text = "\n".join(out)
        if removed > 0:
            print(f"[fix] removed {removed} misplaced registration line(s)")

    # 3. 重新插入到 loop_prompt 行之后（数组内，], 之前）
    if prompt_line not in text:
        print("[err] loop_prompt anchor not found")
        return 1
    text = text.replace(prompt_line, prompt_line + "\n" + REG_BLOCK.rstrip("\n"), 1)
    TOOLS.write_text(text, encoding="utf-8")
    print("[fix] registration re-inserted inside tools array")

    # 4. 校验
    text2 = TOOLS.read_text(encoding="utf-8")
    idx_prompt = text2.index('name: "loop_prompt"')
    idx_oqa = text2.index('name: "loop_output_quality"')
    idx_close = text2.index("    ],")
    idx_handle = text2.index("// ── Handle tool calls")
    ok = idx_prompt < idx_oqa < idx_close < idx_handle
    assert ok, f"validation failed: prompt={idx_prompt} oqa={idx_oqa} close={idx_close} handle={idx_handle}"
    print("[ok] validated: registration inside tools array")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
