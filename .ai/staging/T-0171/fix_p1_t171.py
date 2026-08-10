#!/usr/bin/env python3
"""fix_p1_t171.py — 修复 T-0171 P1×4

P1-1: loop_oqa_patterns 补 remove 分支
P1-3: AI-03 行为验证剥离注释/字符串（防注释伪造）
P1-4: 中英映射补高频同义词
P1-2: AI-03 接入引擎（后续 wire 脚本）
"""
from pathlib import Path

LAB = Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab")
STAGING = Path(r"C:\Users\Administrator\ZCodeProject\loop-engine\.ai\staging\T-0171")

def main() -> int:
    tools = LAB / "src/server/tools.ts"
    tt = tools.read_text(encoding="utf-8")
    if '"remove"' not in tt:
        old = '          return textReply("loop_oqa_patterns: action must be list | add.");'
        new = '''          if (action === "remove") {
            const patternId = args?.pattern_id as string;
            if (!patternId) return textReply("loop_oqa_patterns remove: pattern_id required.");
            const { writeFileSync, existsSync } = await import("node:fs");
            const { join } = await import("node:path");
            const { parseDocument, stringify } = await import("yaml");
            const { readFileSync } = await import("node:fs");
            const pFile = join(root, ".ai", "oqa-patterns.yaml");
            if (!existsSync(pFile)) return textReply("No pattern library file.");
            const data = parseDocument(readFileSync(pFile, "utf-8")).toJSON() as { modes?: Array<Record<string, unknown>> };
            const modes = (data?.modes ?? []).filter(m => m.id !== patternId);
            writeFileSync(pFile, stringify({ version: 1, modes }), "utf-8");
            return textReply(`Pattern ${patternId} removed from ${pFile}.`);
          }
          return textReply("loop_oqa_patterns: action must be list | add | remove.");'''
        assert tt.count(old) == 1, "remove anchor"
        tt = tt.replace(old, new)
        tools.write_text(tt, encoding="utf-8")
        print("[P1-1] remove branch added")
    else:
        print("[P1-1] already present")

    src = STAGING / "oqa_patterns.ts"
    t = src.read_text(encoding="utf-8")

    old_map = '    "加密": ["encrypt"], "解密": ["decrypt"],\n  };'
    new_map = ('    "加密": ["encrypt"], "解密": ["decrypt"],\n'
               '    "查找": ["find", "get", "search"], "获取": ["get", "fetch"],\n'
               '    "添加": ["add", "create"], "移除": ["remove", "delete"],\n'
               '    "写入": ["write", "save"], "读取": ["read", "load"],\n'
               '    "认证": ["auth", "authenticate", "signIn"], "登出": ["logout", "signOut"],\n'
               '    "权限": ["permission", "checkPermission", "authorize"],\n'
               '  };')
    if '"查找":' not in t:
        assert t.count(old_map) == 1, "map anchor"
        t = t.replace(old_map, new_map)
        print("[P1-4] CN_EN_MAP expanded")
    else:
        print("[P1-4] already present")

    old_check = """  const allCode = codeFiles.map(f => contentMap.get(f) ?? "").join("\\n");
  const codeLower = allCode.toLowerCase();"""
    new_check = """  // P1-3 修复：剥离注释/字符串后再验证行为词（防注释/字符串伪造）
  const allCode = codeFiles.map(f => contentMap.get(f) ?? "").join("\\n");
  const stripped = allCode
    .replace(/\\/\\*[\\s\\S]*?\\*\\//g, "")
    .replace(/\\/\\/[^\\n]*/g, "")
    .replace(/"[^"]*"/g, "")
    .replace(/'[^']*'/g, "");
  const codeLower = stripped.toLowerCase();"""
    if "P1-3 修复" not in t:
        assert t.count(old_check) == 1, "strip anchor"
        t = t.replace(old_check, new_check)
        print("[P1-3] comment/string stripping added")
    else:
        print("[P1-3] already present")

    src.write_text(t, encoding="utf-8")
    (LAB / "src/core/oqa_patterns.ts").write_text(t, encoding="utf-8")
    print("[sync] oqa_patterns.ts deployed")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
