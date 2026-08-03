import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, renameSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import { join, resolve, isAbsolute } from "node:path";
import { parseDocument, Document } from "yaml";
import type {
  ProjectState, PhaseRecord, GateDefinition, GatesRegistry,
  GateCheckResult, GateAdvanceResult, GateCondition, UserApproval
} from "../types/index.js";
import { rolesForPhase, PHASE_ROLE_MAP, NORM_PHASES } from "./phase_registry.js";

// ── Error ──────────────────────────────────────────────
export class LoopError extends Error {
  constructor(
    public code: string,
    message: string,
    public detail?: string,
    public recoverable = false,
  ) {
    super(message);
    this.name = "LoopError";
  }
}

// ── Paths ──────────────────────────────────────────────
const AI_DIR = ".ai";
const STATE_FILE = "state.yaml";
const GATES_FILE = "gates.yaml";
const EVIDENCE_DIR = "evidence";

// ── Validation ─────────────────────────────────────────
export function validateProjectRoot(root: string): string {
  if (!isAbsolute(root)) {
    throw new LoopError("INVALID_ROOT", `Project root must be absolute path: ${root}`, root);
  }
  if (root.includes("..")) {
    throw new LoopError("INVALID_ROOT", `Project root must not contain '..': ${root}`, root);
  }
  return resolve(root);
}

function aiPath(root: string) { return join(root, AI_DIR); }
function statePath(root: string) { return join(root, AI_DIR, STATE_FILE); }
function gatesPath(root: string) { return join(root, AI_DIR, GATES_FILE); }
function evidencePath(root: string) { return join(root, AI_DIR, EVIDENCE_DIR); }

// ── Atomic YAML I/O ────────────────────────────────────
function atomicWrite(filePath: string, content: string): void {
  const tmp = filePath + ".tmp";
  writeFileSync(tmp, content, "utf-8");
  renameSync(tmp, filePath);
}

function readYaml<T>(filePath: string): T {
  if (!existsSync(filePath)) {
    throw new LoopError("FILE_NOT_FOUND", `File not found: ${filePath}`, filePath);
  }
  const raw = readFileSync(filePath, "utf-8");
  return parseDocument(raw).toJSON() as T;
}

// ── Schema migration ───────────────────────────────────
/**
 * Current on-disk schema version for ProjectState.
 * v1 = legacy 6-phase (initProject); v2 = extended 12-phase (initProjectExtended).
 */
export const CURRENT_SCHEMA_VERSION = 2;

/**
 * Normalize a loaded ProjectState to the current schema shape.
 *
 * Fixes the Better-Harness finding "state-schema-no-migration": loadState used
 * to return v1 states with the v2-only optional fields left as `undefined`,
 * which risks runtime errors for any consumer reading loop_mode / project_status /
 * iteration / user_approvals.
 *
 * This is a defensive, idempotent, in-memory migration:
 * - It fills the optional governance fields introduced in v2 with safe defaults.
 * - It intentionally does NOT remap legacy 6-phase IDs to the extended 12-phase
 *   system, because that would invalidate existing gate_id references and
 *   completed-role history. Legacy states remain fully usable with their own
 *   PHASE_GATES; only the new optional fields are normalized.
 * - It does not write back to disk, keeping loadState side-effect-free. Callers
 *   persist the normalized shape via saveState on their next write.
 */
export function migrateState(state: ProjectState): ProjectState {
  const version = typeof state.schema_version === "number" ? state.schema_version : 1;
  if (version >= CURRENT_SCHEMA_VERSION) {
    return {
      ...state,
      user_approvals: state.user_approvals ?? {},
    };
  }
  // v1 → current: fill optional governance fields with safe defaults.
  return {
    ...state,
    schema_version: CURRENT_SCHEMA_VERSION,
    loop_mode: state.loop_mode ?? "STANDARD",
    project_status: state.project_status ?? "draft",
    iteration: state.iteration ?? 1,
    user_approvals: state.user_approvals ?? {},
  };
}

// ── State ──────────────────────────────────────────────
export async function loadState(root: string): Promise<ProjectState> {
  const state = readYaml<ProjectState>(statePath(root));
  return migrateState(state);
}

export async function saveState(root: string, state: ProjectState): Promise<void> {
  const { stringify } = await import("yaml");
  atomicWrite(statePath(root), stringify(state));
}

export async function loadGates(root: string): Promise<GatesRegistry> {
  return readYaml<GatesRegistry>(gatesPath(root));
}

export async function saveGates(root: string, gates: GatesRegistry): Promise<void> {
  const { stringify } = await import("yaml");
  atomicWrite(gatesPath(root), stringify(gates));
}

// ── Default phases & gates ─────────────────────────────
const DEFAULT_PHASES: PhaseRecord[] = [
  { phase_id: "requirements", entered_at: "", exited_at: null, status: "active" },
  { phase_id: "architecture", entered_at: "", exited_at: null, status: "skipped" },
  { phase_id: "planning",     entered_at: "", exited_at: null, status: "skipped" },
  { phase_id: "implementation", entered_at: "", exited_at: null, status: "skipped" },
  { phase_id: "review",       entered_at: "", exited_at: null, status: "skipped" },
  { phase_id: "delivery",     entered_at: "", exited_at: null, status: "skipped" },
];

/**
 * Extended 12-phase system aligned with ZCode loop_core/state_machine.py.
 * Uses the canonical NORM_PHASES from phase_registry.ts.
 */
export const EXTENDED_PHASES: PhaseRecord[] = NORM_PHASES.map((id, i) => ({
  phase_id: id,
  entered_at: "",
  exited_at: null,
  status: i === 0 ? "active" as const : "pending" as const,
  roles_active: rolesForPhase(id),
  // S0-init 无 gate 门禁（T-0009-C：消除幽灵 gate，与 EXTENDED_PHASE_GATES 注册一致）
  gate_id: id === "S0-init" ? undefined : `gate-${id}`,
}));

const PHASE_GATES: Record<string, { id: string; name: string; conditions: GateDefinition["conditions"] }> = {
  requirements: {
    id: "gate-requirements",
    name: "需求基线 Gate",
    conditions: [
      { condition_id: "req-baselined", type: "role_required", description: "R01 需求已基线化", params: { role_id: "R01", status: "completed" } },
      { condition_id: "acceptance-defined", type: "evidence_required", description: "验收标准已定义", params: { evidence_type: "acceptance_criteria" } },
    ],
  },
  architecture: {
    id: "gate-architecture",
    name: "架构评审 Gate",
    conditions: [
      { condition_id: "arch-complete", type: "role_required", description: "R04 架构设计完成", params: { role_id: "R04", status: "completed" } },
      { condition_id: "arch-reviewed", type: "evidence_required", description: "架构评审通过", params: { evidence_type: "architecture_review" } },
      { condition_id: "security-boundary", type: "evidence_required", description: "安全边界已定义", params: { evidence_type: "security_boundary" } },
    ],
  },
  planning: {
    id: "gate-planning",
    name: "详细设计 Gate",
    conditions: [
      { condition_id: "detail-design", type: "role_required", description: "R05 详细设计完成", params: { role_id: "R05", status: "completed" } },
    ],
  },
  implementation: {
    id: "gate-implementation",
    name: "实现完成 Gate",
    conditions: [
      { condition_id: "code-complete", type: "role_required", description: "R06 实现完成", params: { role_id: "R06", status: "completed" } },
      { condition_id: "tests-pass", type: "evidence_required", description: "测试全部通过", params: { evidence_type: "test_result" } },
      { condition_id: "lint-pass", type: "evidence_required", description: "Lint 通过", params: { evidence_type: "lint_result" } },
    ],
  },
  review: {
    id: "gate-review",
    name: "评审 Gate",
    conditions: [
      { condition_id: "review-pass", type: "role_required", description: "R09 评审通过", params: { role_id: "R09", status: "completed" } },
      { condition_id: "qa-pass", type: "role_required", description: "R07 质量通过", params: { role_id: "R07", status: "completed" } },
      { condition_id: "security-pass", type: "role_required", description: "R08 安全通过", params: { role_id: "R08", status: "completed" } },
      { condition_id: "p0-zero", type: "evidence_required", description: "P0 缺陷 = 0", params: { evidence_type: "defect_report", condition: "p0_count == 0" } },
    ],
  },
  delivery: {
    id: "gate-delivery",
    name: "交付 Gate",
    conditions: [
      { condition_id: "delivery-ready", type: "role_required", description: "R03 交付就绪", params: { role_id: "R03", status: "completed" } },
      { condition_id: "ops-ready", type: "role_required", description: "R10 运维就绪", params: { role_id: "R10", status: "completed" } },
      { condition_id: "human-approval", type: "manual_approval", description: "用户验收通过", params: {} },
    ],
  },
};

/**
 * Extended phase gates for the 12-phase system.
 * Aligned with ZCode loop_core/state_machine.py init_project().
 */
export const EXTENDED_PHASE_GATES: Record<string, { id: string; name: string; conditions: GateDefinition["conditions"] }> = {
  "S1-requirements": {
    id: "gate-S1-requirements",
    name: "需求基线 Gate",
    conditions: [
      { condition_id: "req-baselined", type: "role_required", description: "R01 需求已基线化", params: { role_id: "R01", status: "completed" } },
      { condition_id: "acceptance-defined", type: "evidence_required", description: "验收标准已定义", params: { evidence_type: "acceptance_criteria" } },
    ],
  },
  "S2-architecture": {
    id: "gate-S2-architecture",
    name: "架构设计 Gate",
    conditions: [
      { condition_id: "arch-complete", type: "role_required", description: "R04 架构设计完成", params: { role_id: "R04", status: "completed" } },
      { condition_id: "security-boundary", type: "evidence_required", description: "安全边界已定义", params: { evidence_type: "security_boundary" } },
    ],
  },
  "S3-interface": {
    id: "gate-S3-interface",
    name: "接口设计 Gate",
    conditions: [
      { condition_id: "interface-complete", type: "role_required", description: "R05 接口设计完成", params: { role_id: "R05", status: "completed" } },
    ],
  },
  "S4-implementation": {
    id: "gate-S4-implementation",
    name: "实现完成 Gate",
    conditions: [
      { condition_id: "code-complete", type: "role_required", description: "R06 实现完成", params: { role_id: "R06", status: "completed" } },
      { condition_id: "tests-pass", type: "evidence_required", description: "测试全部通过", params: { evidence_type: "test_result" } },
      { condition_id: "review-pass", type: "role_required", description: "R09 独立评审通过", params: { role_id: "R09", status: "completed" } },
    ],
  },
  "S5-quality": {
    id: "gate-S5-quality",
    name: "质量 Gate",
    conditions: [
      { condition_id: "qa-pass", type: "role_required", description: "R07 质量通过", params: { role_id: "R07", status: "completed" } },
      { condition_id: "security-pass", type: "role_required", description: "R08 安全通过", params: { role_id: "R08", status: "completed" } },
    ],
  },
  "S6-delivery": {
    id: "gate-S6-delivery",
    name: "交付 Gate",
    conditions: [
      { condition_id: "delivery-ready", type: "role_required", description: "R03 交付就绪", params: { role_id: "R03", status: "completed" } },
      { condition_id: "human-approval", type: "manual_approval", description: "用户验收通过", params: {} },
    ],
  },
  "S7-integration": {
    id: "gate-S7-integration",
    name: "集成 Gate",
    conditions: [
      { condition_id: "integration-pass", type: "evidence_required", description: "集成测试通过", params: { evidence_type: "integration_test" } },
    ],
  },
  "S8-functional-test": {
    id: "gate-S8-functional-test",
    name: "功能测试 Gate",
    conditions: [
      { condition_id: "functional-pass", type: "evidence_required", description: "功能测试通过", params: { evidence_type: "functional_test" } },
    ],
  },
  "S9-fix-optimize": {
    id: "gate-S9-fix-optimize",
    name: "修复优化 Gate",
    conditions: [
      { condition_id: "defects-fixed", type: "evidence_required", description: "缺陷已修复", params: { evidence_type: "rework_tracker" } },
      { condition_id: "regression-pass", type: "evidence_required", description: "回归测试通过", params: { evidence_type: "regression_test" } },
    ],
  },
  "S10-performance": {
    id: "gate-S10-performance",
    name: "压力测试 Gate",
    conditions: [
      { condition_id: "perf-pass", type: "evidence_required", description: "性能指标达标", params: { evidence_type: "stress_test" } },
    ],
  },
  "S11-maintenance": {
    id: "gate-S11-maintenance",
    name: "维护 Gate",
    conditions: [
      { condition_id: "ops-ready", type: "role_required", description: "R10 运维就绪", params: { role_id: "R10", status: "completed" } },
    ],
  },
};

// ── Init ───────────────────────────────────────────────
export async function initProject(root: string, projectName: string): Promise<ProjectState> {
  const dir = aiPath(root);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  if (!existsSync(evidencePath(root))) mkdirSync(evidencePath(root), { recursive: true });

  const now = new Date().toISOString();
  const state: ProjectState = {
    schema_version: 1,
    project_name: projectName,
    current_phase: "requirements",
    current_task_id: null,
    current_gate_id: "gate-requirements",
    active_role: null,
    role_activated_at: null,
    completed_roles: [],
    last_handoff_at: now,
    phases: DEFAULT_PHASES.map(p => ({ ...p, entered_at: p.phase_id === "requirements" ? now : "" })),
  };

  const gates: GatesRegistry = {
    schema_version: 1,
    gates: Object.values(PHASE_GATES).map(g => ({
      gate_id: g.id,
      name: g.name,
      description: `${g.name} — 阶段推进条件`,
      conditions: g.conditions,
      status: "pending" as const,
      created_at: now,
      passed_at: null,
      blocked_reasons: [],
    })),
  };

  await saveState(root, state);
  await saveGates(root, gates);
  return state;
}

/**
 * Initialize a project with the extended 12-phase system.
 * Used for FULL loop_mode projects that need complete governance.
 */
export async function initProjectExtended(root: string, projectName: string, loopMode: "FULL" | "STANDARD" = "FULL"): Promise<ProjectState> {
  const dir = aiPath(root);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  if (!existsSync(evidencePath(root))) mkdirSync(evidencePath(root), { recursive: true });

  const now = new Date().toISOString();
  const state: ProjectState = {
    schema_version: 2,
    project_name: projectName,
    current_phase: "S1-requirements",
    current_task_id: null,
    current_gate_id: "gate-S1-requirements",
    active_role: null,
    role_activated_at: null,
    completed_roles: [],
    last_handoff_at: now,
    phases: EXTENDED_PHASES.map((p, i) => ({
      ...p,
      entered_at: p.phase_id === "S1-requirements" || i === 0 ? now : "",
      exited_at: i === 0 ? now : null,
      status: i === 0 ? "completed" as const : i === 1 ? "active" as const : p.status,
    })),
    loop_mode: loopMode,
    project_status: "draft",
    iteration: 1,
  };

  const gates: GatesRegistry = {
    schema_version: 2,
    gates: Object.values(EXTENDED_PHASE_GATES).map(g => ({
      gate_id: g.id,
      name: g.name,
      description: `${g.name} — 阶段推进条件`,
      conditions: g.conditions,
      status: "pending" as const,
      created_at: now,
      passed_at: null,
      blocked_reasons: [],
    })),
  };

  await saveState(root, state);
  await saveGates(root, gates);
  return state;
}

// ── Gate Check ─────────────────────────────────────────
export async function checkGate(root: string, gateId: string): Promise<GateCheckResult> {
  const gates = await loadGates(root);
  const gate = gates.gates.find(g => g.gate_id === gateId);
  if (!gate) {
    throw new LoopError("GATE_NOT_FOUND", `Gate not found: ${gateId}`, gateId);
  }
  if (gate.status === "passed") {
    return { gate_id: gateId, status: "pass", conditions_total: gate.conditions.length, conditions_met: gate.conditions.length, missing_conditions: [] };
  }

  const state = await loadState(root);
  const missing: GateCheckResult["missing_conditions"] = [];

  for (const cond of gate.conditions) {
    const met = cond.type === "manual_approval"
      ? isUserApproved(state, gateId)
      : await evaluateCondition(root, state, cond);
    if (!met) {
      missing.push({ condition_id: cond.condition_id, type: cond.type, description: cond.description, detail: JSON.stringify(cond.params) });
    }
  }

  return {
    gate_id: gateId,
    status: missing.length === 0 ? "pass" : "block",
    conditions_total: gate.conditions.length,
    conditions_met: gate.conditions.length - missing.length,
    missing_conditions: missing,
  };
}

/**
 * 极简证据条件求值器。fail-safe：无法解析的条件返回 false（宁可阻断，不可放行）。
 * 支持形如 `p0_count == 0`、`coverage >= 80`、`status == "passed"` 的表达式。
 * 取值优先级：record.metadata.<key> → record.<key>。
 */
export function evalEvidenceCondition(condition: string, record: Record<string, unknown>): boolean {
  const m = condition.match(/^(\w+)\s*(==|!=|>=|<=|>|<)\s*(.+)$/);
  if (!m) return false; // fail-safe: 无法解析 → 不满足
  const [, key, op, rawVal] = m;
  const metadata = (record.metadata ?? {}) as Record<string, unknown>;
  const actual = metadata[key] ?? record[key];
  if (actual === undefined || actual === null) return false;

  const numActual = Number(actual);
  const numExpected = Number(rawVal);
  if (!Number.isNaN(numActual) && !Number.isNaN(numExpected)) {
    switch (op) {
      case "==": return numActual === numExpected;
      case "!=": return numActual !== numExpected;
      case ">=": return numActual >= numExpected;
      case "<=": return numActual <= numExpected;
      case ">": return numActual > numExpected;
      case "<": return numActual < numExpected;
    }
  }
  const strActual = String(actual);
  const strExpected = rawVal.replace(/^["']|["']$/g, "");
  switch (op) {
    case "==": return strActual === strExpected;
    case "!=": return strActual !== strExpected;
    default: return false; // 字符串不支持大小比较
  }
}

export async function evaluateCondition(root: string, state: ProjectState, cond: GateDefinition["conditions"][number]): Promise<boolean> {
  switch (cond.type) {
    case "role_required": {
      const roleId = cond.params.role_id as string;
      const requiredStatus = cond.params.status as string;
      if (requiredStatus === "completed") {
        return (state.completed_roles ?? []).includes(roleId);
      }
      return state.active_role === roleId;
    }
    case "evidence_required": {
      const evidenceType = cond.params.evidence_type as string;
      const condition = cond.params.condition as string | undefined;
      const evDir = evidencePath(root);
      if (!existsSync(evDir)) return false;
      const { parseDocument } = await import("yaml");
      const files = readdirSync(evDir).filter(f => f.endsWith(".yaml"));
      for (const f of files) {
        try {
          const raw = readFileSync(join(evDir, f), "utf-8");
          const record = parseDocument(raw).toJSON();
          if (record.type !== evidenceType) continue;
          if (condition) {
            return evalEvidenceCondition(condition, record);
          }
          return true;
        } catch { /* skip malformed */ }
      }
      return false;
    }
    case "phase_required": {
      const phaseId = cond.params.phase_id as string;
      return state.phases.some(p => p.phase_id === phaseId && p.status === "completed");
    }
    case "manual_approval":
      return false; // Always requires explicit human action
    default:
      return false;
  }
}

// ── Gate Advance ───────────────────────────────────────
export async function advanceGate(root: string, gateId: string): Promise<GateAdvanceResult> {
  // Single load to avoid TOCTOU race
  const [state, gates] = await Promise.all([loadState(root), loadGates(root)]);
  const now = new Date().toISOString();

  const gate = gates.gates.find(g => g.gate_id === gateId);
  if (!gate) {
    throw new LoopError("GATE_NOT_FOUND", `Gate not found: ${gateId}`, gateId);
  }

  // P0-1: 幂等保护 — 已通过的 gate 直接返回，禁止重复推进（防止绕过后续 gate）
  if (gate.status === "passed") {
    return {
      gate_id: gateId,
      success: true,
      previous_phase: state.current_phase,
      new_phase: state.current_phase,
      advanced_at: gate.passed_at ?? now,
      idempotent: true,
    };
  }

  // P0-2: gate↔阶段绑定 — 只允许推进当前阶段的出口 gate
  if (state.current_gate_id !== gateId) {
    gate.status = "blocked";
    gate.blocked_reasons = [`Gate ${gateId} does not match current gate ${state.current_gate_id ?? "(none)"} — gate-phase binding violated`];
    await saveGates(root, gates);
    return {
      gate_id: gateId,
      success: false,
      previous_phase: state.current_phase,
      new_phase: state.current_phase,
      advanced_at: now,
      error: `Gate blocked: ${gateId} is not the current gate (current: ${state.current_gate_id ?? "(none)"})`,
    };
  }

  // Evaluate conditions on the same snapshot (幂等已在上方提前返回，无需再判 status)
  const missing: GateCheckResult["missing_conditions"] = [];
  for (const cond of gate.conditions) {
      const met = cond.type === "manual_approval"
        ? isUserApproved(state, gateId)
        : await evaluateCondition(root, state, cond);
      if (!met) {
        missing.push({ condition_id: cond.condition_id, type: cond.type, description: cond.description, detail: JSON.stringify(cond.params) });
      }
    }

  if (missing.length > 0) {
    gate.status = "blocked";
    gate.blocked_reasons = missing.map(m => m.description);
    await saveGates(root, gates);
    return {
      gate_id: gateId,
      success: false,
      previous_phase: state.current_phase,
      new_phase: state.current_phase,
      advanced_at: now,
      error: `Gate blocked: ${missing.map(m => m.description).join("; ")}`,
    };
  }

  // Advance
  gate.status = "passed";
  gate.passed_at = now;
  gate.blocked_reasons = [];

  const currentIdx = state.phases.findIndex(p => p.phase_id === state.current_phase);
  if (currentIdx >= 0) {
    state.phases[currentIdx].status = "completed";
    state.phases[currentIdx].exited_at = now;
  }
  const nextIdx = currentIdx + 1;
  if (nextIdx < state.phases.length) {
    state.phases[nextIdx].status = "active";
    state.phases[nextIdx].entered_at = now;
    state.current_phase = state.phases[nextIdx].phase_id;
  }

  const previousPhase = currentIdx >= 0 ? state.phases[currentIdx].phase_id : "unknown";
  state.current_gate_id = nextIdx < state.phases.length
    ? `gate-${state.phases[nextIdx].phase_id}`
    : null;

  await saveState(root, state);
  await saveGates(root, gates);

  return {
    gate_id: gateId,
    success: true,
    previous_phase: previousPhase,
    new_phase: state.current_phase,
    advanced_at: now,
  };
}

// ── User Approval (manual_approval conditions) ────────

/**
 * Check whether the user has explicitly approved the given gate.
 * Manual-approval conditions can ONLY be satisfied via approveGate —
 * role verdicts and evidence are never treated as user approval.
 * Anti-forgery: the record must be complete (gate_id match, approved_by=user).
 */
export function isUserApproved(state: ProjectState, gateId: string): boolean {
  const rec = state.user_approvals?.[gateId];
  return Boolean(rec && rec.approved_at && rec.approved_by === "user" && rec.gate_id === gateId);
}

/**
 * Record an explicit user approval for a gate's manual_approval condition.
 *
 * This is the ONLY path that satisfies `manual_approval` gate conditions.
 * - `approved_by` is hard-coded to "user" — callers cannot forge an identity.
 * - The approval is automatically appended to the chain-hashed audit ledger.
 * - It does NOT advance the gate — callers must still run advanceGate after
 *   all conditions (including this approval) are satisfied.
 */
export async function approveGate(
  root: string,
  gateId: string,
  note?: string,
): Promise<{ success: boolean; gate_id: string; approved_at: string; error?: string }> {
  const state = await loadState(root);
  const gates = await loadGates(root);
  const gate = gates.gates.find(g => g.gate_id === gateId);
  if (!gate) {
    return { success: false, gate_id: gateId, approved_at: "", error: `Gate not found: ${gateId}` };
  }
  if (!gate.conditions.some(c => c.type === "manual_approval")) {
    return { success: false, gate_id: gateId, approved_at: "", error: `Gate ${gateId} has no manual_approval condition — nothing to approve` };
  }

  const approvedAt = new Date().toISOString();
  const rec: UserApproval = { gate_id: gateId, approved_by: "user", approved_at: approvedAt, note };
  state.user_approvals = { ...(state.user_approvals ?? {}), [gateId]: rec };
  await saveState(root, state);

  // 自动审计：批准事件写入链式账本（可追溯，P0-3 防线之一）
  try {
    const { AuditLedger } = await import("./audit_ledger.js");
    const ledger = new AuditLedger(join(root, ".ai", "audit_ledger.jsonl"));
    ledger.append("user_gate_approval", "user", { gate_id: gateId, approved_at: approvedAt, note: note ?? null });
  } catch { /* 审计失败不阻断批准——账本完整性可单独验证 */ }

  return { success: true, gate_id: gateId, approved_at: approvedAt };
}

// ── Hash utility ───────────────────────────────────────
export function computeHash(content: string): string {
  return createHash("sha256").update(content, "utf-8").digest("hex");
}

// ── User Gate Phases (ZCode v3.3) ─────────────────────

/**
 * Only these phase boundaries represent a user decision.
 * Role verdicts and internal evidence gates must NOT be treated as user approval.
 */
export const USER_GATE_PHASES: ReadonlySet<string> = new Set([
  "S1-requirements",
  "S6-delivery",
]);

/**
 * Check whether entering a phase requires an explicit user gate.
 *
 * @param phase - The phase ID to check
 * @returns true if the phase requires explicit user approval
 */
export function phaseNeedsUserGate(phase: string): boolean {
  return USER_GATE_PHASES.has(phase);
}

// ── Public GateCondition API (ZCode v3.3) ──────────────

/**
 * Evaluate a single gate condition against current project state.
 *
 * Public wrapper around the internal evaluateCondition for use by tools and hooks.
 *
 * @param root - Project root directory
 * @param condition - The condition to evaluate
 * @param state - Optional pre-loaded project state
 * @returns true if the condition is met
 */
export async function evaluateGateCondition(
  root: string,
  condition: GateCondition,
  state?: ProjectState,
): Promise<boolean> {
  const s = state ?? await loadState(root);
  return evaluateCondition(root, s, condition);
}

// ── Enhanced Gate Initialization (ZCode v3.3) ──────────

/**
 * Generate default 6-phase gate definitions with concrete conditions.
 *
 * Produces role_required, evidence_required, and manual_approval conditions
 * for each standard phase gate. Used by initProjectExtended for FULL mode.
 */
export function generateDefaultGates(now: string): GateDefinition[] {
  return [
    {
      gate_id: "gate-requirements",
      name: "Requirements Gate",
      description: "S1-requirements 阶段入口",
      conditions: [
        { condition_id: "req-baselined", type: "role_required" as const, description: "需求已基线化", params: { role_id: "product-manager", status: "completed" } },
      ],
      status: "pending" as const,
      created_at: now,
      passed_at: null,
      blocked_reasons: [],
    },
    {
      gate_id: "gate-architecture",
      name: "Architecture Gate",
      description: "S2-architecture 阶段入口",
      conditions: [
        { condition_id: "arch-complete", type: "role_required" as const, description: "架构设计完成", params: { role_id: "system-architect", status: "completed" } },
      ],
      status: "pending" as const,
      created_at: now,
      passed_at: null,
      blocked_reasons: [],
    },
    {
      gate_id: "gate-implementation",
      name: "Implementation Gate",
      description: "S4-implementation 阶段入口",
      conditions: [
        { condition_id: "code-complete", type: "role_required" as const, description: "代码实现完成", params: { role_id: "developer", status: "completed" } },
        { condition_id: "tests-pass", type: "evidence_required" as const, description: "测试通过", params: { evidence_type: "test_result" } },
      ],
      status: "pending" as const,
      created_at: now,
      passed_at: null,
      blocked_reasons: [],
    },
    {
      gate_id: "gate-quality",
      name: "Quality Gate",
      description: "S5-quality 阶段入口",
      conditions: [
        { condition_id: "qa-pass", type: "role_required" as const, description: "质量验证通过", params: { role_id: "quality-engineer", status: "completed" } },
        { condition_id: "security-pass", type: "role_required" as const, description: "安全审查通过", params: { role_id: "security-engineer", status: "completed" } },
      ],
      status: "pending" as const,
      created_at: now,
      passed_at: null,
      blocked_reasons: [],
    },
    {
      gate_id: "gate-delivery",
      name: "Delivery Gate",
      description: "S6-delivery 阶段入口",
      conditions: [
        { condition_id: "delivery-ready", type: "role_required" as const, description: "交付就绪", params: { role_id: "delivery-manager", status: "completed" } },
        { condition_id: "human-approval", type: "manual_approval" as const, description: "用户验收通过", params: {} },
      ],
      status: "pending" as const,
      created_at: now,
      passed_at: null,
      blocked_reasons: [],
    },
  ];
}
