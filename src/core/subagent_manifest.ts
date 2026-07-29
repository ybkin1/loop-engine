/**
 * subagent_manifest.ts — Subagent Manifest Protocol
 *
 * Aligned with ZCode loop_core/subagent_manifest.py design.
 * Enables role agents to decompose complex tasks into parallel sub-tasks.
 *
 * Architecture:
 *   Role Agent -> produces SubagentManifest
 *   Main Thread -> reads Manifest, schedules sub-agents, collects results
 *   Role Agent -> receives aggregated results, produces final output
 */

import { createHash } from "node:crypto";
import type {
  SubagentSpec,
  SubagentManifest,
  SubagentResult,
  ManifestExecutionResult,
} from "../types/index.js";

// ── Manifest Creation ──────────────────────────────────

let manifestCounter = 0;

export function createManifest(
  producerRole: string,
  purpose: string,
  subagents: SubagentSpec[],
  aggregationPrompt: string,
  maxParallel = 3,
): SubagentManifest {
  manifestCounter++;
  const id = `manifest-${Date.now()}-${manifestCounter}`;
  return {
    manifest_id: id,
    producer_role: producerRole,
    purpose,
    subagents,
    max_parallel_subagents: maxParallel,
    aggregation_prompt: aggregationPrompt,
    created_at: new Date().toISOString(),
  };
}

export function createSubagentSpec(
  id: string,
  roleHint: string,
  prompt: string,
  options: Partial<Pick<SubagentSpec, "input_files" | "expected_output_schema" | "max_parallel" | "timeout_seconds" | "retry_on_failure">> = {},
): SubagentSpec {
  return {
    subagent_id: id,
    role_hint: roleHint,
    prompt,
    input_files: options.input_files ?? [],
    expected_output_schema: options.expected_output_schema,
    max_parallel: options.max_parallel ?? true,
    timeout_seconds: options.timeout_seconds ?? 300,
    retry_on_failure: options.retry_on_failure ?? true,
  };
}

// ── Execution Planning ─────────────────────────────────

/**
 * Plan execution batches considering parallelism and dependencies.
 * Sub-agents with max_parallel=true are grouped into batches.
 * Sub-agents with max_parallel=false each get their own batch (serial).
 */
export function planExecution(manifest: SubagentManifest): SubagentSpec[][] {
  const parallel: SubagentSpec[] = [];
  const serial: SubagentSpec[] = [];

  for (const spec of manifest.subagents) {
    if (spec.max_parallel) {
      parallel.push(spec);
    } else {
      serial.push(spec);
    }
  }

  const batches: SubagentSpec[][] = [];
  const maxParallel = manifest.max_parallel_subagents;

  // Group parallel subagents into batches
  for (let i = 0; i < parallel.length; i += maxParallel) {
    batches.push(parallel.slice(i, i + maxParallel));
  }

  // Serial subagents each get their own batch
  for (const spec of serial) {
    batches.push([spec]);
  }

  return batches;
}

// ── Result Validation ──────────────────────────────────

export interface ValidationResult {
  is_valid: boolean;
  message: string;
}

/**
 * Validate sub-agent output against expectations.
 * Checks: status, non-empty output, schema conformance.
 */
export function validateResult(spec: SubagentSpec, result: SubagentResult): ValidationResult {
  if (result.status !== "completed") {
    return {
      is_valid: false,
      message: `Subagent '${spec.subagent_id}' did not complete (status: ${result.status})`,
    };
  }

  if (!result.output || !result.output.trim()) {
    return {
      is_valid: false,
      message: `Subagent '${spec.subagent_id}' produced empty output`,
    };
  }

  if (spec.expected_output_schema) {
    try {
      const outputJson = JSON.parse(result.output);
      const schemaProperties = (spec.expected_output_schema as Record<string, unknown>).properties as Record<string, unknown> | undefined;
      if (schemaProperties) {
        const requiredFields = (spec.expected_output_schema as Record<string, unknown>).required as string[] | undefined
          ?? Object.keys(schemaProperties);
        const missing = requiredFields.filter(f => !(f in outputJson));
        if (missing.length > 0) {
          return {
            is_valid: false,
            message: `Subagent '${spec.subagent_id}' output missing required fields: ${missing.join(", ")}`,
          };
        }
      }
    } catch (e) {
      return {
        is_valid: false,
        message: `Subagent '${spec.subagent_id}' output is not valid JSON: ${e}`,
      };
    }
  }

  return { is_valid: true, message: "OK" };
}

// ── Result Aggregation ─────────────────────────────────

/**
 * Generate an aggregation prompt for the Role Agent.
 * Includes original instructions + each sub-agent's results.
 */
export function aggregateResults(manifest: SubagentManifest, results: SubagentResult[]): string {
  const lines: string[] = [];
  lines.push("## Aggregation Instructions");
  lines.push("");
  lines.push(manifest.aggregation_prompt);
  lines.push("");
  lines.push("---");
  lines.push("");
  lines.push("## Sub-agent Results");
  lines.push("");

  for (let i = 0; i < results.length; i++) {
    const result = results[i];
    lines.push(`### ${i + 1}. Sub-agent: ${result.subagent_id}`);
    lines.push(`Status: ${result.status}`);
    if (result.error_message) {
      lines.push(`Error: ${result.error_message}`);
    }
    if (result.exit_code !== undefined) {
      lines.push(`Exit code: ${result.exit_code}`);
    }
    lines.push("");
    lines.push("**Output:**");
    lines.push("```");
    lines.push(result.output);
    lines.push("```");
    lines.push("");
  }

  lines.push("---");
  lines.push("");
  lines.push(
    "Based on the above sub-agent results and the aggregation " +
    "instructions, produce a consolidated summary. If any sub-agents " +
    "failed, note the failures and their impact on the overall task.",
  );

  return lines.join("\n");
}

// ── Full Execution Result ──────────────────────────────

export function buildExecutionResult(
  manifest: SubagentManifest,
  results: SubagentResult[],
): ManifestExecutionResult {
  const completed = results.filter(r => r.status === "completed").length;
  const failed = results.filter(r => r.status === "failed").length;
  const aggregated = aggregateResults(manifest, results);

  const hash = createHash("sha256")
    .update(JSON.stringify(results.map(r => ({ id: r.subagent_id, output: r.output }))))
    .digest("hex");

  return {
    manifest_id: manifest.manifest_id,
    total_subagents: results.length,
    completed,
    failed,
    results,
    aggregated_output: aggregated,
    content_hash: hash,
  };
}

// ── Manifest Integrity ─────────────────────────────────

export function computeManifestHash(manifest: SubagentManifest): string {
  const hasher = createHash("sha256");
  hasher.update(manifest.manifest_id);
  hasher.update(manifest.producer_role);
  hasher.update(manifest.purpose);
  for (const spec of manifest.subagents) {
    hasher.update(spec.subagent_id);
    hasher.update(spec.prompt);
  }
  hasher.update(manifest.aggregation_prompt);
  return hasher.digest("hex");
}
