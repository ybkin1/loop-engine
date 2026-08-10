#!/usr/bin/env python3
"""fix_f458_deployed.py — 重新应用 F4/F5/F8 到部署目标（staging 同步失误导致丢失）"""
from pathlib import Path

ENGINE = Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\src\core\output_quality.ts")
GUARD = Path(r"C:\Users\Administrator\.qoder-cn\hooks\scripts\output_quality_guard.js")

def apply(engine: str) -> tuple[str, list[str]]:
    logs: list[str] = []

    # ── F4: DS-02 剥离注释/字符串 ──
    old_f4 = """    for (const f of tsFiles) {
      const c = contentMap.get(f) ?? "";
      const dir = dirname(join(root, f));
      const deps: string[] = [];
      for (const m of c.matchAll(/(?:from|import\\s*\\()\\s*[\"'](\\.[^\"']+)[\"']/g)) {"""
    new_f4 = """    for (const f of tsFiles) {
      const c = contentMap.get(f) ?? "";
      // 剥离注释与字符串字面量后再匹配 import，防注释/常量误报（F4）
      const codeOnly = c
        .replace(/\\/\\*[\\s\\S]*?\\*\\//g, "")
        .replace(/\\/\\/[^\\n]*/g, "")
        .replace(/\"[^\"]*\"/g, "")
        .replace(/'[^']*'/g, "");
      const dir = dirname(join(root, f));
      const deps: string[] = [];
      for (const m of codeOnly.matchAll(/(?:from|import\\s*\\()\\s*[\"'](\\.[^\"']+)[\"']/g)) {"""
    if "codeOnly" not in engine:
        assert engine.count(old_f4) == 1, f"F4 anchor count={engine.count(old_f4)}"
        engine = engine.replace(old_f4, new_f4)
        logs.append("[F4] DS-02 comment/string stripping applied")
    else:
        logs.append("[F4] already applied")

    # ── F5a: RQ-02 AC 边界匹配 ──
    old_f5a = """      const acId = (ac.match(/\\[(AC-\\d+)\\]/) || [])[1];
      if (!acId) continue;
      const hit = codeFiles.some(f => (contentMap.get(f) ?? "").includes(acId));
      if (hit) referenced += 1;"""
    new_f5a = """      const acId = (ac.match(/\\[(AC-\\d+)\\]/) || [])[1];
      if (!acId) continue;
      // \\b 边界匹配，防 "AC-010" 命中 "AC-01"（F5）
      const acPattern = new RegExp(`\\\\b${acId}\\\\b`);
      const hit = codeFiles.some(f => acPattern.test(contentMap.get(f) ?? ""));
      if (hit) referenced += 1;"""
    if "acPattern" not in engine:
        assert engine.count(old_f5a) == 1, f"F5a anchor count={engine.count(old_f5a)}"
        engine = engine.replace(old_f5a, new_f5a)
        logs.append("[F5a] RQ-02 AC boundary matching applied")
    else:
        logs.append("[F5a] already applied")

    # ── F5b: EN-01 精确基名比较 ──
    old_f5b = """    for (const f of codeFiles) {
      const base = basename(f, extname(f));
      const hasTest = testFiles.some(t => {
        const tb = basename(t).toLowerCase();
        const norm = base.toLowerCase().replace(/^test_/, "");
        return tb.includes(norm);
      });"""
    new_f5b = """    for (const f of codeFiles) {
      const base = basename(f, extname(f));
      const normBase = base.toLowerCase().replace(/^test_/, "");
      const hasTest = testFiles.some(t => {
        const tb = basename(t).toLowerCase().replace(/\\.(test|spec)\\.[a-z0-9]+$/, "");
        // 精确基名比较，防 "only" 命中 "lonely.test.ts"（F5）
        return tb === normBase || tb === "test_" + normBase;
      });"""
    if "normBase" not in engine:
        assert engine.count(old_f5b) == 1, f"F5b anchor count={engine.count(old_f5b)}"
        engine = engine.replace(old_f5b, new_f5b)
        logs.append("[F5b] EN-01 exact basename matching applied")
    else:
        logs.append("[F5b] already applied")

    return engine, logs


def apply_guard(guard: str) -> tuple[str, list[str]]:
    logs: list[str] = []
    if "effectiveContent" not in guard:
        old = """  const content = toolInput.content || toolInput.new_str || '';
  if (!content) process.exit(0);

  const warnings = [];
  const lines = content.split('\\n');"""
        new = """  const content = toolInput.content || toolInput.new_str || '';
  // SearchReplace 的内容在 replacements[].new_text（F8：防绕过）
  let effectiveContent = content;
  if (!effectiveContent && Array.isArray(toolInput.replacements)) {
    effectiveContent = toolInput.replacements
      .map((r) => (r && typeof r.new_text === 'string' ? r.new_text : ''))
      .join('\\n');
  }
  if (!effectiveContent) process.exit(0);

  const warnings = [];
  const lines = effectiveContent.split('\\n');"""
        assert guard.count(old) == 1, f"F8 anchor count={guard.count(old)}"
        guard = guard.replace(old, new)
        # 后续 content 引用改 effectiveContent
        guard = guard.replace("const m = content.match(SECRET_PATTERNS[i]);", "const m = effectiveContent.match(SECRET_PATTERNS[i]);")
        guard = guard.replace("const line = content.slice(0, m.index ?? 0).split('\\n').length;", "const line = effectiveContent.slice(0, m.index ?? 0).split('\\n').length;")
        guard = guard.replace("const m = content.match(re);", "const m = effectiveContent.match(re);")
        logs.append("[F8] guard replacements[].new_text handling applied")
    else:
        logs.append("[F8] already applied")
    return guard, logs


def main() -> int:
    e = ENGINE.read_text(encoding="utf-8")
    e, logs_e = apply(e)
    ENGINE.write_text(e, encoding="utf-8")

    g = GUARD.read_text(encoding="utf-8")
    g, logs_g = apply_guard(g)
    GUARD.write_text(g, encoding="utf-8")

    # 同步 staging
    Path(r"C:\Users\Administrator\ZCodeProject\loop-engine\.ai\staging\T-0167\output_quality.ts").write_text(e, encoding="utf-8")
    Path(r"C:\Users\Administrator\ZCodeProject\loop-engine\.ai\staging\T-0167\output_quality_guard.js").write_text(g, encoding="utf-8")

    for log in logs_e + logs_g:
        print(log)
    print("[sync] staging copies updated")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
