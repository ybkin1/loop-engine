/**
 * evidence-chain.ts — Evidence chain verification
 *
 * Reads chain.yaml (or scans evidence/ directory) and verifies:
 * - Each node file exists
 * - SHA-256 hash matches stored hash
 * - Causal dependencies are intact
 * - TTL freshness is valid
 *
 * Usage:
 *   npx tsx scripts/evidence-chain.ts [project_root] [--strict]
 */

import { readFileSync, writeFileSync, existsSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { createHash } from "node:crypto";
import { parseDocument } from "yaml";

// ── Types ──────────────────────────────────────────────
export interface ChainNode {
  id: string;
  type: string;
  file: string;
  expected_hash?: string;
  depends_on?: string[];
  required: boolean;
}

export interface NodeVerification {
  id: string;
  file_exists: boolean;
  hash_valid: boolean | null;  // null if no expected_hash
  hash_match: boolean | null;
  stored_hash: string | null;
  actual_hash: string | null;
  freshness: "fresh" | "stale" | "no_ttl" | "not_found";
  dependencies_ok: boolean;
  required: boolean;
  status: "ok" | "missing" | "tampered" | "expired" | "broken_dep";
}

export interface ChainReport {
  schema: "evidence_chain/v1";
  project_root: string;
  strict_mode: boolean;
  nodes: NodeVerification[];
  total_nodes: number;
  verified: number;
  failed: number;
  missing_required: number;
  overall: "PASS" | "BLOCKED";
  blocked_reasons: string[];
  timestamp: string;
}

// ── Helpers ────────────────────────────────────────────
function computeHash(content: string): string {
  return createHash("sha256").update(content, "utf-8").digest("hex");
}

function loadChainDefinition(projectRoot: string): ChainNode[] | null {
  const chainFile = join(projectRoot, ".ai", "chain.yaml");
  if (!existsSync(chainFile)) return null;

  try {
    const raw = readFileSync(chainFile, "utf-8");
    const parsed = parseDocument(raw).toJSON() as { nodes?: ChainNode[] };
    return parsed.nodes ?? null;
  } catch {
    return null;
  }
}

function scanEvidenceDirectory(projectRoot: string): ChainNode[] {
  const evDir = join(projectRoot, ".ai", "evidence");
  if (!existsSync(evDir)) return [];

  const nodes: ChainNode[] = [];
  const files = readdirSync(evDir).filter(f => f.endsWith(".yaml"));

  for (const f of files) {
    const filePath = join(evDir, f);
    try {
      const raw = readFileSync(filePath, "utf-8");
      const record = parseDocument(raw).toJSON() as {
        evidence_id?: string; type?: string; content_hash?: string;
        content?: string; depends_on?: string[]; ttl_seconds?: number | null;
        submitted_at?: string;
      };

      nodes.push({
        id: record.evidence_id ?? f.replace(".yaml", ""),
        type: record.type ?? "unknown",
        file: `.ai/evidence/${f}`,
        expected_hash: record.content_hash,
        depends_on: record.depends_on ?? [],
        required: true, // All evidence files are required by default
      });
    } catch {
      nodes.push({
        id: f.replace(".yaml", ""),
        type: "unknown",
        file: `.ai/evidence/${f}`,
        required: true,
      });
    }
  }

  return nodes;
}

function verifyNode(projectRoot: string, node: ChainNode, allNodes: Map<string, NodeVerification>): NodeVerification {
  const filePath = join(projectRoot, node.file);

  // Check file exists
  if (!existsSync(filePath)) {
    return {
      id: node.id, file_exists: false, hash_valid: null, hash_match: null,
      stored_hash: null, actual_hash: null, freshness: "not_found",
      dependencies_ok: false, required: node.required, status: "missing",
    };
  }

  // Read and verify hash
  const raw = readFileSync(filePath, "utf-8");
  const record = parseDocument(raw).toJSON() as {
    content?: string; content_hash?: string; ttl_seconds?: number | null;
    submitted_at?: string;
  };

  const actualHash = record.content ? computeHash(record.content) : null;
  let hashMatch: boolean | null = null;
  let hashValid: boolean | null = null;

  if (node.expected_hash && actualHash) {
    hashMatch = actualHash === node.expected_hash;
    hashValid = hashMatch;
  }

  // Check freshness
  let freshness: NodeVerification["freshness"] = "no_ttl";
  if (record.ttl_seconds !== null && record.ttl_seconds !== undefined && record.submitted_at) {
    const submittedAt = new Date(record.submitted_at).getTime();
    const expiresAt = submittedAt + record.ttl_seconds * 1000;
    freshness = Date.now() < expiresAt ? "fresh" : "stale";
  }

  // Check dependencies
  let depsOk = true;
  if (node.depends_on && node.depends_on.length > 0) {
    for (const depId of node.depends_on) {
      const dep = allNodes.get(depId);
      if (!dep || dep.status !== "ok") {
        depsOk = false;
        break;
      }
    }
  }

  // Determine status
  let status: NodeVerification["status"] = "ok";
  if (!hashValid && hashMatch === false) status = "tampered";
  else if (freshness === "stale") status = "expired";
  else if (!depsOk) status = "broken_dep";

  return {
    id: node.id,
    file_exists: true,
    hash_valid: hashValid,
    hash_match: hashMatch,
    stored_hash: node.expected_hash ?? null,
    actual_hash: actualHash,
    freshness,
    dependencies_ok: depsOk,
    required: node.required,
    status,
  };
}

// ── Main Runner ────────────────────────────────────────
export function runEvidenceChain(projectRoot: string, strict = false): ChainReport {
  const root = resolve(projectRoot);

  // Load chain definition or scan evidence directory
  let nodes = loadChainDefinition(root);
  if (!nodes) {
    nodes = scanEvidenceDirectory(root);
  }

  if (nodes.length === 0) {
    return {
      schema: "evidence_chain/v1",
      project_root: root,
      strict_mode: strict,
      nodes: [],
      total_nodes: 0,
      verified: 0,
      failed: 0,
      missing_required: 0,
      overall: strict ? "BLOCKED" : "PASS",
      blocked_reasons: strict ? ["No evidence chain found and strict mode enabled"] : [],
      timestamp: new Date().toISOString(),
    };
  }

  // First pass: verify all nodes (without dependency check)
  const nodeMap = new Map<string, NodeVerification>();
  const verifications: NodeVerification[] = [];

  for (const node of nodes) {
    const v = verifyNode(root, node, nodeMap);
    nodeMap.set(node.id, v);
    verifications.push(v);
  }

  // Second pass: re-check dependencies now that all nodes are verified
  for (let i = 0; i < verifications.length; i++) {
    const node = nodes[i];
    const v = verifications[i];
    if (node.depends_on && node.depends_on.length > 0 && v.status === "ok") {
      for (const depId of node.depends_on) {
        const dep = nodeMap.get(depId);
        if (!dep || dep.status !== "ok") {
          v.dependencies_ok = false;
          v.status = "broken_dep";
          break;
        }
      }
    }
  }

  const verified = verifications.filter(v => v.status === "ok").length;
  const failed = verifications.length - verified;
  const missingRequired = verifications.filter(v => v.status === "missing" && v.required).length;

  const blockedReasons: string[] = [];
  if (missingRequired > 0) {
    blockedReasons.push(`${missingRequired} required evidence files missing`);
  }
  const tampered = verifications.filter(v => v.status === "tampered");
  if (tampered.length > 0) {
    blockedReasons.push(`${tampered.length} evidence files tampered: ${tampered.map(v => v.id).join(", ")}`);
  }
  const brokenDeps = verifications.filter(v => v.status === "broken_dep");
  if (brokenDeps.length > 0) {
    blockedReasons.push(`${brokenDeps.length} broken dependencies: ${brokenDeps.map(v => v.id).join(", ")}`);
  }
  if (strict && failed > 0) {
    blockedReasons.push(`Strict mode: ${failed} nodes not verified`);
  }

  return {
    schema: "evidence_chain/v1",
    project_root: root,
    strict_mode: strict,
    nodes: verifications,
    total_nodes: verifications.length,
    verified,
    failed,
    missing_required: missingRequired,
    overall: blockedReasons.length > 0 ? "BLOCKED" : "PASS",
    blocked_reasons: blockedReasons,
    timestamp: new Date().toISOString(),
  };
}

// ── CLI ────────────────────────────────────────────────
if (process.argv[1]?.includes("evidence-chain")) {
  const root = process.argv[2] || process.cwd();
  const strict = process.argv.includes("--strict");

  const report = runEvidenceChain(root, strict);

  console.log(`\nEvidence Chain: ${report.overall} ${report.strict_mode ? "(STRICT)" : ""}`);
  console.log("=".repeat(50));
  console.log(`  Total nodes: ${report.total_nodes}`);
  console.log(`  Verified:    ${report.verified}`);
  console.log(`  Failed:      ${report.failed}`);
  console.log(`  Missing req: ${report.missing_required}`);
  console.log("");

  for (const n of report.nodes) {
    const icon = n.status === "ok" ? "✓" : "✗";
    console.log(`  ${icon} ${n.id.padEnd(24)} ${n.status.toUpperCase().padEnd(12)} ${n.file_exists ? "exists" : "MISSING"}`);
    if (n.hash_match === false) console.log(`      Hash mismatch!`);
    if (n.freshness === "stale") console.log(`      Evidence expired`);
    if (!n.dependencies_ok) console.log(`      Broken dependency`);
  }

  if (report.blocked_reasons.length > 0) {
    console.log(`\nBlocked:`);
    for (const r of report.blocked_reasons) console.log(`  - ${r}`);
  }

  const outPath = join(root, ".ai", "evidence_chain_report.json");
  writeFileSync(outPath, JSON.stringify(report, null, 2), "utf-8");
  console.log(`\nReport saved: ${outPath}`);

  process.exit(report.overall === "BLOCKED" ? 1 : 0);
}
