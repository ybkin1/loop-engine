/**
 * SubagentManifest types — aligned with ZCode loop_core/subagent_manifest.py
 *
 * Architecture:
 *   Role Agent -> produces SubagentManifest
 *   Main Thread -> reads Manifest, schedules sub-agents, collects results
 *   Role Agent -> receives aggregated results, produces final output
 */

export type SubagentStatus = "pending" | "dispatched" | "running" | "completed" | "failed";

export interface SubagentSpec {
  subagent_id: string;
  role_hint: string;
  prompt: string;
  input_files: string[];
  expected_output_schema?: Record<string, unknown>;
  max_parallel: boolean;
  timeout_seconds: number;
  retry_on_failure: boolean;
}

export interface SubagentManifest {
  manifest_id: string;
  producer_role: string;
  purpose: string;
  subagents: SubagentSpec[];
  max_parallel_subagents: number;
  aggregation_prompt: string;
  created_at: string;
}

export interface SubagentResult {
  subagent_id: string;
  status: SubagentStatus;
  output: string;
  error_message?: string;
  exit_code?: number;
  started_at?: string;
  completed_at?: string;
}

export interface ManifestExecutionResult {
  manifest_id: string;
  total_subagents: number;
  completed: number;
  failed: number;
  results: SubagentResult[];
  aggregated_output: string;
  content_hash: string;
}
