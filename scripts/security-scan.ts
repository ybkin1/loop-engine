/**
 * security-scan.ts — Deterministic security scanner
 *
 * Scans for: secret leaks, injection patterns, dangerous functions,
 * and dependency CVEs.
 *
 * Usage:
 *   npx tsx scripts/security-scan.ts [project_root] [--scan-dir src]
 */

import { execSync } from "node:child_process";
import { readFileSync, writeFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { join, resolve, extname, relative } from "node:path";

// ── Types ──────────────────────────────────────────────
export interface SecurityFinding {
  id: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
  category: "secret" | "injection" | "dangerous_fn" | "cve" | "config";
  file: string;
  line: number;
  code_evidence: string;
  description: string;
}

export interface SecurityScanResult {
  name: string;
  status: "pass" | "blocked";
  findings: SecurityFinding[];
  findings_count: number;
  by_severity: Record<string, number>;
  duration_ms: number;
}

export interface SecurityReport {
  schema: "security_report/v1";
  project_root: string;
  scans: SecurityScanResult[];
  overall: "PASS" | "BLOCKED";
  blocked_by: string[];
  total_findings: number;
  timestamp: string;
}

// ── Secret Patterns ────────────────────────────────────
const SECRET_PATTERNS: { pattern: RegExp; id: string; severity: SecurityFinding["severity"]; description: string }[] = [
  { pattern: /AKIA[0-9A-Z]{16}/, id: "SEC-AWS-KEY", severity: "CRITICAL", description: "AWS Access Key ID" },
  { pattern: /(aws_secret_access_key|aws_secret_key)\s*[=:]\s*\S+/i, id: "SEC-AWS-SECRET", severity: "CRITICAL", description: "AWS Secret Key" },
  { pattern: /(api[_-]?key|apikey)\s*[=:]\s*['"][a-zA-Z0-9]{20,}['"]/i, id: "SEC-API-KEY", severity: "HIGH", description: "Hardcoded API key" },
  { pattern: /(password|passwd|pwd)\s*[=:]\s*['"][^'"]+['"]/i, id: "SEC-PASSWORD", severity: "HIGH", description: "Hardcoded password" },
  { pattern: /(secret|token)\s*[=:]\s*['"][a-zA-Z0-9+/=]{20,}['"]/i, id: "SEC-SECRET", severity: "HIGH", description: "Hardcoded secret/token" },
  { pattern: /-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----/, id: "SEC-PRIVATE-KEY", severity: "CRITICAL", description: "Private key in source" },
  { pattern: /(db_password|database_password|mysql_password|pg_password)\s*[=:]\s*\S+/i, id: "SEC-DB-PASS", severity: "CRITICAL", description: "Database password" },
  { pattern: /ghp_[a-zA-Z0-9]{36}/, id: "SEC-GH-TOKEN", severity: "CRITICAL", description: "GitHub personal access token" },
  { pattern: /sk-[a-zA-Z0-9]{32,}/, id: "SEC-SK", severity: "HIGH", description: "Secret key (sk-...)" },
];

// ── Injection Patterns ─────────────────────────────────
const INJECTION_PATTERNS: { pattern: RegExp; id: string; severity: SecurityFinding["severity"]; description: string }[] = [
  { pattern: /eval\s*\(/, id: "SEC-EVAL", severity: "HIGH", description: "eval() usage — potential code injection" },
  { pattern: /(?<!\/\/).*exec\s*\(\s*[^)]*\+/, id: "SEC-EXEC-CONCAT", severity: "HIGH", description: "exec() with string concatenation — command injection risk" },
  { pattern: /innerHTML\s*=/, id: "SEC-INNERHTML", severity: "MEDIUM", description: "innerHTML assignment — XSS risk" },
  { pattern: /document\.write\s*\(/, id: "SEC-DOC-WRITE", severity: "MEDIUM", description: "document.write() — XSS risk" },
  { pattern: /SELECT\s+.*FROM\s+.*(\$\{|\+\s*)/i, id: "SEC-SQL-INJECT", severity: "CRITICAL", description: "Potential SQL injection (string interpolation in query)" },
  { pattern: /child_process\.exec\s*\(\s*[^)]*\+/, id: "SEC-CHILD-EXEC", severity: "HIGH", description: "child_process.exec with concatenation" },
];

// ── Dangerous Function Patterns ────────────────────────
const DANGEROUS_FN_PATTERNS: { pattern: RegExp; id: string; severity: SecurityFinding["severity"]; description: string }[] = [
  { pattern: /(?<!\/\/).*\bexecSync\s*\(/, id: "SEC-EXEC-SYNC", severity: "MEDIUM", description: "execSync() — blocking shell command" },
  { pattern: /(?<!\/\/).*\bspawn\s*\(\s*['"]sh['"]/, id: "SEC-SPAWN-SH", severity: "MEDIUM", description: "spawn('sh') — shell invocation" },
  { pattern: /process\.env\.\w+\s*\|\|\s*['"]default/, id: "SEC-ENV-DEFAULT", severity: "LOW", description: "Environment variable with hardcoded fallback" },
];

// ── File Scanner ───────────────────────────────────────
const SCAN_EXTENSIONS = new Set([".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rb", ".java", ".yaml", ".yml", ".json", ".env", ".toml", ".cfg", ".ini"]);
const SKIP_DIRS = new Set(["node_modules", ".git", "dist", "build", ".ai", "coverage", ".test-loop-tmp", ".test-integration-tmp"]);

function walkDir(dir: string, base: string): string[] {
  const files: string[] = [];
  if (!existsSync(dir)) return files;

  for (const entry of readdirSync(dir)) {
    const fullPath = join(dir, entry);
    const rel = relative(base, fullPath);

    if (SKIP_DIRS.has(entry) || entry.startsWith(".") && entry !== ".env") continue;

    try {
      const stat = statSync(fullPath);
      if (stat.isDirectory()) {
        files.push(...walkDir(fullPath, base));
      } else if (SCAN_EXTENSIONS.has(extname(fullPath))) {
        files.push(fullPath);
      }
    } catch { /* skip inaccessible */ }
  }
  return files;
}

function scanFile(filePath: string, projectRoot: string, patterns: typeof SECRET_PATTERNS): SecurityFinding[] {
  const findings: SecurityFinding[] = [];
  let content: string;
  try { content = readFileSync(filePath, "utf-8"); } catch { return findings; }

  const lines = content.split("\n");
  const relPath = relative(projectRoot, filePath);

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    for (const p of patterns) {
      if (p.pattern.test(line)) {
        findings.push({
          id: `${p.id}-${i + 1}`,
          severity: p.severity,
          category: p.id.startsWith("SEC-AWS") || p.id.startsWith("SEC-API") || p.id.startsWith("SEC-PASSWORD") || p.id.startsWith("SEC-SECRET") || p.id.startsWith("SEC-DB") || p.id.startsWith("SEC-GH") || p.id.startsWith("SEC-SK") || p.id.startsWith("SEC-PRIVATE") ? "secret" : p.id.startsWith("SEC-EVAL") || p.id.startsWith("SEC-EXEC") || p.id.startsWith("SEC-INNER") || p.id.startsWith("SEC-DOC") || p.id.startsWith("SEC-SQL") || p.id.startsWith("SEC-CHILD") ? "injection" : "dangerous_fn",
          file: relPath,
          line: i + 1,
          code_evidence: line.trim().slice(0, 120),
          description: p.description,
        });
      }
    }
  }

  return findings;
}

// ── Scan Functions ─────────────────────────────────────
function runSecretScan(projectRoot: string, scanDir: string): SecurityScanResult {
  const start = Date.now();
  const dir = join(projectRoot, scanDir);
  const files = walkDir(dir, projectRoot);
  const findings: SecurityFinding[] = [];

  for (const f of files) {
    findings.push(...scanFile(f, projectRoot, SECRET_PATTERNS));
  }

  const bySeverity: Record<string, number> = {};
  for (const f of findings) bySeverity[f.severity] = (bySeverity[f.severity] ?? 0) + 1;

  return {
    name: "secret_scan",
    status: findings.some(f => f.severity === "CRITICAL" || f.severity === "HIGH") ? "blocked" : "pass",
    findings,
    findings_count: findings.length,
    by_severity: bySeverity,
    duration_ms: Date.now() - start,
  };
}

function runInjectionScan(projectRoot: string, scanDir: string): SecurityScanResult {
  const start = Date.now();
  const dir = join(projectRoot, scanDir);
  const files = walkDir(dir, projectRoot);
  const findings: SecurityFinding[] = [];

  for (const f of files) {
    findings.push(...scanFile(f, projectRoot, [...INJECTION_PATTERNS, ...DANGEROUS_FN_PATTERNS]));
  }

  const bySeverity: Record<string, number> = {};
  for (const f of findings) bySeverity[f.severity] = (bySeverity[f.severity] ?? 0) + 1;

  return {
    name: "injection_scan",
    status: findings.some(f => f.severity === "CRITICAL") ? "blocked" : "pass",
    findings,
    findings_count: findings.length,
    by_severity: bySeverity,
    duration_ms: Date.now() - start,
  };
}

function runCveScan(projectRoot: string): SecurityScanResult {
  const start = Date.now();
  const findings: SecurityFinding[] = [];

  const pkgJson = join(projectRoot, "package.json");
  if (existsSync(pkgJson)) {
    try {
      const result = execSync("npm audit --json 2>&1", { cwd: projectRoot, encoding: "utf-8", timeout: 60_000 });
      const audit = JSON.parse(result);
      const vulns = audit.vulnerabilities ?? {};
      for (const [name, info] of Object.entries(vulns)) {
        const v = info as { severity?: string; via?: { url?: string; cves?: string[] }[] };
        const severity = (v.severity?.toUpperCase() ?? "MEDIUM") as SecurityFinding["severity"];
        findings.push({
          id: `CVE-${name}`,
          severity,
          category: "cve",
          file: "package.json",
          line: 0,
          code_evidence: `${name}@${(v as { range?: string }).range ?? "unknown"}`,
          description: v.via?.[0]?.cves?.[0] ?? `Vulnerability in ${name}`,
        });
      }
    } catch { /* audit may fail if vulnerabilities found */ }
  }

  const bySeverity: Record<string, number> = {};
  for (const f of findings) bySeverity[f.severity] = (bySeverity[f.severity] ?? 0) + 1;

  return {
    name: "cve_scan",
    status: findings.some(f => f.severity === "CRITICAL" || f.severity === "HIGH") ? "blocked" : "pass",
    findings,
    findings_count: findings.length,
    by_severity: bySeverity,
    duration_ms: Date.now() - start,
  };
}

// ── Main Runner ────────────────────────────────────────
export function runSecurityScan(projectRoot: string, scanDir = "src"): SecurityReport {
  const root = resolve(projectRoot);

  const scans: SecurityScanResult[] = [
    runSecretScan(root, scanDir),
    runInjectionScan(root, scanDir),
    runCveScan(root),
  ];

  const blocked = scans.filter(s => s.status === "blocked").map(s => s.name);
  const totalFindings = scans.reduce((sum, s) => sum + s.findings_count, 0);

  return {
    schema: "security_report/v1",
    project_root: root,
    scans,
    overall: blocked.length > 0 ? "BLOCKED" : "PASS",
    blocked_by: blocked,
    total_findings: totalFindings,
    timestamp: new Date().toISOString(),
  };
}

// ── CLI ────────────────────────────────────────────────
if (process.argv[1]?.includes("security-scan")) {
  const root = process.argv[2] || process.cwd();
  const scanDirIdx = process.argv.indexOf("--scan-dir");
  const scanDir = scanDirIdx >= 0 ? process.argv[scanDirIdx + 1] : "src";

  const report = runSecurityScan(root, scanDir);

  console.log(`\nSecurity Report: ${report.overall}`);
  console.log("=".repeat(50));
  for (const s of report.scans) {
    const icon = s.status === "pass" ? "✓" : "✗";
    console.log(`  ${icon} ${s.name.padEnd(16)} ${s.status.toUpperCase().padEnd(8)} ${s.findings_count} findings`);
    for (const f of s.findings.slice(0, 5)) {
      console.log(`      ${f.severity.padEnd(8)} ${f.file}:${f.line} — ${f.description}`);
    }
    if (s.findings.length > 5) console.log(`      ... and ${s.findings.length - 5} more`);
  }

  const outPath = join(root, ".ai", "security_report.json");
  writeFileSync(outPath, JSON.stringify(report, null, 2), "utf-8");
  console.log(`\nReport saved: ${outPath}`);

  process.exit(report.overall === "BLOCKED" ? 1 : 0);
}
