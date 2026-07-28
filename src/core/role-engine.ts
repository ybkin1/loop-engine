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
        const gate = gates.gates.find(g => g.gate_id === gateId);
        if (!gate || gate.status !== "passed") {
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
