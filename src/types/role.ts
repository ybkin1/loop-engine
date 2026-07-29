export type RoleStatus = "inactive" | "active" | "completed" | "blocked";

/**
 * Role Contract — aligned with ZCode agents CONTRACT.yaml design.
 * Defines identity, responsibilities, prohibitions, veto power,
 * and quality standards for each role.
 */
export interface RoleIdentity {
  title: string;
  experience: string;
  expertise: string[];
  known_blind_spots: string[];
}

export interface RoleContract {
  role_id: string;
  identity: RoleIdentity;
  /** Immutable principles the role always holds */
  fixed_stance: string[];
  responsibilities: string[];
  prohibitions: string[];
  /** Situations where this role can veto */
  veto_power: string[];
  input_artifacts: string[];
  output_artifacts: string[];
  quality_standards: string[];
  /** Escalation rules when veto conflicts arise */
  veto_escalation: string[];
  /** Context projection rules for this role */
  projection_rules?: {
    include_sections: string[];
    exclude_sections: string[];
    role_dimensions: string[];
  };
}

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
  /** Full role contract (P0-A upgrade) */
  contract?: RoleContract;
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
