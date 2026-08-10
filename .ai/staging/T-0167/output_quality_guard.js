#!/usr/bin/env node
/**
 * output_quality_guard.js — OQA-4D PreToolUse lightweight quality pre-check
 *
 * Runs BEFORE every Write/Edit inside a Loop governance project and inspects
 * the incoming content for quality signals that predict BLOCKER findings of
 * the deep engine (output_quality.ts):
 *
 *   - secret patterns        → deny (exit 2, hard)
 *   - oversized writes       → warn (stderr, advisory; deep engine will block)
 *   - debug residue (2+ hits)→ warn
 *   - TODO/FIXME markers     → warn
 *   - missing task binding   → warn (write has no task context)
 *
 * Decision policy (aligned with gate-guard.js):
 *   - non-governance project  → exit 0
 *   - loop inactive           → exit 0
 *   - governance files (.ai/  → exit 0 (decision-recording exemption)
 *   - secrets                 → exit 2 with permissionDecision deny JSON
 *   - everything else         → exit 0 (+ stderr warnings, advisory)
 *
 * The DEEP four-dimension verification is performed by the MCP tool
 * `loop_output_quality` at delivery time — this hook is the cheap first
 * line of defense, not the verdict.
 *
 * Protocol: stdin = JSON event context, exit 2 = block, exit 0 = allow.
 */

const common = require('./hook_common.js');

// ── Thresholds (mirror output_quality.ts constants) ──
const MAX_LINES_WARN = 400;        // advisory cap
const MAX_LINES_BLOCK = 1200;      // hard cap (deep engine BLOCKER)
const DEBUG_WARN_THRESHOLD = 2;    // hits before advisory

// ── Patterns (mirror output_quality.ts) ──
const SECRET_PATTERNS = [
  /(api[_-]?key|apikey|secret|token|password|passwd|pwd)\s*[:=]\s*["'][A-Za-z0-9_\-]{16,}["']/i,
  /(BEGIN (RSA|EC|OPENSSH|DSA) PRIVATE KEY)/,
  /AKIA[0-9A-Z]{16}/,
  /sk-[A-Za-z0-9]{20,}/,
];

const DEBUG_PATTERNS = [
  /\bconsole\.log\s*\(/,
  /\bprint\s*\(\s*["']?(DEBUG|debug)/,
  /\bdebugger\s*;?/,
];

const TODO_PATTERNS = [
  /\bTODO\s*:/,
  /\bFIXME\s*:/,
  /\bHACK\s*:/,
];

/** 扫描自身定义行豁免（正则字面量的转义形式，防自报）。 */
const DEBUG_EXEMPT_SUBSTRINGS = [
  'DEBUG_PATTERNS',
  'SECRET_PATTERNS',
  'TODO_PATTERNS',
  'DEBUG_EXEMPT_SUBSTRINGS',
  '\\bdebugger',
  '\\bconsole',
];

/** Code extensions eligible for quality pre-check. */
const CODE_EXTS = /\.(ts|tsx|js|jsx|py|go|rs|java|c|h|cpp|hpp)$/i;

async function main() {
  const event = await common.readStdin();
  const root = common.projectRoot(event);
  const toolName = event.tool_name || '';
  const toolInput = event.tool_input || {};

  // 1. Only Write/Edit style operations
  const isWriteOp = ['Write', 'Edit', 'create_file', 'search_replace'].includes(toolName);
  if (!isWriteOp) process.exit(0);

  // 2. Non-governance project → allow (fast path)
  if (!common.isGovernanceProject(root)) process.exit(0);

  // 3. Loop active check — self-contained: state exists with a real phase.
  //    NOT using common.isLoopActive because its loadGates regex cannot parse
  //    large gates.yaml (id:-style entries) and would silently disable the
  //    quality pre-check on real projects.
  let loopActive = false;
  let stateCache = null;
  try {
    stateCache = common.loadState(root);
    const phase = ((stateCache && stateCache.current_phase) || '').toLowerCase();
    loopActive = phase !== '' && phase !== 'null' && phase !== 's0-init' && phase !== 'none';
  } catch {
    loopActive = false;
  }
  if (!loopActive) process.exit(0);

  const filePath = toolInput.file_path || '';
  if (!filePath) process.exit(0);

  // 4. Governance files always allowed (decision-recording exemption).
  //    NOTE: isGovernanceFile covers the GOVERNANCE_PATHS whitelist (.ai/state.yaml etc.);
  //    other .ai/ paths (tasks/, evidence/) still go through code-quality checks.
  if (common.isGovernanceFile(filePath, root)) process.exit(0);

  // 5. Only inspect code-like files
  if (!CODE_EXTS.test(filePath)) process.exit(0);

  const content = toolInput.content || toolInput.new_str || '';
  // SearchReplace 的内容在 replacements[].new_text（F8：防绕过）
  let effectiveContent = content;
  if (!effectiveContent && Array.isArray(toolInput.replacements)) {
    effectiveContent = toolInput.replacements
      .map((r) => (r && typeof r.new_text === 'string' ? r.new_text : ''))
      .join('\n');
  }
  if (!effectiveContent) process.exit(0);

  const warnings = [];
  const lines = effectiveContent.split('\n');

  // ── Secret scan (hard deny) ──
  for (let i = 0; i < SECRET_PATTERNS.length; i++) {
    const m = effectiveContent.match(SECRET_PATTERNS[i]);
    if (m) {
      const line = effectiveContent.slice(0, m.index ?? 0).split('\n').length;
      process.stderr.write(
        `[Loop Output Quality] DENY: possible secret in ${filePath}:${line} (pattern ${i + 1}).\n` +
        `Secrets must live in env vars / vault. Remove before writing.\n`
      );
      // Emit permissionDecision JSON on stdout for clients that support ask/deny
      const decision = {
        hookSpecificOutput: {
          hookEventName: 'PreToolUse',
          permissionDecision: 'deny',
          permissionDecisionReason: `[output-quality-guard] Secret pattern in ${filePath}:${line}.`,
        },
      };
      process.stdout.write(JSON.stringify(decision));
      process.exit(2);
      return;
    }
  }

  // ── File scale (advisory warn; deep engine blocks >1200) ──
  if (lines.length > MAX_LINES_BLOCK) {
    warnings.push(`[Loop Output Quality] WARN: write to ${filePath} is ${lines.length} lines (> hard cap ${MAX_LINES_BLOCK}). Deep verification will BLOCK this artifact. Split the change.`);
  } else if (lines.length > MAX_LINES_WARN) {
    warnings.push(`[Loop Output Quality] WARN: write to ${filePath} is ${lines.length} lines (> advisory ${MAX_LINES_WARN}). Consider splitting.`);
  }

  // ── Debug residue (advisory) ──
  let debugHits = 0;
  for (const lineText of lines) {
    if (DEBUG_EXEMPT_SUBSTRINGS.some(s => lineText.includes(s))) continue;
    for (const re of DEBUG_PATTERNS) {
      if (re.test(lineText)) { debugHits += 1; break; }
    }
  }
  if (debugHits >= DEBUG_WARN_THRESHOLD) {
    warnings.push(`[Loop Output Quality] WARN: ${debugHits} debug residue pattern(s) in ${filePath} (console.log/print/debugger). Remove before delivery.`);
  }

  // ── TODO/FIXME markers (advisory) ──
  let todoHits = 0;
  for (const re of TODO_PATTERNS) {
    const m = effectiveContent.match(re);
    if (m) todoHits += 1;
  }
  if (todoHits > 0) {
    warnings.push(`[Loop Output Quality] WARN: ${todoHits} TODO/FIXME marker(s) in ${filePath}. Resolve before gate advance.`);
  }

  // ── Task binding (advisory) ──
  try {
    const state = stateCache || common.loadState(root);
    if (state && !state.current_task_id && !state.active_task_id) {
      warnings.push(`[Loop Output Quality] WARN: no active task in state.yaml — artifact ${filePath} may not be bound to requirements.`);
    }
  } catch { /* best effort */ }

  if (warnings.length > 0) {
    process.stderr.write(warnings.join('\n') + '\n');
  }

  process.exit(0);
}

main().catch(() => {
  // Fail-open for unexpected errors (this is advisory; deep engine is the gate).
  process.exit(0);
});
