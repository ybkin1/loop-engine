#!/usr/bin/env node
/**
 * sync-state-docs.cjs — 治理文档单一事实源生成器（T-0008）
 *
 * state.yaml / gates.yaml / task_graph.yaml 是唯一权威；
 * HANDOFF.md 与 PROGRESS.md 由本脚本从权威文件重新生成，
 * 任何手写内容都会被覆盖，防止多文件状态漂移。
 *
 * 用法: node scripts/sync-state-docs.cjs [project_root]
 */
const fs = require('fs');
const path = require('path');
const { parseDocument, stringify } = require('yaml');

const ROOT = process.argv[2] || process.cwd();
const AI = path.join(ROOT, '.ai');

function readYaml(file) {
  const p = path.join(AI, file);
  if (!fs.existsSync(p)) return null;
  try {
    return parseDocument(fs.readFileSync(p, 'utf-8')).toJSON();
  } catch (e) {
    console.error(`[sync-state-docs] 解析失败 ${file}: ${e.message}`);
    process.exit(1);
  }
}

const state = readYaml('state.yaml');
const gates = readYaml('gates.yaml');
const tasks = readYaml('task_graph.yaml');
if (!state) { console.error('[sync-state-docs] state.yaml 缺失'); process.exit(1); }

const now = new Date().toISOString();

// ── 生成 HANDOFF.md ────────────────────────────────────
function renderGates() {
  const rows = (gates?.gates ?? []).map(g => {
    const status = g.status ?? 'pending';
    const icon = status === 'passed' ? '✅' : status === 'blocked' ? '⛔' : '🕐';
    const extra = g.blocked_reasons?.length ? ` — ${g.blocked_reasons.join('; ')}` : '';
    return `| ${g.gate_id} | ${icon} ${status}${extra} |`;
  }).join('\n');
  return rows || '| (无 gate 注册) | ⛔ 治理未启用 |';
}

function handoffMd() {
  const phase = state.current_phase ?? '(unknown)';
  const task = tasks?.tasks?.find(t => t.id === state.current_task_id);
  const completedTasks = (tasks?.tasks ?? []).filter(t => t.status === 'completed');
  const gate = (gates?.gates ?? []).find(g => g.gate_id === state.current_gate_id);
  const blocked = (gates?.gates ?? []).filter(g => g.status === 'blocked');

  return [
    '# Handoff',
    '',
    '> 本文件由 `node scripts/sync-state-docs.cjs` 自动生成 — 勿手写编辑，权威源为 .ai/state.yaml',
    '',
    `## 当前阶段`,
    '',
    `\`${phase}\`（当前门禁: \`${state.current_gate_id ?? '(无)'}\`）`,
    '',
    `## 当前任务`,
    '',
    `Task: \`${state.current_task_id ?? '(无)'}\`` + (task ? ` — ${task.title}` : ''),
    '',
    `Status: \`${task?.status ?? '(未注册)'}\``,
    '',
    `活跃角色: \`${state.active_role ?? '(无 — 等待自动编排激活)'}\``,
    '',
    `生成时间: ${now}`,
    '',
    '## 门禁状态',
    '',
    renderGates(),
    '',
    blocked.length > 0
      ? '## ⛔ 阻塞项（必须先解决）\n\n' + blocked.map(b => `- ${b.gate_id}: ${(b.blocked_reasons ?? []).join('; ') || '条件未满足'}`).join('\n')
      : '',
    '',
    '## 历史任务',
    '',
    completedTasks.length
      ? completedTasks.map(t => `- ${t.id} — ${t.title}（${t.completed_at ?? 'completed'}）`).join('\n')
      : '- (无)',
    '',
    '## Next Session First Step',
    '',
    blocked.length > 0
      ? `解决阻塞 gate（${blocked.map(b => b.gate_id).join(', ')}），或由自动编排激活对应角色。`
      : '按当前阶段激活下一个角色（自动编排会自动注入指令）。',
    '',
  ].join('\n');
}

// ── 生成 PROGRESS.md ───────────────────────────────────
function progressMd() {
  const completedTasks = (tasks?.tasks ?? []).filter(t => t.status === 'completed');
  const activeTasks = (tasks?.tasks ?? []).filter(t => t.status === 'active');
  return [
    '# Progress',
    '',
    '> 本文件由 `node scripts/sync-state-docs.cjs` 自动生成 — 勿手写编辑，权威源为 .ai/task_graph.yaml',
    '',
    `## Current Status`,
    '',
    `Phase: ${state.current_phase} | Task: ${state.current_task_id ?? '(无)'} | Generated: ${now}`,
    '',
    '## Recently Completed',
    '',
    ...(completedTasks.slice(-5).reverse().map(t => `- ${t.id}: ${t.title}`) || ['- (无)']),
    '',
    '## Active',
    '',
    ...(activeTasks.map(t => `- ${t.id}: ${t.title}`) || ['- (无)']),
    '',
  ].join('\n');
}

fs.writeFileSync(path.join(AI, 'HANDOFF.md'), handoffMd(), 'utf-8');
fs.writeFileSync(path.join(AI, 'PROGRESS.md'), progressMd(), 'utf-8');
console.log('[sync-state-docs] HANDOFF.md / PROGRESS.md 已从 state/gates/task_graph 重新生成');
console.log(`  phase=${state.current_phase} | task=${state.current_task_id} | gates=${(gates?.gates ?? []).length}`);
