/**
 * veto_escalation.ts — Veto and escalation protocol for Loop Engineering
 *
 * When a role raises a veto, this module determines whether the conflict can
 * be resolved internally, requires cross-role negotiation, or must be
 * escalated to the human operator.
 *
 * Ported from ZCode loop_core/veto_escalation.py.
 */

// ── Enums ─────────────────────────────────────────────────────────────────────

/** Severity of a veto. */
export enum VetoSeverity {
  /** Hard block — the operation must not proceed. */
  BLOCKER = "BLOCKER",
  /** Advisory — the operation may proceed with acknowledged risk. */
  WARNING = "WARNING",
}

/** Escalation level determined by the resolution protocol. */
export enum EscalationLevel {
  /** The vetoing role resolves the conflict internally. */
  ROLE_INTERNAL = "ROLE_INTERNAL",
  /** Multiple roles in the same or adjacent domains negotiate a resolution. */
  CROSS_ROLE = "CROSS_ROLE",
  /** The conflict is escalated to the human operator for a binding decision. */
  USER_GATE = "USER_GATE",
}

// ── Veto Record ───────────────────────────────────────────────────────────────

/** A single veto raised by a role against a proposed operation or artifact. */
export interface VetoRecord {
  /** Unique veto identifier. */
  veto_id: string;
  /** Role that raised the veto (R01–R11). */
  role_id: string;
  /** Severity of the veto. */
  severity: VetoSeverity;
  /** The operation, artifact, or gate being vetoed. */
  target: string;
  /** Human-readable reason for the veto. */
  reason: string;
  /** ISO-8601 timestamp when the veto was created. */
  created_at: string;
  /** Whether the veto has been resolved. */
  resolved: boolean;
}

// ── Escalation Decision ───────────────────────────────────────────────────────

/** The outcome of the escalation analysis. */
export interface EscalationDecision {
  /** Determined escalation level. */
  level: EscalationLevel;
  /** Human-readable explanation of why this level was chosen. */
  reason: string;
  /** Roles that must participate in the resolution process. */
  participants: string[];
  /** `true` when the human operator must make a binding decision. */
  human_review_needed: boolean;
}

// ── Domain Map ────────────────────────────────────────────────────────────────

/**
 * Maps each role to a domain label used to determine whether two roles are
 * "same domain" (easier to negotiate) or "different domain" (harder).
 */
const ROLE_DOMAIN: Record<string, string> = {
  R01: "management",   // Product Owner
  R02: "management",   // Planner
  R03: "management",   // Delivery Manager
  R04: "architecture", // Architect
  R05: "architecture", // Module Designer
  R06: "engineering",  // Developer
  R07: "quality",      // QA Engineer
  R08: "security",     // Security Engineer
  R09: "engineering",  // Code Reviewer
  R10: "operations",   // Ops / DevOps
  R11: "management",   // Orchestrator
};

/** The security engineer role — special escalation rules apply. */
const SECURITY_ROLE = "R08";

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Return the set of distinct role IDs from a list of veto records.
 */
function distinctRoles(vetos: VetoRecord[]): string[] {
  return [...new Set(vetos.map(v => v.role_id))];
}

/**
 * Return the domain label for a given role, defaulting to "unknown".
 */
function domainOf(roleId: string): string {
  return ROLE_DOMAIN[roleId] ?? "unknown";
}

/**
 * Check whether all roles in a set belong to the same domain.
 */
function allSameDomain(roles: string[]): boolean {
  if (roles.length <= 1) return true;
  const domains = new Set(roles.map(domainOf));
  return domains.size === 1;
}

// ── VetoEscalation ────────────────────────────────────────────────────────────

/**
 * Analyses unresolved vetos and determines the appropriate escalation level
 * according to the 5-rule priority protocol.
 */
export class VetoEscalation {
  /**
   * Analyse a list of veto records and return the escalation decision.
   *
   * **Priority rules (evaluated in order):**
   * 1. Security engineer (R08) + any other role → `USER_GATE`
   * 2. ≥ 3 distinct roles → `USER_GATE`
   * 3. 2 roles, same domain → `CROSS_ROLE`
   * 4. 2 roles, different domains → `CROSS_ROLE` (with wider participation)
   * 5. Single role → `ROLE_INTERNAL`
   *
   * @param vetos - All veto records (resolved and unresolved are both
   *                considered; only unresolved vetos drive escalation)
   * @returns The escalation decision
   */
  checkEscalation(vetos: VetoRecord[]): EscalationDecision {
    const unresolved = vetos.filter(v => !v.resolved);

    if (unresolved.length === 0) {
      return {
        level: EscalationLevel.ROLE_INTERNAL,
        reason: "No unresolved vetos — no escalation required.",
        participants: [],
        human_review_needed: false,
      };
    }

    const roles = distinctRoles(unresolved);
    const hasBlocker = unresolved.some(v => v.severity === VetoSeverity.BLOCKER);
    const hasSecurity = roles.includes(SECURITY_ROLE);

    // Rule 1: Security engineer + any other role → USER_GATE
    if (hasSecurity && roles.length >= 2) {
      return {
        level: EscalationLevel.USER_GATE,
        reason: `Security engineer (${SECURITY_ROLE}) is involved in a veto alongside ${roles.length - 1} other role(s). Security concerns always escalate to the human operator.`,
        participants: roles,
        human_review_needed: true,
      };
    }

    // Rule 2: ≥ 3 distinct roles → USER_GATE
    if (roles.length >= 3) {
      return {
        level: EscalationLevel.USER_GATE,
        reason: `${roles.length} distinct roles (${roles.join(", ")}) have unresolved vetos. Multi-party conflicts require human arbitration.`,
        participants: roles,
        human_review_needed: true,
      };
    }

    // Rule 3: 2 roles, same domain → CROSS_ROLE
    if (roles.length === 2 && allSameDomain(roles)) {
      return {
        level: EscalationLevel.CROSS_ROLE,
        reason: `Two roles in the same domain (${domainOf(roles[0])}) have conflicting vetos. Cross-role negotiation within the ${domainOf(roles[0])} domain is required.`,
        participants: roles,
        human_review_needed: false,
      };
    }

    // Rule 4: 2 roles, different domains → CROSS_ROLE (wider scope)
    if (roles.length === 2) {
      const hasBlockerSeverity = hasBlocker ? " BLOCKER severity elevates the urgency." : "";
      return {
        level: EscalationLevel.CROSS_ROLE,
        reason: `Two roles from different domains (${domainOf(roles[0])} and ${domainOf(roles[1])}) have conflicting vetos.${hasBlockerSeverity} Cross-domain negotiation required; escalate to USER_GATE if unresolved within one cycle.`,
        participants: roles,
        human_review_needed: hasBlocker,
      };
    }

    // Rule 5: Single role → ROLE_INTERNAL
    return {
      level: EscalationLevel.ROLE_INTERNAL,
      reason: `Only one role (${roles[0]}) has raised a veto. The role should resolve the issue internally before re-attempting the operation.`,
      participants: roles,
      human_review_needed: false,
    };
  }

  /**
   * Generate a human-readable summary of all unresolved vetos suitable for
   * inclusion in a human review package.
   *
   * @param vetos - All veto records (resolved vetos are excluded)
   * @returns Markdown-formatted summary string
   */
  generateHumanReviewSummary(vetos: VetoRecord[]): string {
    const unresolved = vetos.filter(v => !v.resolved);

    if (unresolved.length === 0) {
      return "## Veto Review Summary\n\nNo unresolved vetos. All conflicts have been resolved.";
    }

    const roles = distinctRoles(unresolved);
    const decision = this.checkEscalation(vetos);
    const blockerCount = unresolved.filter(v => v.severity === VetoSeverity.BLOCKER).length;
    const warningCount = unresolved.filter(v => v.severity === VetoSeverity.WARNING).length;

    const lines: string[] = [
      "## Veto Review Summary",
      "",
      `**Escalation Level:** ${decision.level}`,
      `**Reason:** ${decision.reason}`,
      `**Participants:** ${decision.participants.join(", ")}`,
      `**Human Review Needed:** ${decision.human_review_needed ? "Yes" : "No"}`,
      "",
      `**Total Unresolved Veto(s):** ${unresolved.length} (${blockerCount} BLOCKER, ${warningCount} WARNING)`,
      `**Distinct Roles:** ${roles.length} (${roles.join(", ")})`,
      "",
      "### Veto Details",
      "",
    ];

    for (const veto of unresolved) {
      lines.push(
        `- **${veto.veto_id}** [${veto.severity}] by \`${veto.role_id}\``,
        `  - Target: ${veto.target}`,
        `  - Reason: ${veto.reason}`,
        `  - Created: ${veto.created_at}`,
        "",
      );
    }

    lines.push("### Required Action");
    lines.push("");

    if (decision.human_review_needed) {
      lines.push(
        "The human operator must review and make a binding decision on each veto listed above.",
        "Resolve by either overriding the veto (with documented justification) or directing",
        "the participating roles to address the underlying concern.",
      );
    } else {
      lines.push(
        `The participating roles (${decision.participants.join(", ")}) should negotiate a resolution`,
        "internally. If no resolution is reached within one cycle, the conflict will auto-escalate",
        "to USER_GATE for human arbitration.",
      );
    }

    return lines.join("\n");
  }
}
