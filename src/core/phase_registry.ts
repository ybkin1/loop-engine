/**
 * phase_registry.ts — Single source of truth for phase definitions.
 *
 * All modules that reference phases (executor.ts, hard_constraints.ts,
 * state-machine.ts, auto-orchestrate.js) should import from here.
 *
 * This eliminates the disjoint PHASE_ROLES (6 phases) vs PHASE_ROLE_MAP (12 phases)
 * problem — both now consume the same canonical definition.
 */

/** All 12 canonical phases. Order is significant (defines advancement path). */
export const NORM_PHASES = [
  "S0-init",
  "S1-requirements",
  "S2-architecture",
  "S3-interface",
  "S4-implementation",
  "S5-quality",
  "S6-delivery",
  "S7-integration",
  "S8-functional-test",
  "S9-fix-optimize",
  "S10-performance",
  "S11-maintenance",
] as const;

export type NormPhase = typeof NORM_PHASES[number];

/** Role assignments per phase: { lead, participants }. */
export const PHASE_ROLE_MAP: Record<string, { lead: string; participants: string[]; name: string }> = {
  "S0-init":            { lead: "R11", participants: [], name: "Init" },
  "S1-requirements":    { lead: "R01", participants: ["R02"], name: "Requirements" },
  "S2-architecture":    { lead: "R04", participants: ["R01", "R08"], name: "Architecture" },
  "S3-interface":       { lead: "R05", participants: ["R04"], name: "Interface Design" },
  "S4-implementation":  { lead: "R06", participants: ["R05"], name: "Implementation" },
  "S5-quality":         { lead: "R07", participants: ["R06", "R08"], name: "Quality" },
  "S6-delivery":        { lead: "R03", participants: ["R10", "R08"], name: "Delivery" },
  "S7-integration":     { lead: "R06", participants: ["R05", "R07"], name: "Integration" },
  "S8-functional-test": { lead: "R07", participants: ["R01"], name: "Functional Test" },
  "S9-fix-optimize":    { lead: "R06", participants: ["R09", "R07"], name: "Fix & Optimize" },
  "S10-performance":    { lead: "R07", participants: ["R10", "R04"], name: "Performance" },
  "S11-maintenance":    { lead: "R10", participants: ["R08", "R06"], name: "Maintenance" },
  // Short S-prefix aliases (for normPhase lookup)
  "S1": { lead: "R01", participants: ["R02"], name: "Requirements" },
  "S2": { lead: "R04", participants: ["R01", "R08"], name: "Architecture" },
  "S3": { lead: "R05", participants: ["R04"], name: "Interface Design" },
  "S4": { lead: "R06", participants: ["R05"], name: "Implementation" },
  "S5": { lead: "R07", participants: ["R06", "R08"], name: "Quality" },
  "S6": { lead: "R03", participants: ["R10", "R08"], name: "Delivery" },
  "S7": { lead: "R06", participants: ["R05", "R07"], name: "Integration" },
  "S8": { lead: "R07", participants: ["R01"], name: "Functional Test" },
  "S9": { lead: "R06", participants: ["R09", "R07"], name: "Fix & Optimize" },
  "S10": { lead: "R07", participants: ["R10", "R04"], name: "Performance" },
  "S11": { lead: "R10", participants: ["R08", "R06"], name: "Maintenance" },
};

/** Roles per phase (flat array, consumed by PhaseExecutor). Derived from PHASE_ROLE_MAP. */
export function rolesForPhase(phaseId: string): string[] {
  const canonical = normPhase(phaseId);
  // Try full name first, then short canonical form
  const mapping = PHASE_ROLE_MAP[phaseId] ?? PHASE_ROLE_MAP[canonical];
  if (!mapping) return [];
  return [mapping.lead, ...mapping.participants];
}

/** Gate ID per phase. */
export const PHASE_GATE: Record<string, string> = {};
for (const p of NORM_PHASES) {
  PHASE_GATE[p] = `gate-${p}`;
}
// Legacy aliases (backward compat)
PHASE_GATE["requirements"]   = "gate-requirements";
PHASE_GATE["architecture"]   = "gate-architecture";
PHASE_GATE["planning"]       = "gate-planning";
PHASE_GATE["implementation"] = "gate-implementation";
PHASE_GATE["review"]         = "gate-review";
PHASE_GATE["delivery"]       = "gate-delivery";

/**
 * Normalize any phase name to its canonical S-prefix short form (S1–S12).
 * Supports: legacy (requirements), S-prefix (S4-implementation), P-prefix (P4-implementation), short (S4).
 */
const PHASE_TO_S: Record<string, string> = {
  // Legacy
  "requirements": "S1", "architecture": "S2", "planning": "S3",
  "implementation": "S4", "review": "S5", "delivery": "S6",
  // Full S-prefix → short
  "S1-requirements": "S1", "S2-architecture": "S2",
  "S3-interface": "S3", "S4-implementation": "S4",
  "S5-quality": "S5", "S6-delivery": "S6",
  "S7-integration": "S7", "S8-functional-test": "S8",
  "S9-fix-optimize": "S9", "S10-performance": "S10",
  "S11-maintenance": "S11",
  // P-prefix
  "P1-requirements": "S1", "P2-architecture": "S2",
  "P3-planning": "S3", "P4-implementation": "S4",
  "P5-review": "S5", "P6-delivery": "S6",
  // Short S-prefix → identity
  "S1": "S1", "S2": "S2", "S3": "S3", "S4": "S4", "S5": "S5", "S6": "S6",
  "S7": "S7", "S8": "S8", "S9": "S9", "S10": "S10", "S11": "S11", "S12": "S12",
};

export function normPhase(phase: string): string {
  return PHASE_TO_S[phase] ?? phase;
}
