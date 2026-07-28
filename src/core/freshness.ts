import type { EvidenceRecord } from "../types/index.js";
import { loadEvidence } from "./evidence.js";
import { LoopError } from "./state-machine.js";
import { readdirSync, existsSync } from "node:fs";
import { join } from "node:path";

export interface FreshnessResult {
  evidence_id: string;
  status: "fresh" | "stale" | "no_ttl" | "not_found";
  detail: string;
  ttl_remaining_seconds: number | null;
}

export interface CausalChainResult {
  evidence_id: string;
  valid: boolean;
  chain: { evidence_id: string; status: "ok" | "missing" | "expired" }[];
  broken_links: string[];
}

export async function checkFreshness(root: string, evidenceId: string): Promise<FreshnessResult> {
  let record: EvidenceRecord;
  try {
    record = await loadEvidence(root, evidenceId);
  } catch {
    return { evidence_id: evidenceId, status: "not_found", detail: "Evidence file not found", ttl_remaining_seconds: null };
  }

  if (record.ttl_seconds === null) {
    return { evidence_id: evidenceId, status: "no_ttl", detail: "No TTL configured — evidence never expires", ttl_remaining_seconds: null };
  }

  const submittedAt = new Date(record.submitted_at).getTime();
  const expiresAt = submittedAt + record.ttl_seconds * 1000;
  const rawRemaining = Math.floor((expiresAt - Date.now()) / 1000);

  if (rawRemaining <= 0) {
    return { evidence_id: evidenceId, status: "stale", detail: `Evidence expired ${Math.abs(rawRemaining)}s ago`, ttl_remaining_seconds: 0 };
  }

  return { evidence_id: evidenceId, status: "fresh", detail: `Valid for ${rawRemaining}s more`, ttl_remaining_seconds: rawRemaining };
}

export async function checkCausalChain(root: string, evidenceId: string): Promise<CausalChainResult> {
  const chain: CausalChainResult["chain"] = [];
  const broken: string[] = [];
  const visited = new Set<string>();

  async function walk(id: string): Promise<void> {
    if (visited.has(id)) return;
    visited.add(id);

    let record: EvidenceRecord;
    try {
      record = await loadEvidence(root, id);
    } catch {
      chain.push({ evidence_id: id, status: "missing" });
      broken.push(id);
      return;
    }

    // Check if this evidence is fresh
    let status: "ok" | "expired" = "ok";
    if (record.ttl_seconds !== null) {
      const submittedAt = new Date(record.submitted_at).getTime();
      const expiresAt = submittedAt + record.ttl_seconds * 1000;
      if (Date.now() >= expiresAt) status = "expired";
    }

    chain.push({ evidence_id: id, status });
    if (status === "expired") broken.push(id);

    // Walk dependencies
    for (const dep of record.depends_on) {
      await walk(dep);
    }
  }

  await walk(evidenceId);

  return { evidence_id: evidenceId, valid: broken.length === 0, chain, broken_links: broken };
}

// ── Batch Operations ─────────────────────────────────────────────────

/** Summary of freshness state across all evidence in a project. */
export interface FreshnessSummary {
  total: number;
  fresh: number;
  stale: number;
  no_ttl: number;
  not_found: number;
  /** IDs of stale evidence */
  stale_ids: string[];
  /** Overall health: true if no stale evidence */
  healthy: boolean;
}

/**
 * List all evidence IDs in a project by scanning the evidence directory.
 */
export function listEvidenceIds(root: string): string[] {
  const dir = join(root, ".ai", "evidence");
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter(f => f.endsWith(".yaml"))
    .map(f => f.replace(/\.yaml$/, ""));
}

/**
 * Check freshness of all evidence in a project.
 * Returns an array of FreshnessResult for each evidence file found.
 */
export async function checkAllFreshness(root: string): Promise<FreshnessResult[]> {
  const ids = listEvidenceIds(root);
  const results: FreshnessResult[] = [];
  for (const id of ids) {
    results.push(await checkFreshness(root, id));
  }
  return results;
}

/**
 * Get a summary of evidence freshness across the project.
 * Useful for governance dashboards and health checks.
 */
export async function getFreshnessSummary(root: string): Promise<FreshnessSummary> {
  const results = await checkAllFreshness(root);

  const fresh = results.filter(r => r.status === "fresh").length;
  const stale = results.filter(r => r.status === "stale").length;
  const noTtl = results.filter(r => r.status === "no_ttl").length;
  const notFound = results.filter(r => r.status === "not_found").length;
  const staleIds = results.filter(r => r.status === "stale").map(r => r.evidence_id);

  return {
    total: results.length,
    fresh,
    stale,
    no_ttl: noTtl,
    not_found: notFound,
    stale_ids: staleIds,
    healthy: stale === 0,
  };
}
