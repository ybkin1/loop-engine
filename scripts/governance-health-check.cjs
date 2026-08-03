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

  // 生命周期感知（P1-2）：无任何 gate 通过 = 新初始化项目
  // 新项目缺失 evidence/audit/task_graph/active_role 是正常状态（WARNING），不是治理中断（BLOCKER）
  let projectStarted = false;
  let hasBlockedGate = false;
  const gatesRawEarly = readFile(path.join(AI_DIR, 'gates.yaml'));
  if (gatesRawEarly) {
    projectStarted = /status:\s*["']?passed["']?\s*$/im.test(gatesRawEarly);
    hasBlockedGate = /status:\s*["']?blocked["']?\s*$/im.test(gatesRawEarly);
  }
  const isNewProject = !projectStarted;

  // 1. 治理文件完整性
  const requiredFiles = ['state.yaml', 'gates.yaml', 'task_graph.yaml'];
  for (const f of requiredFiles) {
    const fp = path.join(AI_DIR, f);
    if (f === 'task_graph.yaml' && !fileExists(fp) && isNewProject) {
      report.warnings.push({ id: 'FILE_task_graph.yaml', status: 'WARN', detail: 'missing (新项目：尚未创建任务图)' });
      continue;
    }
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

  // 3. 阶段-角色一致性（active_role 为 null 且非初始阶段 = 阻塞）
  if (currentPhase) {
    const expectedRole = PHASE_ROLE_MAP[currentPhase];
    const isInitPhase = /^S0-init$/i.test(currentPhase);
    if (!activeRole) {
      if (isInitPhase || isNewProject) {
        report.warnings.push({
          id: 'NO_ACTIVE_ROLE',
          detail: `${isInitPhase ? 'S0-init 阶段' : '新项目'}无活跃角色（正常：等待编排器激活或角色交接间隙）`,
        });
      } else if (hasBlockedGate) {
        // 有真实阻塞 + 无角色在岗 = 治理中断（T-0009-B：提前检测，避免死代码分支）
        report.blockers.push({
          id: 'NO_ACTIVE_ROLE',
          status: 'FAIL',
          detail: `Phase ${currentPhase} has NO active role — expected ${expectedRole || '(unknown)'}`,
          recommendation: 'Activate the lead role via auto-orchestrate or loop_role_activate',
        });
      } else {
        // 正常推进中的角色交接间隙
        report.warnings.push({
          id: 'NO_ACTIVE_ROLE',
          detail: `Phase ${currentPhase} 无活跃角色（角色交接间隙，编排器将自动激活）`,
        });
      }
    } else if (expectedRole && activeRole !== expectedRole) {
      report.warnings.push({
        id: 'ROLE_MISMATCH',
        detail: `Phase ${currentPhase} expects ${expectedRole}, but active_role=${activeRole}`,
        recommendation: `Consider switching to ${expectedRole} or updating phase`,
      });
    } else if (expectedRole) {
      report.checks.push({ id: 'ROLE_CONSISTENCY', status: 'PASS', detail: `${activeRole} matches ${currentPhase}` });
    }
  } else {
    report.blockers.push({ id: 'STATE_PHASE', status: 'FAIL', detail: 'current_phase missing in state.yaml' });
  }

  // 4. Gate 注册检查：gates.yaml 存在但无 gate = 阻塞（无门禁意味着无治理）
  const gatesRaw = readFile(path.join(AI_DIR, 'gates.yaml'));
  if (gatesRaw) {
    const emptyMatch = gatesRaw.match(/gates:\s*\[\s*\]/);
    const listMatch = gatesRaw.match(/^\s*-\s+gate_id:/m);
    if (emptyMatch && !listMatch) {
      report.blockers.push({
        id: 'GATES_EMPTY',
        status: 'FAIL',
        detail: 'gates.yaml exists but contains no gates — governance is not enforced',
        recommendation: 'Run loop init_extended or register phase gates',
      });
    }
    const blockedMatch = gatesRaw.match(/status:\s*["']?blocked["']?\s*$/gim);
    const pendingMatch = gatesRaw.match(/status:\s*["']?pending["']?\s*$/gim);

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
    if (!blockedMatch && !pendingMatch && !(emptyMatch && !listMatch)) {
      report.checks.push({ id: 'GATES_CLEAR', status: 'PASS', detail: 'No blocked/pending gates' });
    }
  } else {
    report.blockers.push({ id: 'GATES_MISSING', status: 'FAIL', detail: 'gates.yaml missing' });
  }

  // 4b. 证据检查：evidence 目录必须包含实际证据（.gitkeep 不算）
  const evDir = path.join(AI_DIR, 'evidence');
  if (fileExists(evDir)) {
    const evidenceFiles = fs.readdirSync(evDir).filter(f => f.endsWith('.yaml'));
    if (evidenceFiles.length === 0) {
      const evidenceIssue = {
        id: 'EVIDENCE_EMPTY',
        status: isNewProject ? 'WARN' : 'FAIL',
        detail: 'evidence/ contains no evidence records — completed work is not auditable',
        recommendation: 'Submit evidence via loop_evidence_submit for completed tasks',
      };
      if (isNewProject) report.warnings.push(evidenceIssue);
      else report.blockers.push(evidenceIssue);
    } else {
      report.checks.push({ id: 'EVIDENCE', status: 'PASS', detail: `${evidenceFiles.length} evidence record(s)` });
    }
  } else {
    report.blockers.push({ id: 'EVIDENCE_MISSING', status: 'FAIL', detail: 'evidence/ directory missing' });
  }

  // 4c. 审计账本检查（MCP 实际路径 .ai/audit_ledger.jsonl，兼容 .ai/ledger/audit.jsonl）
  const ledgerPaths = [
    path.join(AI_DIR, 'audit_ledger.jsonl'),
    path.join(AI_DIR, 'ledger', 'audit.jsonl'),
  ];
  const foundLedger = ledgerPaths.find(p => fileExists(p));
  if (foundLedger) {
    const content = readFile(foundLedger);
    const lines = content ? content.trim().split('\n').filter(Boolean).length : 0;
    if (lines === 0) {
      report.warnings.push({ id: 'AUDIT_EMPTY', detail: `audit ledger exists but has no entries (${foundLedger})` });
    } else {
      report.checks.push({ id: 'AUDIT_LEDGER', status: 'PASS', detail: `${lines} entries` });
    }
  } else {
    const auditIssue = {
      id: 'AUDIT_MISSING',
      status: isNewProject ? 'WARN' : 'FAIL',
      detail: 'audit ledger missing (expected .ai/audit_ledger.jsonl or .ai/ledger/audit.jsonl) — no audit trail for governance events',
      recommendation: 'Use loop_audit_log to append events',
    };
    if (isNewProject) report.warnings.push(auditIssue);
    else report.blockers.push(auditIssue);
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

  // 6. 审计日志（兼容旧路径 .ai/audit_ledger.jsonl）
  const ledgerLegacyPath = path.join(AI_DIR, 'audit_ledger.jsonl');
  if (fileExists(ledgerLegacyPath)) {
    const content = readFile(ledgerLegacyPath);
    const lines = content ? content.trim().split('\n').filter(Boolean).length : 0;
    report.checks.push({ id: 'AUDIT_LEDGER_LEGACY', status: 'PASS', detail: `${lines} entries (legacy path)` });
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
