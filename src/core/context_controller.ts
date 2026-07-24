/**
 * context_controller.ts — Unified Authorization Engine
 *
 * All sensitive operations must pass through this controller's
 * 5-level priority decision chain. Uses fail-closed default deny.
 *
 * Ported from ZCode loop_core/context_controller.py.
 */

import { readFileSync, existsSync } from "node:fs";
import { join, resolve, relative, normalize } from "node:path";
import { parseDocument } from "yaml";
import { loadState, loadGates } from "./state-machine.js";
import type { ProjectState, GatesRegistry, GateDefinition } from "../types/index.js";

// ── Enums ────────────────────────────────────────────────────────────────────

/** Action types that require authorization */
export enum Action {
  WRITE_FILE = "WRITE_FILE",
  EDIT_FILE = "EDIT_FILE",
  EXEC_BASH = "EXEC_BASH",
  LAUNCH_ROLE = "LAUNCH_ROLE",
  INSTALL_PACKAGE = "INSTALL_PACKAGE",
  DELETE_FILE = "DELETE_FILE",
  MODIFY_GATE = "MODIFY_GATE",
  MODIFY_STATE = "MODIFY_STATE",
  SUBMIT_EVIDENCE = "SUBMIT_EVIDENCE",
  CREATE_HANDOFF = "CREATE_HANDOFF",
  ADVANCE_PHASE = "ADVANCE_PHASE",
}

/** Authorization decision */
export enum Decision {
  ALLOW = "ALLOW",
  DENY = "DENY",
  ASK_USER = "ASK_USER",
}

// ── Interfaces ───────────────────────────────────────────────────────────────

/** Authorization request */
export interface AuthRequest {
  action: Action;
  target_path?: string;
  task_id?: string;
  role_id?: string;
  command?: string;
  project_root: string;
}

/** Authorization result */
export interface AuthResult {
  decision: Decision;
  reason: string;
  required_gate_id?: string;
  allowed_paths?: string[];
  /** Which check level produced this result */
  check_level: number;
}

// ── Constants ────────────────────────────────────────────────────────────────

/** Protected paths that always require user approval */
export const PROTECTED_PATHS: string[] = [
  "AGENTS.md",
  ".ai/state.yaml",
  ".ai/gates.yaml",
];

/** Dangerous command patterns that are always denied for EXEC_BASH */
const DANGEROUS_COMMANDS: RegExp[] = [
  /\brm\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+)*\//,       // rm -rf / or rm file
  /\bformat\s+[a-zA-Z]:/,                           // Windows format
  /\bdd\s+.*\bof=\/dev\/[sh]d/,                     // dd to disk
  /\bmkfs\b/,                                        // mkfs
  /\b(del|remove)\s+\/[sSfq]/,                       // Windows del /S /F /Q
  /\bshutdown\b/,                                    // shutdown
  /\breboot\b/,                                      // reboot
  /\breg\s+delete\b/,                                // Windows registry delete
];

/** Governance file directory pattern */
const GOVERNANCE_DIR = ".ai";

/** Task graph file path relative to project root */
const TASK_GRAPH_FILE = join(".ai", "task_graph.yaml");

// ── Task types (local) ───────────────────────────────────────────────────────

/** Minimal task record shape for task scope checking */
interface TaskRecord {
  task_id: string;
  status: string;
  allowed_paths?: string[];
}

/** Minimal task graph shape */
interface TaskGraph {
  tasks: TaskRecord[];
}

// ── Helper Functions ─────────────────────────────────────────────────────────

/**
 * Check if a file path points to a governance file under .ai/.
 *
 * @param filePath - The file path to check (absolute or relative)
 * @returns `true` if the path is a governance file
 */
export function isGovernancePath(filePath: string): boolean {
  const normalized = normalize(filePath).replace(/\\/g, "/");
  // Match .ai/ prefix or /.ai/ in the path
  return (
    normalized.startsWith(".ai/") ||
    normalized.includes("/.ai/") ||
    normalized.startsWith(GOVERNANCE_DIR) ||
    normalized.endsWith("/state.yaml") ||
    normalized.endsWith("/gates.yaml")
  );
}

/**
 * Check if a path matches any of the protected path patterns.
 *
 * @param filePath - The file path to check
 * @returns `true` if the path is protected
 */
function isProtectedPath(filePath: string): boolean {
  const normalized = normalize(filePath).replace(/\\/g, "/");
  return PROTECTED_PATHS.some(pp => {
    const ppNorm = normalize(pp).replace(/\\/g, "/");
    return normalized.endsWith(ppNorm) || normalized === ppNorm;
  });
}

/**
 * Check if a bash command contains dangerous patterns.
 *
 * @param command - The command string to inspect
 * @returns `true` if the command is considered dangerous
 */
function isDangerousCommand(command: string): boolean {
  return DANGEROUS_COMMANDS.some(pattern => pattern.test(command));
}

/**
 * Safely read and parse a YAML file, returning null if not found or malformed.
 *
 * @param filePath - Absolute path to the YAML file
 * @returns Parsed object or null
 */
function safeReadYaml<T>(filePath: string): T | null {
  try {
    if (!existsSync(filePath)) return null;
    const raw = readFileSync(filePath, "utf-8");
    return parseDocument(raw).toJSON() as T;
  } catch {
    return null;
  }
}

// ── ContextController ────────────────────────────────────────────────────────

/**
 * Unified authorization engine implementing a 5-level priority decision chain.
 *
 * Every sensitive operation must call {@link authorize} before proceeding.
 * The chain is evaluated top-down; the first level that returns a non-null
 * result wins. If no level matches, the fail-closed default deny applies.
 *
 * Priority levels:
 * 1. High-risk operations → DENY
 * 2. Protected paths → ASK_USER
 * 3. Governance files check → ALLOW if no pending gate
 * 4. Task scope validation → check allowed_paths
 * 5. Default → fail-closed DENY
 */
export class ContextController {
  /**
   * Unified authorization entry point.
   *
   * Executes the 5-level priority decision chain and returns the first
   * non-null result. If all checks pass through, returns a default deny.
   *
   * @param request - The authorization request describing the intended action
   * @returns The authorization result with decision, reason, and check level
   */
  async authorize(request: AuthRequest): Promise<AuthResult> {
    // Level 1: High-risk operations
    const highRisk = await this._check_high_risk(request);
    if (highRisk) return highRisk;

    // Level 2: Protected paths
    const protected_ = await this._check_protected(request);
    if (protected_) return protected_;

    // Level 3: Governance files check
    const governance = await this._check_governance(request);
    if (governance) return governance;

    // Level 4: Task scope validation
    const taskScope = await this._check_task_scope(request);
    if (taskScope) return taskScope;

    // Level 5: Default deny
    return this._default_deny(request);
  }

  /**
   * Level 1 — High-risk operations check.
   *
   * Immediately denies operations that are inherently dangerous:
   * - INSTALL_PACKAGE and DELETE_FILE are always denied
   * - EXEC_BASH with dangerous commands (rm, format, etc.) is denied
   *
   * @param request - The authorization request
   * @returns AuthResult with DENY if high-risk, or null to pass to next level
   */
  private async _check_high_risk(request: AuthRequest): Promise<AuthResult | null> {
    // Always deny package installation
    if (request.action === Action.INSTALL_PACKAGE) {
      return {
        decision: Decision.DENY,
        reason: "High-risk: INSTALL_PACKAGE is not permitted. Use manual package management.",
        check_level: 1,
      };
    }

    // Always deny file deletion
    if (request.action === Action.DELETE_FILE) {
      return {
        decision: Decision.DENY,
        reason: "High-risk: DELETE_FILE is not permitted. Use manual file removal.",
        check_level: 1,
      };
    }

    // Check for dangerous bash commands
    if (request.action === Action.EXEC_BASH && request.command) {
      if (isDangerousCommand(request.command)) {
        return {
          decision: Decision.DENY,
          reason: `High-risk: EXEC_BASH command matches dangerous pattern: "${request.command}". Destructive system commands are blocked.`,
          check_level: 1,
        };
      }
    }

    return null;
  }

  /**
   * Level 2 — Protected paths check.
   *
   * Operations targeting protected files (AGENTS.md, .ai/state.yaml,
   * .ai/gates.yaml) require explicit user approval.
   *
   * MODIFY_GATE and MODIFY_STATE from non-system roles also require approval.
   *
   * @param request - The authorization request
   * @returns AuthResult with ASK_USER if protected, or null to pass to next level
   */
  private async _check_protected(request: AuthRequest): Promise<AuthResult | null> {
    // Check if target path is a protected file
    if (request.target_path && isProtectedPath(request.target_path)) {
      return {
        decision: Decision.ASK_USER,
        reason: `Protected path: "${request.target_path}" requires explicit user approval.`,
        check_level: 2,
      };
    }

    // MODIFY_GATE / MODIFY_STATE from non-system roles need approval
    if (request.action === Action.MODIFY_GATE || request.action === Action.MODIFY_STATE) {
      const systemRoles = ["system", "loop", "orchestrator"];
      const role = request.role_id?.toLowerCase() ?? "";
      if (!systemRoles.includes(role)) {
        return {
          decision: Decision.ASK_USER,
          reason: `Protected action: ${request.action} from non-system role "${request.role_id ?? "unknown"}" requires user approval.`,
          check_level: 2,
        };
      }
    }

    return null;
  }

  /**
   * Level 3 — Governance files check.
   *
   * Loads state.yaml and gates.yaml to determine governance status.
   * - If state.yaml not found → ALLOW (non-governance project)
   * - If no pending/blocked gates → ALLOW
   * - If target is a governance file (.ai/*) → ALLOW (Loop can write its own files)
   * - Otherwise → pass to next level
   *
   * @param request - The authorization request
   * @returns AuthResult with ALLOW if governance check passes, or null to continue
   */
  private async _check_governance(request: AuthRequest): Promise<AuthResult | null> {
    const root = resolve(request.project_root);

    // Try to load state — if not found, this is a non-governance project
    let state: ProjectState;
    try {
      state = await loadState(root);
    } catch {
      // No state.yaml → non-governance project, allow freely
      return {
        decision: Decision.ALLOW,
        reason: "No governance state found: project is not under Loop governance.",
        check_level: 3,
      };
    }

    // Load gates registry
    let gates: GatesRegistry;
    try {
      gates = await loadGates(root);
    } catch {
      // No gates.yaml → allow
      return {
        decision: Decision.ALLOW,
        reason: "No gates registry found: governance is not fully initialized.",
        check_level: 3,
      };
    }

    // Check for pending or blocked gates
    const pendingGates = gates.gates.filter(
      (g: GateDefinition) => g.status === "pending" || g.status === "blocked"
    );

    // Governance files are always writable by Loop itself
    if (request.target_path && isGovernancePath(request.target_path)) {
      return {
        decision: Decision.ALLOW,
        reason: "Governance file write: .ai/ files are always writable by Loop engine.",
        check_level: 3,
      };
    }

    // No pending gates → allow
    if (pendingGates.length === 0) {
      return {
        decision: Decision.ALLOW,
        reason: "No pending or blocked gates: all governance gates are passed.",
        check_level: 3,
      };
    }

    // Has pending gates but not a governance file → continue to task scope
    return null;
  }

  /**
   * Level 4 — Task scope validation.
   *
   * Loads the task graph and validates that:
   * - An active task exists
   * - The target path falls within the active task's allowed_paths
   *
   * @param request - The authorization request
   * @returns AuthResult with ALLOW/DENY based on task scope, or null if no task graph
   */
  private async _check_task_scope(request: AuthRequest): Promise<AuthResult | null> {
    const root = resolve(request.project_root);
    const taskGraphPath = join(root, TASK_GRAPH_FILE);

    // Load task graph
    const taskGraph = safeReadYaml<TaskGraph>(taskGraphPath);
    if (!taskGraph || !taskGraph.tasks || taskGraph.tasks.length === 0) {
      // No task graph → cannot validate scope, deny
      return {
        decision: Decision.DENY,
        reason: "No active task: task graph is missing or empty. Create a task before performing operations.",
        check_level: 4,
      };
    }

    // Find active task
    const activeTask = taskGraph.tasks.find(
      t => t.status === "active" || t.status === "in_progress"
    );

    if (!activeTask) {
      return {
        decision: Decision.DENY,
        reason: "No active task: all tasks are completed, pending, or blocked. Activate a task first.",
        check_level: 4,
      };
    }

    // If no target path specified, allow (e.g., read-only operations)
    if (!request.target_path) {
      return {
        decision: Decision.ALLOW,
        reason: `Task scope: active task "${activeTask.task_id}" — no target path to validate.`,
        allowed_paths: activeTask.allowed_paths,
        check_level: 4,
      };
    }

    // Check target path against allowed_paths
    const allowedPaths = activeTask.allowed_paths ?? [];

    if (allowedPaths.length === 0) {
      // No allowed_paths defined — deny by default for safety
      return {
        decision: Decision.DENY,
        reason: `Task scope: active task "${activeTask.task_id}" has no allowed_paths defined. Cannot verify target path.`,
        check_level: 4,
      };
    }

    // Normalize the target path for comparison
    const normalizedTarget = normalize(request.target_path).replace(/\\/g, "/");

    const inScope = allowedPaths.some(prefix => {
      const normalizedPrefix = normalize(prefix).replace(/\\/g, "/");
      return normalizedTarget.startsWith(normalizedPrefix);
    });

    if (!inScope) {
      return {
        decision: Decision.DENY,
        reason: `Task scope: target "${request.target_path}" is outside allowed paths [${allowedPaths.join(", ")}] for task "${activeTask.task_id}".`,
        allowed_paths: allowedPaths,
        check_level: 4,
      };
    }

    return {
      decision: Decision.ALLOW,
      reason: `Task scope: target "${request.target_path}" is within allowed paths for task "${activeTask.task_id}".`,
      allowed_paths: allowedPaths,
      check_level: 4,
    };
  }

  /**
   * Level 5 — Default deny (fail-closed).
   *
   * If no previous level produced a result, the operation is denied by default.
   * This is the fail-closed security posture: anything not explicitly allowed
   * is denied.
   *
   * @param request - The authorization request
   * @returns AuthResult with DENY
   */
  private _default_deny(request: AuthRequest): AuthResult {
    return {
      decision: Decision.DENY,
      reason: `Default deny: operation ${request.action} is not explicitly authorized.`,
      check_level: 5,
    };
  }
}

// ── Quick Auth Helper ────────────────────────────────────────────────────────

/**
 * Quick authorization check for common operations.
 *
 * Creates a ContextController and runs a single authorization check
 * with minimal parameters.
 *
 * @param root - The project root directory
 * @param action - The action to authorize
 * @param targetPath - Optional target file path
 * @returns The authorization result
 */
export async function quickAuth(
  root: string,
  action: Action,
  targetPath?: string,
): Promise<AuthResult> {
  const controller = new ContextController();
  return controller.authorize({
    action,
    target_path: targetPath,
    project_root: root,
  });
}
