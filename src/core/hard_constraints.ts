/**
 * hard_constraints.ts — Deterministic gate constraints for Loop Engineering
 *
 * Implements 8 hard constraints (C1–C8) that must be satisfied before
 * phase transitions. These are enforced by deterministic code, never by
 * model compliance alone.
 *
 * Ported from ZCode loop_core/hard_constraints.py.
 */

import { normPhase } from "./phase_registry.js";

// ── Constraint IDs ────────────────────────────────────────────────────────────

/** Identifiers for the 8 hard constraints. */
export enum ConstraintID {
  /** Requirements baseline approved before entering S2/S3/S4 */
  C1 = "C1",
  /** Architecture baseline approved before entering S3/S4 */
  C2 = "C2",
  /** Active task package required for write operations */
  C3 = "C3",
  /** Target path must fall within allowed paths */
  C4 = "C4",
  /** Quality verification (test/lint/build) must PASS before S6 delivery */
  C5 = "C5",
  /** Independent review required before leaving S4 implementation */
  C6 = "C6",
  /** No BLOCKED gates or tasks may exist when advancing */
  C7 = "C7",
  /** All bound evidence must be fresh and hash-stable */
  C8 = "C8",
}

// ── Severity ──────────────────────────────────────────────────────────────────

/** Severity level for a constraint violation. */
export enum Severity {
  /** Hard block — phase transition is forbidden until resolved. */
  BLOCKER = "BLOCKER",
  /** Warning — operation may proceed but risk is acknowledged. */
  WARNING = "WARNING",
}

// ── Violation ─────────────────────────────────────────────────────────────────

/** A single constraint violation record. */
export interface ConstraintViolation {
  /** Which constraint was violated. */
  constraint_id: ConstraintID;
  /** Severity of the violation. */
  severity: Severity;
  /** Human-readable description of the violation. */
  message: string;
  /** Actionable remediation advice for the operator or role. */
  remediation: string;
}

// ── Check Result ──────────────────────────────────────────────────────────────

/** Aggregate result of running all constraint checks. */
export interface ConstraintCheckResult {
  /** `true` when no BLOCKER-severity violations were found. */
  passed: boolean;
  /** All violations discovered (may include WARNINGs even when passed). */
  violations: ConstraintViolation[];
}

// ── Evidence Envelope ─────────────────────────────────────────────────────────

/**
 * An evidence envelope binds a piece of evidence to a specific content hash
 * and an expiration date, allowing freshness and tamper checks.
 */
export interface EvidenceEnvelope {
  /** Unique evidence identifier. */
  evidence_id: string;
  /** SHA-256 hex digest of the evidence content at submission time. */
  content_hash: string;
  /** Phase in which the evidence was produced (e.g. "S1", "S2"). */
  phase: string;
  /** ISO-8601 date-time at which the evidence expires. */
  expires_at: string;
  /** ISO-8601 date-time at which the evidence was created. */
  created_at: string;
  /**
   * Returns `true` when the current time is before `expires_at`.
   */
  is_fresh(): boolean;
  /**
   * Returns `true` when `current_hash` differs from the stored `content_hash`,
   * indicating the underlying content has been modified.
   */
  has_hash_changed(current_hash: string): boolean;
}

/**
 * Create a plain-object EvidenceEnvelope with bound methods.
 *
 * @param evidence_id - Unique evidence identifier
 * @param content_hash - SHA-256 hex digest at submission time
 * @param phase - Phase in which the evidence was produced
 * @param expires_at - ISO-8601 expiration date-time
 * @param created_at - ISO-8601 creation date-time
 */
export function createEvidenceEnvelope(
  evidence_id: string,
  content_hash: string,
  phase: string,
  expires_at: string,
  created_at: string,
): EvidenceEnvelope {
  return {
    evidence_id,
    content_hash,
    phase,
    expires_at,
    created_at,
    is_fresh(): boolean {
      return Date.now() < new Date(this.expires_at).getTime();
    },
    has_hash_changed(current_hash: string): boolean {
      return this.content_hash !== current_hash;
    },
  };
}

// ── Constraint Context ────────────────────────────────────────────────────────

/**
 * The context object supplied to {@link HardConstraints.checkAll}.
 *
 * Each constraint reads only the fields it needs; unused fields may be
 * omitted.
 */
export interface ConstraintContext {
  /** The phase the role is currently executing in (e.g. "S1", "S4"). */
  current_phase?: string;
  /** The phase the role is attempting to enter. */
  target_phase?: string;
  /**
   * Map of gate identifiers to their approval status.
   * Example: `{ "S1-requirements": "APPROVED" }`
   */
  phase_gates?: Record<string, string>;
  /** Task list visible to the current role. */
  tasks?: Array<{ id: string; status: string; allowed_paths?: string[] }>;
  /** File path the role intends to write to. */
  target_path?: string;
  /** Paths the current role is permitted to write to (prefix-matched). */
  allowed_paths?: string[];
  /**
   * Deterministic quality check results.
   * Keys: "test" | "lint" | "build"; Values: "PASS" | "FAIL"
   */
  quality_results?: Record<string, string>;
  /**
   * Review verdicts keyed by reviewer role.
   * Example: `{ "independent-reviewer": "PASS" }`
   */
  review_status?: Record<string, string>;
  /** Gate records (alternative to `phase_gates` for C7 blocker scan). */
  gates?: Array<{ id: string; status: string }>;
  /** Evidence envelopes bound to the current operation. */
  evidence_list?: EvidenceEnvelope[];
  /**
   * Current content hashes keyed by evidence_id, used by C8 to detect
   * tampering.
   */
  current_hashes?: Record<string, string>;
}

// ── Helper ────────────────────────────────────────────────────────────────────

/** Phases that require the S1 requirements baseline to be approved. */
const PHASES_REQUIRING_S1 = new Set(["S2", "S3", "S4"]);

/** Phases that require the S2 architecture baseline to be approved. */
const PHASES_REQUIRING_S2 = new Set(["S3", "S4"]);

/** Quality check types that must all PASS before S6 delivery. */
const REQUIRED_QUALITY_CHECKS = ["test", "lint", "build"] as const;

// ── HardConstraints ───────────────────────────────────────────────────────────

/**
 * Deterministic constraint checker.
 *
 * All methods are pure: they read from the supplied {@link ConstraintContext}
 * and return violation arrays without side effects.
 */
export class HardConstraints {
  /**
   * Run all 8 constraints against the given context.
   *
   * @param context - The constraint context describing the current state
   * @returns Aggregate result with `passed = true` when no BLOCKER violations
   */
  checkAll(context: ConstraintContext): ConstraintCheckResult {
    const violations: ConstraintViolation[] = [
      ...this.checkC1(context),
      ...this.checkC2(context),
      ...this.checkC3(context),
      ...this.checkC4(context),
      ...this.checkC5(context),
      ...this.checkC6(context),
      ...this.checkC7(context),
      ...this.checkC8(context),
    ];
    const passed = !violations.some(v => v.severity === Severity.BLOCKER);
    return { passed, violations };
  }

  /**
   * C1 — Requirements Baseline.
   *
   * When `target_phase` is S2, S3, or S4 the gate `"S1-requirements"` must
   * have status `"APPROVED"` in `phase_gates`.
   */
  checkC1(context: ConstraintContext): ConstraintViolation[] {
    const { target_phase, phase_gates } = context;
    const phase = normPhase(target_phase ?? "");
    if (!phase || !PHASES_REQUIRING_S1.has(phase)) return [];
    if (!phase_gates) {
      return [{
        constraint_id: ConstraintID.C1,
        severity: Severity.BLOCKER,
        message: `Cannot enter ${target_phase}: phase_gates context is missing.`,
        remediation: "Provide phase_gates with gate statuses. Ensure S1-requirements has been completed and approved before advancing.",
      }];
    }
    const gateStatus = phase_gates["S1-requirements"];
    if (gateStatus !== "APPROVED") {
      return [{
        constraint_id: ConstraintID.C1,
        severity: Severity.BLOCKER,
        message: `Cannot enter ${target_phase}: S1-requirements gate is "${gateStatus ?? "NOT_FOUND"}", expected "APPROVED".`,
        remediation: "Complete the requirements elicitation phase (S1). Obtain explicit approval for the requirements baseline before proceeding to design or implementation.",
      }];
    }
    return [];
  }

  /**
   * C2 — Architecture Baseline.
   *
   * When `target_phase` is S3 or S4 the gate `"S2-architecture"` must have
   * status `"APPROVED"` in `phase_gates`.
   */
  checkC2(context: ConstraintContext): ConstraintViolation[] {
    const { target_phase, phase_gates } = context;
    const phase = normPhase(target_phase ?? "");
    if (!phase || !PHASES_REQUIRING_S2.has(phase)) return [];
    if (!phase_gates) {
      return [{
        constraint_id: ConstraintID.C2,
        severity: Severity.BLOCKER,
        message: `Cannot enter ${target_phase}: phase_gates context is missing.`,
        remediation: "Provide phase_gates with gate statuses. Ensure S2-architecture has been completed and approved before proceeding.",
      }];
    }
    const gateStatus = phase_gates["S2-architecture"];
    if (gateStatus !== "APPROVED") {
      return [{
        constraint_id: ConstraintID.C2,
        severity: Severity.BLOCKER,
        message: `Cannot enter ${target_phase}: S2-architecture gate is "${gateStatus ?? "NOT_FOUND"}", expected "APPROVED".`,
        remediation: "Complete the architecture design phase (S2). Obtain explicit approval for the architecture baseline before proceeding to implementation.",
      }];
    }
    return [];
  }

  /**
   * C3 — Task Package.
   *
   * There must be at least one task with status `"active"` or
   * `"in_progress"` in the `tasks` list.
   */
  checkC3(context: ConstraintContext): ConstraintViolation[] {
    const { tasks } = context;
    if (!tasks || tasks.length === 0) {
      return [{
        constraint_id: ConstraintID.C3,
        severity: Severity.BLOCKER,
        message: "No task package: tasks list is empty or missing.",
        remediation: "Create and assign at least one task before performing write operations. Use loop_task_create to define the work scope.",
      }];
    }
    const hasActive = tasks.some(t => t.status === "active" || t.status === "in_progress");
    if (!hasActive) {
      return [{
        constraint_id: ConstraintID.C3,
        severity: Severity.BLOCKER,
        message: "No active task found: all tasks are completed, pending, or blocked.",
        remediation: "Activate or create a task with status 'active' or 'in_progress' before proceeding with write operations.",
      }];
    }
    return [];
  }

  /**
   * C4 — Path Scope.
   *
   * When `target_path` is set, it must be prefixed by at least one entry in
   * `allowed_paths`.
   */
  checkC4(context: ConstraintContext): ConstraintViolation[] {
    const { target_path, allowed_paths, tasks } = context;
    if (!target_path) return [];

    // Reject path traversal attempts
    if (target_path.includes("..")) {
      return [{
        constraint_id: ConstraintID.C4,
        severity: Severity.BLOCKER,
        message: `Path traversal detected in target_path "${target_path}": ".." is not permitted.`,
        remediation: "Use absolute paths or paths relative to the project root only.",
      }];
    }

    // Collect allowed paths from both explicit allowed_paths and task definitions
    const allAllowed: string[] = [...(allowed_paths ?? [])];
    if (tasks) {
      for (const task of tasks) {
        if ((task.status === "active" || task.status === "in_progress") && task.allowed_paths) {
          allAllowed.push(...task.allowed_paths);
        }
      }
    }

    if (allAllowed.length === 0) {
      return [{
        constraint_id: ConstraintID.C4,
        severity: Severity.BLOCKER,
        message: `No allowed_paths defined: cannot verify target_path "${target_path}".`,
        remediation: "Define allowed_paths in the task package or role configuration to scope write operations.",
      }];
    }

    const inScope = allAllowed.some(prefix => {
      // Normalize both paths to forward slashes for cross-platform comparison
      const normTarget = target_path.replace(/\\/g, "/");
      const normPrefix = prefix.replace(/\\/g, "/");
      // Ensure proper path boundary: prefix must end with '/' or target must continue with '/'
      return normTarget === normPrefix ||
        normTarget.startsWith(normPrefix.endsWith("/") ? normPrefix : normPrefix + "/");
    });
    if (!inScope) {
      return [{
        constraint_id: ConstraintID.C4,
        severity: Severity.BLOCKER,
        message: `Target path "${target_path}" is outside allowed paths: [${allAllowed.join(", ")}].`,
        remediation: `Restrict writes to paths within the allowed scope. Current allowed prefixes: ${allAllowed.join(", ")}. Update the task package if a new path is legitimately required.`,
      }];
    }
    return [];
  }

  /**
   * C5 — Verification Pass.
   *
   * When `target_phase` is S6 (delivery), all of `test`, `lint`, and `build`
   * in `quality_results` must be `"PASS"`.
   */
  checkC5(context: ConstraintContext): ConstraintViolation[] {
    const { target_phase, quality_results } = context;
    const phase = normPhase(target_phase ?? "");
    if (phase !== "S6") return [];

    if (!quality_results) {
      return [{
        constraint_id: ConstraintID.C5,
        severity: Severity.BLOCKER,
        message: "Cannot deliver (S6): quality_results context is missing.",
        remediation: "Run all quality gates (test, lint, build) and provide results before attempting delivery.",
      }];
    }

    const violations: ConstraintViolation[] = [];
    for (const check of REQUIRED_QUALITY_CHECKS) {
      const result = quality_results[check];
      if (result !== "PASS") {
        violations.push({
          constraint_id: ConstraintID.C5,
          severity: Severity.BLOCKER,
          message: `Quality check "${check}" is "${result ?? "NOT_RUN"}", expected "PASS".`,
          remediation: `Run the ${check} quality gate and ensure it passes. Fix any ${check} failures before attempting delivery.`,
        });
      }
    }
    return violations;
  }

  /**
   * C6 — Independent Review.
   *
   * When `current_phase` is S4 (implementation), the reviewer role
   * `"independent-reviewer"` must have verdict `"PASS"` in `review_status`.
   */
  checkC6(context: ConstraintContext): ConstraintViolation[] {
    const { current_phase, review_status } = context;
    const phase = normPhase(current_phase ?? "");
    if (phase !== "S4") return [];

    if (!review_status) {
      return [{
        constraint_id: ConstraintID.C6,
        severity: Severity.BLOCKER,
        message: "Cannot pass S4 implementation: review_status context is missing.",
        remediation: "Request an independent code review from the independent-reviewer role before advancing past implementation.",
      }];
    }

    const reviewerVerdict = review_status["independent-reviewer"];
    if (reviewerVerdict !== "PASS") {
      return [{
        constraint_id: ConstraintID.C6,
        severity: Severity.BLOCKER,
        message: `Cannot pass S4 implementation: independent-reviewer verdict is "${reviewerVerdict ?? "NOT_REVIEWED"}", expected "PASS".`,
        remediation: "Obtain a PASS verdict from the independent-reviewer role. Address any review comments and re-submit for review.",
      }];
    }
    return [];
  }

  /**
   * C7 — No Blockers.
   *
   * Neither `gates` nor `tasks` may contain any entry with status
   * `"BLOCKED"`.
   */
  checkC7(context: ConstraintContext): ConstraintViolation[] {
    const violations: ConstraintViolation[] = [];

    // Check gates
    if (context.gates) {
      for (const gate of context.gates) {
        if (gate.status === "BLOCKED") {
          violations.push({
            constraint_id: ConstraintID.C7,
            severity: Severity.BLOCKER,
            message: `Gate "${gate.id}" has BLOCKED status.`,
            remediation: `Resolve the blocker on gate "${gate.id}" before advancing. Investigate the root cause and update the gate status to PASS or APPROVED.`,
          });
        }
      }
    }

    // Check tasks
    if (context.tasks) {
      for (const task of context.tasks) {
        if (task.status === "BLOCKED") {
          violations.push({
            constraint_id: ConstraintID.C7,
            severity: Severity.BLOCKER,
            message: `Task "${task.id}" has BLOCKED status.`,
            remediation: `Resolve the blocker on task "${task.id}" before advancing. Remove the dependency or condition causing the block.`,
          });
        }
      }
    }

    return violations;
  }

  /**
   * C8 — Evidence Freshness.
   *
   * Every envelope in `evidence_list` must:
   * - Be fresh (`is_fresh()` returns `true`)
   * - Have a stable hash (no tampering detected via `has_hash_changed`)
   */
  checkC8(context: ConstraintContext): ConstraintViolation[] {
    const { evidence_list, current_hashes } = context;
    if (!evidence_list || evidence_list.length === 0) return [];

    const violations: ConstraintViolation[] = [];
    for (const envelope of evidence_list) {
      // Freshness check
      if (!envelope.is_fresh()) {
        violations.push({
          constraint_id: ConstraintID.C8,
          severity: Severity.BLOCKER,
          message: `Evidence "${envelope.evidence_id}" has expired (expires_at: ${envelope.expires_at}).`,
          remediation: `Re-submit evidence "${envelope.evidence_id}" with a new expiration date. The evidence produced in phase ${envelope.phase} is no longer considered valid.`,
        });
      }

      // Hash stability check
      if (current_hashes) {
        const currentHash = current_hashes[envelope.evidence_id];
        if (currentHash !== undefined && envelope.has_hash_changed(currentHash)) {
          violations.push({
            constraint_id: ConstraintID.C8,
            severity: Severity.BLOCKER,
            message: `Evidence "${envelope.evidence_id}" content hash has changed (stored: ${envelope.content_hash}, current: ${currentHash}).`,
            remediation: `Evidence "${envelope.evidence_id}" may have been tampered with or regenerated. Re-submit the evidence to update the bound hash, or restore the original content.`,
          });
        }
      }
    }
    return violations;
  }
}
