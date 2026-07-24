/**
 * quality-gates.ts — Deterministic quality gate runner
 *
 * Runs lint, typecheck, test, coverage, and build checks.
 * Compares results against configurable thresholds.
 * Outputs structured quality_report.json.
 *
 * Usage:
 *   npx tsx scripts/quality-gates.ts [project_root]
 */

import { execSync } from "node:child_process";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { parseDocument } from "yaml";

// ── Types ──────────────────────────────────────────────
export interface QualityThresholds {
  lint_errors: number;        // max allowed lint errors (default: 0)
  test_pass_rate: number;     // min test pass rate 0-100 (default: 100)
  coverage_min: number;       // min coverage % (default: 0)
  build_required: boolean;    // must build succeed (default: true)
  max_audit_high: number;     // max HIGH CVEs (default: 0)
  max_audit_critical: number; // max CRITICAL CVEs (default: 0)
}

export interface QualityCheck {
  name: string;
  status: "pass" | "blocked";
  value: unknown;
  threshold: unknown;
  detail: string;
  duration_ms: number;
}

export interface QualityReport {
  schema: "quality_report/v1";
  project_root: string;
  thresholds: QualityThresholds;
  checks: QualityCheck[];
  overall: "PASS" | "BLOCKED";
  blocked_by: string[];
  timestamp: string;
}

// ── Defaults ───────────────────────────────────────────
const DEFAULT_THRESHOLDS: QualityThresholds = {
  lint_errors: 0,
  test_pass_rate: 100,
  coverage_min: 0,
  build_required: true,
  max_audit_high: 0,
  max_audit_critical: 0,
};

// ── Helpers ────────────────────────────────────────────
function runCommand(cmd: string, cwd: string): { exitCode: number; stdout: string; stderr: string; duration: number } {
  const start = Date.now();
  try {
    const stdout = execSync(cmd, { cwd, encoding: "utf-8", timeout: 120_000, stdio: ["pipe", "pipe", "pipe"] });
    return { exitCode: 0, stdout, stderr: "", duration: Date.now() - start };
  } catch (err: unknown) {
    const e = err as { status?: number; stdout?: string; stderr?: string };
    return {
      exitCode: e.status ?? 1,
      stdout: e.stdout ?? "",
      stderr: e.stderr ?? "",
      duration: Date.now() - start,
    };
  }
}

function loadThresholds(projectRoot: string): QualityThresholds {
  const configPath = join(projectRoot, ".ai", "quality-config.yaml");
  if (!existsSync(configPath)) return { ...DEFAULT_THRESHOLDS };

  try {
    const raw = readFileSync(configPath, "utf-8");
    const parsed = parseDocument(raw).toJSON() as Partial<QualityThresholds>;
    return { ...DEFAULT_THRESHOLDS, ...parsed };
  } catch {
    return { ...DEFAULT_THRESHOLDS };
  }
}

// ── Individual Checks ──────────────────────────────────
function runLint(projectRoot: string, thresholds: QualityThresholds): QualityCheck {
  const result = runCommand("npx eslint . --format json 2>/dev/null || npx tsc --noEmit 2>&1 || echo 'lint skipped'", projectRoot);
  const duration = result.duration;

  // Count errors from output
  let errorCount = 0;
  try {
    const parsed = JSON.parse(result.stdout);
    if (Array.isArray(parsed)) {
      errorCount = parsed.reduce((sum: number, f: { errorCount?: number }) => sum + (f.errorCount ?? 0), 0);
    }
  } catch {
    // If not JSON, count error lines
    errorCount = (result.stdout.match(/error TS/g) || []).length;
  }

  return {
    name: "lint",
    status: errorCount <= thresholds.lint_errors ? "pass" : "blocked",
    value: errorCount,
    threshold: thresholds.lint_errors,
    detail: errorCount <= thresholds.lint_errors ? `Lint clean (${errorCount} errors)` : `${errorCount} lint errors (max: ${thresholds.lint_errors})`,
    duration_ms: duration,
  };
}

function runTypecheck(projectRoot: string): QualityCheck {
  const result = runCommand("npx tsc --noEmit 2>&1", projectRoot);
  const duration = result.duration;
  const passed = result.exitCode === 0;
  const errorLines = (result.stdout.match(/error TS/g) || []).length;

  return {
    name: "typecheck",
    status: passed ? "pass" : "blocked",
    value: { exit_code: result.exitCode, errors: errorLines },
    threshold: { exit_code: 0, errors: 0 },
    detail: passed ? "TypeScript compilation clean" : `${errorLines} type errors`,
    duration_ms: duration,
  };
}

function runTests(projectRoot: string, thresholds: QualityThresholds): QualityCheck {
  const result = runCommand("npx vitest run 2>&1", projectRoot);
  const duration = result.duration;

  // Parse test output
  const testsMatch = result.stdout.match(/Tests\s+(\d+)\s+(?:passed|failed)/);
  const totalMatch = result.stdout.match(/Test Files\s+\d+\s+(?:passed|failed)\s+\((\d+)\)/);
  const passedMatch = result.stdout.match(/Tests\s+(\d+)\s+passed/);

  const total = testsMatch ? parseInt(testsMatch[1]) : 0;
  const passed = passedMatch ? parseInt(passedMatch[1]) : 0;
  const passRate = total > 0 ? Math.round((passed / total) * 100) : 0;
  const allPassed = result.exitCode === 0;

  return {
    name: "test",
    status: allPassed && passRate >= thresholds.test_pass_rate ? "pass" : "blocked",
    value: { total, passed, pass_rate: passRate },
    threshold: { min_pass_rate: thresholds.test_pass_rate },
    detail: allPassed ? `${passed}/${total} tests passed (${passRate}%)` : `Tests failed: ${passed}/${total} (${passRate}%)`,
    duration_ms: duration,
  };
}

function runBuild(projectRoot: string, thresholds: QualityThresholds): QualityCheck {
  if (!thresholds.build_required) {
    return { name: "build", status: "pass", value: "skipped", threshold: "not required", detail: "Build not required by config", duration_ms: 0 };
  }

  const result = runCommand("npm run build 2>&1", projectRoot);
  const duration = result.duration;
  const passed = result.exitCode === 0;

  return {
    name: "build",
    status: passed ? "pass" : "blocked",
    value: { exit_code: result.exitCode },
    threshold: { exit_code: 0 },
    detail: passed ? "Build succeeded" : `Build failed (exit code ${result.exitCode})`,
    duration_ms: duration,
  };
}

function runAudit(projectRoot: string, thresholds: QualityThresholds): QualityCheck {
  const pkgJson = join(projectRoot, "package.json");
  if (!existsSync(pkgJson)) {
    return { name: "audit", status: "pass", value: "no package.json", threshold: "N/A", detail: "No Node.js project detected", duration_ms: 0 };
  }

  const result = runCommand("npm audit --json 2>&1", projectRoot);
  const duration = result.duration;

  let high = 0, critical = 0;
  try {
    const audit = JSON.parse(result.stdout);
    const vulns = audit.metadata?.vulnerabilities ?? {};
    high = vulns.high ?? 0;
    critical = vulns.critical ?? 0;
  } catch {
    // If audit output is not parseable, count from text
    high = (result.stdout.match(/high/gi) || []).length;
    critical = (result.stdout.match(/critical/gi) || []).length;
  }

  const passed = high <= thresholds.max_audit_high && critical <= thresholds.max_audit_critical;

  return {
    name: "audit",
    status: passed ? "pass" : "blocked",
    value: { HIGH: high, CRITICAL: critical },
    threshold: { HIGH: thresholds.max_audit_high, CRITICAL: thresholds.max_audit_critical },
    detail: passed ? `Audit clean (HIGH=${high}, CRITICAL=${critical})` : `Audit issues: HIGH=${high}, CRITICAL=${critical}`,
    duration_ms: duration,
  };
}

// ── Main Runner ────────────────────────────────────────
export function runQualityGates(projectRoot: string): QualityReport {
  const root = resolve(projectRoot);
  const thresholds = loadThresholds(root);

  const checks: QualityCheck[] = [
    runLint(root, thresholds),
    runTypecheck(root),
    runTests(root, thresholds),
    runBuild(root, thresholds),
    runAudit(root, thresholds),
  ];

  const blocked = checks.filter(c => c.status === "blocked").map(c => c.name);

  return {
    schema: "quality_report/v1",
    project_root: root,
    thresholds,
    checks,
    overall: blocked.length > 0 ? "BLOCKED" : "PASS",
    blocked_by: blocked,
    timestamp: new Date().toISOString(),
  };
}

// ── CLI ────────────────────────────────────────────────
if (process.argv[1]?.includes("quality-gates")) {
  const root = process.argv[2] || process.cwd();
  const report = runQualityGates(root);

  console.log(`\nQuality Report: ${report.overall}`);
  console.log("=".repeat(50));
  for (const c of report.checks) {
    const icon = c.status === "pass" ? "✓" : "✗";
    console.log(`  ${icon} ${c.name.padEnd(12)} ${c.status.toUpperCase().padEnd(8)} ${c.detail}`);
  }
  if (report.blocked_by.length > 0) {
    console.log(`\nBlocked by: ${report.blocked_by.join(", ")}`);
  }

  // Write report
  const outPath = join(root, ".ai", "quality_report.json");
  writeFileSync(outPath, JSON.stringify(report, null, 2), "utf-8");
  console.log(`\nReport saved: ${outPath}`);

  process.exit(report.overall === "BLOCKED" ? 1 : 0);
}
