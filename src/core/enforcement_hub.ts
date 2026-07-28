/**
 * enforcement_hub.ts — Hook-Core Bridge for Loop Engineering
 *
 * Bridge between the hook system and Loop Core governance state.
 * Eliminates reliance on "model self-discipline" — hooks call these
 * methods to make execution decisions based on actual governance state.
 *
 * Ported from ZCode loop_core/enforcement_hub.py.
 */

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { join, relative, normalize } from "node:path";
import { createHash } from "node:crypto";
import { parseDocument } from "yaml";
import { loadState, loadGates } from "./state-machine.js";
import {
  HardConstraints,
  type ConstraintContext,
  ConstraintID,
  Severity,
  type ConstraintViolation,
  type EvidenceEnvelope,
  createEvidenceEnvelope,
} from "./hard_constraints.js";
import {
  EnforcementLevel,
  HOST_PRESETS,
  deriveEnforcementLevel,
} from "./enforcement.js";
import type { ProjectState, GatesRegistry } from "../types/index.js";

// ── EnforcementDecision ──────────────────────────────────────────────────────

/** Result of an enforcement check, consumable by hook scripts. */
export interface EnforcementDecision {
  allowed: boolean;
  reason: string;
  violations: string[];
  blocker_count: number;
  /** Convert to hook stderr output. */
  toHookOutput(): string;
}

function makeDecision(
  allowed: boolean,
  reason: string,
  violations: string[],
  blocker_count: number,
): EnforcementDecision {
  return {
    allowed,
    reason,
    violations,
    blocker_count,
    toHookOutput(): string {
      const lines: string[] = [];
      if (allowed) {
        lines.push(`[ENFORCEMENT] ALLOW — ${reason}`);
      } else {
        lines.push(`[ENFORCEMENT] DENY — ${reason}`);
        if (violations.length > 0) {
          lines.push("Violations:");
          for (const v of violations) {
            lines.push(`  • ${v}`);
          }
        }
        if (blocker_count > 0) {
          lines.push(`Blockers: ${blocker_count}`);
        }
      }
      return lines.join("\n") + "\n";
    },
  };
}

// ── GovernanceStatus ─────────────────────────────────────────────────────────

/** Summary of the current governance state. */
export interface GovernanceStatus {
  project_root: string;
  current_phase: string;
  current_gate: string | null;
  active_role: string | null;
  pending_gates: string[];
  blocked_gates: string[];
  constraint_violations: number;
  overall_status: "HEALTHY" | "DEGRADED" | "BLOCKED";
}

// ── Role domain separation ───────────────────────────────────────────────────

/** Roles that belong to the development domain. */
const DEVELOPMENT_ROLES = new Set(["R05", "R06"]);

/** Roles that belong to the quality / review domain. */
const QUALITY_ROLES = new Set(["R07", "R08", "R09"]);

/** Default evidence TTL: 24 hours in milliseconds. */
const DEFAULT_EVIDENCE_TTL_MS = 86400_000;

// ── Helpers ──────────────────────────────────────────────────────────────────

const hardConstraints = new HardConstraints();

/** Build a ConstraintContext from state + gates + extras. */
function buildContext(
  state: ProjectState,
  gates: GatesRegistry,
  extras: Partial<ConstraintContext> = {},
): ConstraintContext {
  return {
    current_phase: state.current_phase,
    gates: gates.gates.map(g => ({ id: g.gate_id, status: g.status })),
    phase_gates: Object.fromEntries(
      gates.gates.map(g => [g.gate_id, g.status === "passed" ? "APPROVED" : g.status.toUpperCase()]),
    ),
    ...extras,
  };
}

/** Collect BLOCKER violations from a violation list. */
function blockerCount(violations: ConstraintViolation[]): number {
  return violations.filter(v => v.severity === Severity.BLOCKER).length;
}

/** Load evidence envelopes from .ai/evidence/ directory. */
function loadEvidenceEnvelopes(projectRoot: string): EvidenceEnvelope[] {
  const evDir = join(projectRoot, ".ai", "evidence");
  if (!existsSync(evDir)) return [];

  const envelopes: EvidenceEnvelope[] = [];
  const files = readdirSync(evDir).filter(f => f.endsWith(".yaml"));
  for (const file of files) {
    try {
      const raw = readFileSync(join(evDir, file), "utf-8");
      const record = parseDocument(raw).toJSON() as Record<string, string>;
      if (record?.evidence_id && record?.content_hash) {
        envelopes.push(
          createEvidenceEnvelope(
            record.evidence_id,
            record.content_hash,
            record.phase ?? "unknown",
            record.expires_at ?? new Date(Date.now() + DEFAULT_EVIDENCE_TTL_MS).toISOString(),
            record.created_at ?? new Date().toISOString(),
          ),
        );
      }
    } catch {
      /* skip malformed evidence files */
    }
  }
  return envelopes;
}

// ── EnforcementHub ───────────────────────────────────────────────────────────

/**
 * Bridge between the hook system and Loop Core governance state.
 *
 * Each method loads the latest state + gates, runs the relevant constraint
 * checks, and returns an {@link EnforcementDecision} that hook scripts can
 * act on directly.
 */
export class EnforcementHub {
  constructor(private projectRoot: string) {}

  /**
   * Check if a file write should be allowed.
   * Combines C3 (task package) + C4 (path scope) + C7 (no blockers) + phase constraints.
   */
  async shouldAllowWrite(
    targetPath: string,
    allowedPaths?: string[],
  ): Promise<EnforcementDecision> {
    let state: ProjectState;
    let gates: GatesRegistry;
    try {
      [state, gates] = await Promise.all([
        loadState(this.projectRoot),
        loadGates(this.projectRoot),
      ]);
    } catch (err) {
      return makeDecision(
        false,
        `Cannot load governance state for write check: ${err instanceof Error ? err.message : String(err)}`,
        [`State load error: ${err instanceof Error ? err.message : String(err)}`],
        1,
      );
    }

    // Any BLOCKED gate → DENY
    const blockedGates = gates.gates.filter(g => g.status === "blocked");
    if (blockedGates.length > 0) {
      const reasons = blockedGates.map(g => g.blocked_reasons.join(", ")).filter(Boolean);
      return makeDecision(
        false,
        `Write blocked: ${blockedGates.length} gate(s) in BLOCKED status.`,
        reasons.length > 0 ? reasons : ["Gates are blocked — resolve blockers before writing."],
        blockedGates.length,
      );
    }

    // Build context for C3 + C4 + C7
    const normalizedPath = normalize(targetPath);
    const ctx = buildContext(state, gates, {
      target_path: normalizedPath,
      allowed_paths: allowedPaths,
      tasks: state.current_task_id
        ? [{ id: state.current_task_id, status: "active", allowed_paths: allowedPaths }]
        : undefined,
    });

    const c3 = hardConstraints.checkC3(ctx);
    const c4 = hardConstraints.checkC4(ctx);
    const c7 = hardConstraints.checkC7(ctx);
    const all = [...c3, ...c4, ...c7];
    const blockers = blockerCount(all);

    if (blockers > 0) {
      return makeDecision(
        false,
        `Write denied: ${blockers} constraint violation(s) detected.`,
        all.filter(v => v.severity === Severity.BLOCKER).map(v => `[${v.constraint_id}] ${v.message}`),
        blockers,
      );
    }

    return makeDecision(true, "Write allowed — all constraints satisfied.", [], 0);
  }

  /**
   * Check if phase advance should be allowed.
   * Checks all gates, constraints C1-C8, and blocker status.
   */
  async shouldAllowPhaseAdvance(
    targetPhase: string,
  ): Promise<EnforcementDecision> {
    let state: ProjectState;
    let gates: GatesRegistry;
    try {
      [state, gates] = await Promise.all([
        loadState(this.projectRoot),
        loadGates(this.projectRoot),
      ]);
    } catch (err) {
      return makeDecision(
        false,
        `Cannot load governance state for phase advance check: ${err instanceof Error ? err.message : String(err)}`,
        [`State load error: ${err instanceof Error ? err.message : String(err)}`],
        1,
      );
    }

    const ctx = buildContext(state, gates, {
      target_phase: targetPhase,
      evidence_list: loadEvidenceEnvelopes(this.projectRoot),
    });

    const result = hardConstraints.checkAll(ctx);
    const blockers = blockerCount(result.violations);

    if (blockers > 0) {
      return makeDecision(
        false,
        `Phase advance to ${targetPhase} denied: ${blockers} blocker(s).`,
        result.violations
          .filter(v => v.severity === Severity.BLOCKER)
          .map(v => `[${v.constraint_id}] ${v.message}`),
        blockers,
      );
    }

    // Check if target gate is passed
    const targetGateId = `gate-${targetPhase}`;
    const targetGate = gates.gates.find(g => g.gate_id === targetGateId);
    if (targetGate && targetGate.status !== "passed") {
      return makeDecision(
        false,
        `Phase advance to ${targetPhase} denied: gate "${targetGateId}" status is "${targetGate.status}".`,
        targetGate.blocked_reasons.length > 0
          ? targetGate.blocked_reasons.map(r => `Gate blocker: ${r}`)
          : [`Gate "${targetGateId}" has not been passed.`],
        1,
      );
    }

    return makeDecision(
      true,
      `Phase advance to ${targetPhase} allowed — all constraints satisfied.`,
      [],
      0,
    );
  }

  /**
   * Hard check for role isolation.
   * Developer (R06) cannot be the same as Reviewer (R09).
   */
  checkRoleIsolation(
    developerId: string,
    reviewerId: string,
  ): EnforcementDecision {
    if (developerId === reviewerId) {
      return makeDecision(
        false,
        "Role isolation violated: same actor cannot develop and review.",
        [`Developer "${developerId}" and Reviewer "${reviewerId}" are the same entity.`],
        1,
      );
    }

    // Check domain separation
    const devInDevDomain = DEVELOPMENT_ROLES.has(developerId);
    const reviewerInQualityDomain = QUALITY_ROLES.has(reviewerId);
    const devInQualityDomain = QUALITY_ROLES.has(developerId);
    const reviewerInDevDomain = DEVELOPMENT_ROLES.has(reviewerId);

    if (devInDevDomain && reviewerInDevDomain) {
      return makeDecision(
        false,
        "Role isolation violated: both actors belong to the development domain.",
        [`Developer "${developerId}" and Reviewer "${reviewerId}" are both in the development domain.`],
        1,
      );
    }

    if (devInQualityDomain && reviewerInQualityDomain) {
      return makeDecision(
        false,
        "Role isolation violated: both actors belong to the quality domain.",
        [`Developer "${developerId}" and Reviewer "${reviewerId}" are both in the quality domain.`],
        1,
      );
    }

    return makeDecision(
      true,
      "Role isolation satisfied — developer and reviewer are in separate domains.",
      [],
      0,
    );
  }

  /**
   * Check evidence freshness across all bound evidence.
   * Delegates to HardConstraints.checkC8.
   */
  async checkEvidenceFreshness(): Promise<EnforcementDecision> {
    let state: ProjectState;
    let gates: GatesRegistry;
    try {
      [state, gates] = await Promise.all([
        loadState(this.projectRoot),
        loadGates(this.projectRoot),
      ]);
    } catch (err) {
      return makeDecision(
        false,
        `Cannot load governance state for evidence freshness check: ${err instanceof Error ? err.message : String(err)}`,
        [`State load error: ${err instanceof Error ? err.message : String(err)}`],
        1,
      );
    }

    const evidenceList = loadEvidenceEnvelopes(this.projectRoot);
    if (evidenceList.length === 0) {
      return makeDecision(true, "No evidence bound — freshness check not applicable.", [], 0);
    }

    const ctx = buildContext(state, gates, { evidence_list: evidenceList });
    const violations = hardConstraints.checkC8(ctx);
    const blockers = blockerCount(violations);

    if (blockers > 0) {
      return makeDecision(
        false,
        `Evidence freshness check failed: ${blockers} stale/tampered evidence(s).`,
        violations.filter(v => v.severity === Severity.BLOCKER).map(v => `[${v.constraint_id}] ${v.message}`),
        blockers,
      );
    }

    return makeDecision(true, "All evidence is fresh and hash-stable.", [], 0);
  }

  /**
   * Full governance status check.
   * Returns a summary of the current governance state.
   */
  async getGovernanceStatus(): Promise<GovernanceStatus> {
    let state: ProjectState;
    let gates: GatesRegistry;
    try {
      [state, gates] = await Promise.all([
        loadState(this.projectRoot),
        loadGates(this.projectRoot),
      ]);
    } catch (err) {
      return {
        project_root: this.projectRoot,
        current_phase: "unknown",
        current_gate: null,
        active_role: null,
        pending_gates: [],
        blocked_gates: [],
        constraint_violations: 0,
        overall_status: "BLOCKED",
      };
    }

    const ctx = buildContext(state, gates, {
      evidence_list: loadEvidenceEnvelopes(this.projectRoot),
    });
    const result = hardConstraints.checkAll(ctx);

    const pendingGates = gates.gates
      .filter(g => g.status === "pending")
      .map(g => g.gate_id);
    const blockedGates = gates.gates
      .filter(g => g.status === "blocked")
      .map(g => g.gate_id);

    const violationCount = result.violations.filter(
      v => v.severity === Severity.BLOCKER,
    ).length;

    let overall_status: GovernanceStatus["overall_status"];
    if (blockedGates.length > 0) {
      overall_status = "BLOCKED";
    } else if (violationCount > 0) {
      overall_status = "DEGRADED";
    } else {
      overall_status = "HEALTHY";
    }

    return {
      project_root: this.projectRoot,
      current_phase: state.current_phase,
      current_gate: state.current_gate_id,
      active_role: state.active_role,
      pending_gates: pendingGates,
      blocked_gates: blockedGates,
      constraint_violations: violationCount,
      overall_status,
    };
  }
  /**
   * SEC-003: Compute integrity hash of governance files.
   * Returns a SHA-256 hash combining state.yaml and gates.yaml content.
   *
   * IMPORTANT: The `integrity_hash` line in state.yaml is excluded from
   * computation to avoid circular dependency (storing the hash changes the
   * file, which would invalidate the hash).
   */
  computeGovernanceFileHash(): { hash: string; files: Record<string, string> } {
    const files: Record<string, string> = {};
    const statePath = join(this.projectRoot, ".ai", "state.yaml");
    const gatesPath = join(this.projectRoot, ".ai", "gates.yaml");

    for (const [key, filePath] of [["state", statePath], ["gates", gatesPath]] as const) {
      if (existsSync(filePath)) {
        let content = readFileSync(filePath, "utf-8");
        // Exclude integrity_hash line from state.yaml to prevent circular dependency
        if (key === "state") {
          content = content.replace(/^integrity_hash:.*$\n?/m, "");
        }
        files[key] = createHash("sha256").update(content, "utf-8").digest("hex");
      }
    }

    // Combined hash: hash of all individual file hashes concatenated
    const combined = Object.values(files).sort().join(":");
    const hash = createHash("sha256").update(combined, "utf-8").digest("hex");
    return { hash, files };
  }

  /**
   * SEC-003: Check governance file integrity.
   * Compares current hash of state.yaml/gates.yaml against the expected
   * integrity_hash stored in state.yaml.
   */
  async checkGovernanceFileIntegrity(): Promise<EnforcementDecision> {
    const statePath = join(this.projectRoot, ".ai", "state.yaml");
    if (!existsSync(statePath)) {
      return makeDecision(true, "No governance state found — integrity check N/A.", [], 0);
    }

    const state = await loadState(this.projectRoot);
    if (!state) {
      return makeDecision(
        false,
        "Cannot parse governance state — file may be corrupted.",
        ["state.yaml parse failure"],
        1,
      );
    }

    // If no integrity_hash has been recorded yet, compute and store it
    const rawState = readFileSync(statePath, "utf-8");
    const storedHashMatch = rawState.match(/integrity_hash:\s*["']?([a-f0-9]{64})["']?/);
    const currentHash = this.computeGovernanceFileHash();

    if (!storedHashMatch) {
      // No hash recorded yet — this is the baseline. Caller should persist it.
      return makeDecision(
        true,
        `No integrity_hash recorded. Baseline hash: ${currentHash.hash}. Persist this value to state.yaml.`,
        [],
        0,
      );
    }

    const storedHash = storedHashMatch[1];
    if (storedHash !== currentHash.hash) {
      return makeDecision(
        false,
        "Governance file integrity check FAILED — files may have been tampered with.",
        [
          `Stored hash:   ${storedHash}`,
          `Computed hash: ${currentHash.hash}`,
          "Re-run `loop init` or restore governance files from a trusted backup.",
        ],
        1,
      );
    }

    return makeDecision(true, "Governance file integrity verified.", [], 0);
  }
}

// ── quickCheck ───────────────────────────────────────────────────────────────

/**
 * Quick global check — returns a summary decision for hook scripts.
 * Used by gate-guard.js and other hooks for fast decision making.
 */
export async function quickCheck(
  projectRoot: string,
): Promise<EnforcementDecision> {
  const hub = new EnforcementHub(projectRoot);

  let state: ProjectState;
  let gates: GatesRegistry;
  try {
    [state, gates] = await Promise.all([
      loadState(projectRoot),
      loadGates(projectRoot),
    ]);
  } catch (err) {
    return makeDecision(
      false,
      "Cannot load governance state — project may not be initialised.",
      [`State load error: ${err instanceof Error ? err.message : String(err)}`],
      1,
    );
  }

  // Quick blocked-gate check
  const blockedGates = gates.gates.filter(g => g.status === "blocked");
  if (blockedGates.length > 0) {
    const reasons = blockedGates
      .flatMap(g => g.blocked_reasons)
      .filter(Boolean);
    return makeDecision(
      false,
      `${blockedGates.length} gate(s) BLOCKED — operations restricted.`,
      reasons.length > 0 ? reasons : ["Unresolved gate blockers."],
      blockedGates.length,
    );
  }

  // Active role warning
  if (!state.active_role) {
    return makeDecision(
      true,
      "No active role — proceed with caution. Role activation recommended.",
      ["No role is currently active. Consider activating a role for full governance."],
      0,
    );
  }

  return makeDecision(
    true,
    `Governance OK — phase: ${state.current_phase}, role: ${state.active_role}.`,
    [],
    0,
  );
}
