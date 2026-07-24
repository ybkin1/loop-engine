import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';
import { EnforcementHub, quickCheck } from '../src/core/enforcement_hub.js';

// ── Helpers ──────────────────────────────────────────────────────────────────

function setupProject(opts: { state?: string; gates?: string } = {}) {
  const root = mkdtempSync(join(tmpdir(), 'enf-hub-test-'));
  const aiDir = join(root, '.ai');
  mkdirSync(aiDir, { recursive: true });
  if (opts.state) writeFileSync(join(aiDir, 'state.yaml'), opts.state, 'utf-8');
  if (opts.gates) writeFileSync(join(aiDir, 'gates.yaml'), opts.gates, 'utf-8');
  return root;
}

const STATE_ACTIVE = `
schema_version: 1
project_name: test
current_phase: requirements
current_task_id: task-1
current_gate_id: gate-requirements
active_role: R06
role_activated_at: "2025-01-01T00:00:00Z"
completed_roles: []
last_handoff_at: "2025-01-01T00:00:00Z"
phases:
  - phase_id: requirements
    entered_at: "2025-01-01T00:00:00Z"
    exited_at: null
    status: active
  - phase_id: architecture
    entered_at: ""
    exited_at: null
    status: skipped
`;

const GATES_ALL_PASSED = `
schema_version: 1
gates:
  - gate_id: gate-requirements
    name: Req Gate
    description: ""
    conditions: []
    status: passed
    created_at: "2025-01-01T00:00:00Z"
    passed_at: "2025-01-01T00:00:00Z"
    blocked_reasons: []
`;

const GATES_WITH_BLOCKED = `
schema_version: 1
gates:
  - gate_id: gate-requirements
    name: Req Gate
    description: ""
    conditions: []
    status: blocked
    created_at: "2025-01-01T00:00:00Z"
    passed_at: null
    blocked_reasons:
      - "missing evidence"
`;

const GATES_WITH_PENDING = `
schema_version: 1
gates:
  - gate_id: gate-requirements
    name: Req Gate
    description: ""
    conditions: []
    status: pending
    created_at: "2025-01-01T00:00:00Z"
    passed_at: null
    blocked_reasons: []
`;

// ── EnforcementHub.shouldAllowWrite ──────────────────────────────────────────

describe('EnforcementHub.shouldAllowWrite', () => {
  let root: string;

  afterEach(() => {
    if (root) rmSync(root, { recursive: true, force: true });
  });

  it('所有约束满足 → ALLOW', async () => {
    root = setupProject({ state: STATE_ACTIVE, gates: GATES_ALL_PASSED });
    const hub = new EnforcementHub(root);
    // Use backslash paths on Windows since normalize() converts / to \\
    const result = await hub.shouldAllowWrite('src\\main.ts', ['src\\']);
    expect(result.allowed).toBe(true);
    expect(result.blocker_count).toBe(0);
  });

  it('有 blocked gate → DENY', async () => {
    root = setupProject({ state: STATE_ACTIVE, gates: GATES_WITH_BLOCKED });
    const hub = new EnforcementHub(root);
    const result = await hub.shouldAllowWrite('src\\main.ts', ['src\\']);
    expect(result.allowed).toBe(false);
    expect(result.blocker_count).toBeGreaterThan(0);
    expect(result.toHookOutput()).toContain('DENY');
  });
});

// ── EnforcementHub.shouldAllowPhaseAdvance ───────────────────────────────────

describe('EnforcementHub.shouldAllowPhaseAdvance', () => {
  let root: string;

  afterEach(() => {
    if (root) rmSync(root, { recursive: true, force: true });
  });

  it('条件不满足 (C3 无 task context) → DENY', async () => {
    root = setupProject({ state: STATE_ACTIVE, gates: GATES_ALL_PASSED });
    const hub = new EnforcementHub(root);
    const result = await hub.shouldAllowPhaseAdvance('requirements');
    // shouldAllowPhaseAdvance does not load tasks into constraint context,
    // so C3 (task package required) fires as a BLOCKER
    expect(result.allowed).toBe(false);
  });

  it('gate 未通过 → DENY', async () => {
    root = setupProject({ state: STATE_ACTIVE, gates: GATES_WITH_PENDING });
    const hub = new EnforcementHub(root);
    const result = await hub.shouldAllowPhaseAdvance('requirements');
    // gate-requirements is pending, not passed → denied
    expect(result.allowed).toBe(false);
  });
});

// ── EnforcementHub.checkRoleIsolation ────────────────────────────────────────

describe('EnforcementHub.checkRoleIsolation', () => {
  let hub: EnforcementHub;

  beforeEach(() => {
    // Use a minimal project root for construction
    const root = setupProject({ state: STATE_ACTIVE, gates: GATES_ALL_PASSED });
    hub = new EnforcementHub(root);
    // Store root for cleanup
    (hub as any)._root = root;
  });

  afterEach(() => {
    const root = (hub as any)._root;
    if (root) rmSync(root, { recursive: true, force: true });
  });

  it('相同角色 → DENY', () => {
    const result = hub.checkRoleIsolation('R06', 'R06');
    expect(result.allowed).toBe(false);
    expect(result.toHookOutput()).toContain('DENY');
  });

  it('不同域角色 → ALLOW (R06 dev, R07 quality)', () => {
    const result = hub.checkRoleIsolation('R06', 'R07');
    expect(result.allowed).toBe(true);
  });

  it('同域角色 → DENY (R05 dev, R06 dev)', () => {
    const result = hub.checkRoleIsolation('R05', 'R06');
    expect(result.allowed).toBe(false);
  });

  it('不同域角色 → ALLOW (R07 quality, R06 dev)', () => {
    const result = hub.checkRoleIsolation('R07', 'R06');
    expect(result.allowed).toBe(true);
  });
});

// ── EnforcementHub.getGovernanceStatus ───────────────────────────────────────

describe('EnforcementHub.getGovernanceStatus', () => {
  let root: string;

  afterEach(() => {
    if (root) rmSync(root, { recursive: true, force: true });
  });

  it('返回 GovernanceStatus', async () => {
    root = setupProject({ state: STATE_ACTIVE, gates: GATES_ALL_PASSED });
    const hub = new EnforcementHub(root);
    const status = await hub.getGovernanceStatus();
    expect(status.project_root).toBe(root);
    expect(status.current_phase).toBe('requirements');
    expect(status.active_role).toBe('R06');
    // C3 violation (no tasks in phase-advance context) → DEGRADED
    expect(status.overall_status).toBe('DEGRADED');
  });

  it('blocked gates → BLOCKED status', async () => {
    root = setupProject({ state: STATE_ACTIVE, gates: GATES_WITH_BLOCKED });
    const hub = new EnforcementHub(root);
    const status = await hub.getGovernanceStatus();
    expect(status.overall_status).toBe('BLOCKED');
    expect(status.blocked_gates).toContain('gate-requirements');
  });
});

// ── quickCheck ───────────────────────────────────────────────────────────────

describe('quickCheck', () => {
  let root: string;

  afterEach(() => {
    if (root) rmSync(root, { recursive: true, force: true });
  });

  it('无治理状态 → DENY (cannot load)', async () => {
    root = mkdtempSync(join(tmpdir(), 'qc-test-'));
    const result = await quickCheck(root);
    // No state.yaml → loadState throws → caught → DENY
    expect(result.allowed).toBe(false);
    expect(result.toHookOutput()).toContain('DENY');
  });

  it('有 blocked gates → DENY', async () => {
    root = setupProject({ state: STATE_ACTIVE, gates: GATES_WITH_BLOCKED });
    const result = await quickCheck(root);
    expect(result.allowed).toBe(false);
    expect(result.toHookOutput()).toContain('BLOCKED');
  });

  it('治理正常 → ALLOW', async () => {
    root = setupProject({ state: STATE_ACTIVE, gates: GATES_ALL_PASSED });
    const result = await quickCheck(root);
    expect(result.allowed).toBe(true);
    expect(result.toHookOutput()).toContain('ALLOW');
  });
});

// ── EnforcementDecision.toHookOutput ─────────────────────────────────────────

describe('EnforcementDecision.toHookOutput', () => {
  it('ALLOW 返回格式化字符串', async () => {
    const root = setupProject({ state: STATE_ACTIVE, gates: GATES_ALL_PASSED });
    const hub = new EnforcementHub(root);
    const result = await hub.shouldAllowWrite('src\\main.ts', ['src\\']);
    const output = result.toHookOutput();
    expect(output).toContain('[ENFORCEMENT] ALLOW');
    rmSync(root, { recursive: true, force: true });
  });

  it('DENY 返回格式化字符串含 violations', async () => {
    const root = setupProject({ state: STATE_ACTIVE, gates: GATES_WITH_BLOCKED });
    const hub = new EnforcementHub(root);
    const result = await hub.shouldAllowWrite('src\\main.ts', ['src\\']);
    const output = result.toHookOutput();
    expect(output).toContain('[ENFORCEMENT] DENY');
    expect(output).toContain('Blockers:');
    rmSync(root, { recursive: true, force: true });
  });
});
