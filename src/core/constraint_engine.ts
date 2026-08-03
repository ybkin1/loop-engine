/**
 * constraint_engine.ts — Unified Constraint Engine for Loop Engineering
 *
 * Consolidates three enforcement modules (enforcement.ts, hard_constraints.ts,
 * enforcement_hub.ts) into a single facade. This reduces cognitive load and
 * provides a cleaner API for consumers.
 *
 * Architecture:
 * - HardConstraints: Deterministic C1-C11 checking (pure functions)
 * - EnforcementLevel: Host capability derivation and validation
 * - EnforcementHub: Hook-core bridge for governance state
 *
 * This module re-exports the essential types and provides a unified
 * ConstraintEngine class that combines all three capabilities.
 */

import {
  HardConstraints,
  type ConstraintContext,
  type ConstraintCheckResult,
  type ConstraintViolation,
  ConstraintID,
  Severity,
  type EvidenceEnvelope,
  createEvidenceEnvelope,
} from "./hard_constraints.js";

import {
  EnforcementLevel,
  type HostCapabilities,
  type HardConstraint,
  type EnforcementResult,
  HOST_PRESETS,
  deriveEnforcementLevel,
  validateHostCapabilities,
  HARD_CONSTRAINTS,
} from "./enforcement.js";

import {
  EnforcementHub,
  type EnforcementDecision,
  type GovernanceStatus,
  quickCheck,
} from "./enforcement_hub.js";

// ── Re-exports ───────────────────────────────────────────────────────────────

export {
  // Hard constraints
  HardConstraints,
  ConstraintID,
  Severity,
  createEvidenceEnvelope,
  // Enforcement levels
  EnforcementLevel,
  HOST_PRESETS,
  deriveEnforcementLevel,
  validateHostCapabilities,
  HARD_CONSTRAINTS,
  // Enforcement hub
  EnforcementHub,
  quickCheck,
};

export type {
  ConstraintContext,
  ConstraintCheckResult,
  ConstraintViolation,
  EvidenceEnvelope,
  HostCapabilities,
  HardConstraint,
  EnforcementResult,
  EnforcementDecision,
  GovernanceStatus,
};

// ── ConstraintEngine ─────────────────────────────────────────────────────────

/**
 * Unified constraint engine combining hard constraints, enforcement level
 * derivation, and governance state checking.
 *
 * This facade provides a single entry point for all constraint-related
 * operations, reducing the need to import from multiple modules.
 *
 * @example
 * ```ts
 * const engine = new ConstraintEngine("/path/to/project");
 *
 * // Check all constraints
 * const result = await engine.checkAllConstraints(context);
 *
 * // Derive enforcement level from host capabilities
 * const level = engine.deriveEnforcementLevel(caps);
 *
 * // Quick governance check for hooks
 * const decision = await engine.quickCheck();
 * ```
 */
export class ConstraintEngine {
  private readonly hardConstraints: HardConstraints;
  private readonly enforcementHub: EnforcementHub;
  private readonly projectRoot: string;

  constructor(projectRoot: string) {
    this.projectRoot = projectRoot;
    this.hardConstraints = new HardConstraints();
    this.enforcementHub = new EnforcementHub(projectRoot);
  }

  // ── Hard Constraints ─────────────────────────────────────────────────

  /**
   * Run all 11 constraints (C1-C11) against the given context.
   */
  checkAllConstraints(context: ConstraintContext): ConstraintCheckResult {
    return this.hardConstraints.checkAll(context);
  }

  /**
   * Check individual constraints.
   */
  checkC1(context: ConstraintContext): ConstraintViolation[] {
    return this.hardConstraints.checkC1(context);
  }

  checkC2(context: ConstraintContext): ConstraintViolation[] {
    return this.hardConstraints.checkC2(context);
  }

  checkC3(context: ConstraintContext): ConstraintViolation[] {
    return this.hardConstraints.checkC3(context);
  }

  checkC4(context: ConstraintContext): ConstraintViolation[] {
    return this.hardConstraints.checkC4(context);
  }

  checkC5(context: ConstraintContext): ConstraintViolation[] {
    return this.hardConstraints.checkC5(context);
  }

  checkC6(context: ConstraintContext): ConstraintViolation[] {
    return this.hardConstraints.checkC6(context);
  }

  checkC7(context: ConstraintContext): ConstraintViolation[] {
    return this.hardConstraints.checkC7(context);
  }

  checkC8(context: ConstraintContext): ConstraintViolation[] {
    return this.hardConstraints.checkC8(context);
  }

  checkC9(context: ConstraintContext): ConstraintViolation[] {
    return this.hardConstraints.checkC9(context);
  }

  checkC10(context: ConstraintContext): ConstraintViolation[] {
    return this.hardConstraints.checkC10(context);
  }

  checkC11(context: ConstraintContext): ConstraintViolation[] {
    return this.hardConstraints.checkC11(context);
  }

  // ── Enforcement Level ────────────────────────────────────────────────

  /**
   * Derive enforcement level from host capabilities.
   */
  deriveEnforcementLevel(caps: HostCapabilities): EnforcementLevel {
    return deriveEnforcementLevel(caps);
  }

  /**
   * Validate host capabilities against claimed enforcement level.
   */
  validateHostCapabilities(
    caps: HostCapabilities,
    claimedLevel: EnforcementLevel,
  ): EnforcementResult {
    return validateHostCapabilities(caps, claimedLevel);
  }

  /**
   * Get a host preset by name.
   */
  getHostPreset(name: string): HostCapabilities | undefined {
    return HOST_PRESETS[name];
  }

  // ── Governance State ─────────────────────────────────────────────────

  /**
   * Quick governance check — returns a summary decision for hook scripts.
   */
  async quickCheck(): Promise<EnforcementDecision> {
    return quickCheck(this.projectRoot);
  }

  /**
   * Check if a file write should be allowed.
   */
  async shouldAllowWrite(
    targetPath: string,
    allowedPaths?: string[],
  ): Promise<EnforcementDecision> {
    return this.enforcementHub.shouldAllowWrite(targetPath, allowedPaths);
  }

  /**
   * Check if phase advance should be allowed.
   */
  async shouldAllowPhaseAdvance(targetPhase: string): Promise<EnforcementDecision> {
    return this.enforcementHub.shouldAllowPhaseAdvance(targetPhase);
  }

  /**
   * Check role isolation (developer vs reviewer independence).
   */
  checkRoleIsolation(
    developerId: string,
    reviewerId: string,
  ): EnforcementDecision {
    return this.enforcementHub.checkRoleIsolation(developerId, reviewerId);
  }

  /**
   * Check evidence freshness across all bound evidence.
   */
  async checkEvidenceFreshness(): Promise<EnforcementDecision> {
    return this.enforcementHub.checkEvidenceFreshness();
  }

  /**
   * Get full governance status summary.
   */
  async getGovernanceStatus(): Promise<GovernanceStatus> {
    return this.enforcementHub.getGovernanceStatus();
  }

  /**
   * Compute integrity hash of governance files.
   */
  computeGovernanceFileHash(): { hash: string; files: Record<string, string> } {
    return this.enforcementHub.computeGovernanceFileHash();
  }

  /**
   * Check governance file integrity against stored hash.
   */
  async checkGovernanceFileIntegrity(): Promise<EnforcementDecision> {
    return this.enforcementHub.checkGovernanceFileIntegrity();
  }

  // ── Utility ──────────────────────────────────────────────────────────

  /**
   * Get the underlying HardConstraints instance for advanced usage.
   */
  getHardConstraints(): HardConstraints {
    return this.hardConstraints;
  }

  /**
   * Get the underlying EnforcementHub instance for advanced usage.
   */
  getEnforcementHub(): EnforcementHub {
    return this.enforcementHub;
  }
}
