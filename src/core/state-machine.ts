import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, renameSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import { join, resolve, isAbsolute } from "node:path";
import { parseDocument, Document } from "yaml";
import type {
  ProjectState, PhaseRecord, GateDefinition, GatesRegistry,
  GateCheckResult, GateAdvanceResult
} from "../types/index.js";

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

// ── State ──────────────────────────────────────────────
export async function loadState(root: string): Promise<ProjectState> {
  return readYaml<ProjectState>(statePath(root));
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
    const met = await evaluateCondition(root, state, cond);
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

async function evaluateCondition(root: string, state: ProjectState, cond: GateDefinition["conditions"][number]): Promise<boolean> {
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
      const evDir = evidencePath(root);
      if (!existsSync(evDir)) return false;
      const { parseDocument } = await import("yaml");
      const files = readdirSync(evDir).filter(f => f.endsWith(".yaml"));
      for (const f of files) {
        try {
          const raw = readFileSync(join(evDir, f), "utf-8");
          const record = parseDocument(raw).toJSON();
          if (record.type === evidenceType) return true;
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

  // Evaluate conditions on the same snapshot
  const missing: GateCheckResult["missing_conditions"] = [];
  if (gate.status !== "passed") {
    for (const cond of gate.conditions) {
      const met = await evaluateCondition(root, state, cond);
      if (!met) {
        missing.push({ condition_id: cond.condition_id, type: cond.type, description: cond.description, detail: JSON.stringify(cond.params) });
      }
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

// ── Hash utility ───────────────────────────────────────
export function computeHash(content: string): string {
  return createHash("sha256").update(content, "utf-8").digest("hex");
}
