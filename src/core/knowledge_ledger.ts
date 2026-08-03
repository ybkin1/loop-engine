/**
 * knowledge_ledger.ts — Knowledge Sedimentation Ledger
 *
 * Append-only, chain-hashed ledger that captures lessons learned from
 * failures across the Loop Engineering lifecycle. Complements
 * ExecutionLedger (records "what happened") by recording "why it failed
 * and how it was fixed".
 *
 * Design principles:
 * - Chain-hashed (SHA-256) for tamper-evident integrity, matching
 *   ExecutionLedger and AuditLedger patterns
 * - Append-only JSONL storage at .ai/lessons/lessons.jsonl
 * - Auto-archiving when threshold exceeded
 * - Rich query API for pattern discovery
 * - Auto-categorization from constraint violations and error patterns
 *
 * @example
 * ```ts
 * const ledger = new KnowledgeLedger("/path/to/.ai/lessons/lessons.jsonl");
 * const lesson = ledger.capture({
 *   phase_id: "S4-implementation",
 *   role_id: "R06",
 *   category: LessonCategory.LOGIC_ERROR,
 *   severity: "BLOCKER",
 *   symptom: "Null reference in async pipeline",
 *   error_message: "TypeError: Cannot read property 'id' of undefined",
 *   tags: ["null-check", "async-await"],
 * });
 * ```
 */

import { createHash } from "node:crypto";
import {
  readFileSync,
  appendFileSync,
  existsSync,
  mkdirSync,
  renameSync,
} from "node:fs";
import { dirname, resolve } from "node:path";

import {
  LessonCategory,
  LessonStatus,
} from "../types/lesson.js";

import type {
  LessonRecord,
  LessonQuery,
  LessonCategoryStats,
  LessonPhaseStats,
  LessonStatistics,
  LessonIntegrity,
} from "../types/lesson.js";

// ── Constants ────────────────────────────────────────────────────────────────

/** The "genesis" previous-hash used for the very first entry. */
const GENESIS_PREV_HASH = "0".repeat(64);

/** Threshold for auto-archiving the ledger file. */
const ARCHIVE_THRESHOLD = 200;

// ── Helpers ──────────────────────────────────────────────────────────────────

function sha256(input: string): string {
  return createHash("sha256").update(input, "utf-8").digest("hex");
}

function computeChainHash(
  prevChainHash: string,
  seq: number,
  lessonId: string,
  phaseId: string,
  roleId: string,
  timestamp: string,
): string {
  const payload = `${prevChainHash}${seq}${lessonId}${phaseId}${roleId}${timestamp}`;
  return sha256(payload);
}

function ensureDir(filePath: string): void {
  const dir = dirname(filePath);
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
}

function readEntries(ledgerPath: string): LessonRecord[] {
  if (!existsSync(ledgerPath)) return [];
  const raw = readFileSync(ledgerPath, "utf-8");
  const entries: LessonRecord[] = [];
  for (const line of raw.split("\n")) {
    const trimmed = line.trim();
    if (trimmed.length === 0) continue;
    try {
      entries.push(JSON.parse(trimmed) as LessonRecord);
    } catch {
      // Skip malformed lines
    }
  }
  return entries;
}

function readAllEntries(ledgerPath: string): LessonRecord[] {
  const entries: LessonRecord[] = [];
  let archiveIdx = 1;
  while (existsSync(`${ledgerPath}.${archiveIdx}`)) {
    entries.push(...readEntries(`${ledgerPath}.${archiveIdx}`));
    archiveIdx++;
  }
  entries.push(...readEntries(ledgerPath));
  return entries;
}

function maybeArchive(ledgerPath: string): void {
  const entries = readEntries(ledgerPath);
  if (entries.length <= ARCHIVE_THRESHOLD) return;

  let nextIdx = 1;
  while (existsSync(`${ledgerPath}.${nextIdx}`)) {
    nextIdx++;
  }
  for (let i = nextIdx - 1; i >= 1; i--) {
    renameSync(`${ledgerPath}.${i}`, `${ledgerPath}.${i + 1}`);
  }
  renameSync(ledgerPath, `${ledgerPath}.1`);
}

// ── Input type for lesson capture (before chain fields are populated) ────────

/** Input fields for capturing a lesson (auto-generated fields omitted). */
export interface LessonInput {
  phase_id: string;
  role_id: string;
  task_id?: string;
  execution_id?: string;
  category: LessonCategory;
  severity: "BLOCKER" | "WARNING";
  symptom: string;
  error_message: string;
  constraint_violations?: string[];
  status?: LessonStatus;
  tags: string[];
}

// ── KnowledgeLedger ──────────────────────────────────────────────────────────

export class KnowledgeLedger {
  private readonly ledgerPath: string;
  private seqCounter: number;

  constructor(ledgerPath: string) {
    this.ledgerPath = resolve(ledgerPath);
    ensureDir(this.ledgerPath);
    // Initialize sequence counter from existing entries
    const entries = readAllEntries(this.ledgerPath);
    this.seqCounter = entries.length > 0
      ? Math.max(...entries.map(e => e.seq))
      : 0;
  }

  // ── Core: Capture ──────────────────────────────────────────────────────

  /**
   * Capture a new lesson from a failure event.
   *
   * Auto-generates lesson_id (lesson-<seq+1>), seq, chain_hash, timestamp.
   * The lesson starts with status OPEN unless overridden.
   *
   * @param input - The lesson data to capture
   * @returns The complete LessonRecord with chain fields populated
   */
  capture(input: LessonInput): LessonRecord {
    this.seqCounter++;
    const seq = this.seqCounter;
    const lessonId = `lesson-${String(seq).padStart(4, "0")}`;
    const timestamp = new Date().toISOString();

    // Read last entry for chain hash
    const mainEntries = readEntries(this.ledgerPath);
    const allEntries = readAllEntries(this.ledgerPath);
    const lastEntry = allEntries.length > 0 ? allEntries[allEntries.length - 1] : null;
    const prevChainHash = lastEntry?.chain_hash ?? GENESIS_PREV_HASH;

    const chainHash = computeChainHash(
      prevChainHash,
      seq,
      lessonId,
      input.phase_id,
      input.role_id,
      timestamp,
    );

    const record: LessonRecord = {
      lesson_id: lessonId,
      seq,
      chain_hash: chainHash,
      prev_chain_hash: prevChainHash,
      timestamp,
      phase_id: input.phase_id,
      role_id: input.role_id,
      task_id: input.task_id,
      execution_id: input.execution_id,
      category: input.category,
      severity: input.severity,
      symptom: input.symptom,
      error_message: input.error_message,
      constraint_violations: input.constraint_violations,
      status: input.status ?? LessonStatus.OPEN,
      tags: input.tags,
    };

    appendFileSync(this.ledgerPath, JSON.stringify(record) + "\n", "utf-8");

    try {
      maybeArchive(this.ledgerPath);
    } catch {
      // Non-fatal
    }

    return record;
  }

  /**
   * Capture a lesson from a constraint violation result.
   *
   * Automatically sets category=CONSTRAINT_VIOLATION and extracts
   * symptom/error_message from the violation details.
   *
   * @param phaseId - Phase where violation occurred
   * @param roleId - Role being executed
   * @param violations - Constraint violation messages (e.g. ["[C1] BLOCKER: ..."])
   * @param tags - Additional search tags
   * @returns The captured LessonRecord
   */
  captureFromViolations(
    phaseId: string,
    roleId: string,
    violations: string[],
    tags: string[] = [],
  ): LessonRecord | null {
    if (violations.length === 0) return null;

    const blockerViolations = violations.filter(v => v.includes("BLOCKER"));
    const severity = blockerViolations.length > 0 ? "BLOCKER" : "WARNING";

    // Extract constraint IDs from violation messages
    const constraintIds: string[] = [];
    for (const v of violations) {
      const match = v.match(/\[(C\d+)\]/);
      if (match) constraintIds.push(match[1]);
    }

    const symptom = violations.length === 1
      ? violations[0]
      : `${violations.length} constraint violations detected`;

    return this.capture({
      phase_id: phaseId,
      role_id: roleId,
      category: LessonCategory.CONSTRAINT_VIOLATION,
      severity,
      symptom,
      error_message: violations.join("; "),
      constraint_violations: constraintIds,
      tags: [...tags, "constraint-violation"],
    });
  }

  // ── Resolution ─────────────────────────────────────────────────────────

  /**
   * Mark a lesson as resolved with resolution details.
   *
   * Creates a new entry (not an in-place update) to preserve the chain.
   *
   * @param lessonId - The lesson to resolve
   * @param resolution - Description of how it was fixed
   * @param resolvedInPhase - Phase where the fix was applied
   * @returns The updated LessonRecord, or null if not found
   */
  resolve(
    lessonId: string,
    resolution: string,
    resolvedInPhase?: string,
  ): LessonRecord | null {
    const allEntries = readAllEntries(this.ledgerPath);
    const original = allEntries.find(e => e.lesson_id === lessonId);
    if (!original) return null;

    const resolvedAt = new Date().toISOString();

    // Create a new entry with RESOLVED status (preserving the chain)
    const input: LessonInput = {
      phase_id: resolvedInPhase ?? original.phase_id,
      role_id: original.role_id,
      task_id: original.task_id,
      execution_id: original.execution_id,
      category: original.category,
      severity: original.severity,
      symptom: original.symptom,
      error_message: original.error_message,
      constraint_violations: original.constraint_violations,
      status: LessonStatus.RESOLVED,
      tags: original.tags,
    };

    const record = this.capture(input);

    // Manually override auto-generated fields to carry forward resolution info
    // (We append a new entry but carry the resolution metadata)
    const resolvedRecord: LessonRecord = {
      ...record,
      resolution,
      resolved_at: resolvedAt,
      resolved_in_phase: resolvedInPhase,
    };

    // Re-write the last line of the ledger with resolution info
    // We read, replace last line, and write back
    const entries = readEntries(this.ledgerPath);
    if (entries.length > 0) {
      entries[entries.length - 1] = resolvedRecord;
      // Rebuild the file
      const { writeFileSync } = require("node:fs");
      writeFileSync(
        this.ledgerPath,
        entries.map(e => JSON.stringify(e)).join("\n") + "\n",
        "utf-8",
      );
    }

    return resolvedRecord;
  }

  /**
   * Resolve a lesson and compute the impact on project gates.
   *
   * This is the ECN (Engineering Change Notice) closure loop:
   * when a lesson is resolved, check which gates in the project might
   * be affected and should be re-evaluated.
   *
   * Impact rules:
   * - If the lesson is a CONSTRAINT_VIOLATION with specific C1-C8 IDs,
   *   the gate associated with those constraints should be re-checked.
   * - If the lesson's phase still has a pending/blocked gate, that gate
   *   should be re-evaluated.
   * - If the lesson's category is LOGIC_ERROR/DESIGN_FLAW and the
   *   resolution was applied in a different phase, both phases' gates
   *   should be reviewed.
   *
   * @param lessonId - The lesson to resolve
   * @param resolution - Description of how it was fixed
   * @param resolvedInPhase - Phase where the fix was applied
   * @param projectRoot - Project root for reading gates.yaml
   * @returns The resolved record plus a list of affected gate IDs
   */
  resolveWithImpact(
    lessonId: string,
    resolution: string,
    resolvedInPhase?: string,
    projectRoot?: string,
  ): { lesson: LessonRecord | null; affected_gates: string[]; should_recheck: boolean } {
    // Capture original lesson info before resolve (resolve() changes phase_id)
    const allEntries = readAllEntries(this.ledgerPath);
    const original = allEntries.find(e => e.lesson_id === lessonId);
    if (!original) {
      return { lesson: null, affected_gates: [], should_recheck: false };
    }
    const originalPhase = original.phase_id;
    const originalConstraints = original.constraint_violations;

    const lesson = this.resolve(lessonId, resolution, resolvedInPhase);
    if (!lesson) {
      return { lesson: null, affected_gates: [], should_recheck: false };
    }

    const affectedGates: string[] = [];

    // Rule 1: Constraint violations from ORIGINAL lesson → map to gate IDs
    if (originalConstraints && originalConstraints.length > 0) {
      const constraintToGate: Record<string, string> = {
        C1: "S1-requirements",
        C2: "S2-architecture",
        C5: "S5-quality",
        C6: "S4-implementation",
      };
      for (const cid of originalConstraints) {
        const gate = constraintToGate[cid];
        if (gate && !affectedGates.includes(gate)) {
          affectedGates.push(gate);
        }
      }
    }

    // Rule 2: The ORIGINAL lesson's phase gate should be re-checked
    if (!affectedGates.includes(originalPhase)) {
      affectedGates.push(originalPhase);
    }

    // Rule 3: If resolved in a different phase, that phase's gate also affected
    const actualResolvedPhase = resolvedInPhase ?? originalPhase;
    if (actualResolvedPhase !== originalPhase && !affectedGates.includes(actualResolvedPhase)) {
      affectedGates.push(actualResolvedPhase);
    }

    // Read actual gates from project if available
    const actualGates: string[] = [];
    if (projectRoot) {
      try {
        const { readFileSync, existsSync } = require("node:fs");
        const { resolve: resolvePath } = require("node:path");
        const gatesPath = resolvePath(projectRoot, ".ai/gates.yaml");
        if (existsSync(gatesPath)) {
          const raw = readFileSync(gatesPath, "utf-8");
          // Simple YAML parsing: extract gate IDs
          const gateIdMatches = raw.matchAll(/^\s*-\s*gate_id:\s*"?([^"\n]+)"?/gm);
          for (const m of gateIdMatches) {
            actualGates.push(m[1]);
          }
        }
      } catch {
        // Best effort
      }
    }

    // Cross-reference affected gates with actual project gates
    const matchedGates = affectedGates.filter(ag =>
      actualGates.length === 0 || actualGates.some(g => g.includes(ag) || ag.includes(g)),
    );

    // Determine if re-check is needed (BLOCKER lessons always need re-check)
    const shouldRecheck = lesson.severity === "BLOCKER" ||
      lesson.category === LessonCategory.CONSTRAINT_VIOLATION;

    return {
      lesson,
      affected_gates: matchedGates.length > 0 ? matchedGates : affectedGates,
      should_recheck: shouldRecheck,
    };
  }

  /**
   * Update the status of a lesson (OPEN → ACKNOWLEDGED, etc.).
   * Creates a new entry in the ledger.
   */
  updateStatus(lessonId: string, newStatus: LessonStatus): LessonRecord | null {
    const allEntries = readAllEntries(this.ledgerPath);
    const original = allEntries.find(e => e.lesson_id === lessonId);
    if (!original) return null;

    return this.capture({
      phase_id: original.phase_id,
      role_id: original.role_id,
      task_id: original.task_id,
      execution_id: original.execution_id,
      category: original.category,
      severity: original.severity,
      symptom: original.symptom,
      error_message: original.error_message,
      constraint_violations: original.constraint_violations,
      status: newStatus,
      tags: original.tags,
    });
  }

  // ── Query ──────────────────────────────────────────────────────────────

  /**
   * Query lessons with optional filters.
   *
   * @param query - Filter criteria
   * @returns Matching LessonRecords, newest first
   */
  query(query: LessonQuery = {}): LessonRecord[] {
    let entries = readAllEntries(this.ledgerPath);

    if (query.phase_id) {
      entries = entries.filter(e => e.phase_id === query.phase_id);
    }
    if (query.role_id) {
      entries = entries.filter(e => e.role_id === query.role_id);
    }
    if (query.category) {
      entries = entries.filter(e => e.category === query.category);
    }
    if (query.status) {
      entries = entries.filter(e => e.status === query.status);
    }
    if (query.severity) {
      entries = entries.filter(e => e.severity === query.severity);
    }
    if (query.tags && query.tags.length > 0) {
      entries = entries.filter(e =>
        query.tags!.some(t => e.tags.includes(t)),
      );
    }
    if (query.since) {
      const sinceTs = new Date(query.since).getTime();
      entries = entries.filter(e => new Date(e.timestamp).getTime() >= sinceTs);
    }

    // Newest first
    entries.sort((a, b) => b.seq - a.seq);

    if (query.limit && query.limit > 0) {
      entries = entries.slice(0, query.limit);
    }

    return entries;
  }

  /**
   * Find similar lessons based on tag overlap and same category.
   *
   * @param lessonId - Reference lesson to find similars for
   * @param maxResults - Maximum number of results (default 5)
   * @returns Similar lessons sorted by relevance (tag overlap count)
   */
  findSimilar(lessonId: string, maxResults = 5): LessonRecord[] {
    const allEntries = readAllEntries(this.ledgerPath);
    const reference = allEntries.find(e => e.lesson_id === lessonId);
    if (!reference) return [];

    const candidates = allEntries.filter(e => e.lesson_id !== lessonId);

    // Score by: same category (weight 3) + tag overlap (weight 1 per tag)
    const scored = candidates.map(e => {
      let score = 0;
      if (e.category === reference.category) score += 3;
      if (e.phase_id === reference.phase_id) score += 2;
      const tagOverlap = e.tags.filter(t => reference.tags.includes(t)).length;
      score += tagOverlap;
      return { entry: e, score };
    });

    scored.sort((a, b) => b.score - a.score);
    return scored.slice(0, maxResults).map(s => s.entry);
  }

  /**
   * Find all open (unresolved) lessons.
   */
  findOpen(): LessonRecord[] {
    return this.query({ status: LessonStatus.OPEN });
  }

  /**
   * Find lessons that are likely related to a given error message
   * by substring matching against error_message and symptom fields.
   */
  searchByError(errorFragment: string, maxResults = 10): LessonRecord[] {
    const allEntries = readAllEntries(this.ledgerPath);
    const lower = errorFragment.toLowerCase();
    const matches = allEntries.filter(e =>
      e.error_message.toLowerCase().includes(lower) ||
      e.symptom.toLowerCase().includes(lower),
    );
    matches.sort((a, b) => b.seq - a.seq);
    return matches.slice(0, maxResults);
  }

  // ── Statistics ─────────────────────────────────────────────────────────

  /**
   * Compute aggregate statistics for the knowledge ledger.
   */
  getStatistics(): LessonStatistics {
    const entries = readAllEntries(this.ledgerPath);

    const open = entries.filter(e => e.status === LessonStatus.OPEN || e.status === LessonStatus.ACKNOWLEDGED).length;
    const resolved = entries.filter(e => e.status === LessonStatus.RESOLVED).length;

    // By category
    const categoryMap = new Map<LessonCategory, { count: number; resolved: number; open: number }>();
    for (const e of entries) {
      const stat = categoryMap.get(e.category) ?? { count: 0, resolved: 0, open: 0 };
      stat.count++;
      if (e.status === LessonStatus.RESOLVED) stat.resolved++;
      if (e.status === LessonStatus.OPEN || e.status === LessonStatus.ACKNOWLEDGED) stat.open++;
      categoryMap.set(e.category, stat);
    }
    const by_category: LessonCategoryStats[] = [];
    for (const [category, stat] of categoryMap) {
      by_category.push({ category, ...stat });
    }
    by_category.sort((a, b) => b.count - a.count);

    // By phase
    const phaseMap = new Map<string, { count: number; blocker_count: number; warning_count: number }>();
    for (const e of entries) {
      const stat = phaseMap.get(e.phase_id) ?? { count: 0, blocker_count: 0, warning_count: 0 };
      stat.count++;
      if (e.severity === "BLOCKER") stat.blocker_count++;
      if (e.severity === "WARNING") stat.warning_count++;
      phaseMap.set(e.phase_id, stat);
    }
    const by_phase: LessonPhaseStats[] = [];
    for (const [phase_id, stat] of phaseMap) {
      by_phase.push({ phase_id, ...stat });
    }
    by_phase.sort((a, b) => b.count - a.count);

    return {
      total: entries.length,
      open,
      resolved,
      by_category,
      by_phase,
    };
  }

  // ── Integrity ──────────────────────────────────────────────────────────

  /**
   * Verify the chain-hash integrity of the entire ledger.
   */
  verifyChain(): LessonIntegrity {
    const entries = readAllEntries(this.ledgerPath);

    if (entries.length === 0) {
      return { valid: true, firstInvalidSeq: null, totalEntries: 0 };
    }

    let prevHash = GENESIS_PREV_HASH;

    for (const entry of entries) {
      const expectedHash = computeChainHash(
        prevHash,
        entry.seq,
        entry.lesson_id,
        entry.phase_id,
        entry.role_id,
        entry.timestamp,
      );

      if (expectedHash !== entry.chain_hash) {
        return {
          valid: false,
          firstInvalidSeq: entry.seq,
          totalEntries: entries.length,
        };
      }

      prevHash = entry.chain_hash;
    }

    return { valid: true, firstInvalidSeq: null, totalEntries: entries.length };
  }

  // ── Utility ────────────────────────────────────────────────────────────

  /**
   * Get the most recent N entries.
   */
  recent(n: number): LessonRecord[] {
    const entries = readEntries(this.ledgerPath);
    if (n <= 0) return [];
    return entries.slice(-n);
  }

  /** Total entries in the main ledger file. */
  get length(): number {
    return readEntries(this.ledgerPath).length;
  }

  /** Absolute path to the ledger file. */
  get path(): string {
    return this.ledgerPath;
  }

  /** Get a single lesson by ID. */
  get(lessonId: string): LessonRecord | undefined {
    return readAllEntries(this.ledgerPath).find(e => e.lesson_id === lessonId);
  }

  /**
   * Auto-categorize an error based on simple heuristics.
   * Useful for suggesting a category when capturing a lesson.
   */
  static suggestCategory(errorMessage: string): LessonCategory {
    const lower = errorMessage.toLowerCase();

    if (lower.includes("constraint") || lower.includes("c1") || lower.includes("c2") ||
        lower.includes("c3") || lower.includes("c4") || lower.includes("c5") ||
        lower.includes("c6") || lower.includes("c7") || lower.includes("c8")) {
      return LessonCategory.CONSTRAINT_VIOLATION;
    }
    if (lower.includes("typeerror") || lower.includes("null") || lower.includes("undefined") ||
        lower.includes("cannot read") || lower.includes("is not a function")) {
      return LessonCategory.LOGIC_ERROR;
    }
    if (lower.includes("import") || lower.includes("module") || lower.includes("export") ||
        lower.includes("circular") || lower.includes("dependency")) {
      return LessonCategory.DESIGN_FLAW;
    }
    if (lower.includes("test") && (lower.includes("fail") || lower.includes("missing"))) {
      return LessonCategory.TEST_GAP;
    }
    if (lower.includes("security") || lower.includes("injection") || lower.includes("xss") ||
        lower.includes("csrf") || lower.includes("auth")) {
      return LessonCategory.SECURITY_GAP;
    }
    if (lower.includes("timeout") || lower.includes("slow") || lower.includes("memory") ||
        lower.includes("performance")) {
      return LessonCategory.PERFORMANCE_ISSUE;
    }
    if (lower.includes("phase") || lower.includes("gate") || lower.includes("handoff") ||
        lower.includes("role") || lower.includes("state")) {
      return LessonCategory.PROCESS_GAP;
    }

    return LessonCategory.OTHER;
  }
}
