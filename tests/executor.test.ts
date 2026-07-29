import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, existsSync } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';
import { PhaseExecutor, PHASE_ROLES, StepStatus, HookRegistry } from '../src/core/executor.js';
import type { RoleExecutionHook, RoleExecutionContext, RoleStepResult } from '../src/core/executor.js';

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
  it('requirements → ["R01", "R02"] (lead + participant from unified registry)', () => {
    expect(PHASE_ROLES['requirements']).toEqual(['R01', 'R02']);
  });

  it('architecture → ["R04", "R01", "R08"]', () => {
    expect(PHASE_ROLES['architecture']).toEqual(['R04', 'R01', 'R08']);
  });

  it('review → ["R07", "R06", "R08"]', () => {
    expect(PHASE_ROLES['review']).toEqual(['R07', 'R06', 'R08']);
  });

  it('delivery → ["R03", "R10", "R08"]', () => {
    expect(PHASE_ROLES['delivery']).toEqual(['R03', 'R10', 'R08']);
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
    expect(plan.steps).toHaveLength(2);
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

  it('executePhase 无 state.yaml → STATE_LOAD_FAILED 异常', async () => {
    // tmpDir has no .ai/state.yaml
    const emptyExecutor = new PhaseExecutor(tmpDir);
    await expect(emptyExecutor.executePhase('requirements')).rejects.toThrow(/STATE_LOAD_FAILED|failed to load/i);
  });

  it('executeRole 无 hook → 返回 FAILED（不再是模拟假成功）', async () => {
    const plan = executor.planPhase('requirements');
    const step = plan.steps[0]; // R01
    const result = await executor.executeRole(step);
    expect(result.status).toBe(StepStatus.FAILED);
    expect(result.role_id).toBe('R01');
    expect(result.error).toContain('No execution hook registered');
  });

  it('planPhase 创建的计划包含正确的 gate_id', () => {
    const plan = executor.planPhase('architecture');
    expect(plan.gate_id).toBe('gate-architecture');
    expect(plan.status).toBe(StepStatus.PENDING);
    expect(plan.steps).toHaveLength(3);
    expect(plan.steps[0].role_id).toBe('R04');
    expect(plan.steps[1].role_id).toBe('R01');
    expect(plan.steps[2].role_id).toBe('R08');
  });
});

// ── HookRegistry ──────────────────────────────────────────────────

describe('HookRegistry', () => {
  it('register + get + has 基本操作', () => {
    const registry = new HookRegistry();
    const mockHook: RoleExecutionHook = {
      execute: async () => ({ role_id: 'R01', status: StepStatus.COMPLETE, duration_ms: 0 }),
    };

    expect(registry.has('R01')).toBe(false);
    expect(registry.size).toBe(0);

    registry.register('R01', mockHook);
    expect(registry.has('R01')).toBe(true);
    expect(registry.get('R01')).toBe(mockHook);
    expect(registry.size).toBe(1);
  });

  it('get 未注册的 role 返回 undefined', () => {
    const registry = new HookRegistry();
    expect(registry.get('R99')).toBeUndefined();
  });
});

// ── PhaseExecutor with Hooks ────────────────────────────────────────

describe('PhaseExecutor with hooks', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), 'executor-hook-test-'));
  });

  afterEach(() => {
    if (existsSync(tmpDir)) rmSync(tmpDir, { recursive: true });
  });

  it('无 hook 时返回 FAILED（不再模拟假成功）', async () => {
    const executor = new PhaseExecutor(tmpDir);
    const plan = executor.planPhase('requirements');
    const result = await executor.executeRole(plan.steps[0]);
    expect(result.status).toBe(StepStatus.FAILED);
    expect(result.error).toContain('No execution hook registered');
  });

  it('注册 hook 后调用 hook 执行', async () => {
    const registry = new HookRegistry();
    const hook: RoleExecutionHook = {
      execute: async (ctx: RoleExecutionContext): Promise<RoleStepResult> => ({
        role_id: ctx.role_id,
        status: StepStatus.COMPLETE,
        output: { requirements_doc: 'real_output', acceptance_criteria: 'real_ac' },
        duration_ms: 0,
      }),
    };
    registry.register('R01', hook);

    const executor = new PhaseExecutor(tmpDir, registry);
    const plan = executor.planPhase('requirements');
    const result = await executor.executeRole(plan.steps[0], 'requirements');

    expect(result.status).toBe(StepStatus.COMPLETE);
    expect(result.output!['requirements_doc']).toBe('real_output');
    expect(result.output!['acceptance_criteria']).toBe('real_ac');
  });

  it('hook 抛异常 → FAILED 状态', async () => {
    const registry = new HookRegistry();
    const hook: RoleExecutionHook = {
      execute: async (): Promise<RoleStepResult> => {
        throw new Error('hook crashed');
      },
    };
    registry.register('R01', hook);

    const executor = new PhaseExecutor(tmpDir, registry);
    const plan = executor.planPhase('requirements');
    const result = await executor.executeRole(plan.steps[0], 'requirements');

    expect(result.status).toBe(StepStatus.FAILED);
    expect(result.error).toContain('hook crashed');
  });

  it('hook 超时 → FAILED 状态', async () => {
    const registry = new HookRegistry();
    const hook: RoleExecutionHook = {
      execute: async (): Promise<RoleStepResult> => {
        // Never resolves — will timeout
        return new Promise<RoleStepResult>(() => {});
      },
    };
    registry.register('R01', hook);

    const executor = new PhaseExecutor(tmpDir, registry, { default_timeout_ms: 50 });
    const plan = executor.planPhase('requirements');
    const result = await executor.executeRole(plan.steps[0], 'requirements');

    expect(result.status).toBe(StepStatus.FAILED);
    expect(result.error).toContain('timed out');
  });

  it('hook 接收正确的 context', async () => {
    const registry = new HookRegistry();
    let capturedCtx: RoleExecutionContext | null = null;
    const hook: RoleExecutionHook = {
      execute: async (ctx: RoleExecutionContext): Promise<RoleStepResult> => {
        capturedCtx = ctx;
        return { role_id: ctx.role_id, status: StepStatus.COMPLETE, duration_ms: 0 };
      },
    };
    registry.register('R04', hook);

    const executor = new PhaseExecutor(tmpDir, registry, { default_timeout_ms: 5000 });
    const plan = executor.planPhase('architecture');
    await executor.executeRole(plan.steps[0], 'architecture');

    expect(capturedCtx).not.toBeNull();
    expect(capturedCtx!.role_id).toBe('R04');
    expect(capturedCtx!.phase_id).toBe('architecture');
    expect(capturedCtx!.timeout_ms).toBe(5000);
    expect(capturedCtx!.required_fields).toContain('architecture_doc');
  });
});
