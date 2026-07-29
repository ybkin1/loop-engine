/**
 * executor.ts — Phase Execution Engine for Loop Engineering
 *
 * Drives complete phase execution: validate transition → freeze inputs →
 * execute roles → persist state. Supports 6 phases mapped to roles.
 *
 * Ported from ZCode loop_core/executor.py.
 */

import {
  loadState,
  saveState,
  loadGates,
  saveGates,
  checkGate,
  advanceGate,
  computeHash,
  LoopError,
} from "./state-machine.js";

import { rolesForPhase, PHASE_GATE, normPhase } from "./phase_registry.js";
import { HardConstraints } from "./hard_constraints.js";
import type { ConstraintContext } from "./hard_constraints.js";
import { createManifest, planExecution, validateResult, buildExecutionResult, computeManifestHash } from "./subagent_manifest.js";
import type { SubagentManifest, SubagentSpec, SubagentResult } from "../types/index.js";

import type {
  ProjectState,
  GatesRegistry,
  GateCheckResult,
  GateAdvanceResult,
} from "../types/index.js";

// ── Enums & Constants ────────────────────────────────────

export enum StepStatus {
  PENDING = "PENDING",
  RUNNING = "RUNNING",
  COMPLETE = "COMPLETE",
  FAILED = "FAILED",
  BLOCKED = "BLOCKED",
}

// ── Role Execution Hook System ─────────────────────────────

/** Context passed to a RoleExecutionHook when executing a role. */
export interface RoleExecutionContext {
  role_id: string;
  phase_id: string;
  required_fields: string[];
  input_hashes: Record<string, string>;
  timeout_ms: number;
}

/**
 * Pluggable hook interface for real role execution.
 * Implement this to connect external Skill/Agent pipelines.
 */
export interface RoleExecutionHook {
  execute(context: RoleExecutionContext): Promise<RoleStepResult>;
}

/** Registry mapping role IDs to their execution hooks. */
export class HookRegistry {
  private hooks = new Map<string, RoleExecutionHook>();

  register(roleId: string, hook: RoleExecutionHook): void {
    this.hooks.set(roleId, hook);
  }

  get(roleId: string): RoleExecutionHook | undefined {
    return this.hooks.get(roleId);
  }

  has(roleId: string): boolean {
    return this.hooks.has(roleId);
  }

  /** Number of registered hooks. */
  get size(): number {
    return this.hooks.size;
  }
}

/** Options for PhaseExecutor configuration. */
export interface ExecutorOptions {
  /** Default timeout for hook execution in milliseconds. Default: 30000. */
  default_timeout_ms?: number;
}

const DEFAULT_TIMEOUT_MS = 30_000;

// ── Phase → Role mapping (derived from phase_registry) ───

export const PHASE_ROLES: Record<string, string[]> = {};
for (const phase of [
  "requirements", "architecture", "planning",
  "implementation", "review", "delivery",
  "S0-init", "S1-requirements", "S2-architecture", "S3-interface",
  "S4-implementation", "S5-quality", "S6-delivery", "S7-integration",
  "S8-functional-test", "S9-fix-optimize", "S10-performance", "S11-maintenance",
]) {
  PHASE_ROLES[phase] = rolesForPhase(phase);
}

// ── Interfaces ───────────────────────────────────────────

export interface RoleStep {
  role_id: string;
  status: StepStatus;
  agent_id?: string;
  verdict?: string;
  retries: number;
  max_retries: number;
  required_fields: string[];
  started_at?: string;
  completed_at?: string;
  error?: string;
}

export interface PhasePlan {
  phase_id: string;
  steps: RoleStep[];
  gate_id: string;
  input_hashes: Record<string, string>;
  created_at: string;
  status: StepStatus;
  started_at?: string;
  completed_at?: string;
}

export interface PhaseExecutionResult {
  phase_id: string;
  success: boolean;
  steps_total: number;
  steps_completed: number;
  steps_failed: number;
  duration_ms: number;
  started_at: string;
  completed_at: string;
  errors: string[];
}

export interface RoleStepResult {
  role_id: string;
  status: StepStatus;
  output?: Record<string, unknown>;
  error?: string;
  duration_ms: number;
}

export interface ValidationResult {
  valid: boolean;
  missing_fields: string[];
}

// ── Default required fields per role ─────────────────────

/** Maximum retry attempts for a failed role step. */
const DEFAULT_MAX_RETRIES = 2;

const ROLE_REQUIRED_FIELDS: Record<string, string[]> = {
  R01: ["requirements_doc", "acceptance_criteria"],
  R03: ["delivery_checklist", "release_notes"],
  R04: ["architecture_doc", "component_diagram"],
  R05: ["detail_design_doc", "task_breakdown"],
  R06: ["source_code", "test_results", "lint_results"],
  R07: ["qa_report", "defect_report"],
  R08: ["security_review", "threat_model"],
  R09: ["review_report", "approval_status"],
  R10: ["ops_runbook", "monitoring_config"],
};

// ── PhaseExecutor ────────────────────────────────────────

export class PhaseExecutor {
  private projectRoot: string;
  private hooks: HookRegistry;
  private options: Required<ExecutorOptions>;

  constructor(projectRoot: string, hooks?: HookRegistry, options?: ExecutorOptions) {
    this.projectRoot = projectRoot;
    this.hooks = hooks ?? new HookRegistry();
    this.options = { default_timeout_ms: options?.default_timeout_ms ?? DEFAULT_TIMEOUT_MS };
  }

  /**
   * Create an execution plan for a phase.
   * Builds a PhasePlan with one RoleStep per role defined in PHASE_ROLES.
   */
  planPhase(phaseId: string): PhasePlan {
    const roles = PHASE_ROLES[phaseId];
    if (!roles) {
      throw new LoopError(
        "UNKNOWN_PHASE",
        `No phase definition found for: ${phaseId}`,
        phaseId,
      );
    }

    const steps: RoleStep[] = roles.map((roleId) => ({
      role_id: roleId,
      status: StepStatus.PENDING,
      retries: 0,
      max_retries: DEFAULT_MAX_RETRIES,
      required_fields: ROLE_REQUIRED_FIELDS[roleId] ?? [],
    }));

    const now = new Date().toISOString();
    return {
      phase_id: phaseId,
      steps,
      gate_id: PHASE_GATE[phaseId] ?? `gate-${phaseId}`,
      input_hashes: {},
      created_at: now,
      status: StepStatus.PENDING,
    };
  }

  /**
   * Execute a complete phase end-to-end.
   *
   * 1. Verify current_phase matches phaseId
   * 2. Freeze input hashes
   * 3. Execute each RoleStep sequentially
   * 4. Mark steps RUNNING → COMPLETE / FAILED
   * 5. After all steps complete, advance the gate
   * 6. Return PhaseExecutionResult
   */
  async executePhase(phaseId: string): Promise<PhaseExecutionResult> {
    const startedAt = new Date();
    const errors: string[] = [];

    // Normalize phase name so legacy/P-prefix names map correctly
    const canonicalPhase = normPhase(phaseId);

    // ── 1. Validate current phase ──────────────────────
    let state: ProjectState;
    try {
      state = await loadState(this.projectRoot);
    } catch (err) {
      throw new LoopError(
        "STATE_LOAD_FAILED",
        `Failed to load project state for phase '${phaseId}': ${err instanceof Error ? err.message : String(err)}`,
        phaseId,
      );
    }
    // Accept both legacy and canonical phase names in state comparison
    const stateCanonical = normPhase(state.current_phase);
    if (stateCanonical !== canonicalPhase) {
      throw new LoopError(
        "PHASE_MISMATCH",
        `Cannot execute phase '${phaseId}': current phase is '${state.current_phase}' (normalized: ${stateCanonical}, expected: ${canonicalPhase})`,
        phaseId,
      );
    }

    // ── 2. Build plan & freeze input hashes ────────────
    const plan = this.planPhase(phaseId);
    plan.input_hashes = await this.freezeInputs(state, phaseId);
    plan.status = StepStatus.RUNNING;
    plan.started_at = startedAt.toISOString();

    // ── 3. Execute each step sequentially ──────────────
    const { stepsCompleted, stepsFailed } = await this._executeSteps(plan, errors);

    // ── 4. Finalize plan status ────────────────────────
    const completedAt = new Date();
    plan.completed_at = completedAt.toISOString();
    const allStepsSucceeded = stepsFailed === 0 && stepsCompleted === plan.steps.length;
    let allSucceeded = allStepsSucceeded;
    plan.status = allSucceeded ? StepStatus.COMPLETE : StepStatus.FAILED;
    await this.persistState(plan);

    // ── 5. Run hard constraints before advancing gate ───
    if (allSucceeded) {
      const constraintResult = await this._checkConstraints(state, phaseId, canonicalPhase, errors);
      if (!constraintResult.passed) {
        // Constraints blocked — mark as failed, don't advance gate
        errors.push(`Hard constraints BLOCKED phase advance: ${constraintResult.violations.filter(v => v.severity === "BLOCKER").map(v => v.constraint_id).join(", ")}`);
        allSucceeded = false;
      }
    }

    // ── 6. Advance gate if all steps + constraints passed ─
    if (allSucceeded) {
      await this._tryAdvanceGate(plan.gate_id, errors);
    }

    // ── 6. Update project state ────────────────────────
    await this.updateProjectState(phaseId, plan, allSucceeded);

    const durationMs = completedAt.getTime() - startedAt.getTime();

    return {
      phase_id: phaseId,
      success: allSucceeded,
      steps_total: plan.steps.length,
      steps_completed: stepsCompleted,
      steps_failed: stepsFailed,
      duration_ms: durationMs,
      started_at: startedAt.toISOString(),
      completed_at: completedAt.toISOString(),
      errors,
    };
  }

  /**
   * Execute a single role step.
   *
   * If a hook is registered for the role, delegates to the hook with timeout.
   * Otherwise falls back to simulated execution (placeholder output).
   */
  async executeRole(step: RoleStep, phaseId?: string, inputHashes?: Record<string, string>): Promise<RoleStepResult> {
    const startedAt = Date.now();

    // If a hook is registered, use it with timeout protection
    const hook = this.hooks.get(step.role_id);
    if (hook) {
      return this._executeWithHook(step, hook, phaseId ?? "unknown", startedAt, inputHashes);
    }

    // Fallback: no hook registered — cannot execute role
    const durationMs = Date.now() - startedAt;
    return {
      role_id: step.role_id,
      status: StepStatus.FAILED,
      error: `No execution hook registered for role '${step.role_id}'. Register a hook via HookRegistry before executing this role.`,
      duration_ms: durationMs,
    };
  }

  /**
   * Execute a role via its registered hook with timeout protection.
   */
  private async _executeWithHook(
    step: RoleStep,
    hook: RoleExecutionHook,
    phaseId: string,
    startedAt: number,
    inputHashes?: Record<string, string>,
  ): Promise<RoleStepResult> {
    const timeoutMs = this.options.default_timeout_ms;
    const context: RoleExecutionContext = {
      role_id: step.role_id,
      phase_id: phaseId,
      required_fields: step.required_fields,
      input_hashes: inputHashes ?? {},
      timeout_ms: timeoutMs,
    };

    try {
      const result = await new Promise<RoleStepResult>((resolve, reject) => {
        const timer = setTimeout(
          () => reject(new Error(`Role '${step.role_id}' execution timed out after ${timeoutMs}ms`)),
          timeoutMs,
        );
        hook.execute(context)
          .then((res) => { clearTimeout(timer); resolve(res); })
          .catch((err) => { clearTimeout(timer); reject(err); });
      });
      return {
        ...result,
        duration_ms: Date.now() - startedAt,
      };
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return {
        role_id: step.role_id,
        status: StepStatus.FAILED,
        error: msg,
        duration_ms: Date.now() - startedAt,
      };
    }
  }

  /**
   * Validate step output against required_fields.
   * Returns a ValidationResult indicating which fields are missing.
   */
  validateStep(step: RoleStep, output: Record<string, unknown>): ValidationResult {
    const missing: string[] = [];
    for (const field of step.required_fields) {
      if (!(field in output) || output[field] === null || output[field] === undefined) {
        missing.push(field);
      }
    }
    return {
      valid: missing.length === 0,
      missing_fields: missing,
    };
  }

  /**
   * Persist execution state — writes the current plan status into the
   * project's state.yaml phases array.
   */
  async persistState(plan: PhasePlan): Promise<void> {
    const state = await loadState(this.projectRoot);
    const phaseIdx = state.phases.findIndex((p) => p.phase_id === plan.phase_id);
    if (phaseIdx < 0) {
      throw new LoopError(
        "PHASE_NOT_FOUND",
        `Phase '${plan.phase_id}' not found in project state`,
        plan.phase_id,
      );
    }

    // Map plan status to phase record status
    const phaseRecord = state.phases[phaseIdx];
    if (plan.status === StepStatus.COMPLETE) {
      phaseRecord.status = "completed";
    } else if (plan.status === StepStatus.RUNNING) {
      phaseRecord.status = "active";
    } else if (plan.status === StepStatus.FAILED) {
      phaseRecord.status = "active"; // Keep active for retry
    }

    await saveState(this.projectRoot, state);
  }

  // ── SubagentManifest integration (T-0007-B) ──────────

  /**
   * Decompose a role's work into parallel sub-agents using the
   * SubagentManifest protocol. The host is responsible for
   * actually launching the sub-agents; this method provides
   * the execution plan and validation framework.
   */
  buildManifestFromRole(
    roleId: string,
    phaseId: string,
    subagents: SubagentSpec[],
    aggregationPrompt: string,
    maxParallel = 3,
  ): SubagentManifest {
    return createManifest(roleId, `Phase ${phaseId} - ${roleId}`, subagents, aggregationPrompt, maxParallel);
  }

  /**
   * Plan parallel execution of a manifest into batches.
   */
  planParallelExecution(manifest: SubagentManifest): SubagentSpec[][] {
    return planExecution(manifest);
  }

  /**
   * Validate and aggregate subagent results into a final execution result.
   * Checks each result against the original spec's schema and produces
   * a combined output with content hash for evidence binding.
   */
  aggregateManifestResults(
    manifest: SubagentManifest,
    results: SubagentResult[],
  ) {
    // Validate each result against its spec
    const specMap = new Map(manifest.subagents.map(s => [s.subagent_id, s]));
    const errors: string[] = [];
    for (const r of results) {
      const spec = specMap.get(r.subagent_id);
      if (!spec) {
        errors.push(`Unknown subagent: ${r.subagent_id}`);
        continue;
      }
      const validation = validateResult(spec, r);
      if (!validation.is_valid) {
        errors.push(`[${r.subagent_id}] ${validation.message}`);
      }
    }

    const execResult = buildExecutionResult(manifest, results);
    const hash = computeManifestHash(manifest);

    return {
      result: execResult,
      errors,
      manifest_hash: hash,
      all_valid: errors.length === 0 && execResult.failed === 0,
    };
  }

  /**
   * Execute all steps in a plan sequentially, tracking completion/failure counts.
   */
  private async _executeSteps(
    plan: PhasePlan,
    errors: string[],
  ): Promise<{ stepsCompleted: number; stepsFailed: number }> {
    let stepsCompleted = 0;
    let stepsFailed = 0;

    for (const step of plan.steps) {
      step.status = StepStatus.RUNNING;
      step.started_at = new Date().toISOString();
      await this.persistState(plan);

      try {
        const completed = await this._executeSingleStep(step, plan, errors);
        if (completed) {
          stepsCompleted++;
        } else {
          stepsFailed++;
        }
      } catch (err) {
        step.status = StepStatus.FAILED;
        step.completed_at = new Date().toISOString();
        const msg = err instanceof Error ? err.message : String(err);
        step.error = msg;
        stepsFailed++;
        errors.push(`[${step.role_id}] ${msg}`);
        break;
      }

      await this.persistState(plan);
    }

    return { stepsCompleted, stepsFailed };
  }

  /**
   * Execute a single step with validation and retry logic.
   * Returns true if the step completed successfully, false otherwise.
   */
  private async _executeSingleStep(
    step: RoleStep,
    plan: PhasePlan,
    errors: string[],
  ): Promise<boolean> {
    const result = await this.executeRole(step, plan.phase_id, plan.input_hashes);
    step.completed_at = new Date().toISOString();

    if (result.status === StepStatus.COMPLETE) {
      // Validate output against required fields
      if (step.required_fields.length > 0 && result.output) {
        const validation = this.validateStep(step, result.output);
        if (!validation.valid) {
          step.status = StepStatus.FAILED;
          step.error = `Missing required fields: ${validation.missing_fields.join(", ")}`;
          errors.push(`[${step.role_id}] ${step.error}`);
          return false;
        }
      }
      step.status = StepStatus.COMPLETE;
      step.verdict = "approved";
      return true;
    }

    // Step did not complete — attempt retry
    step.status = StepStatus.FAILED;
    step.error = result.error ?? "Unknown error during role execution";
    errors.push(`[${step.role_id}] ${step.error}`);

    return this._retryStepIfNeeded(step, errors, plan.phase_id);
  }

  /**
   * Retry a failed step if retries remain.
   * Returns true if the retry succeeded, false otherwise.
   */
  private async _retryStepIfNeeded(
    step: RoleStep,
    errors: string[],
    phaseId?: string,
  ): Promise<boolean> {
    if (step.retries >= step.max_retries) return false;

    step.retries++;
    step.status = StepStatus.PENDING;
    step.error = undefined;
    step.started_at = undefined;
    step.completed_at = undefined;

    const retryResult = await this.executeRole(step, phaseId);
    step.completed_at = new Date().toISOString();

    if (retryResult.status === StepStatus.COMPLETE) {
      step.status = StepStatus.COMPLETE;
      step.verdict = "approved";
      errors.pop();
      return true;
    }

    step.status = StepStatus.FAILED;
    step.error = retryResult.error ?? "Retry failed";
    errors.push(`[${step.role_id}] Retry ${step.retries} failed: ${step.error}`);
    return false;
  }

  /**
   * Run HardConstraints check before gate advance.
   * Maps phase execution state to ConstraintContext and runs all C1-C8.
   */
  private async _checkConstraints(
    state: ProjectState,
    phaseId: string,
    canonicalPhase: string,
    errors: string[],
  ) {
    const hc = new HardConstraints();

    // Build constraint context from current project state
    const gates = await loadGates(this.projectRoot);
    const phaseGateMap: Record<string, string> = {};
    if (gates?.gates) {
      for (const g of gates.gates) {
        const gid = g.gate_id ?? "";
        const gs = (g.status ?? "pending").toUpperCase();
        phaseGateMap[gid] = gs;
      }
    }

    const ctx: ConstraintContext = {
      current_phase: canonicalPhase,
      target_phase: canonicalPhase,
      phase_gates: phaseGateMap,
      tasks: [{ id: state.current_task_id ?? "unknown", status: "active" }],
      gates: gates?.gates?.map(g => ({ id: g.gate_id ?? "", status: g.status ?? "pending" })) ?? [],
    };

    const result = hc.checkAll(ctx);
    for (const v of result.violations) {
      errors.push(`[${v.constraint_id}] ${v.severity}: ${v.message}`);
    }
    return result;
  }

  /**
   * Attempt to advance the gate, catching and logging errors.
   */
  private async _tryAdvanceGate(gateId: string, errors: string[]): Promise<void> {
    try {
      const gateResult = await advanceGate(this.projectRoot, gateId);
      if (!gateResult.success) {
        errors.push(`Gate advance failed: ${gateResult.error ?? "unknown"}`);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      errors.push(`Gate advance error: ${msg}`);
    }
  }

  /**
   * Freeze input hashes — captures a snapshot of the current project state
   * to detect mid-execution mutations.
   */
  private async freezeInputs(
    state: ProjectState,
    phaseId: string,
  ): Promise<Record<string, string>> {
    const hashes: Record<string, string> = {};
    hashes["phase"] = computeHash(phaseId);
    hashes["current_gate"] = computeHash(state.current_gate_id ?? "");
    hashes["completed_roles"] = computeHash(
      JSON.stringify(state.completed_roles ?? []),
    );
    hashes["active_role"] = computeHash(state.active_role ?? "");
    hashes["timestamp"] = computeHash(new Date().toISOString());
    return hashes;
  }

  /**
   * Update project state after phase execution — marks completed roles
   * and updates handoff metadata.
   */
  private async updateProjectState(
    phaseId: string,
    plan: PhasePlan,
    success: boolean,
  ): Promise<void> {
    const state = await loadState(this.projectRoot);
    const now = new Date().toISOString();

    if (success) {
      // Mark all roles in this phase as completed
      for (const step of plan.steps) {
        if (step.status === StepStatus.COMPLETE && !state.completed_roles.includes(step.role_id)) {
          state.completed_roles.push(step.role_id);
        }
      }
      state.last_handoff_at = now;
    }

    // Update active role to last executed step
    const lastStep = plan.steps[plan.steps.length - 1];
    if (lastStep) {
      state.active_role = lastStep.role_id;
      state.role_activated_at = now;
    }

    await saveState(this.projectRoot, state);
  }
}
