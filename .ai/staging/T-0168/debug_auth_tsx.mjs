#!/usr/bin/env node
/**
 * debug_auth_tsx.mjs — 用 tsx 运行（与 vitest 相同 src 源码路径），复现 4 个失败
 */
import { mkdtempSync, writeFileSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { OutputQualityEngine } from "./src/core/output_quality.js";

const root = mkdtempSync(join(tmpdir(), "auth-dbg2-"));
function write(rel, content) {
  const p = join(root, rel);
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, content, "utf-8");
}
write(".ai/state.yaml", "schema_version: 1\ncurrent_task_id: T-0001\ncurrent_phase: S4\n");
write(".ai/tasks/T-0001.md", "---\ntask_id: T-0001\nallowed_paths:\n  - src/\n  - tests/\n  - docs/\n  - .ai/\n---\n# T-0001\n## 可验证验收标准\n1. **[AC-01]** feature works\n2. **[AC-02]** tests pass\n");

const engine = new OutputQualityEngine(root);
function show(label, report, checkerId) {
  const dim = report.dimensions.find(d => d.dimension === "AUTHENTICITY");
  const ck = dim ? dim.checks.find(c => c.checker_id === checkerId) : null;
  console.log(`=== ${label} ===`);
  if (!ck) { console.log("  (checker not found, dims:", report.dimensions.map(d => d.dimension).join(","), ")"); return; }
  console.log("  findings:", JSON.stringify(ck.findings.map(f => f.severity + ":" + f.message.slice(0, 90))));
}

// AF-01
write(".ai/evidence/T-0001/fake.json", JSON.stringify({ content: "real output", content_hash: "f".repeat(64) }));
show("AF-01 hash mismatch", engine.verifyTarget(".ai/evidence/T-0001/fake.json", { task_id: "T-0001" }), "AF-01-evidence-authenticity");

// AL-02 happy path
write("src/g.ts", "export const g = 1;\n");
write("tests/g.test.ts", "import { g } from '../src/g.js';\nexpect(g).toBe(1);\n");
show("AL-02 happy-path", engine.verifyTarget("tests", { task_id: "T-0001" }), "AL-02-test-quality");

// AI-02 empty src
show("AI-02 empty target", engine.verifyTarget("src", { task_id: "T-0001", phase: "S4" }), "AI-02-state-artifact-drift");
