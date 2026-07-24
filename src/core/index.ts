/**
 * core/index.ts — Barrel exports for the Loop Engineering core modules.
 *
 * Re-exports all public types, classes, enums, and functions from the core
 * subsystem so that consumers can import from a single entry point:
 *
 * ```ts
 * import { HardConstraints, AuditLedger, VetoEscalation } from "../core/index.js";
 * ```
 */

// ── State Machine ─────────────────────────────────────────────────────────────
export {
  LoopError,
  initProject,
  loadState,
  saveState,
  checkGate,
  advanceGate,
  computeHash,
  validateProjectRoot,
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
  computeHash as computeEvidenceHash,
} from "./evidence.js";

// ── Handoff ───────────────────────────────────────────────────────────────────
export {
  createHandoff,
  getHandoffHistory,
} from "./handoff.js";

// ── Enforcement ───────────────────────────────────────────────────────────────
export {
  EnforcementLevel,
  deriveEnforcementLevel,
  validateHostCapabilities,
  checkConstraint,
  getDegradationTable,
  HOST_PRESETS,
  HARD_CONSTRAINTS,
} from "./enforcement.js";
export type {
  HostCapabilities,
  HardConstraint,
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
} from "./freshness.js";
export type {
  FreshnessResult,
  CausalChainResult,
} from "./freshness.js";

// ── Hard Constraints (new) ────────────────────────────────────────────────────
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

// ── Veto Escalation (new) ─────────────────────────────────────────────────────
export {
  VetoSeverity,
  EscalationLevel,
  VetoEscalation,
} from "./veto_escalation.js";
export type {
  VetoRecord,
  EscalationDecision,
} from "./veto_escalation.js";

// ── Audit Ledger (new) ────────────────────────────────────────────────────────
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
export {
  Action,
  Decision,
  ContextController,
  quickAuth,
  isGovernancePath,
  PROTECTED_PATHS,
} from "./context_controller.js";
export type {
  AuthRequest,
  AuthResult,
} from "./context_controller.js";

// ── Phase Executor ────────────────────────────────────────────────────────────
export {
  StepStatus,
  PhaseExecutor,
  PHASE_ROLES,
} from "./executor.js";
export type {
  RoleStep,
  PhasePlan,
  PhaseExecutionResult,
  RoleStepResult,
  ValidationResult,
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
