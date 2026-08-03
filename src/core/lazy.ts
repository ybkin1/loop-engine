/**
 * lazy.ts — On-Demand Loading Entry Point for Loop Engineering Core
 *
 * Instead of loading all 22 modules upfront (as index.ts does via barrel export),
 * this module provides namespace-based lazy loading using dynamic imports.
 *
 * Benefits:
 * - MCP Server startup only loads what's needed per tool call
 * - Subagents load only their relevant module subset
 * - Reduces initial memory footprint and import chain depth
 *
 * Usage:
 *   import { kernel, evidence, enforcement, execution, knowledge, context, audit, handoff } from "./lazy.js";
 *
 *   // Each namespace is a function that returns a Promise<Module>
 *   const ev = await evidence();
 *   ev.submitEvidence(...);
 */

// ── Kernel (always available — synchronous re-exports) ──────────────────────
// The kernel is tiny (~3 modules) and needed by everything else.
// These are eagerly loaded since they're always required.

export {
  LoopError,
  initProject,
  initProjectExtended,
  loadState,
  saveState,
  checkGate,
  advanceGate,
  computeHash,
  validateProjectRoot,
  evaluateCondition,
  evaluateGateCondition,
  generateDefaultGates,
  phaseNeedsUserGate,
  USER_GATE_PHASES,
  isUserApproved,
  approveGate,
  EXTENDED_PHASES,
  EXTENDED_PHASE_GATES,
} from "./state-machine.js";

export {
  NORM_PHASES,
  PHASE_ROLE_MAP,
  rolesForPhase,
  PHASE_GATE,
  normPhase,
} from "./phase_registry.js";
export type { NormPhase } from "./phase_registry.js";

// ── Lazy Namespace Loaders ─────────────────────────────────────────────────
// Each function returns a dynamic import promise, loading the module only
// when first called. Subsequent calls hit the module cache.

/** Evidence management: submit, verify, freshness, causal chain. */
export function evidence() {
  return import("./evidence.js");
}

/** Freshness checking: TTL, causal chain, batch verification. */
export function freshness() {
  return import("./freshness.js");
}

/** Handoff protocol: create and query role handoffs. */
export function handoff() {
  return import("./handoff.js");
}

/** Enforcement: level derivation, host capability validation. */
export function enforcement() {
  return import("./enforcement.js");
}

/** Enforcement Hub: hook-core bridge for real-time governance. */
export function enforcementHub() {
  return import("./enforcement_hub.js");
}

/** Hard Constraints: C1-C8 constraint checker + evidence envelope. */
export function hardConstraints() {
  return import("./hard_constraints.js");
}

/** Router: intent routing, project profiling, risk assessment. */
export function router() {
  return import("./router.js");
}

/** Certification: role challenge/certification system. */
export function certification() {
  return import("./certification.js");
}

/** Context Controller: unified authorization engine. */
export function contextController() {
  return import("./context_controller.js");
}

/** Context Loader: progressive context loading with token budget. */
export function contextLoader() {
  return import("./context_loader.js");
}

/** Role Context: generate context injection for subagents. */
export function roleContext() {
  return import("./role_context.js");
}

/** Role Engine: role activation and status queries. */
export function roleEngine() {
  return import("./role-engine.js");
}

/** Phase Executor: full phase execution with hooks and retry. */
export function executor() {
  return import("./executor.js");
}

/** Subagent Manifest: parallel sub-agent decomposition protocol. */
export function subagentManifest() {
  return import("./subagent_manifest.js");
}

/** Audit Ledger: tamper-evident append-only audit log. */
export function auditLedger() {
  return import("./audit_ledger.js");
}

/** Execution Ledger: role execution tracking and cross-validation. */
export function executionLedger() {
  return import("./execution_ledger.js");
}

/** Knowledge Ledger: lesson capture and sedimentation loop. */
export function knowledgeLedger() {
  return import("./knowledge_ledger.js");
}

/** Review Advisor: R09 pre-review historical check. */
export function reviewAdvisor() {
  return import("./review_advisor.js");
}

/** Session Restore: loopany knowledge ledger integration. */
export function sessionRestore() {
  return import("./session_restore.js");
}

/** Prompt Engine: four-quadrant cognitive protocol. */
export function promptEngine() {
  return import("./prompt_engine.js");
}

/** Veto Escalation: severity-based escalation logic. */
export function vetoEscalation() {
  return import("./veto_escalation.js");
}

/** Host Adapter Contracts: Qoder/Standalone adapter implementations. */
export function contracts() {
  return import("./contracts.js");
}

/** Human Review Packet: structured human-approval packets. */
export function humanReviewPacket() {
  return import("./human_review_packet.js");
}

// ── Convenience: Grouped Namespace Loaders ──────────────────────────────────

/** Load all evidence-related modules at once. */
export async function loadEvidenceGroup() {
  const [ev, fr] = await Promise.all([evidence(), freshness()]);
  return { ...ev, ...fr };
}

/** Load all enforcement-related modules at once. */
export async function loadEnforcementGroup() {
  const [enf, eh, hc] = await Promise.all([
    enforcement(),
    enforcementHub(),
    hardConstraints(),
  ]);
  return { ...enf, ...eh, ...hc };
}

/** Load all execution-related modules at once. */
export async function loadExecutionGroup() {
  const [ex, sm] = await Promise.all([executor(), subagentManifest()]);
  return { ...ex, ...sm };
}

/** Load all knowledge/learning modules at once. */
export async function loadKnowledgeGroup() {
  const [kl, ra, sr] = await Promise.all([
    knowledgeLedger(),
    reviewAdvisor(),
    sessionRestore(),
  ]);
  return { ...kl, ...ra, ...sr };
}

/** Load all context-related modules at once. */
export async function loadContextGroup() {
  const [cl, cc, rc, pe] = await Promise.all([
    contextLoader(),
    contextController(),
    roleContext(),
    promptEngine(),
  ]);
  return { ...cl, ...cc, ...rc, ...pe };
}

/** Load all audit/ledger modules at once. */
export async function loadAuditGroup() {
  const [al, el] = await Promise.all([auditLedger(), executionLedger()]);
  return { ...al, ...el };
}
