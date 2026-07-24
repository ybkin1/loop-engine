import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, existsSync } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';
import { PhaseExecutor, PHASE_ROLES, StepStatus } from '../src/core/executor.js';

// ── StepStatus enum ─────────────────────────────────────────────

describe('StepStatus', () => {
  it('包含 PENDING/RUNNING/COMPLETE/FAILED/BLOCKED', () => {
    expect(StepStatus.PENDING).toBe('PENDING');
    expect(StepStatus.RUNNING).toBe('RUNNING');
    expect(StepStatus.COMPLETE).toBe('COMPLETE');
    expect(StepStatus.FAILED).toBe('FAILED');
    expect(StepStatus.BLOCKED).toBe('BLOCKED');
  });
});

// ── PHASE_ROLES mapping ─────────────────────────────────────────

describe('PHASE_ROLES', () => {
  it('requirements → ["R01"]', () => {
    expect(PHASE_ROLES['requirements']).toEqual(['R01']);
  });

  it('architecture → ["R04", "R08"]', () => {
    expect(PHASE_ROLES['architecture']).toEqual(['R04', 'R08']);
  });

  it('review → ["R09", "R07", "R08"]', () => {
    expect(PHASE_ROLES['review']).toEqual(['R09', 'R07', 'R08']);
  });

  it('delivery → ["R03", "R10"]', () => {
    expect(PHASE_ROLES['delivery']).toEqual(['R03', 'R10']);
  });
});

// ── PhaseExecutor ───────────────────────────────────────────────

describe('PhaseExecutor', () => {
  let tmpDir: string;
  let executor: PhaseExecutor;

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), 'executor-test-'));
    executor = new PhaseExecutor(tmpDir);
  });

  afterEach(() => {
    if (existsSync(tmpDir)) rmSync(tmpDir, { recursive: true });
  });

  it('planPhase 创建正确的 steps (requirements)', () => {
    const plan = executor.planPhase('requirements');
    expect(plan.phase_id).toBe('requirements');
    expect(plan.steps).toHaveLength(1);
    expect(plan.steps[0].role_id).toBe('R01');
    expect(plan.steps[0].status).toBe(StepStatus.PENDING);
    expect(plan.gate_id).toBe('gate-requirements');
  });

  it('planPhase steps 数量匹配 PHASE_ROLES', () => {
    for (const [phaseId, roles] of Object.entries(PHASE_ROLES)) {
      const plan = executor.planPhase(phaseId);
      expect(plan.steps).toHaveLength(roles.length);
      for (let i = 0; i < roles.length; i++) {
        expect(plan.steps[i].role_id).toBe(roles[i]);
      }
    }
  });

  it('planPhase 未知阶段抛出异常', () => {
    expect(() => executor.planPhase('nonexistent')).toThrow();
  });

  it('validateStep 有 required_fields → valid', () => {
    const plan = executor.planPhase('requirements');
    const step = plan.steps[0]; // R01: requires ["requirements_doc", "acceptance_criteria"]
    const output = {
      requirements_doc: 'some doc',
      acceptance_criteria: 'some criteria',
    };
    const result = executor.validateStep(step, output);
    expect(result.valid).toBe(true);
    expect(result.missing_fields).toHaveLength(0);
  });

  it('validateStep 缺少字段 → invalid', () => {
    const plan = executor.planPhase('requirements');
    const step = plan.steps[0]; // R01: requires ["requirements_doc", "acceptance_criteria"]
    const output = {
      requirements_doc: 'some doc',
      // missing acceptance_criteria
    };
    const result = executor.validateStep(step, output);
    expect(result.valid).toBe(false);
    expect(result.missing_fields).toContain('acceptance_criteria');
  });

  it('validateStep 空 required_fields → valid', () => {
    const step = {
      role_id: 'UNKNOWN',
      status: StepStatus.PENDING,
      retries: 0,
      max_retries: 2,
      required_fields: [] as string[],
    };
    const result = executor.validateStep(step, {});
    expect(result.valid).toBe(true);
  });

  it('executePhase 非当前阶段 → 返回失败', async () => {
    // Set up a minimal project state with current_phase = "requirements"
    const aiDir = join(tmpDir, '.ai');
    mkdirSync(aiDir, { recursive: true });
    const stateYaml = [
      'schema_version: 1',
      'project_name: test',
      'current_phase: requirements',
      'current_task_id: null',
      'current_gate_id: gate-requirements',
      'active_role: null',
      'role_activated_at: null',
      'completed_roles: []',
      'last_handoff_at: ""',
      'phases:',
      '  - phase_id: requirements',
      '    entered_at: "2025-01-01T00:00:00Z"',
      '    exited_at: null',
      '    status: active',
    ].join('\n');
    writeFileSync(join(aiDir, 'state.yaml'), stateYaml, 'utf-8');

    // Try to execute "architecture" phase — should throw PHASE_MISMATCH
    await expect(executor.executePhase('architecture')).rejects.toThrow(/PHASE_MISMATCH|current phase/i);
  });
});
