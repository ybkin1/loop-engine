export type GateStatus = "pending" | "passed" | "blocked" | "skipped";

export interface GateCondition {
  condition_id: string;
  type: "evidence_required" | "role_required" | "phase_required" | "manual_approval";
  description: string;
  params: Record<string, unknown>;
}

export interface GateDefinition {
  gate_id: string;
  name: string;
  description: string;
  conditions: GateCondition[];
  status: GateStatus;
  created_at: string;
  passed_at: string | null;
  blocked_reasons: string[];
}

export interface GatesRegistry {
  schema_version: number;
  gates: GateDefinition[];
}

export interface GateCheckResult {
  gate_id: string;
  status: "pass" | "block";
  conditions_total: number;
  conditions_met: number;
  missing_conditions: {
    condition_id: string;
    type: string;
    description: string;
    detail: string;
  }[];
}

export interface GateAdvanceResult {
  gate_id: string;
  success: boolean;
  previous_phase: string;
  new_phase: string;
  advanced_at: string;
  error?: string;
}
