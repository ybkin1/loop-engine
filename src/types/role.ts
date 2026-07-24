export type RoleStatus = "inactive" | "active" | "completed" | "blocked";

export interface RoleSpec {
  role_id: string;
  name: string;
  description: string;
  prerequisites: {
    required_roles: string[];
    required_gates: string[];
    required_evidence: string[];
  };
  permissions: {
    allowed_operations: string[];
    allowed_write_paths: string[];
    forbidden_operations: string[];
  };
  handoff_artifacts: string[];
}

export interface RoleActivation {
  role_id: string;
  status: RoleStatus;
  activated_at: string | null;
  completed_at: string | null;
  activated_by: string;
  handoff_from: string | null;
}

export interface RoleActivateResult {
  success: boolean;
  role_id: string;
  status: RoleStatus;
  missing_prerequisites: string[];
  handoff_received: boolean;
  activated_at: string | null;
  error?: string;
}

export interface RoleStatusResult {
  role_id: string;
  status: RoleStatus;
  activated_at: string | null;
  completed_at: string | null;
  available_operations: string[];
  allowed_write_paths: string[];
}
