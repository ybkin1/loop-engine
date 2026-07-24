import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';
import {
  ContextController, Action, Decision,
  isGovernancePath, PROTECTED_PATHS, quickAuth,
} from '../src/core/context_controller.js';

// ── Helpers ──────────────────────────────────────────────────────────────────

function setupProject(opts: { state?: string; gates?: string; taskGraph?: string } = {}) {
  const root = mkdtempSync(join(tmpdir(), 'ctx-ctrl-test-'));
  const aiDir = join(root, '.ai');
  mkdirSync(aiDir, { recursive: true });
  if (opts.state) writeFileSync(join(aiDir, 'state.yaml'), opts.state, 'utf-8');
  if (opts.gates) writeFileSync(join(aiDir, 'gates.yaml'), opts.gates, 'utf-8');
  if (opts.taskGraph) writeFileSync(join(aiDir, 'task_graph.yaml'), opts.taskGraph, 'utf-8');
  return root;
}

const MINIMAL_STATE = `
schema_version: 1
project_name: test
current_phase: requirements
current_task_id: null
current_gate_id: gate-requirements
active_role: null
role_activated_at: null
completed_roles: []
last_handoff_at: "2025-01-01T00:00:00Z"
phases:
  - phase_id: requirements
    entered_at: "2025-01-01T00:00:00Z"
    exited_at: null
    status: active
`;

const MINIMAL_GATES = `
schema_version: 1
gates:
  - gate_id: gate-requirements
    name: Req Gate
    description: ""
    conditions: []
    status: passed
    created_at: "2025-01-01T00:00:00Z"
    passed_at: null
    blocked_reasons: []
`;

const GATES_WITH_PENDING = `
schema_version: 1
gates:
  - gate_id: gate-requirements
    name: Req Gate
    description: ""
    conditions: []
    status: passed
    created_at: "2025-01-01T00:00:00Z"
    passed_at: null
    blocked_reasons: []
  - gate_id: gate-implementation
    name: Impl Gate
    description: ""
    conditions: []
    status: pending
    created_at: "2025-01-01T00:00:00Z"
    passed_at: null
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

const TASK_GRAPH_ACTIVE = `
tasks:
  - task_id: task-1
    status: active
    allowed_paths:
      - src/
`;

// ── Action enum ──────────────────────────────────────────────────────────────

describe('Action enum', () => {
  it('包含所有预期值', () => {
    expect(Action.WRITE_FILE).toBe('WRITE_FILE');
    expect(Action.EDIT_FILE).toBe('EDIT_FILE');
    expect(Action.EXEC_BASH).toBe('EXEC_BASH');
    expect(Action.LAUNCH_ROLE).toBe('LAUNCH_ROLE');
    expect(Action.INSTALL_PACKAGE).toBe('INSTALL_PACKAGE');
    expect(Action.DELETE_FILE).toBe('DELETE_FILE');
    expect(Action.MODIFY_GATE).toBe('MODIFY_GATE');
    expect(Action.MODIFY_STATE).toBe('MODIFY_STATE');
    expect(Action.SUBMIT_EVIDENCE).toBe('SUBMIT_EVIDENCE');
    expect(Action.CREATE_HANDOFF).toBe('CREATE_HANDOFF');
    expect(Action.ADVANCE_PHASE).toBe('ADVANCE_PHASE');
  });
});

// ── Decision enum ────────────────────────────────────────────────────────────

describe('Decision enum', () => {
  it('包含 ALLOW / DENY / ASK_USER', () => {
    expect(Decision.ALLOW).toBe('ALLOW');
    expect(Decision.DENY).toBe('DENY');
    expect(Decision.ASK_USER).toBe('ASK_USER');
  });
});

// ── isGovernancePath ─────────────────────────────────────────────────────────

describe('isGovernancePath', () => {
  it('.ai/state.yaml → true', () => {
    expect(isGovernancePath('.ai/state.yaml')).toBe(true);
  });

  it('.ai/gates.yaml → true', () => {
    expect(isGovernancePath('.ai/gates.yaml')).toBe(true);
  });

  it('src/main.ts → false', () => {
    expect(isGovernancePath('src/main.ts')).toBe(false);
  });

  it('absolute .ai path → true', () => {
    expect(isGovernancePath('/project/.ai/state.yaml')).toBe(true);
  });
});

// ── PROTECTED_PATHS ──────────────────────────────────────────────────────────

describe('PROTECTED_PATHS', () => {
  it('包含 AGENTS.md', () => {
    expect(PROTECTED_PATHS).toContain('AGENTS.md');
  });

  it('包含 .ai/state.yaml', () => {
    expect(PROTECTED_PATHS).toContain('.ai/state.yaml');
  });

  it('包含 .ai/gates.yaml', () => {
    expect(PROTECTED_PATHS).toContain('.ai/gates.yaml');
  });
});

// ── ContextController ────────────────────────────────────────────────────────

describe('ContextController', () => {
  let controller: ContextController;
  let root: string;

  beforeEach(() => { controller = new ContextController(); });

  afterEach(() => {
    if (root) rmSync(root, { recursive: true, force: true });
  });

  it('非治理项目（无 state.yaml）→ ALLOW', async () => {
    root = setupProject(); // no state.yaml
    const result = await controller.authorize({
      action: Action.WRITE_FILE,
      target_path: 'src/main.ts',
      project_root: root,
    });
    expect(result.decision).toBe(Decision.ALLOW);
    expect(result.check_level).toBe(3);
  });

  it('INSTALL_PACKAGE → DENY (高风险)', async () => {
    root = setupProject();
    const result = await controller.authorize({
      action: Action.INSTALL_PACKAGE,
      project_root: root,
    });
    expect(result.decision).toBe(Decision.DENY);
    expect(result.check_level).toBe(1);
  });

  it('DELETE_FILE → DENY (高风险)', async () => {
    root = setupProject();
    const result = await controller.authorize({
      action: Action.DELETE_FILE,
      project_root: root,
    });
    expect(result.decision).toBe(Decision.DENY);
    expect(result.check_level).toBe(1);
  });

  it('治理文件写入 → ALLOW', async () => {
    root = setupProject({ state: MINIMAL_STATE, gates: MINIMAL_GATES });
    const result = await controller.authorize({
      action: Action.WRITE_FILE,
      target_path: '.ai/evidence/test.yaml',
      project_root: root,
    });
    expect(result.decision).toBe(Decision.ALLOW);
    expect(result.check_level).toBe(3);
  });

  it('无 pending gate → ALLOW', async () => {
    root = setupProject({ state: MINIMAL_STATE, gates: MINIMAL_GATES });
    const result = await controller.authorize({
      action: Action.WRITE_FILE,
      target_path: 'src/main.ts',
      project_root: root,
    });
    expect(result.decision).toBe(Decision.ALLOW);
    expect(result.check_level).toBe(3);
  });

  it('有 pending gate + 无 active task → DENY', async () => {
    root = setupProject({ state: MINIMAL_STATE, gates: GATES_WITH_PENDING });
    const result = await controller.authorize({
      action: Action.WRITE_FILE,
      target_path: 'src/main.ts',
      project_root: root,
    });
    // pending gate → continues to level 4, no task graph → DENY
    expect(result.decision).toBe(Decision.DENY);
    expect(result.check_level).toBe(4);
  });

  it('有 pending gate + 路径在 active task 范围内 → ALLOW', async () => {
    root = setupProject({
      state: MINIMAL_STATE,
      gates: GATES_WITH_PENDING,
      taskGraph: TASK_GRAPH_ACTIVE,
    });
    const result = await controller.authorize({
      action: Action.WRITE_FILE,
      target_path: 'src/index.ts',
      project_root: root,
    });
    expect(result.decision).toBe(Decision.ALLOW);
    expect(result.check_level).toBe(4);
  });

  it('有 blocked gate + 无 task graph → DENY', async () => {
    root = setupProject({ state: MINIMAL_STATE, gates: GATES_WITH_BLOCKED });
    const result = await controller.authorize({
      action: Action.WRITE_FILE,
      target_path: 'src/main.ts',
      project_root: root,
    });
    // blocked counts as pending → level 3 passes through → level 4 no task → DENY
    expect(result.decision).toBe(Decision.DENY);
    expect(result.check_level).toBe(4);
  });

  it('protected path → ASK_USER', async () => {
    root = setupProject();
    const result = await controller.authorize({
      action: Action.WRITE_FILE,
      target_path: 'AGENTS.md',
      project_root: root,
    });
    // Non-governance project → level 3 ALLOW fires first
    // But AGENTS.md is a protected path → level 2 ASK_USER
    // Actually level 2 fires before level 3, so ASK_USER
    expect(result.decision).toBe(Decision.ASK_USER);
    expect(result.check_level).toBe(2);
  });
});

// ── quickAuth ────────────────────────────────────────────────────────────────

describe('quickAuth', () => {
  let root: string;

  afterEach(() => {
    if (root) rmSync(root, { recursive: true, force: true });
  });

  it('非治理项目 → ALLOW', async () => {
    root = mkdtempSync(join(tmpdir(), 'quick-auth-test-'));
    const result = await quickAuth(root, Action.WRITE_FILE, 'src/main.ts');
    expect(result.decision).toBe(Decision.ALLOW);
  });
});
