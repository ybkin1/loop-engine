/**
 * execution_ledger.ts — Chain-Hashed Execution Ledger
 *
 * Records Agent/role execution with chain-hashed integrity.
 * Complements audit_ledger.ts (event ledger) by focusing on
 * execution-level records: role launches, completions, violations.
 *
 * Ported from ZCode loop_core/execution_ledger.py.
 */

import {
  appendFileSync,
} from "node:fs";
import { resolve } from "node:path";
import {
  sha256,
  chainHashFields,
  ensureDir,
  readJsonlEntries,
  readAllArchivedEntries,
  maybeArchive,
  GENESIS_HASH_LONG,
  DEFAULT_ARCHIVE_THRESHOLD,
} from "./chain_ledger_utils.js";

// ── ExecutionStatus ──────────────────────────────────────────────────────────

export enum ExecutionStatus {
  LAUNCHED = "LAUNCHED",
  COMPLETED = "COMPLETED",
  FAILED = "FAILED",
  VIOLATED = "VIOLATED",
}

// ── ExecutionRecord ──────────────────────────────────────────────────────────

export interface ExecutionRecord {
  execution_id: string;
  session_id: string;
  actor_id: string;
  role_id: string;
  task_id: string;
  /** SHA-256 of prompt */
  prompt_fingerprint: string;
  /** SHA-256 of input files list */
  input_files_hash: string;
  status: ExecutionStatus;
  /** Constraints applied */
  tool_constraints: string[];
  /** Violations detected */
  tool_violations: string[];
  /** Path to output */
  output_artifact?: string;
  started_at: string;
  completed_at?: string;
  /** Chain hash fields (auto-computed) */
  seq?: number;
  chain_hash?: string;
  prev_chain_hash?: string;
}

// ── ExecutionIntegrity ───────────────────────────────────────────────────────

export interface ExecutionIntegrity {
  valid: boolean;
  firstInvalidSeq: number | null;
  totalEntries: number;
}

// ── CrossValidation ──────────────────────────────────────────────────────────

export interface CrossValidation {
  task_id: string;
  developer_id: string;
  reviewer_id: string;
  is_independent: boolean;
  developer_sessions: string[];
  reviewer_sessions: string[];
}

// ── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Compute the chain_hash for an execution record.
 *
 * chain_hash = SHA-256(prev_chain_hash + seq + execution_id + role_id + status + started_at)
 */
function computeChainHash(
  prevChainHash: string,
  seq: number,
  executionId: string,
  roleId: string,
  status: ExecutionStatus,
  startedAt: string,
): string {
  return chainHashFields(prevChainHash, seq, executionId, roleId, status, startedAt);
}

const readEntries = readJsonlEntries<ExecutionRecord>;
const readAllEntries = readAllArchivedEntries<ExecutionRecord>;

// ── ExecutionLedger ──────────────────────────────────────────────────────────

/**
 * Append-only, chain-hashed execution ledger.
 *
 * Records Agent/role execution lifecycle: launches, completions, failures,
 * and violations. Each entry is linked via SHA-256 chain hashes for
 * tamper-evident integrity.
 *
 * @example
 * ```ts
 * const ledger = new ExecutionLedger("/path/to/execution.jsonl");
 * const launch = ledger.recordLaunch({
 *   execution_id: "exec-001",
 *   session_id: "sess-001",
 *   actor_id: "agent-1",
 *   role_id: "R06",
 *   task_id: "task-001",
 *   prompt_fingerprint: "abc123...",
 *   input_files_hash: "def456...",
 *   tool_constraints: ["no_network"],
 *   tool_violations: [],
 * });
 * ```
 */
export class ExecutionLedger {
  /** Resolved absolute path to the ledger file. */
  private readonly ledgerPath: string;

  /**
   * Create or open an execution ledger.
   *
   * @param ledgerPath - Path to the JSONL ledger file. Parent directories
   *                     are created automatically if they do not exist.
   */
  constructor(ledgerPath: string) {
    this.ledgerPath = resolve(ledgerPath);
    ensureDir(this.ledgerPath);
  }

  /**
   * Append an entry with auto chain_hash computation.
   *
   * Reads the last entry to determine prev_chain_hash, computes the new
   * seq and chain_hash, then appends the record to the file.
   *
   * @param record - The execution record (without seq/chain_hash/prev_chain_hash)
   * @returns The complete execution record with chain fields populated
   */
  appendEntry(record: ExecutionRecord): ExecutionRecord {
    const entries = readEntries(this.ledgerPath);
    const lastEntry = entries.length > 0 ? entries[entries.length - 1] : null;

    const seq = lastEntry && lastEntry.seq ? lastEntry.seq + 1 : 1;
    const prevChainHash = lastEntry?.chain_hash ?? GENESIS_HASH_LONG;

    const chainHash = computeChainHash(
      prevChainHash,
      seq,
      record.execution_id,
      record.role_id,
      record.status,
      record.started_at,
    );

    const fullRecord: ExecutionRecord = {
      ...record,
      seq,
      chain_hash: chainHash,
      prev_chain_hash: prevChainHash,
    };

    appendFileSync(this.ledgerPath, JSON.stringify(fullRecord) + "\n", "utf-8");

    // Auto-archive if threshold exceeded (non-critical — skip on error)
    try {
      maybeArchive(this.ledgerPath, readEntries(this.ledgerPath).length, DEFAULT_ARCHIVE_THRESHOLD);
    } catch {
      // Archival failure is non-fatal; the entry is still persisted
    }

    return fullRecord;
  }

  /**
   * Record a role launch.
   *
   * Creates an ExecutionRecord with status=LAUNCHED and the current
   * timestamp, then appends it to the ledger.
   *
   * @param record - Execution record fields (excluding status, started_at, seq, chain_hash, prev_chain_hash)
   * @returns The complete execution record
   */
  recordLaunch(
    record: Omit<ExecutionRecord, "status" | "started_at" | "seq" | "chain_hash" | "prev_chain_hash">,
  ): ExecutionRecord {
    const fullRecord: ExecutionRecord = {
      ...record,
      status: ExecutionStatus.LAUNCHED,
      started_at: new Date().toISOString(),
    };
    return this.appendEntry(fullRecord);
  }

  /**
   * Record completion of an execution.
   *
   * Finds the existing record by execution_id, creates a new entry with
   * status=COMPLETED (or VIOLATED if violations are present), and appends
   * it to the ledger.
   *
   * @param executionId - The execution ID to mark as completed
   * @param outputArtifact - Optional path to the output artifact
   * @param violations - Optional list of violations detected
   * @returns The new completion record, or null if the execution was not found
   */
  recordCompletion(
    executionId: string,
    outputArtifact?: string,
    violations?: string[],
  ): ExecutionRecord | null {
    const allEntries = readAllEntries(this.ledgerPath);
    const original = allEntries.find(
      (e) => e.execution_id === executionId && e.status === ExecutionStatus.LAUNCHED,
    );
    if (!original) return null;

    const hasViolations = violations && violations.length > 0;
    const status = hasViolations ? ExecutionStatus.VIOLATED : ExecutionStatus.COMPLETED;

    const completionRecord: ExecutionRecord = {
      ...original,
      status,
      output_artifact: outputArtifact,
      tool_violations: violations ?? original.tool_violations,
      completed_at: new Date().toISOString(),
    };

    return this.appendEntry(completionRecord);
  }

  /**
   * Record failure of an execution.
   *
   * Finds the existing record by execution_id and creates a new entry
   * with status=FAILED.
   *
   * @param executionId - The execution ID to mark as failed
   * @param error - Error description
   * @returns The new failure record, or null if the execution was not found
   */
  recordFailure(executionId: string, error: string): ExecutionRecord | null {
    const allEntries = readAllEntries(this.ledgerPath);
    const original = allEntries.find(
      (e) => e.execution_id === executionId && e.status === ExecutionStatus.LAUNCHED,
    );
    if (!original) return null;

    const failureRecord: ExecutionRecord = {
      ...original,
      status: ExecutionStatus.FAILED,
      tool_violations: [...original.tool_violations, error],
      completed_at: new Date().toISOString(),
    };

    return this.appendEntry(failureRecord);
  }

  /**
   * Verify the entire chain's hash integrity.
   *
   * Reads all entries (including archives) and re-computes each entry's
   * chain_hash to verify the chain has not been tampered with.
   *
   * @returns An {@link ExecutionIntegrity} result
   */
  verifyChain(): ExecutionIntegrity {
    const entries = readAllEntries(this.ledgerPath);

    if (entries.length === 0) {
      return { valid: true, firstInvalidSeq: null, totalEntries: 0 };
    }

    let prevHash = GENESIS_HASH_LONG;

    for (const entry of entries) {
      const seq = entry.seq ?? 0;
      const expectedHash = computeChainHash(
        prevHash,
        seq,
        entry.execution_id,
        entry.role_id,
        entry.status,
        entry.started_at,
      );

      if (expectedHash !== entry.chain_hash) {
        return {
          valid: false,
          firstInvalidSeq: seq,
          totalEntries: entries.length,
        };
      }

      prevHash = entry.chain_hash ?? GENESIS_HASH_LONG;
    }

    return { valid: true, firstInvalidSeq: null, totalEntries: entries.length };
  }

  /**
   * Cross-validate developer vs reviewer independence for a task.
   *
   * Finds all developer (R06) and reviewer (R09) records for the given
   * task_id and checks whether they used different sessions (independence).
   *
   * @param taskId - The task ID to cross-validate
   * @returns A {@link CrossValidation} result
   */
  crossValidate(taskId: string): CrossValidation {
    const entries = readAllEntries(this.ledgerPath);

    const taskEntries = entries.filter((e) => e.task_id === taskId);

    const devEntries = taskEntries.filter((e) => e.role_id === "R06");
    const revEntries = taskEntries.filter((e) => e.role_id === "R09");

    const developerSessions = [...new Set(devEntries.map((e) => e.session_id))];
    const reviewerSessions = [...new Set(revEntries.map((e) => e.session_id))];

    // Independent if no session overlap between developer and reviewer
    const devSet = new Set(developerSessions);
    const isIndependent = reviewerSessions.every((s) => !devSet.has(s));

    return {
      task_id: taskId,
      developer_id: devEntries.length > 0 ? devEntries[0].actor_id : "",
      reviewer_id: revEntries.length > 0 ? revEntries[0].actor_id : "",
      is_independent: isIndependent,
      developer_sessions: developerSessions,
      reviewer_sessions: reviewerSessions,
    };
  }

  /**
   * Find entries by task_id.
   *
   * @param taskId - The task ID to filter by
   * @returns Array of matching entries in chronological order
   */
  findByTask(taskId: string): ExecutionRecord[] {
    const entries = readAllEntries(this.ledgerPath);
    return entries.filter((e) => e.task_id === taskId);
  }

  /**
   * Find entries by role_id.
   *
   * @param roleId - The role ID to filter by
   * @returns Array of matching entries in chronological order
   */
  findByRole(roleId: string): ExecutionRecord[] {
    const entries = readAllEntries(this.ledgerPath);
    return entries.filter((e) => e.role_id === roleId);
  }

  /**
   * Retrieve the most recent `n` entries from the ledger.
   *
   * @param n - Maximum number of entries to return (from the tail)
   * @returns Array of the most recent entries, ordered oldest-first
   */
  recent(n: number): ExecutionRecord[] {
    const entries = readEntries(this.ledgerPath);
    if (n <= 0) return [];
    return entries.slice(-n);
  }

  /**
   * Return the total number of entries in the ledger (main file only).
   */
  get length(): number {
    return readEntries(this.ledgerPath).length;
  }

  /**
   * Return the absolute path to the ledger file.
   */
  get path(): string {
    return this.ledgerPath;
  }

  // ── Enhanced Query Methods ─────────────────────────────────────────────

  /**
   * Find all currently active (LAUNCHED but not yet COMPLETED/FAILED) executions.
   *
   * Scans all entries and returns LAUNCHED records whose execution_id
   * does not have a corresponding COMPLETED, FAILED, or VIOLATED entry.
   */
  findActive(): ExecutionRecord[] {
    const entries = readAllEntries(this.ledgerPath);

    // Collect execution IDs that have a terminal status
    const terminalIds = new Set(
      entries
        .filter(e =>
          e.status === ExecutionStatus.COMPLETED ||
          e.status === ExecutionStatus.FAILED ||
          e.status === ExecutionStatus.VIOLATED,
        )
        .map(e => e.execution_id),
    );

    // Return LAUNCHED entries without a terminal counterpart
    return entries.filter(
      e => e.status === ExecutionStatus.LAUNCHED && !terminalIds.has(e.execution_id),
    );
  }

  /**
   * Find entries by status.
   *
   * @param status - The execution status to filter by
   * @returns Array of matching entries in chronological order
   */
  findByStatus(status: ExecutionStatus): ExecutionRecord[] {
    const entries = readAllEntries(this.ledgerPath);
    return entries.filter(e => e.status === status);
  }

  /**
   * Compute per-role execution statistics.
   *
   * Aggregates total launches, completions, failures, violations,
   * success rate, and average duration per role.
   */
  getStatistics(): RoleStatistics[] {
    const entries = readAllEntries(this.ledgerPath);
    const byRole = new Map<string, ExecutionRecord[]>();

    for (const entry of entries) {
      const list = byRole.get(entry.role_id) ?? [];
      list.push(entry);
      byRole.set(entry.role_id, list);
    }

    const stats: RoleStatistics[] = [];

    for (const [roleId, roleEntries] of byRole) {
      const launches = roleEntries.filter(e => e.status === ExecutionStatus.LAUNCHED).length;
      const completions = roleEntries.filter(e => e.status === ExecutionStatus.COMPLETED).length;
      const failures = roleEntries.filter(e => e.status === ExecutionStatus.FAILED).length;
      const violations = roleEntries.filter(e => e.status === ExecutionStatus.VIOLATED).length;

      // Compute average duration for completed entries
      const durations: number[] = [];
      for (const e of roleEntries) {
        if (e.started_at && e.completed_at) {
          const ms = new Date(e.completed_at).getTime() - new Date(e.started_at).getTime();
          if (ms >= 0) durations.push(ms);
        }
      }
      const avgDurationMs = durations.length > 0
        ? Math.round(durations.reduce((a, b) => a + b, 0) / durations.length)
        : null;

      const terminal = completions + failures + violations;
      const successRate = terminal > 0 ? completions / terminal : null;

      stats.push({
        role_id: roleId,
        total_launches: launches,
        total_completions: completions,
        total_failures: failures,
        total_violations: violations,
        success_rate: successRate,
        avg_duration_ms: avgDurationMs,
      });
    }

    return stats.sort((a, b) => a.role_id.localeCompare(b.role_id));
  }
}

// ── RoleStatistics ───────────────────────────────────────────────────────────

/** Per-role execution statistics. */
export interface RoleStatistics {
  role_id: string;
  total_launches: number;
  total_completions: number;
  total_failures: number;
  total_violations: number;
  /** completions / (completions + failures + violations), null if no terminal entries */
  success_rate: number | null;
  /** Average execution duration in ms, null if no duration data */
  avg_duration_ms: number | null;
}
