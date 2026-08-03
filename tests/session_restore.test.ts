import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, rmSync, existsSync, writeFileSync, mkdirSync } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';
import {
  restoreSessionContext,
  getKnowledgeStatusLine,
} from '../src/core/session_restore.js';

// ── Helpers ────────────────────────────────────────────────────────

function setupProject(projectDir: string, options: {
  current_phase?: string;
  lessons?: Array<Record<string, unknown>>;
} = {}) {
  // Create .ai directory
  const aiDir = join(projectDir, '.ai');
  mkdirSync(aiDir, { recursive: true });

  // Write state.yaml
  const phase = options.current_phase ?? 'S4-implementation';
  writeFileSync(
    join(aiDir, 'state.yaml'),
    `schema_version: 1\nproject_name: "Test"\ncurrent_phase: ${phase}\ncurrent_task_id: null\ncurrent_gate_id: null\nactive_role: null\ncompleted_roles: []\nlast_handoff_at: "2026-01-01T00:00:00"\nphases: []\n`,
    'utf-8',
  );

  // Write lessons if provided
  if (options.lessons && options.lessons.length > 0) {
    const lessonsDir = join(aiDir, 'lessons');
    mkdirSync(lessonsDir, { recursive: true });
    const lines = options.lessons.map(l => JSON.stringify(l)).join('\n') + '\n';
    writeFileSync(join(lessonsDir, 'lessons.jsonl'), lines, 'utf-8');
  }
}

// ── restoreSessionContext ──────────────────────────────────────────

describe('restoreSessionContext', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), 'session-restore-test-'));
  });

  afterEach(() => {
    if (existsSync(tmpDir)) rmSync(tmpDir, { recursive: true });
  });

  it('无知识账本时返回空', () => {
    setupProject(tmpDir, { current_phase: 'S4-implementation' });
    const ctx = restoreSessionContext(tmpDir);
    expect(ctx.unresolved_lessons_count).toBe(0);
    expect(ctx.current_phase).toBe('S4-implementation');
    expect(ctx.summary_markdown).toContain('暂无未解决');
  });

  it('有未解决教训时显示', () => {
    setupProject(tmpDir, {
      current_phase: 'S4-implementation',
      lessons: [
        {
          lesson_id: 'lesson-0001',
          seq: 1,
          chain_hash: 'a'.repeat(64),
          prev_chain_hash: '0'.repeat(64),
          timestamp: '2026-01-01T00:00:00Z',
          phase_id: 'S4-implementation',
          role_id: 'R06',
          category: 'LOGIC_ERROR',
          severity: 'BLOCKER',
          symptom: 'Null reference in handler',
          error_message: 'TypeError: ...',
          status: 'OPEN',
          tags: ['null-safety'],
        },
      ],
    });

    const ctx = restoreSessionContext(tmpDir);
    expect(ctx.unresolved_lessons_count).toBe(1);
    expect(ctx.current_phase_lessons).toHaveLength(1);
    expect(ctx.brief_reminders[0]).toContain('未解决');
  });

  it('区分当前阶段和其他阶段', () => {
    setupProject(tmpDir, {
      current_phase: 'S4-implementation',
      lessons: [
        {
          lesson_id: 'lesson-0001',
          seq: 1,
          chain_hash: 'a'.repeat(64),
          prev_chain_hash: '0'.repeat(64),
          timestamp: '2026-01-01T00:00:00Z',
          phase_id: 'S4-implementation',
          role_id: 'R06',
          category: 'LOGIC_ERROR',
          severity: 'BLOCKER',
          symptom: 'Phase S4 issue',
          error_message: '...',
          status: 'OPEN',
          tags: [],
        },
        {
          lesson_id: 'lesson-0002',
          seq: 2,
          chain_hash: 'b'.repeat(64),
          prev_chain_hash: 'a'.repeat(64),
          timestamp: '2026-01-02T00:00:00Z',
          phase_id: 'S5-quality',
          role_id: 'R07',
          category: 'TEST_GAP',
          severity: 'WARNING',
          symptom: 'Phase S5 issue',
          error_message: '...',
          status: 'OPEN',
          tags: [],
        },
      ],
    });

    const ctx = restoreSessionContext(tmpDir);
    expect(ctx.current_phase_lessons).toHaveLength(1);
    expect(ctx.current_phase_lessons[0].phase_id).toBe('S4-implementation');
    expect(ctx.other_unresolved_lessons).toHaveLength(1);
    expect(ctx.other_unresolved_lessons[0].phase_id).toBe('S5-quality');
  });

  it('已解决的教训不显示', () => {
    setupProject(tmpDir, {
      current_phase: 'S4-implementation',
      lessons: [
        {
          lesson_id: 'lesson-0001',
          seq: 1,
          chain_hash: 'a'.repeat(64),
          prev_chain_hash: '0'.repeat(64),
          timestamp: '2026-01-01T00:00:00Z',
          phase_id: 'S4-implementation',
          role_id: 'R06',
          category: 'LOGIC_ERROR',
          severity: 'BLOCKER',
          symptom: 'Resolved issue',
          error_message: '...',
          status: 'RESOLVED',
          tags: [],
        },
      ],
    });

    const ctx = restoreSessionContext(tmpDir);
    expect(ctx.unresolved_lessons_count).toBe(0);
    expect(ctx.summary_markdown).toContain('暂无未解决');
  });

  it('ACKNOWLEDGED 状态算作未解决', () => {
    setupProject(tmpDir, {
      current_phase: 'S4-implementation',
      lessons: [
        {
          lesson_id: 'lesson-0001',
          seq: 1,
          chain_hash: 'a'.repeat(64),
          prev_chain_hash: '0'.repeat(64),
          timestamp: '2026-01-01T00:00:00Z',
          phase_id: 'S4-implementation',
          role_id: 'R06',
          category: 'LOGIC_ERROR',
          severity: 'BLOCKER',
          symptom: 'Acknowledged issue',
          error_message: '...',
          status: 'ACKNOWLEDGED',
          tags: [],
        },
      ],
    });

    const ctx = restoreSessionContext(tmpDir);
    expect(ctx.unresolved_lessons_count).toBe(1);
  });

  it('不存在 state.yaml 时返回 unknown', () => {
    // Don't set up project — just verify it handles missing state gracefully
    const ctx = restoreSessionContext(tmpDir);
    expect(ctx.current_phase).toBe('unknown');
    expect(ctx.unresolved_lessons_count).toBe(0);
  });
});

// ── getKnowledgeStatusLine ─────────────────────────────────────────

describe('getKnowledgeStatusLine', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), 'status-line-test-'));
  });

  afterEach(() => {
    if (existsSync(tmpDir)) rmSync(tmpDir, { recursive: true });
  });

  it('无教训时返回 ✅', () => {
    setupProject(tmpDir, { current_phase: 'S4-implementation' });
    const line = getKnowledgeStatusLine(tmpDir);
    expect(line).toContain('✅');
    expect(line).toContain('无未解决教训');
  });

  it('有教训时返回 ⚠️', () => {
    setupProject(tmpDir, {
      current_phase: 'S4-implementation',
      lessons: [
        {
          lesson_id: 'lesson-0001',
          seq: 1,
          chain_hash: 'a'.repeat(64),
          prev_chain_hash: '0'.repeat(64),
          timestamp: '2026-01-01T00:00:00Z',
          phase_id: 'S4-implementation',
          role_id: 'R06',
          category: 'LOGIC_ERROR',
          severity: 'BLOCKER',
          symptom: 'Issue',
          error_message: '...',
          status: 'OPEN',
          tags: [],
        },
      ],
    });

    const line = getKnowledgeStatusLine(tmpDir);
    expect(line).toContain('⚠️');
    expect(line).toContain('1 条未解决教训');
  });
});
