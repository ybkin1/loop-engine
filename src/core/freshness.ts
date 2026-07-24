import type { EvidenceRecord } from "../types/index.js";
import { loadEvidence } from "./evidence.js";
import { LoopError } from "./state-machine.js";

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
