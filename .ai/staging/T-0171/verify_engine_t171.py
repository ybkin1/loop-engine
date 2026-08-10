#!/usr/bin/env python3
"""verify_engine_t171.py — 引擎 e2e：loop_output_quality 产出 AI-03/AI-04"""
import subprocess

ns = r"""
const { OutputQualityEngine } = require("./dist/src/core/output_quality.js");
const { mkdtempSync, writeFileSync, mkdirSync } = require("node:fs");
const { tmpdir } = require("node:os");
const { join, dirname } = require("node:path");
const root = mkdtempSync(join(tmpdir(), "t171-e2e-"));
function w(rel, c) { const p = join(root, rel); mkdirSync(dirname(p), { recursive: true }); writeFileSync(p, c, "utf-8"); }
w(".ai/state.yaml", "schema_version: 1\ncurrent_task_id: T-9\ncurrent_phase: S4\n");
w(".ai/tasks/T-9.md", "---\ntask_id: T-9\nallowed_paths:\n  - src/\n  - .ai/\n---\n# T-9\n## 可验证验收标准\n1. **[AC-01]** 用户登录功能 works\n");
w(".ai/oqa-patterns.yaml", "version: 1\nmodes:\n  - id: CUSTOM-X\n    dimension: CODING\n    severity: WARNING\n    patterns:\n      - \"return\\s+\\[\\s*1\\s*\\]\"\n    message: custom x\n    remediation: fix\n");

w("src/impl.ts", "export const unrelated = 1;\n");
const r1 = new OutputQualityEngine(root).verifyTarget("src", { task_id: "T-9", phase: "S4" });
const auth1 = r1.dimensions.find(d => d.dimension === "AUTHENTICITY");
console.log("S1 overall:", r1.overall, "blocked_by:", r1.blocked_by);
const ai03 = auth1.checks.find(c => c.checker_id === "AI-03-ac-implementation");
console.log("S1 AI-03 blockers:", ai03.findings.filter(f => f.severity === "BLOCKER").length);
const ai04 = auth1.checks.find(c => c.checker_id === "AI-04-pattern-library");
console.log("S1 AI-04 present:", !!ai04, "findings:", ai04.findings.length);

w("src/login.ts", "export function login(u, p) { return u === p; }\n");
w("src/fake.ts", "export function f() { return [1]; }\n");
const r2 = new OutputQualityEngine(root).verifyTarget("src", { task_id: "T-9", phase: "S4" });
const auth2 = r2.dimensions.find(d => d.dimension === "AUTHENTICITY");
const ai03b = auth2.checks.find(c => c.checker_id === "AI-03-ac-implementation");
console.log("S2 AI-03 blockers:", ai03b.findings.filter(f => f.severity === "BLOCKER").length);
const ai04b = auth2.checks.find(c => c.checker_id === "AI-04-pattern-library");
console.log("S2 AI-04 findings:", JSON.stringify(ai04b.findings.map(f => f.message.slice(0, 50))));
console.log("S2 overall:", r2.overall);
"""

r = subprocess.run(["node", "-e", ns], capture_output=True, text=True, encoding="utf-8", cwd=r"C:\Users\Administrator\.qoder-cn\loop-engine-lab")
print(r.stdout)
if r.stderr.strip():
    print("STDERR:", r.stderr[:300])
