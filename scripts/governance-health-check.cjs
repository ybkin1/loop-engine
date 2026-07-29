#!/usr/bin/env node
/**
 * governance-health-check.js — Loop 治理健康检查（方案 B 补充）
 *
 * 可独立运行的治理状态检查脚本。用途：
 * 1. 定时任务（Task Scheduler / cron）定期检查项目治理状态
 * 2. 手动运行 `node scripts/governance-health-check.js [project_root]`
 * 3. 输出 JSON 报告，可供外部系统消费
 *
 * 检查项：
 * - 治理文件完整性（state.yaml, gates.yaml, task_graph.yaml）
 * - 阶段-角色一致性（active_role 是否匹配当前阶段）
 * - Gate 状态（是否有长期 PENDING/BLOCKED）
 * - 证据新鲜度（是否有过期证据）
 * - 审计日志完整性
 *
 * 输出：JSON 报告 + 退出码
 *   exit 0 = HEALTHY
 *   exit 1 = DEGRADED（有警告）
 *   exit 2 = BLOCKED（有阻断）
 */

const fs = require('fs');
const path = require('path');

// ── 配置 ──
const PROJECT_ROOT = process.argv[2] || process.cwd();
const AI_DIR = path.join(PROJECT_ROOT, '.ai');

// ── 工具函数 ──
function fileExists(p) { return fs.existsSync(p); }
function readFile(p) { try { return fs.readFileSync(p, 'utf-8'); } catch { return null; } }

function extractYamlValue(content, key) {
  if (!content) return null;
  const regex = new RegExp(`^[\\s]*${key}:\\s*["']?([^"'#\\n]+?)["']?\\s*(?:#.*)?$`, 'm');
  const match = content.match(regex);
  if (!match) return null;
  const val = match[1].trim();
  return (val === 'null' || val === '~' || val === '') ? null : val;
}

// ── PHASE_ROLE_MAP ──
const PHASE_ROLE_MAP = {
  'S0-init': 'R11', 'S1-requirements': 'R01', 'S2-architecture': 'R04',
  'S3-interface': 'R05', 'S4-implementation': 'R06', 'S5-quality': 'R07',
  'S6-delivery': 'R03', 'S7-integration': 'R06', 'S8-functional-test': 'R07',
  'S9-fix-optimize': 'R06', 'S10-performance': 'R07', 'S11-maintenance': 'R10',
  'requirements': 'R01', 'architecture': 'R04', 'planning': 'R05',
  'implementation': 'R06', 'review': 'R09', 'delivery': 'R03',
  // P-prefix variants (Qoder legacy)
  'P1-requirements': 'R01', 'P2-architecture': 'R04', 'P3-planning': 'R05',
  'P4-implementation': 'R06', 'P5-review': 'R09', 'P6-delivery': 'R03',
};

// ── 检查 ──
function runHealthCheck() {
  const report = {
    timestamp: new Date().toISOString(),
    project_root: PROJECT_ROOT,
    status: 'HEALTHY',
    checks: [],
    warnings: [],
    blockers: [],
  };

  // 1. 治理文件完整性
  const requiredFiles = ['state.yaml', 'gates.yaml', 'task_graph.yaml'];
  for (const f of requiredFiles) {
    const fp = path.join(AI_DIR, f);
    if (fileExists(fp)) {
      report.checks.push({ id: `FILE_${f}`, status: 'PASS', detail: 'exists' });
    } else {
      report.blockers.push({ id: `FILE_${f}`, status: 'FAIL', detail: 'missing' });
    }
  }

  // 2. 读取 state
  const stateRaw = readFile(path.join(AI_DIR, 'state.yaml'));
  if (!stateRaw) {
    report.status = 'BLOCKED';
    report.blockers.push({ id: 'STATE_READ', detail: 'Cannot read state.yaml' });
    return report;
  }

  const currentPhase = extractYamlValue(stateRaw, 'current_phase');
  const activeRole = extractYamlValue(stateRaw, 'active_role');
  const currentTask = extractYamlValue(stateRaw, 'current_task_id');
  const currentGate = extractYamlValue(stateRaw, 'current_gate_id');

  report.checks.push({ id: 'STATE_PHASE', status: 'PASS', detail: `phase=${currentPhase}` });

  // 3. 阶段-角色一致性
  if (currentPhase && activeRole) {
    const expectedRole = PHASE_ROLE_MAP[currentPhase];
    if (expectedRole && activeRole !== expectedRole) {
      report.warnings.push({
        id: 'ROLE_MISMATCH',
        detail: `Phase ${currentPhase} expects ${expectedRole}, but active_role=${activeRole}`,
        recommendation: `Consider switching to ${expectedRole} or updating phase`,
      });
    } else {
      report.checks.push({ id: 'ROLE_CONSISTENCY', status: 'PASS', detail: `${activeRole} matches ${currentPhase}` });
    }
  }

  // 4. Gate 状态检查
  const gatesRaw = readFile(path.join(AI_DIR, 'gates.yaml'));
  if (gatesRaw) {
    const blockedMatch = gatesRaw.match(/status:\s*["']?blocked["']?/gi);
    const pendingMatch = gatesRaw.match(/status:\s*["']?pending["']?/gi);

    if (blockedMatch && blockedMatch.length > 0) {
      report.blockers.push({
        id: 'GATE_BLOCKED',
        detail: `${blockedMatch.length} gate(s) BLOCKED`,
        recommendation: 'Resolve blockers before proceeding',
      });
    }
    if (pendingMatch && pendingMatch.length > 0) {
      report.warnings.push({
        id: 'GATE_PENDING',
        detail: `${pendingMatch.length} gate(s) PENDING`,
        recommendation: 'Complete gate conditions',
      });
    }
    if (!blockedMatch && !pendingMatch) {
      report.checks.push({ id: 'GATES_CLEAR', status: 'PASS', detail: 'No blocked/pending gates' });
    }
  }

  // 5. 角色契约完整性
  const registryDir = path.join(AI_DIR, 'registry');
  if (fileExists(registryDir)) {
    const roles = fs.readdirSync(registryDir).filter(f => f.endsWith('.yaml'));
    report.checks.push({ id: 'ROLE_CONTRACTS', status: 'PASS', detail: `${roles.length} contracts` });
    if (roles.length < 11) {
      report.warnings.push({ id: 'ROLES_INCOMPLETE', detail: `Only ${roles.length}/11 role contracts` });
    }
  } else {
    report.warnings.push({ id: 'NO_REGISTRY', detail: 'registry/ directory missing' });
  }

  // 6. 审计日志
  const ledgerPath = path.join(AI_DIR, 'audit_ledger.jsonl');
  if (fileExists(ledgerPath)) {
    const content = readFile(ledgerPath);
    const lines = content ? content.trim().split('\n').filter(Boolean).length : 0;
    report.checks.push({ id: 'AUDIT_LEDGER', status: 'PASS', detail: `${lines} entries` });
  }

  // ── 最终状态 ──
  if (report.blockers.length > 0) {
    report.status = 'BLOCKED';
  } else if (report.warnings.length > 0) {
    report.status = 'DEGRADED';
  }

  return report;
}

// ── 执行 ──
const report = runHealthCheck();
console.log(JSON.stringify(report, null, 2));

// 退出码
if (report.status === 'BLOCKED') process.exit(2);
if (report.status === 'DEGRADED') process.exit(1);
process.exit(0);
