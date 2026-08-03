/**
 * core/index.ts — Barrel exports for the Loop Engineering core modules.
 *
 * Re-exports the **public API** of the core subsystem. Internal types,
 * constants, and deprecated helpers are intentionally excluded — import
 * them directly from the source module if needed.
 *
 * ```ts
 * import { HardConstraints, AuditLedger, VetoEscalation } from "../core/index.js";
 * ```
 */

// ── State Machine ─────────────────────────────────────────────────────────────
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

// ── Role Engine ───────────────────────────────────────────────────────────────
export {
  activateRole,
  getRoleStatus,
} from "./role-engine.js";

// ── Evidence ──────────────────────────────────────────────────────────────────
export {
  submitEvidence,
  verifyEvidence,
  loadEvidence,
} from "./evidence.js";

// ── Handoff ───────────────────────────────────────────────────────────────────
export {
  createHandoff,
  getHandoffHistory,
} from "./handoff.js";

// ── Enforcement ───────────────────────────────────────────────────────────────
// Public API: level derivation + validation.
// Internal constants (HOST_PRESETS, HARD_CONSTRAINTS) and deprecated helpers
// (checkConstraint, getDegradationTable) are NOT re-exported.
export {
  EnforcementLevel,
  deriveEnforcementLevel,
  validateHostCapabilities,
} from "./enforcement.js";
export type {
  HostCapabilities,
  EnforcementResult,
} from "./enforcement.js";

// ── Router ────────────────────────────────────────────────────────────────────
export {
  routeIntent,
  defaultProfile,
  LoopMode,
  RiskLevel,
} from "./router.js";
export type { ProjectProfile } from "./router.js";

// ── Certification ─────────────────────────────────────────────────────────────
export {
  runChallengeForRole,
  runAllCertifications,
  buildCertStateAfterRun,
  ALL_ROLES,
} from "./certification.js";
export type { RoleCertState } from "./certification.js";

// ── Freshness ─────────────────────────────────────────────────────────────────
export {
  checkFreshness,
  checkCausalChain,
  checkAllFreshness,
  getFreshnessSummary,
  listEvidenceIds,
} from "./freshness.js";
export type {
  FreshnessResult,
  CausalChainResult,
  FreshnessSummary,
} from "./freshness.js";

// ── Hard Constraints ──────────────────────────────────────────────────────────
// Public API: constraint checker class + envelope factory.
export {
  ConstraintID,
  Severity,
  HardConstraints,
  createEvidenceEnvelope,
} from "./hard_constraints.js";
export type {
  ConstraintViolation,
  ConstraintCheckResult,
  EvidenceEnvelope,
  ConstraintContext,
} from "./hard_constraints.js";

// ── Veto Escalation ───────────────────────────────────────────────────────────
export {
  VetoSeverity,
  EscalationLevel,
  VetoEscalation,
} from "./veto_escalation.js";
export type {
  VetoRecord,
  EscalationDecision,
} from "./veto_escalation.js";

// ── Audit Ledger ──────────────────────────────────────────────────────────────
export { AuditLedger } from "./audit_ledger.js";
export type { LedgerEntry, IntegrityResult } from "./audit_ledger.js";

// ── Host Adapter Contracts ────────────────────────────────────────────────────
export {
  HostAdapterQoder,
  HostAdapterStandalone,
  createHostAdapter,
} from "./contracts.js";
export type {
  IHostAdapter,
  ExecResult,
  TaskRecord,
  GateDecision,
  EvidenceFreeze,
  FreshnessCheck,
} from "./contracts.js";

// ── Enforcement Hub (Hook-Core bridge) ───────────────────────────────────────
export {
  EnforcementHub,
  quickCheck,
} from "./enforcement_hub.js";
export type {
  EnforcementDecision,
  GovernanceStatus,
} from "./enforcement_hub.js";

// ── Context Controller (unified authorization engine) ────────────────────────
// Public API: controller class + quick helper.
// Internal constants (PROTECTED_PATHS) and utilities (isGovernancePath)
// are NOT re-exported.
export {
  Action,
  Decision,
  ContextController,
  quickAuth,
} from "./context_controller.js";
export type {
  AuthRequest,
  AuthResult,
} from "./context_controller.js";

// ── Phase Executor ────────────────────────────────────────────────────────────
export {
  StepStatus,
  PhaseExecutor,
  HookRegistry,
  PHASE_ROLES,
} from "./executor.js";
export type {
  PhasePlan,
  PhaseExecutionResult,
  RoleStepResult,
  ValidationResult,
  RoleExecutionHook,
  RoleExecutionContext,
  ExecutorOptions,
} from "./executor.js";

// ── Context Loader ────────────────────────────────────────────────────────────
export {
  LoadLevel,
  ContextLoader,
} from "./context_loader.js";
export type {
  LoadedContext,
  DocumentSection,
  DocumentIndex,
} from "./context_loader.js";

// ── Execution Ledger ──────────────────────────────────────────────────────────
export {
  ExecutionStatus,
  ExecutionLedger,
} from "./execution_ledger.js";
export type {
  ExecutionRecord,
  ExecutionIntegrity,
  CrossValidation,
  RoleStatistics,
} from "./execution_ledger.js";

// ── Human Review Packet ──────────────────────────────────────────────────────
export {
  PacketType,
  PacketBuilder,
  toMarkdown,
  toPlainText,
} from "./human_review_packet.js";
export type {
  KeyChoice,
  RiskItem,
  DecisionRequired,
  HumanReviewPacket,
} from "./human_review_packet.js";

// ── Subagent Manifest (P1-A upgrade) ────────────────────────────────────────
export {
  createManifest,
  createSubagentSpec,
  planExecution,
  validateResult,
  aggregateResults,
  buildExecutionResult,
  computeManifestHash,
} from "./subagent_manifest.js";

// ── Phase Registry (T-0006-A: single source of truth) ──────────────────────
export {
  NORM_PHASES,
  PHASE_ROLE_MAP,
  rolesForPhase,
  PHASE_GATE,
  normPhase,
} from "./phase_registry.js";
export type { NormPhase } from "./phase_registry.js";

// ── Role Context Protocol (platform limitation workaround) ──────────────────
export { generateRoleContext } from "./role_context.js";
export type { RoleContextResult } from "./role_context.js";

// ── Knowledge Ledger (knowledge sedimentation loop) ────────────────────────
export { KnowledgeLedger } from "./knowledge_ledger.js";
export type { LessonInput } from "./knowledge_ledger.js";

// ── Review Advisor (R09 pre-review historical check) ───────────────────────
export {
  generatePreReviewAdvisory,
  generateQualitySection,
} from "./review_advisor.js";
export type { PreReviewInput, PreReviewAdvisory, AdvisoryItem, QualitySectionInput } from "./review_advisor.js";

// ── Session Restore (loopany knowledge ledger integration) ─────────────────
export { restoreSessionContext, getKnowledgeStatusLine } from "./session_restore.js";
export type { SessionRestoreContext, UnresolvedLessonSummary } from "./session_restore.js";

// ── Prompt Engine (four-quadrant cognitive protocol) ────────────────────────
export { generatePrompt, loadQuadrantTemplate, getRoleQuadrantConfig } from "./prompt_engine.js";
export type { PromptContext, PromptResult } from "./prompt_engine.js";

// ── Harness Analyzer (self-diagnosis engine, inspired by Better Harness) ────
export { HarnessAnalyzer, DIMENSION_LABELS } from "./harness_analyzer.js";
export type {
  HarnessReport, DimensionResult, Finding, EvidenceItem,
  DimensionName, DimensionScore, FindingSeverity, LoopAssets,
} from "./harness_analyzer.js";

// ── Constraint Engine (unified facade for enforcement modules) ──────────────
export { ConstraintEngine } from "./constraint_engine.js";

// ── Loop Discovery (10-gate decision, aligned with Better Harness) ──────────
export {
  LoopDiscovery,
  DISCOVERY_GATE_LABELS,
} from "./loop_discovery.js";
export type {
  DiscoveryGateId,
  GateEvaluation,
  RuntimeFit,
  DiscoveryDecision,
  DurableOwner,
  LoopDiscoveryResult,
  LoopCandidateInput,
} from "./loop_discovery.js";
