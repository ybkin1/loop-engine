#!/usr/bin/env node
/**
 * auto-orchestrate.js — Loop Engineering Auto-Orchestration Engine v2
 *
 * UserPromptSubmit Hook: Detects phase/role state and injects MANDATORY
 * orchestration directives. Roles are dispatched automatically via Agent tool
 * when their phase is active and no other role is working.
 *
 * v2 enhancements (T-0008):
 * - Detects completed roles → auto-activates next in chain
 * - Includes exact Agent tool dispatch parameters
 * - Includes RoleContext generation command
 * - Non-optional: directive MUST be followed
 */

const fs = require('fs');
const path = require('path');

// hook_common.js 优先加载本地副本，找不到时回退到 Qoder 全局 hooks 目录
// （部署事实：运行时 hook 实际安装在 ~/.qoder-cn/hooks/scripts/）
let common;
try {
  common = require('./hook_common.js');
} catch (err) {
  const globalHook = path.join(
    process.env.USERPROFILE || process.env.HOME || '',
    '.qoder-cn', 'hooks', 'scripts', 'hook_common.js'
  );
  try {
    common = require(globalHook);
  } catch (err2) {
    console.error('[auto-orchestrate] hook_common.js not found locally or globally:', err2.message);
    process.exit(2);
  }
}

const PHASE_ROLE_MAP = {
  'S0-init':            { lead: 'R11', participants: [], name: 'Init' },
  'S1-requirements':    { lead: 'R01', participants: ['R02'], name: 'Requirements' },
  'S2-architecture':    { lead: 'R04', participants: ['R01', 'R08'], name: 'Architecture' },
  'S3-interface':       { lead: 'R05', participants: ['R04'], name: 'Interface Design' },
  'S4-implementation':  { lead: 'R06', participants: ['R05'], name: 'Implementation' },
  'S5-quality':         { lead: 'R07', participants: ['R06', 'R08'], name: 'Quality' },
  'S6-delivery':        { lead: 'R03', participants: ['R10', 'R08'], name: 'Delivery' },
  'S7-integration':     { lead: 'R06', participants: ['R05', 'R07'], name: 'Integration' },
  'S8-functional-test': { lead: 'R07', participants: ['R01'], name: 'Functional Test' },
  'S9-fix-optimize':    { lead: 'R06', participants: ['R09', 'R07'], name: 'Fix & Optimize' },
  'S10-performance':    { lead: 'R07', participants: ['R10', 'R04'], name: 'Performance' },
  'S11-maintenance':    { lead: 'R10', participants: ['R08', 'R06'], name: 'Maintenance' },
  'requirements':       { lead: 'R01', participants: ['R02'], name: 'Requirements' },
  'architecture':       { lead: 'R04', participants: ['R08'], name: 'Architecture' },
  'planning':           { lead: 'R05', participants: ['R04'], name: 'Planning' },
  'implementation':     { lead: 'R06', participants: ['R05'], name: 'Implementation' },
  'review':             { lead: 'R09', participants: ['R07', 'R08'], name: 'Review' },
  'delivery':           { lead: 'R03', participants: ['R10'], name: 'Delivery' },
  'P1-requirements':    { lead: 'R01', participants: ['R02'], name: 'Requirements' },
  'P2-architecture':    { lead: 'R04', participants: ['R08'], name: 'Architecture' },
  'P3-planning':        { lead: 'R05', participants: ['R04'], name: 'Planning' },
  'P4-implementation':  { lead: 'R06', participants: ['R05'], name: 'Implementation' },
  'P5-review':          { lead: 'R09', participants: ['R07', 'R08'], name: 'Review' },
  'P6-delivery':        { lead: 'R03', participants: ['R10'], name: 'Delivery' },
};

const ROLE_NAMES = {
  'R01': 'Product Manager', 'R02': 'Project Manager', 'R03': 'Delivery Manager',
  'R04': 'System Architect', 'R05': 'Module Architect', 'R06': 'Developer',
  'R07': 'QA Engineer', 'R08': 'Security Engineer', 'R09': 'Code Reviewer',
  'R10': 'Release Ops', 'R11': 'Orchestrator',
};

const ROLE_SKILLS = {
  'R01': 'loop-r01-product', 'R02': 'loop-r02-plan', 'R03': 'loop-r03-delivery',
  'R04': 'loop-r04-architect', 'R05': 'loop-r05-module', 'R06': 'loop-r06-developer',
  'R07': 'loop-r07-qa', 'R08': 'loop-r08-security', 'R09': 'loop-r09-reviewer',
  'R10': 'loop-r10-ops', 'R11': 'loop-r11-orchestrator',
};

const PHASE_ORDER = [
  'S0-init', 'S1-requirements', 'S2-architecture', 'S3-interface',
  'S4-implementation', 'S5-quality', 'S6-delivery', 'S7-integration',
  'S8-functional-test', 'S9-fix-optimize', 'S10-performance', 'S11-maintenance',
];

/**
 * Read completed_roles from state.yaml raw content.
 * Returns array of role IDs that have completed.
 */
function getCompletedRoles(root) {
  try {
    const statePath = path.join(root, '.ai', 'state.yaml');
    const content = fs.readFileSync(statePath, 'utf-8');
    const listMatch = content.match(/completed_roles:\s*\n((?:\s+-\s+.+\n?)*)/);
    if (!listMatch) return [];
    return listMatch[1]
      .split('\n')
      .map(function(line) { return line.replace(/^\s*-\s*/, '').trim().replace(/['"]/g, ''); })
      .filter(Boolean);
  } catch {
    return [];
  }
}

/**
 * Generate Agent tool dispatch parameters for a role.
 */
function buildAgentDispatch(root, roleId, phaseName) {
  var skillName = ROLE_SKILLS[roleId] || 'loop-engineering';
  var contextFile = path.join(root, '.ai', 'role-context', roleId + '.md').replace(/\\/g, '/');
  return [
    '**Agent Dispatch Parameters:**',
    '```',
    '{',
    '  "skill": "' + skillName + '",',
    '  "description": "Auto-activate ' + roleId + ' for ' + phaseName + '",',
    '  "prompt": "You are ' + roleId + ' (' + ROLE_NAMES[roleId] + '). ' + phaseName + ' phase. Follow Internal Loop. Context: ' + contextFile + '",',
    '  "must_read": ["' + contextFile + '", ".ai/registry/' + roleId + '.yaml", ".ai/internal-loops.md"],',
    '  "allowed_write": ["src/", "tests/", "docs/", ".ai/"]',
    '}',
    '```',
    '',
    '**Before dispatch:**',
    '1. Update .ai/state.yaml: active_role -> ' + roleId + ', role_activated_at -> now',
    '2. Generate role context: `node -e "import(\'../src/core/role_context.js\').then(m=>m.generateRoleContext(\'' + root + '\',\'' + roleId + '\'))"`',
    '3. Verify context file exists: ' + contextFile,
    '4. Dispatch Agent tool with parameters above',
  ].join('\n');
}

async function main() {
  var event = await common.readStdin();
  var root = common.projectRoot(event);

  if (!common.isGovernanceProject(root)) { process.exit(0); }

  var state = common.loadState(root);
  if (!state) { process.exit(0); }

  var loopActive = common.isLoopActive(root);
  // Even if loop is not fully active, if there's a current_task_id we should orchestrate
  if (!loopActive && !state.current_task_id) { process.exit(0); }

  var currentPhase = state.current_phase || '';
  var activeRole = state.active_role || null;
  var completedRoles = getCompletedRoles(root);
  var mapping = PHASE_ROLE_MAP[currentPhase];

  if (!mapping) { process.exit(0); }

  var expectedRole = mapping.lead;
  var expectedRoleName = ROLE_NAMES[expectedRole] || expectedRole;
  var phaseName = mapping.name || currentPhase;

  var lines = [];
  lines.push('## AUTO-ORCHESTRATION [v2] — Phase: ' + currentPhase);
  lines.push('');

  // ── Check if expected role is already completed ──
  var leadCompleted = completedRoles.indexOf(expectedRole) >= 0;

  if (leadCompleted) {
    // Lead role done → auto-advance signal
    lines.push('### SIGNAL: ' + expectedRole + '(' + expectedRoleName + ') COMPLETED');
    lines.push('');
    lines.push('Role ' + expectedRole + ' has completed for phase ' + currentPhase + '.');
    if (mapping.participants.length > 0) {
      var pendingParticipants = mapping.participants.filter(function(r) { return completedRoles.indexOf(r) < 0; });
      if (pendingParticipants.length > 0) {
        lines.push('**Next: Activate participant role(s): ' + pendingParticipants.join(', ') + '**');
        lines.push('');
        lines.push(buildAgentDispatch(root, pendingParticipants[0], phaseName + ' (participant)'));
      } else {
        lines.push('**Next: All roles for this phase complete. Advance gate.**');
        lines.push('- Check gate conditions with loop_gate_check');
        lines.push('- Request user approval for phase advance');
      }
    } else {
      lines.push('**Next: All roles for this phase complete. Advance gate.**');
    }
  } else if (!activeRole) {
    // No active role → MUST activate lead role NOW
    lines.push('### MANDATORY: Activate ' + expectedRole + '(' + expectedRoleName + ')');
    lines.push('');
    lines.push('Phase **' + currentPhase + '** (' + phaseName + ') has NO active role.');
    lines.push('The lead role **' + expectedRole + '(' + expectedRoleName + ')** MUST be activated IMMEDIATELY.');
    lines.push('');
    lines.push(buildAgentDispatch(root, expectedRole, phaseName));
    lines.push('');
    lines.push('**DO NOT wait for user confirmation. Activate the role now.**');
  } else if (activeRole !== expectedRole) {
    // Wrong role active → switch
    var currentRoleName = ROLE_NAMES[activeRole] || activeRole;
    lines.push('### MANDATORY: Switch from ' + activeRole + ' to ' + expectedRole);
    lines.push('');
    lines.push('Current role ' + activeRole + '(' + currentRoleName + ') does NOT match phase ' + currentPhase + '.');
    lines.push('');
    lines.push('**Execute immediately:**');
    lines.push('1. If ' + activeRole + ' work is in progress → complete and produce handoff');
    lines.push('2. Switch active_role to ' + expectedRole + ' in state.yaml');
    lines.push('3. Then dispatch:');
    lines.push('');
    lines.push(buildAgentDispatch(root, expectedRole, phaseName));
  } else {
    // Active role matches — continue or detect completion
    var isCompletedCurrent = completedRoles.indexOf(activeRole) >= 0;
    if (isCompletedCurrent) {
      lines.push('### SIGNAL: ' + activeRole + ' Already Completed — Advance Needed');
      lines.push('');
      lines.push('Active role ' + activeRole + ' is marked as completed but still active.');
      lines.push('Set active_role to null and advance to next participant or gate.');
    } else {
      lines.push('### Active: ' + activeRole + '(' + expectedRoleName + ') — Continue');
      lines.push('');
      lines.push('Role ' + activeRole + ' is active and matching phase ' + currentPhase + '.');
      lines.push('Continue work. On completion:');
      lines.push('- Submit evidence via loop_evidence_submit');
      lines.push('- Mark role complete: Update state.yaml completed_roles');
      lines.push('- Next role will be auto-detected by this hook');
    }

    var pending = common.pendingGates(root);
    var blocked = common.blockedGates(root);
    if (blocked.length > 0) {
      lines.push('');
      lines.push('BLOCKED Gate: ' + blocked.join(', ') + ' — resolve first');
    } else if (pending.length > 0) {
      lines.push('');
      lines.push('PENDING Gate: ' + pending.join(', ') + ' — complete conditions');
    }
  }

  // Next phase preview
  var phaseIdx = PHASE_ORDER.indexOf(currentPhase);
  if (phaseIdx >= 0 && phaseIdx < PHASE_ORDER.length - 1) {
    var nextPhase = PHASE_ORDER[phaseIdx + 1];
    var nextMapping = PHASE_ROLE_MAP[nextPhase];
    if (nextMapping) {
      lines.push('');
      lines.push('---');
      lines.push('Next phase: ' + nextPhase + '(' + nextMapping.name + ') → ' + nextMapping.lead + '(' + ROLE_NAMES[nextMapping.lead] + ')');
      lines.push('Will be auto-activated when current phase gate advances.');
    }
  }

  lines.push('');
  lines.push('> Phase: **' + currentPhase + '** | Active: **' + (activeRole || 'none') + '** | Expected: **' + expectedRole + '** | Completed: [' + completedRoles.join(',') + ']');

  var output = {
    hookSpecificOutput: {
      hookEventName: 'UserPromptSubmit',
      additionalContext: lines.join('\n')
    }
  };

  process.stdout.write(JSON.stringify(output));
  process.exit(0);
}

module.exports = { PHASE_ROLE_MAP, ROLE_NAMES, PHASE_ORDER, buildAgentDispatch, getCompletedRoles };

main().catch(function() { process.exit(2); });
