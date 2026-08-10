#!/usr/bin/env python3
"""wire_ai03_engine.py — P1-2：AI-03 + 模式库扫描接入 OQA 引擎

1. authenticity.ts 新增 AI-03 检查器（checkAcImplementation）
2. output_quality.ts 引擎新增 AI-04-pattern-library 检查器（scanWithPatterns）
"""
from pathlib import Path

LAB = Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab")

def main() -> int:
    # ── 1. authenticity.ts 注册 AI-03 ──
    auth = LAB / "src/core/authenticity.ts"
    t = auth.read_text(encoding="utf-8")
    if "AI-03-ac-implementation" not in t:
        # 在 CHECKER 数组末尾追加 AI-03 检查器
        marker = """  // ── AI-02: state-artifact drift (inconsistency) — WARNING ──"""
        block = """  // ── AI-03: AC 实现真实性（T-0171）—— BLOCKER/WARNING ──
  (env): QualityCheck => {
    const { root, ctx, files, contentMap } = env;
    const { checkAcImplementation } = require("./oqa_patterns.js");
    const result = checkAcImplementation(root, files, contentMap, ctx.task_id);
    return {
      checker_id: "AI-03-ac-implementation", dimension: "AUTHENTICITY",
      passed: !result.findings.some(f => f.severity === "BLOCKER"),
      findings: result.findings.map(f => ({
        checker_id: "AI-03-ac-implementation", severity: f.severity as "BLOCKER" | "WARNING",
        message: f.message, evidence: f.evidence, remediation: f.remediation,
      })),
      duration_ms: 0,
    };
  },

  // ── AI-02: state-artifact drift (inconsistency) — WARNING ──"""
        assert t.count(marker) == 1, "auth marker"
        t = t.replace(marker, block, 1)
        auth.write_text(t, encoding="utf-8")
        print("[1] authenticity.ts AI-03 registered")
    else:
        print("[1] AI-03 already present")

    # ── 2. output_quality.ts 新增 AI-04-pattern-library 检查器 ──
    oq = LAB / "src/core/output_quality.ts"
    t2 = oq.read_text(encoding="utf-8")
    if "AI-04-pattern-library" not in t2:
        # 在 authenticityCheckers 之后加 AI-04（通过 import + registry 追加）
        old_import = 'import { authenticityCheckers, AUTHENTICITY_LABEL } from "./authenticity.js";'
        new_import = ('import { authenticityCheckers, AUTHENTICITY_LABEL } from "./authenticity.js";\n'
                      'import { scanWithPatterns } from "./oqa_patterns.js";')
        if old_import not in t2:
            # 可能已有 oqa 导入
            print("[warn] authenticity import not found, trying alt")
            old_import = 'import { authenticityCheckers, AUTHENTICITY_LABEL } from "./authenticity.js";'
        if old_import in t2 and "scanWithPatterns" not in t2:
            t2 = t2.replace(old_import, new_import)
            print("[2] oqa_patterns import added")

        # 注册 AI-04 检查器到 CHECKER_REGISTRY
        old_reg = "  AUTHENTICITY: authenticityCheckers as unknown as Checker[],"
        new_reg = """  AUTHENTICITY: [
    ...authenticityCheckers as unknown as Checker[],
    (env: CheckerEnv): QualityCheck => {
      const hits = scanWithPatterns(env.root, env.files, env.contentMap);
      const findings = hits.map(h => ({
        checker_id: "AI-04-pattern-library", severity: h.severity as "BLOCKER" | "WARNING" | "INFO",
        message: h.message, evidence: h.evidence, remediation: h.remediation,
      }));
      return {
        checker_id: "AI-04-pattern-library", dimension: "AUTHENTICITY",
        passed: !findings.some(f => f.severity === "BLOCKER"),
        findings, duration_ms: 0,
      };
    },
  ],"""
        assert t2.count(old_reg) == 1, "registry anchor"
        t2 = t2.replace(old_reg, new_reg)
        oq.write_text(t2, encoding="utf-8")
        print("[2] AI-04-pattern-library registered in CHECKER_REGISTRY")
    else:
        print("[2] AI-04 already present")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
