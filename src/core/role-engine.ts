import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { parseDocument } from "yaml";
import type { RoleSpec, RoleActivateResult, RoleStatusResult, RoleStatus } from "../types/index.js";
import { loadState, saveState, loadGates, LoopError } from "./state-machine.js";

function specsPath(root: string) { return join(root, ".ai", "registry"); }

// ── Sanitize ───────────────────────────────────────────
function sanitizeRoleId(roleId: string): string {
  if (!/^[a-zA-Z0-9_-]+$/.test(roleId)) {
    throw new LoopError("INVALID_ROLE_ID", `Role ID contains invalid characters: ${roleId}. Only [a-zA-Z0-9_-] allowed.`, roleId);
  }
  return roleId;
}

/**
 * Gate ID 别名：legacy（gate-architecture）↔ canonical（gate-S2-architecture）双命名兼容。
 * 6-phase 与 12-phase 项目可共用同一份角色契约。
 */
const GATE_ALIASES: Record<string, string> = {
  "gate-requirements": "gate-S1-requirements",
  "gate-architecture": "gate-S2-architecture",
  "gate-planning": "gate-S3-interface",
  "gate-implementation": "gate-S4-implementation",
  "gate-review": "gate-S5-quality",
  "gate-delivery": "gate-S6-delivery",
};
const GATE_ALIASES_REV: Record<string, string> = Object.fromEntries(
  Object.entries(GATE_ALIASES).map(([k, v]) => [v, k]),
);

/** 任一命名下 gate 已 passed 即视为满足（双命名兼容）。 */
function gatePassedAnyName(gates: { gates: Array<{ gate_id: string; status?: string }> }, gateId: string): boolean {
  const candidates = [gateId, GATE_ALIASES[gateId], GATE_ALIASES_REV[gateId]].filter(Boolean);
  return gates.gates.some(g => candidates.includes(g.gate_id) && g.status === "passed");
}

function loadRoleSpec(root: string, roleId: string): RoleSpec | null {
  const dir = specsPath(root);
  const file = join(dir, `${roleId}.yaml`);
  if (!existsSync(file)) return null;
  const raw = readFileSync(file, "utf-8");
  return parseDocument(raw).toJSON() as RoleSpec;
}

export async function activateRole(root: string, roleId: string, activatedBy = "system"): Promise<RoleActivateResult> {
  sanitizeRoleId(roleId);
  const state = await loadState(root);
  const now = new Date().toISOString();
  const spec = loadRoleSpec(root, roleId);

  // Check prerequisites if spec exists
  const missing: string[] = [];
  if (spec) {
    const requiredRoles = spec.prerequisites?.required_roles ?? [];
    for (const req of requiredRoles) {
      if (!(state.completed_roles ?? []).includes(req)) {
        missing.push(`Role ${req} not completed`);
      }
    }
    const requiredGates = spec.prerequisites?.required_gates ?? [];
    if (requiredGates.length > 0) {
      const gates = await loadGates(root);
      for (const gateId of requiredGates) {
        if (!gatePassedAnyName(gates, gateId)) {
          missing.push(`Gate ${gateId} not passed`);
        }
      }
    }
  }

  if (missing.length > 0) {
    return {
      success: false,
      role_id: roleId,
      status: "blocked",
      missing_prerequisites: missing,
      handoff_received: false,
      activated_at: null,
      error: `Missing prerequisites: ${missing.join(", ")}`,
    };
  }

  state.active_role = roleId;
  state.role_activated_at = now;
  await saveState(root, state);

  return {
    success: true,
    role_id: roleId,
    status: "active",
    missing_prerequisites: [],
    handoff_received: true,
    activated_at: now,
  };
}

export async function getRoleStatus(root: string, roleId: string): Promise<RoleStatusResult> {
  sanitizeRoleId(roleId);
  const state = await loadState(root);
  const spec = loadRoleSpec(root, roleId);
  const isActive = state.active_role === roleId;
  const isCompleted = (state.completed_roles ?? []).includes(roleId);

  let status: RoleStatus = "inactive";
  if (isActive) status = "active";
  else if (isCompleted) status = "completed";

  return {
    role_id: roleId,
    status,
    activated_at: state.role_activated_at ?? null,
    completed_at: null,
    available_operations: spec?.permissions.allowed_operations ?? [],
    allowed_write_paths: spec?.permissions.allowed_write_paths ?? [],
  };
}

export async function completeRole(root: string, roleId: string): Promise<void> {
  sanitizeRoleId(roleId);
  const state = await loadState(root);
  if (state.active_role !== roleId) {
    throw new LoopError("ROLE_NOT_ACTIVE", `Role ${roleId} is not currently active`, roleId);
  }
  state.active_role = null;
  if (!state.completed_roles) state.completed_roles = [];
  if (!state.completed_roles.includes(roleId)) {
    state.completed_roles.push(roleId);
  }
  await saveState(root, state);
}
