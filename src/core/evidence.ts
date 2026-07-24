import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, existsSync, mkdirSync, renameSync } from "node:fs";
import { join } from "node:path";
import { stringify } from "yaml";
import type {
  EvidenceRecord, EvidenceSubmitParams, EvidenceSubmitResult,
  EvidenceVerifyResult
} from "../types/index.js";
import { LoopError } from "./state-machine.js";

// ── Sanitize ───────────────────────────────────────────
function sanitizeId(id: string): string {
  if (!/^[a-zA-Z0-9_-]+$/.test(id)) {
    throw new LoopError("INVALID_ID", `ID contains invalid characters: ${id}. Only [a-zA-Z0-9_-] allowed.`, id);
  }
  return id;
}

function evDir(root: string) { return join(root, ".ai", "evidence"); }
function evFile(root: string, id: string) { return join(root, ".ai", "evidence", `${id}.yaml`); }

function atomicWrite(filePath: string, content: string): void {
  const tmp = filePath + ".tmp";
  writeFileSync(tmp, content, "utf-8");
  renameSync(tmp, filePath);
}

export function computeHash(content: string): string {
  return createHash("sha256").update(content, "utf-8").digest("hex");
}

export async function submitEvidence(root: string, params: EvidenceSubmitParams): Promise<EvidenceSubmitResult> {
  const id = sanitizeId(params.evidence_id);
  const dir = evDir(root);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });

  const hash = computeHash(params.content);
  const now = new Date().toISOString();

  const record: EvidenceRecord = {
    evidence_id: params.evidence_id,
    type: params.type,
    content: params.content,
    content_hash: hash,
    submitted_at: now,
    submitted_by: params.role_id ?? "unknown",
    gate_id: params.gate_id ?? null,
    role_id: params.role_id ?? null,
    ttl_seconds: params.ttl_seconds ?? null,
    depends_on: params.depends_on ?? [],
    metadata: params.metadata ?? {},
  };

  atomicWrite(evFile(root, id), stringify(record));

  return {
    success: true,
    evidence_id: id,
    content_hash: hash,
    stored_at: evFile(root, id),
    submitted_at: now,
  };
}

export async function verifyEvidence(root: string, evidenceId: string): Promise<EvidenceVerifyResult> {
  const id = sanitizeId(evidenceId);
  const file = evFile(root, id);
  if (!existsSync(file)) {
    throw new LoopError("EVIDENCE_NOT_FOUND", `Evidence not found: ${evidenceId}`, evidenceId);
  }

  const raw = readFileSync(file, "utf-8");
  const { parseDocument } = await import("yaml");
  const record = parseDocument(raw).toJSON() as EvidenceRecord;

  const currentHash = computeHash(record.content);
  const match = currentHash === record.content_hash;

  // Check freshness
  let freshness: EvidenceVerifyResult["freshness"] = "no_ttl";
  if (record.ttl_seconds !== null) {
    const submittedAt = new Date(record.submitted_at).getTime();
    const expiresAt = submittedAt + record.ttl_seconds * 1000;
    freshness = Date.now() < expiresAt ? "fresh" : "stale";
  }

  return {
    evidence_id: id,
    status: match ? (freshness === "stale" ? "expired" : "verified") : "tampered",
    content_hash: currentHash,
    stored_hash: record.content_hash,
    match,
    submitted_at: record.submitted_at,
    freshness,
  };
}

export async function loadEvidence(root: string, evidenceId: string): Promise<EvidenceRecord> {
  const id = sanitizeId(evidenceId);
  const file = evFile(root, id);
  if (!existsSync(file)) {
    throw new LoopError("EVIDENCE_NOT_FOUND", `Evidence not found: ${evidenceId}`, evidenceId);
  }
  const raw = readFileSync(file, "utf-8");
  const { parseDocument } = await import("yaml");
  return parseDocument(raw).toJSON() as EvidenceRecord;
}
