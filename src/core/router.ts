/**
 * router.ts — Intent recognition & project classification routing
 *
 * Determines whether a project should enter LIGHTWEIGHT, STANDARD, or FULL Loop
 * based on 13 risk factors. When uncertain, upgrades to FULL rather than
 * silently downgrading.
 *
 * Aligned with ZCode loop_core/router.py design.
 */

// ── Loop Modes ───────────────────────────────────────
export enum LoopMode {
  LIGHTWEIGHT = "LIGHTWEIGHT", // Single file, low risk, no persistent data
  STANDARD = "STANDARD",       // Medium complexity, core phases only
  FULL = "FULL",               // Large/complex/high-risk, all 6 phases
}

// ── Risk Levels ──────────────────────────────────────
export enum RiskLevel {
  LOW = "LOW",
  MEDIUM = "MEDIUM",
  HIGH = "HIGH",
  CRITICAL = "CRITICAL",
}

// ── Project Profile (13 risk factors) ────────────────
export interface ProjectProfile {
  // High risk factors (5)
  has_database: boolean;
  has_auth_permissions: boolean;
  has_payments: boolean;
  has_production_data: boolean;
  has_security_requirements: boolean;

  // Medium risk factors (8)
  has_multiple_modules: boolean;
  has_external_api: boolean;
  has_concurrency_performance: boolean;
  requires_deployment: boolean;
  requires_monitoring_rollback: boolean;
  requires_ongoing_iteration: boolean;
  has_high_uncertainty: boolean;
  has_complex_business_logic: boolean;

  // User override
  user_forced_mode: LoopMode | null;
}

// ── Route Result ─────────────────────────────────────
export interface RouteResult {
  mode: LoopMode;
  risk_level: RiskLevel;
  reason: string;
  /** Which phases to execute */
  phases: string[];
  high_risk_factors: string[];
  medium_risk_factors: string[];
}

// ── Phase Definitions per Mode ───────────────────────
const PHASES_LIGHTWEIGHT = ["requirements", "implementation", "delivery"];
const PHASES_STANDARD = ["requirements", "architecture", "planning", "implementation", "review", "delivery"];
const PHASES_FULL = ["requirements", "architecture", "planning", "implementation", "review", "delivery"];

// ── High Risk Factor Names ───────────────────────────
const HIGH_RISK_KEYS: (keyof ProjectProfile)[] = [
  "has_database",
  "has_auth_permissions",
  "has_payments",
  "has_production_data",
  "has_security_requirements",
];

const MEDIUM_RISK_KEYS: (keyof ProjectProfile)[] = [
  "has_multiple_modules",
  "has_external_api",
  "has_concurrency_performance",
  "requires_deployment",
  "requires_monitoring_rollback",
  "requires_ongoing_iteration",
  "has_high_uncertainty",
  "has_complex_business_logic",
];

// ── Risk Level Calculation ───────────────────────────
function calculateRiskLevel(profile: ProjectProfile): { level: RiskLevel; high: string[]; medium: string[] } {
  const highFactors = HIGH_RISK_KEYS.filter(k => profile[k] === true).map(k => k as string);
  const mediumFactors = MEDIUM_RISK_KEYS.filter(k => profile[k] === true).map(k => k as string);

  const highCount = highFactors.length;
  const mediumCount = mediumFactors.length;

  let level: RiskLevel;
  if (highCount >= 2) {
    level = RiskLevel.CRITICAL;
  } else if (highCount >= 1 || mediumCount >= 3) {
    level = RiskLevel.HIGH;
  } else if (mediumCount >= 1) {
    level = RiskLevel.MEDIUM;
  } else {
    level = RiskLevel.LOW;
  }

  return { level, high: highFactors, medium: mediumFactors };
}

// ── Mode from Risk Level ─────────────────────────────
function modeFromRisk(level: RiskLevel): { mode: LoopMode; phases: string[] } {
  switch (level) {
    case RiskLevel.CRITICAL:
    case RiskLevel.HIGH:
      return { mode: LoopMode.FULL, phases: PHASES_FULL };
    case RiskLevel.MEDIUM:
      return { mode: LoopMode.STANDARD, phases: PHASES_STANDARD };
    case RiskLevel.LOW:
      return { mode: LoopMode.LIGHTWEIGHT, phases: PHASES_LIGHTWEIGHT };
  }
}

// ── Main Entry: Route Intent ─────────────────────────
export function routeIntent(profile: ProjectProfile): RouteResult {
  // User override takes precedence
  if (profile.user_forced_mode) {
    const { level, high, medium } = calculateRiskLevel(profile);
    const phases = profile.user_forced_mode === LoopMode.FULL ? PHASES_FULL
      : profile.user_forced_mode === LoopMode.STANDARD ? PHASES_STANDARD
      : PHASES_LIGHTWEIGHT;

    return {
      mode: profile.user_forced_mode,
      risk_level: level,
      reason: `User forced mode: ${profile.user_forced_mode}`,
      phases,
      high_risk_factors: high,
      medium_risk_factors: medium,
    };
  }

  const { level, high, medium } = calculateRiskLevel(profile);
  const { mode, phases } = modeFromRisk(level);

  // Build reason string
  const reasons: string[] = [];
  if (high.length > 0) reasons.push(`high-risk: ${high.join(", ")}`);
  if (medium.length > 0) reasons.push(`medium-risk: ${medium.join(", ")}`);
  if (reasons.length === 0) reasons.push("no risk factors detected");

  return {
    mode,
    risk_level: level,
    reason: reasons.join("; "),
    phases,
    high_risk_factors: high,
    medium_risk_factors: medium,
  };
}

/**
 * Create a default (all-false) profile for initialization.
 */
export function defaultProfile(): ProjectProfile {
  return {
    has_database: false,
    has_auth_permissions: false,
    has_payments: false,
    has_production_data: false,
    has_security_requirements: false,
    has_multiple_modules: false,
    has_external_api: false,
    has_concurrency_performance: false,
    requires_deployment: false,
    requires_monitoring_rollback: false,
    requires_ongoing_iteration: false,
    has_high_uncertainty: false,
    has_complex_business_logic: false,
    user_forced_mode: null,
  };
}
