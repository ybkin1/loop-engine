/**
 * Phase IDs for the extended 12-phase state machine.
 * Aligned with ZCode loop_core/state_machine.py Phase enum.
 */
export type PhaseId =
  | "S0-init"
  | "S1-requirements"
  | "S2-architecture"
  | "S3-interface"
  | "S4-implementation"
  | "S5-quality"
  | "S6-delivery"
  | "S7-integration"
  | "S8-functional-test"
  | "S9-fix-optimize"
  | "S10-performance"
  | "S11-maintenance";

/** Legacy 6-phase IDs (backward compatible) */
export type LegacyPhaseId =
  | "requirements"
  | "architecture"
  | "planning"
  | "implementation"
  | "review"
  | "delivery";

export type PhaseStatus = "pending" | "active" | "completed" | "skipped" | "blocked";

/** Project lifecycle status (iteration support) */
export type ProjectStatus = "draft" | "released" | "maintenance";

/** Loop mode determines governance depth */
export type LoopMode = "FULL" | "STANDARD" | "LITE" | "HOTFIX";

export interface PhaseRecord {
  phase_id: string;
  entered_at: string;
  exited_at: string | null;
  status: PhaseStatus;
  /** Roles activated during this phase */
  roles_active?: string[];
  /** Gate ID associated with this phase */
  gate_id?: string;
}

/**
 * Explicit human approval record for a manual_approval gate condition.
 * Only the user (or an explicitly delegated actor) may create these.
 */
export interface UserApproval {
  gate_id: string;
  approved_by: string;
  approved_at: string;
  /** Optional note from the approving user */
  note?: string;
}

export interface ProjectState {
  schema_version: number;
  project_name: string;
  current_phase: string;
  current_task_id: string | null;
  current_gate_id: string | null;
  active_role: string | null;
  role_activated_at: string | null;
  completed_roles: string[];
  last_handoff_at: string;
  phases: PhaseRecord[];
  /** Loop governance mode */
  loop_mode?: LoopMode;
  /** Project lifecycle status */
  project_status?: ProjectStatus;
  /** Iteration number for maintenance cycles */
  iteration?: number;
  /** Explicit user approvals: gate_id → approval record (manual_approval conditions) */
  user_approvals?: Record<string, UserApproval>;
}

export interface StateStore {
  load(projectRoot: string): Promise<ProjectState>;
  save(projectRoot: string, state: ProjectState): Promise<void>;
}
