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
}

export interface PhaseRecord {
  phase_id: string;
  entered_at: string;
  exited_at: string | null;
  status: "active" | "completed" | "skipped";
}

export interface StateStore {
  load(projectRoot: string): Promise<ProjectState>;
  save(projectRoot: string, state: ProjectState): Promise<void>;
}
