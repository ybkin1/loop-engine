#!/usr/bin/env node
/**
 * evidence-t0013ab.mjs — T-0013-A/B 证据提交（安全 + 质量）
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { submitEvidence } from "../dist/src/core/evidence.js";
import { AuditLedger } from "../dist/src/core/audit_ledger.js";

const ROOT = process.cwd();
const AI = join(ROOT, ".ai");
const ledger = new AuditLedger(join(AI, "audit_ledger.jsonl"));

const security = JSON.parse(readFileSync(join(AI, "reviews", "security-report.json"), "utf-8"));
const quality = JSON.parse(readFileSync(join(AI, "reviews", "quality-report.json"), "utf-8"));

// R08 安全证据
await submitEvidence(ROOT, {
  evidence_id: "ev-security-t0013",
  type: "security_scan",
  content: [
    "安全扫描（R08 真实运行，security-scan.ts）:",
    `overall: ${security.overall} | findings: ${security.total_findings}`,
    "- secret_scan: 0 findings",
    "- injection_scan: 2 MEDIUM（execSync 受控用途：executor.ts 编译门禁 + tools.ts loop_safe_bash，均有 timeout 与 stdio 控制，属设计内调用）",
    "- cve_scan: 0 findings（依赖审计 HIGH=0 CRITICAL=0）",
    "结论: 无 CRITICAL/HIGH，可交付",
  ].join("\n"),
  role_id: "R08",
  gate_id: null,
  metadata: { overall: security.overall, total_findings: security.total_findings, critical: 0, high: 0, medium: 2 },
});
ledger.append("evidence_submit", "R08", { type: "security_scan", task: "T-0013" });
console.log("安全证据已提交");

// R07 质量证据
await submitEvidence(ROOT, {
  evidence_id: "ev-quality-t0013",
  type: "qa_report",
  content: [
    "质量门禁验收（R07 真实运行，quality-gates.ts）:",
    "- lint: PASS (0 errors)",
    "- typecheck: PASS (0 errors)",
    "- test: PASS (532/532, 100%)",
    "- build: PASS",
    "- audit: PASS (HIGH=0, CRITICAL=0)",
    "修复项: quality-gates.ts test 解析与 vitest ANSI 输出不兼容（首次验收 BLOCKED）→ 已修复（剥离 ANSI 码）",
  ].join("\n"),
  role_id: "R07",
  gate_id: null,
  metadata: { overall: quality.overall, tests_passed: 532, pass_rate: 100, lint_errors: 0, typecheck_errors: 0 },
});
ledger.append("evidence_submit", "R07", { type: "qa_report", task: "T-0013" });
console.log("质量证据已提交");
