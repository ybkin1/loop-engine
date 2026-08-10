#!/usr/bin/env python3
"""fix_tools_reg2.py — 修复 tools.ts loop_prompt 行被截断 + OQA 注册位置

问题：fix_tools_reg.py 的锚点 'Generate a four-quadrant' 只匹配行首，
把 OQA 注册块插进了 loop_prompt 行中间，破坏该行。
修复：重建完整的 loop_prompt 行 + OQA 注册块，并正确放回数组内。
幂等：已修复则跳过。
"""
from pathlib import Path

TOOLS = Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\src\server\tools.ts")

PROMPT_FULL_LINE = '      { name: "loop_prompt", description: "Generate a four-quadrant collaboration prompt automatically. Mode: \'user\' (full copy-paste), \'compact\' (quick), \'subagent\' (role context). User never needs to remember prompt structure.", inputSchema: { type: "object", properties: { task_description: { type: "string", description: "What you want to do" }, role_id: { type: "string", description: "Role ID (R01-R11) for role-specific guidance" }, phase_id: { type: "string", description: "Current phase" }, known_info: { type: "string", description: "What you already know" }, known_gaps: { type: "string", description: "What you know you don\'t know" }, constraints: { type: "string", description: "Time/resource/tech constraints" }, experience_level: { type: "string", description: "Your experience level on this task" }, mode: { type: "string", description: "user | compact | subagent. Default: user" } } } },'

OQA_BLOCK = """      // ── T-0167 OQA-4D Output Quality tools ──
      { name: "loop_output_quality", description: "Four-dimension output quality verification (REQUIREMENTS/CODING/DESIGN/ENGINEERING). Returns structured report with BLOCKER/WARNING/INFO findings.", inputSchema: { type: "object", properties: { project_root: { type: "string" }, target: { type: "string", description: "File or directory to verify (relative to project_root)" }, task_id: { type: "string", description: "Task ID for requirement binding (from state.yaml)" }, phase: { type: "string" }, role: { type: "string" }, dimensions: { type: "array", items: { type: "string" } } }, required: ["target"] } },
      { name: "loop_quality_gate", description: "Gate decision for an artifact: true when overall != BLOCKED. Call before gate advance / role handoff.", inputSchema: { type: "object", properties: { project_root: { type: "string" }, target: { type: "string", description: "File or directory to verify" }, task_id: { type: "string" } }, required: ["target"] } },
"""

def main() -> int:
    text = TOOLS.read_text(encoding="utf-8")

    # 1. 已修复检查：loop_prompt 完整行存在且 OQA 在其后
    if PROMPT_FULL_LINE in text:
        after = text[text.index(PROMPT_FULL_LINE):]
        if "OQA-4D Output Quality tools" in after.split("    ],")[0]:
            print("[ok] already fixed — loop_prompt intact, OQA inside array")
            return 0

    # 2. 删除所有 OQA 注册行（注释 + 两行注册）
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
    print(f"[fix] removed {removed} OQA registration line(s)")

    # 3. 修复被截断的 loop_prompt 行：找到残行（以 'Generate a four-quadrant' 开头但非完整行）
    #    残行形如: { name: "loop_prompt", description: "Generate a four-quadrant\n      // ── T-0167...
    import re
    broken = re.compile(
        r'      \{ name: "loop_prompt", description: "Generate a four-quadrant\n      // ── T-0167 OQA-4D Output Quality tools ──\n.*?\n    \],',
        re.DOTALL,
    )
    if broken.search(text):
        text = broken.sub(PROMPT_FULL_LINE + "\n" + OQA_BLOCK.rstrip("\n") + "\n    ],", text)
        print("[fix] rebuilt broken loop_prompt line + OQA block")
    else:
        # 可能残行后面直接跟 ], 或 OQA 已删但残行仍在
        broken2 = re.compile(
            r'      \{ name: "loop_prompt", description: "Generate a four-quadrant\n    \],',
            re.DOTALL,
        )
        if broken2.search(text):
            text = broken2.sub(PROMPT_FULL_LINE + "\n" + OQA_BLOCK.rstrip("\n") + "\n    ],", text)
            print("[fix] rebuilt broken loop_prompt line (no OQA after)")
        else:
            # loop_prompt 行完整但 OQA 不在 → 直接插
            if PROMPT_FULL_LINE in text:
                text = text.replace(PROMPT_FULL_LINE, PROMPT_FULL_LINE + "\n" + OQA_BLOCK.rstrip("\n"), 1)
                print("[fix] inserted OQA after intact loop_prompt line")
            else:
                print("[err] cannot locate loop_prompt line")
                return 1

    TOOLS.write_text(text, encoding="utf-8")

    # 4. 校验
    text2 = TOOLS.read_text(encoding="utf-8")
    assert PROMPT_FULL_LINE in text2, "loop_prompt line still broken"
    idx_prompt = text2.index('name: "loop_prompt"')
    idx_oqa = text2.index('name: "loop_output_quality"')
    idx_close = text2.index("    ],")
    idx_handle = text2.index("// ── Handle tool calls")
    ok = idx_prompt < idx_oqa < idx_close < idx_handle
    assert ok, f"validation failed: prompt={idx_prompt} oqa={idx_oqa} close={idx_close} handle={idx_handle}"
    assert text2.count('name: "loop_output_quality"') == 1, "duplicate registration!"
    print("[ok] validated: loop_prompt intact, single OQA registration inside array")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
