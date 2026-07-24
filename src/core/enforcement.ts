/**
 * enforcement.ts — Host adaptation & hard constraints
 *
 * Defines enforcement levels (STRONG/MEDIUM/ADVISORY) and 8 hard constraints
 * that must be enforced by deterministic mechanisms, not model compliance.
 *
 * Aligned with ZCode loop_core/enforcement.py design.
 */

// ── Enforcement Levels ───────────────────────────────
export enum EnforcementLevel {
  STRONG = "STRONG",     // Can intercept writes + commands + exit codes
  MEDIUM = "MEDIUM",     // Can intercept via hooks/plugins/MCP
  ADVISORY = "ADVISORY", // Read-only: can suggest but not enforce
}

// ── Host Capabilities ────────────────────────────────
export interface HostCapabilities {
  can_intercept_writes: boolean;
  can_intercept_commands: boolean;
  can_isolate_agents: boolean;
  can_enforce_exit_codes: boolean;
  has_hooks_api: boolean;
}

// ── Hard Constraint ──────────────────────────────────
export interface HardConstraint {
  id: string;
  description: string;
  /** Behavior at each enforcement level */
  behavior: Record<EnforcementLevel, "BLOCK" | "WARN" | "ADVISORY">;
}

/**
 * Legacy constraint definitions.
 * For programmatic constraint checking, use HardConstraints class from ./hard_constraints.js
 * which provides deterministic C1-C8 checking with full context support.
 *
 * Mapping:
 *   NO_IMPL_WITHOUT_REQUIREMENTS → C1 (Requirements Baseline)
 *   NO_DEV_WITHOUT_ARCHITECTURE → C2 (Architecture Baseline)
 *   NO_WRITE_WITHOUT_TASK → C3 (Task Package)
 *   (path scope) → C4 (Path Scope)
 *   NO_DELIVERY_WITHOUT_VERIFICATION → C5 (Verification Pass)
 *   NO_PASS_WITHOUT_REVIEW → C6 (Independent Review)
 *   NO_NEXT_PHASE_WITH_BLOCKERS → C7 (No Blockers)
 *   EVIDENCE_STALE_ON_CHANGE → C8 (Evidence Freshness)
 */
export const HARD_CONSTRAINTS: HardConstraint[] = [
  {
    id: "NO_IMPL_WITHOUT_REQUIREMENTS",
    description: "Cannot enter implementation without requirements baseline",
    behavior: { STRONG: "BLOCK", MEDIUM: "WARN", ADVISORY: "ADVISORY" },
  },
  {
    id: "NO_DEV_WITHOUT_ARCHITECTURE",
    description: "Cannot enter development without architecture constraints",
    behavior: { STRONG: "BLOCK", MEDIUM: "WARN", ADVISORY: "ADVISORY" },
  },
  {
    id: "NO_WRITE_WITHOUT_TASK",
    description: "Cannot write files without an active task and allowed_write paths",
    behavior: { STRONG: "BLOCK", MEDIUM: "WARN", ADVISORY: "ADVISORY" },
  },
  {
    id: "NO_DELIVERY_WITHOUT_VERIFICATION",
    description: "Cannot deliver without deterministic verification (test + lint)",
    behavior: { STRONG: "BLOCK", MEDIUM: "WARN", ADVISORY: "ADVISORY" },
  },
  {
    id: "NO_PASS_WITHOUT_REVIEW",
    description: "Cannot pass implementation phase without independent review",
    behavior: { STRONG: "BLOCK", MEDIUM: "WARN", ADVISORY: "ADVISORY" },
  },
  {
    id: "NO_NEXT_PHASE_WITH_BLOCKERS",
    description: "Cannot advance to next phase with unresolved blockers",
    behavior: { STRONG: "BLOCK", MEDIUM: "WARN", ADVISORY: "ADVISORY" },
  },
  {
    id: "EVIDENCE_STALE_ON_CHANGE",
    description: "Evidence becomes stale when bound inputs change",
    behavior: { STRONG: "BLOCK", MEDIUM: "WARN", ADVISORY: "ADVISORY" },
  },
  {
    id: "NO_AUTO_GATE_PASS",
    description: "Gates cannot auto-approve — requires explicit user approval",
    behavior: { STRONG: "BLOCK", MEDIUM: "BLOCK", ADVISORY: "WARN" },
  },
];

// ── Enforcement Result ───────────────────────────────
export interface EnforcementResult {
  level: EnforcementLevel;
  violations: string[];
  warnings: string[];
  is_blocked: boolean;
  /** This module never lies about enforcement level */
  is_honest: true;
}

// ── Core Functions ───────────────────────────────────

/**
 * Derive enforcement level from host capabilities.
 * STRONG: intercept writes + commands + exit codes
 * MEDIUM: has hooks API OR can isolate agents
 * ADVISORY: everything else
 */
export function deriveEnforcementLevel(caps: HostCapabilities): EnforcementLevel {
  if (caps.can_intercept_writes && caps.can_intercept_commands && caps.can_enforce_exit_codes) {
    return EnforcementLevel.STRONG;
  }
  if (caps.has_hooks_api || caps.can_isolate_agents) {
    return EnforcementLevel.MEDIUM;
  }
  return EnforcementLevel.ADVISORY;
}

/**
 * Validate that a host's declared capabilities are consistent
 * with its claimed enforcement level.
 */
export function validateHostCapabilities(
  caps: HostCapabilities,
  claimedLevel: EnforcementLevel,
): EnforcementResult {
  const actualLevel = deriveEnforcementLevel(caps);
  const violations: string[] = [];
  const warnings: string[] = [];

  // Host cannot claim higher enforcement than capabilities allow
  const levelOrder = [EnforcementLevel.ADVISORY, EnforcementLevel.MEDIUM, EnforcementLevel.STRONG];
  const actualIdx = levelOrder.indexOf(actualLevel);
  const claimedIdx = levelOrder.indexOf(claimedLevel);

  if (claimedIdx > actualIdx) {
    violations.push(
      `Host claims ${claimedLevel} but capabilities only support ${actualLevel}. ` +
      `Weak integration cannot pretend to have hard constraints.`,
    );
  }

  return {
    level: actualLevel,
    violations,
    warnings,
    is_blocked: violations.length > 0 && actualLevel === EnforcementLevel.STRONG,
    is_honest: true,
  };
}

/**
 * Check a specific constraint at a given enforcement level.
 * @deprecated Use HardConstraints class from ./hard_constraints.js for deterministic C1-C8 checking.
 */
export function checkConstraint(
  constraintId: string,
  level: EnforcementLevel,
  context: Record<string, unknown>,
): { constraint_id: string; action: "BLOCK" | "WARN" | "ADVISORY"; passed: boolean; reason: string } {
  const constraint = HARD_CONSTRAINTS.find(c => c.id === constraintId);
  if (!constraint) {
    return { constraint_id: constraintId, action: "ADVISORY", passed: false, reason: `Unknown constraint: ${constraintId}` };
  }

  const action = constraint.behavior[level];
  const passed = evaluateConstraint(constraintId, context);

  return {
    constraint_id: constraintId,
    action,
    passed,
    reason: passed ? "Constraint satisfied" : `Constraint violated: ${constraint.description}`,
  };
}

/**
 * Evaluate a constraint against current context.
 * Returns true if the constraint is satisfied (no violation).
 */
function evaluateConstraint(constraintId: string, ctx: Record<string, unknown>): boolean {
  switch (constraintId) {
    case "NO_IMPL_WITHOUT_REQUIREMENTS":
      return ctx.phase !== "implementation" || Boolean(ctx.requirements_baselined);
    case "NO_DEV_WITHOUT_ARCHITECTURE":
      return ctx.phase !== "implementation" || Boolean(ctx.architecture_approved);
    case "NO_WRITE_WITHOUT_TASK":
      return Boolean(ctx.has_active_task && ctx.target_in_allowed_paths);
    case "NO_DELIVERY_WITHOUT_VERIFICATION":
      return ctx.phase !== "delivery" || (Boolean(ctx.has_test_evidence) && Boolean(ctx.has_lint_evidence));
    case "NO_PASS_WITHOUT_REVIEW":
      return ctx.phase !== "implementation" || Boolean(ctx.has_independent_review);
    case "NO_NEXT_PHASE_WITH_BLOCKERS":
      return !Boolean(ctx.has_unresolved_blockers);
    case "EVIDENCE_STALE_ON_CHANGE":
      return !Boolean(ctx.evidence_is_stale);
    case "NO_AUTO_GATE_PASS":
      return ctx.gate_status !== "approved" || Boolean(ctx.explicit_user_approval);
    default:
      return false;
  }
}

/**
 * Get the full degradation table for a given enforcement level.
 * Shows what action each constraint takes at each level.
 */
export function getDegradationTable(level: EnforcementLevel): Array<{
  constraint_id: string;
  description: string;
  action: "BLOCK" | "WARN" | "ADVISORY";
  can_enforce: boolean;
}> {
  return HARD_CONSTRAINTS.map(c => ({
    constraint_id: c.id,
    description: c.description,
    action: c.behavior[level],
    can_enforce: c.behavior[level] === "BLOCK",
  }));
}

/**
 * Known host adapter presets.
 */
export const HOST_PRESETS: Record<string, HostCapabilities> = {
  qoder: {
    can_intercept_writes: true,     // PreToolUse: gate-guard, path-guard, role-isolation, ledger-guard
    can_intercept_commands: true,   // PreToolUse: gate-guard (Bash matcher)
    can_isolate_agents: false,      // Skills share same context
    can_enforce_exit_codes: true,   // PreToolUse exit 2 blocks execution
    has_hooks_api: true,            // 7 hooks in settings.json
  },
  zcode: {
    can_intercept_writes: true,
    can_intercept_commands: true,
    can_isolate_agents: true,
    can_enforce_exit_codes: true,
    has_hooks_api: true,
  },
  claude_code: {
    can_intercept_writes: true,
    can_intercept_commands: true,
    can_isolate_agents: true,
    can_enforce_exit_codes: true,
    has_hooks_api: true,
  },
  standalone: {
    can_intercept_writes: false,
    can_intercept_commands: false,
    can_isolate_agents: false,
    can_enforce_exit_codes: false,
    has_hooks_api: false,
  },
};
