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

// ── Phase → Role mapping ─────────────────────────────────

export const PHASE_ROLES: Record<string, string[]> = {
  requirements: ["R01"],
  architecture: ["R04", "R08"],
  planning: ["R05"],
  implementation: ["R06"],
  review: ["R09", "R07", "R08"],
  delivery: ["R03", "R10"],
};

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

// ── Phase → Gate mapping ─────────────────────────────────

const PHASE_GATE: Record<string, string> = {
  requirements: "gate-requirements",
  architecture: "gate-architecture",
  planning: "gate-planning",
  implementation: "gate-implementation",
  review: "gate-review",
  delivery: "gate-delivery",
};

// ── PhaseExecutor ────────────────────────────────────────

export class PhaseExecutor {
  constructor(private projectRoot: string) {}

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
      max_retries: 2,
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

    // ── 1. Validate current phase ──────────────────────
    const state = await loadState(this.projectRoot);
    if (state.current_phase !== phaseId) {
      throw new LoopError(
        "PHASE_MISMATCH",
        `Cannot execute phase '${phaseId}': current phase is '${state.current_phase}'`,
        phaseId,
      );
    }

    // ── 2. Build plan & freeze input hashes ────────────
    const plan = this.planPhase(phaseId);
    plan.input_hashes = await this.freezeInputs(state, phaseId);
    plan.status = StepStatus.RUNNING;
    plan.started_at = startedAt.toISOString();

    // ── 3. Execute each step sequentially ──────────────
    let stepsCompleted = 0;
    let stepsFailed = 0;

    for (const step of plan.steps) {
      step.status = StepStatus.RUNNING;
      step.started_at = new Date().toISOString();
      await this.persistState(plan);

      try {
        const result = await this.executeRole(step);

        step.completed_at = new Date().toISOString();

        if (result.status === StepStatus.COMPLETE) {
          // Validate output against required fields
          if (step.required_fields.length > 0 && result.output) {
            const validation = this.validateStep(step, result.output);
            if (!validation.valid) {
              step.status = StepStatus.FAILED;
              step.error = `Missing required fields: ${validation.missing_fields.join(", ")}`;
              stepsFailed++;
              errors.push(`[${step.role_id}] ${step.error}`);
              await this.persistState(plan);
              break;
            }
          }
          step.status = StepStatus.COMPLETE;
          step.verdict = "approved";
          stepsCompleted++;
        } else {
          step.status = StepStatus.FAILED;
          step.error = result.error ?? "Unknown error during role execution";
          stepsFailed++;
          errors.push(`[${step.role_id}] ${step.error}`);

          // Retry logic
          if (step.retries < step.max_retries) {
            step.retries++;
            step.status = StepStatus.PENDING;
            step.error = undefined;
            step.started_at = undefined;
            step.completed_at = undefined;
            // Retry immediately
            const retryResult = await this.executeRole(step);
            step.completed_at = new Date().toISOString();
            if (retryResult.status === StepStatus.COMPLETE) {
              step.status = StepStatus.COMPLETE;
              step.verdict = "approved";
              stepsFailed--;
              stepsCompleted++;
              errors.pop();
            } else {
              step.status = StepStatus.FAILED;
              step.error = retryResult.error ?? "Retry failed";
              errors.push(`[${step.role_id}] Retry ${step.retries} failed: ${step.error}`);
              break;
            }
          } else {
            break;
          }
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

    // ── 4. Finalize plan status ────────────────────────
    const completedAt = new Date();
    plan.completed_at = completedAt.toISOString();
    const allSucceeded = stepsFailed === 0 && stepsCompleted === plan.steps.length;
    plan.status = allSucceeded ? StepStatus.COMPLETE : StepStatus.FAILED;
    await this.persistState(plan);

    // ── 5. Advance gate if all steps succeeded ─────────
    if (allSucceeded) {
      try {
        const gateResult = await advanceGate(this.projectRoot, plan.gate_id);
        if (!gateResult.success) {
          errors.push(`Gate advance failed: ${gateResult.error ?? "unknown"}`);
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        errors.push(`Gate advance error: ${msg}`);
      }
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
   * This is a simulated execution — actual role work is driven by the
   * Skill system. Returns COMPLETE status with empty output by default.
   */
  async executeRole(step: RoleStep): Promise<RoleStepResult> {
    const startedAt = Date.now();

    // Simulate role execution: in a real system this would invoke the
    // Skill/agent pipeline. Here we mark the step as complete to allow
    // the engine flow to be exercised end-to-end.
    const output: Record<string, unknown> = {};

    // Populate expected output keys from required_fields so validation passes
    for (const field of step.required_fields) {
      output[field] = `generated_by_${step.role_id}`;
    }

    const durationMs = Date.now() - startedAt;

    return {
      role_id: step.role_id,
      status: StepStatus.COMPLETE,
      output,
      duration_ms: durationMs,
    };
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

  // ── Private helpers ──────────────────────────────────

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
