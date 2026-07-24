import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, mkdirSync, rmSync, existsSync } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';
import { ExecutionLedger, ExecutionStatus } from '../src/core/execution_ledger.js';

// ── ExecutionStatus enum ────────────────────────────────────────

describe('ExecutionStatus', () => {
  it('包含 LAUNCHED/COMPLETED/FAILED/VIOLATED', () => {
    expect(ExecutionStatus.LAUNCHED).toBe('LAUNCHED');
    expect(ExecutionStatus.COMPLETED).toBe('COMPLETED');
    expect(ExecutionStatus.FAILED).toBe('FAILED');
    expect(ExecutionStatus.VIOLATED).toBe('VIOLATED');
  });
});

// ── ExecutionLedger ─────────────────────────────────────────────

describe('ExecutionLedger', () => {
  let tmpDir: string;
  let ledger: ExecutionLedger;

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), 'exec-ledger-test-'));
    ledger = new ExecutionLedger(join(tmpDir, 'execution.jsonl'));
  });

  afterEach(() => {
    if (existsSync(tmpDir)) rmSync(tmpDir, { recursive: true });
  });

  function makeRecord(overrides: Partial<{
    execution_id: string; session_id: string; actor_id: string;
    role_id: string; task_id: string; prompt_fingerprint: string;
    input_files_hash: string; tool_constraints: string[]; tool_violations: string[];
  }> = {}) {
    return {
      execution_id: overrides.execution_id ?? 'exec-001',
      session_id: overrides.session_id ?? 'sess-001',
      actor_id: overrides.actor_id ?? 'agent-1',
      role_id: overrides.role_id ?? 'R06',
      task_id: overrides.task_id ?? 'task-001',
      prompt_fingerprint: overrides.prompt_fingerprint ?? 'abc123',
      input_files_hash: overrides.input_files_hash ?? 'def456',
      tool_constraints: overrides.tool_constraints ?? ['no_network'],
      tool_violations: overrides.tool_violations ?? [],
    };
  }

  // ── appendEntry ────────────────────────────────────────────────

  it('appendEntry 增加 length', () => {
    expect(ledger.length).toBe(0);
    ledger.appendEntry({ ...makeRecord(), status: ExecutionStatus.LAUNCHED, started_at: new Date().toISOString() });
    expect(ledger.length).toBe(1);
    ledger.appendEntry({ ...makeRecord({ execution_id: 'exec-002' }), status: ExecutionStatus.LAUNCHED, started_at: new Date().toISOString() });
    expect(ledger.length).toBe(2);
  });

  it('appendEntry 自动计算 seq', () => {
    const e1 = ledger.appendEntry({ ...makeRecord(), status: ExecutionStatus.LAUNCHED, started_at: new Date().toISOString() });
    const e2 = ledger.appendEntry({ ...makeRecord({ execution_id: 'exec-002' }), status: ExecutionStatus.LAUNCHED, started_at: new Date().toISOString() });
    expect(e1.seq).toBe(1);
    expect(e2.seq).toBe(2);
  });

  it('chain_hash 非空', () => {
    const entry = ledger.appendEntry({ ...makeRecord(), status: ExecutionStatus.LAUNCHED, started_at: new Date().toISOString() });
    expect(entry.chain_hash).toBeTruthy();
    expect(entry.chain_hash).toHaveLength(64); // SHA-256 hex
  });

  // ── verifyChain ────────────────────────────────────────────────

  it('verifyChain 正常 → valid', () => {
    ledger.appendEntry({ ...makeRecord(), status: ExecutionStatus.LAUNCHED, started_at: '2025-01-01T00:00:00Z' });
    ledger.appendEntry({ ...makeRecord({ execution_id: 'exec-002' }), status: ExecutionStatus.COMPLETED, started_at: '2025-01-01T00:01:00Z' });
    const result = ledger.verifyChain();
    expect(result.valid).toBe(true);
    expect(result.firstInvalidSeq).toBeNull();
  });

  it('verifyChain 空 → valid', () => {
    const result = ledger.verifyChain();
    expect(result.valid).toBe(true);
    expect(result.totalEntries).toBe(0);
  });

  // ── recordLaunch ───────────────────────────────────────────────

  it('recordLaunch 创建 LAUNCHED 记录', () => {
    const entry = ledger.recordLaunch(makeRecord());
    expect(entry.status).toBe(ExecutionStatus.LAUNCHED);
    expect(entry.started_at).toBeTruthy();
    expect(entry.seq).toBe(1);
    expect(ledger.length).toBe(1);
  });

  // ── recordCompletion ───────────────────────────────────────────

  it('recordCompletion 更新状态', () => {
    ledger.recordLaunch(makeRecord());
    const completed = ledger.recordCompletion('exec-001', '/output/artifact.txt');
    expect(completed).toBeTruthy();
    expect(completed!.status).toBe(ExecutionStatus.COMPLETED);
    expect(completed!.output_artifact).toBe('/output/artifact.txt');
    expect(completed!.completed_at).toBeTruthy();
  });

  // ── findByTask ─────────────────────────────────────────────────

  it('findByTask 按 task_id 查找', () => {
    ledger.recordLaunch(makeRecord({ task_id: 'task-A' }));
    ledger.recordLaunch(makeRecord({ execution_id: 'exec-002', task_id: 'task-B' }));
    ledger.recordLaunch(makeRecord({ execution_id: 'exec-003', task_id: 'task-A' }));

    const taskA = ledger.findByTask('task-A');
    expect(taskA).toHaveLength(2);
    expect(taskA.every(e => e.task_id === 'task-A')).toBe(true);

    const taskB = ledger.findByTask('task-B');
    expect(taskB).toHaveLength(1);
  });

  // ── findByRole ─────────────────────────────────────────────────

  it('findByRole 按 role_id 查找', () => {
    ledger.recordLaunch(makeRecord({ role_id: 'R06' }));
    ledger.recordLaunch(makeRecord({ execution_id: 'exec-002', role_id: 'R09' }));
    ledger.recordLaunch(makeRecord({ execution_id: 'exec-003', role_id: 'R06' }));

    const r06 = ledger.findByRole('R06');
    expect(r06).toHaveLength(2);
    expect(r06.every(e => e.role_id === 'R06')).toBe(true);

    const r09 = ledger.findByRole('R09');
    expect(r09).toHaveLength(1);
  });

  // ── recent ─────────────────────────────────────────────────────

  it('recent(n) 返回最近 n 条', () => {
    ledger.recordLaunch(makeRecord({ execution_id: 'exec-001' }));
    ledger.recordLaunch(makeRecord({ execution_id: 'exec-002' }));
    ledger.recordLaunch(makeRecord({ execution_id: 'exec-003' }));
    ledger.recordLaunch(makeRecord({ execution_id: 'exec-004' }));
    ledger.recordLaunch(makeRecord({ execution_id: 'exec-005' }));

    const last3 = ledger.recent(3);
    expect(last3).toHaveLength(3);
    expect(last3[0].execution_id).toBe('exec-003');
    expect(last3[2].execution_id).toBe('exec-005');
  });

  // ── crossValidate ──────────────────────────────────────────────

  it('crossValidate 检查独立性', () => {
    // Developer R06 in sess-dev, Reviewer R09 in sess-rev → independent
    ledger.recordLaunch(makeRecord({ execution_id: 'exec-001', role_id: 'R06', session_id: 'sess-dev', task_id: 'task-X' }));
    ledger.recordLaunch(makeRecord({ execution_id: 'exec-002', role_id: 'R09', session_id: 'sess-rev', task_id: 'task-X' }));

    const cv = ledger.crossValidate('task-X');
    expect(cv.task_id).toBe('task-X');
    expect(cv.is_independent).toBe(true);
    expect(cv.developer_sessions).toContain('sess-dev');
    expect(cv.reviewer_sessions).toContain('sess-rev');
  });

  it('crossValidate 相同 session → 不独立', () => {
    ledger.recordLaunch(makeRecord({ execution_id: 'exec-001', role_id: 'R06', session_id: 'sess-same', task_id: 'task-Y' }));
    ledger.recordLaunch(makeRecord({ execution_id: 'exec-002', role_id: 'R09', session_id: 'sess-same', task_id: 'task-Y' }));

    const cv = ledger.crossValidate('task-Y');
    expect(cv.is_independent).toBe(false);
  });

  // ── empty ledger ───────────────────────────────────────────────

  it('空 ledger → length = 0', () => {
    expect(ledger.length).toBe(0);
  });
});
