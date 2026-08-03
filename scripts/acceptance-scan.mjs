#!/usr/bin/env node
/**
 * acceptance-scan.mjs — T-0013 验收扫描：R08 安全 + R07 质量（真实运行）
 */
import { writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { runSecurityScan } from "../dist/scripts/security-scan.js";
import { runQualityGates } from "../dist/scripts/quality-gates.js";

const ROOT = process.cwd();
const AI = join(ROOT, ".ai");
const OUT = join(AI, "reviews");

mkdirSync(OUT, { recursive: true });

// ── R08 安全扫描（真实运行：secrets/injection/CVE） ──
console.log("== R08 安全扫描 ==");
const security = runSecurityScan(ROOT, "src");
console.log(`overall: ${security.overall} | total findings: ${security.total_findings}`);
for (const s of security.scans) {
  console.log(`  ${s.name}: ${s.status} (${s.findings_count})`);
  for (const f of s.findings.slice(0, 5)) {
    console.log(`    [${f.severity}] ${f.id} ${f.file}:${f.line} — ${f.description}`);
  }
}
if (security.blocked_by.length > 0) {
  console.log("BLOCKED BY:", security.blocked_by.join(", "));
}
writeFileSync(join(OUT, "security-report.json"), JSON.stringify(security, null, 2), "utf-8");
console.log("安全报告存档: .ai/reviews/security-report.json");

// ── R07 质量门禁（真实运行：lint/typecheck/test/build/audit） ──
console.log("\n== R07 质量门禁 ==");
const quality = runQualityGates(ROOT);
console.log(`overall: ${quality.overall} | timestamp: ${quality.timestamp}`);
for (const c of quality.checks) {
  console.log(`  ${c.name}: ${c.status} (value=${JSON.stringify(c.value)}, threshold=${JSON.stringify(c.threshold)}) ${c.detail}`);
}
if (quality.blocked_by.length > 0) {
  console.log("BLOCKED BY:", quality.blocked_by.join(", "));
}
writeFileSync(join(OUT, "quality-report.json"), JSON.stringify(quality, null, 2), "utf-8");
console.log("质量报告存档: .ai/reviews/quality-report.json");

console.log(`\n安全: ${security.overall} | 质量: ${quality.overall}`);
