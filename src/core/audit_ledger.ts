/**
 * audit_ledger.ts — Chain-hashed audit ledger for Loop Engineering
 *
 * Provides an append-only, tamper-evident audit log. Each entry's
 * `chain_hash` incorporates the previous entry's hash, forming a SHA-256
 * hash chain similar in spirit to a simplified blockchain.
 *
 * Uses only Node.js built-in modules (`crypto`, `fs`, `path`).
 */

import { createHash } from "node:crypto";
import {
  readFileSync,
  writeFileSync,
  existsSync,
  mkdirSync,
  appendFileSync,
} from "node:fs";
import { dirname, resolve } from "node:path";

// ── Ledger Entry ──────────────────────────────────────────────────────────────

/** A single entry in the audit ledger. */
export interface LedgerEntry {
  /** Monotonically increasing sequence number (1-based). */
  seq: number;
  /** ISO-8601 timestamp of when the entry was created. */
  timestamp: string;
  /** Event type (e.g. "gate_advance", "role_activate", "veto", "handoff"). */
  event: string;
  /** The role or actor that triggered the event. */
  actor: string;
  /** Arbitrary structured details about the event. */
  details: Record<string, unknown>;
  /**
   * SHA-256 hex digest computed over the concatenation of the previous
   * entry's `chain_hash` and the JSON serialisation of this entry
   * (excluding the `chain_hash` field itself). For the first entry the
   * "previous hash" is the string `"0"`.
   */
  chain_hash: string;
}

// ── Integrity Result ──────────────────────────────────────────────────────────

/** Result of verifying the ledger's hash-chain integrity. */
export interface IntegrityResult {
  /** `true` when every entry's `chain_hash` is valid. */
  valid: boolean;
  /** Sequence number of the first invalid entry (only set when `valid` is `false`). */
  firstInvalidSeq?: number;
}

// ── Constants ─────────────────────────────────────────────────────────────────

/** The "genesis" previous-hash used for the very first entry. */
const GENESIS_PREV_HASH = "0";

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Compute the SHA-256 hex digest of the given string.
 */
function sha256(input: string): string {
  return createHash("sha256").update(input, "utf-8").digest("hex");
}

/**
 * Compute the chain_hash for a new entry.
 *
 * The hash is computed over: `prevHash + JSON.stringify(entryWithoutHash)`.
 *
 * @param prevHash - The `chain_hash` of the preceding entry (or `"0"`)
 * @param entryWithoutHash - The entry object with `chain_hash` omitted
 */
function computeChainHash(prevHash: string, entryWithoutHash: Omit<LedgerEntry, "chain_hash">): string {
  const payload = prevHash + JSON.stringify(entryWithoutHash);
  return sha256(payload);
}

/**
 * Ensure the directory for the given file path exists.
 */
function ensureDir(filePath: string): void {
  const dir = dirname(filePath);
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
}

/**
 * Read all entries from a JSONL ledger file.
 *
 * Each line is expected to be a valid JSON object representing a
 * {@link LedgerEntry}. Blank lines are silently skipped.
 */
function readEntries(ledgerPath: string): LedgerEntry[] {
  if (!existsSync(ledgerPath)) return [];
  const raw = readFileSync(ledgerPath, "utf-8");
  const entries: LedgerEntry[] = [];
  for (const line of raw.split("\n")) {
    const trimmed = line.trim();
    if (trimmed.length === 0) continue;
    try {
      entries.push(JSON.parse(trimmed) as LedgerEntry);
    } catch {
      // Skip malformed lines — they will be caught by verifyIntegrity.
    }
  }
  return entries;
}

// ── AuditLedger ───────────────────────────────────────────────────────────────

/**
 * Append-only, chain-hashed audit ledger.
 *
 * Entries are stored in JSONL format (one JSON object per line) to allow
 * efficient appends without rewriting the entire file.
 *
 * @example
 * ```ts
 * const ledger = new AuditLedger("/path/to/audit.jsonl");
 * const entry = ledger.append("gate_advance", "R06", { gate: "S3→S4" });
 * console.log(entry.chain_hash);
 * ```
 */
export class AuditLedger {
  /** Resolved absolute path to the ledger file. */
  private readonly ledgerPath: string;

  /**
   * Create or open an audit ledger.
   *
   * @param ledgerPath - Path to the JSONL ledger file. Parent directories
   *                       are created automatically if they do not exist.
   */
  constructor(ledgerPath: string) {
    this.ledgerPath = resolve(ledgerPath);
    ensureDir(this.ledgerPath);
  }

  /**
   * Append a new entry to the ledger.
   *
   * The `seq` number is automatically set to one greater than the current
   * last entry (or `1` for the first entry). The `chain_hash` is computed
   * from the previous entry's hash and the new entry's content.
   *
   * @param event - Event type identifier
   * @param actor - Role or actor that triggered the event
   * @param details - Arbitrary structured details
   * @returns The newly created ledger entry
   */
  append(event: string, actor: string, details: Record<string, unknown>): LedgerEntry {
    const entries = readEntries(this.ledgerPath);
    const lastEntry = entries.length > 0 ? entries[entries.length - 1] : null;

    const seq = lastEntry ? lastEntry.seq + 1 : 1;
    const timestamp = new Date().toISOString();
    const prevHash = lastEntry ? lastEntry.chain_hash : GENESIS_PREV_HASH;

    const entryWithoutHash: Omit<LedgerEntry, "chain_hash"> = {
      seq,
      timestamp,
      event,
      actor,
      details,
    };

    const chain_hash = computeChainHash(prevHash, entryWithoutHash);

    const entry: LedgerEntry = { ...entryWithoutHash, chain_hash };

    // Append as a single JSON line
    appendFileSync(this.ledgerPath, JSON.stringify(entry) + "\n", "utf-8");

    return entry;
  }

  /**
   * Verify the integrity of the entire hash chain.
   *
   * Re-computes each entry's `chain_hash` from its predecessor and
   * compares against the stored value.
   *
   * @returns An {@link IntegrityResult} indicating whether the chain is
   *          valid and, if not, the sequence number of the first invalid
   *          entry.
   */
  verifyIntegrity(): IntegrityResult {
    const entries = readEntries(this.ledgerPath);

    if (entries.length === 0) {
      return { valid: true };
    }

    let prevHash = GENESIS_PREV_HASH;

    for (const entry of entries) {
      const entryWithoutHash: Omit<LedgerEntry, "chain_hash"> = {
        seq: entry.seq,
        timestamp: entry.timestamp,
        event: entry.event,
        actor: entry.actor,
        details: entry.details,
      };

      const expectedHash = computeChainHash(prevHash, entryWithoutHash);

      if (expectedHash !== entry.chain_hash) {
        return { valid: false, firstInvalidSeq: entry.seq };
      }

      prevHash = entry.chain_hash;
    }

    return { valid: true };
  }

  /**
   * Retrieve the most recent `n` entries from the ledger.
   *
   * @param n - Maximum number of entries to return (from the tail)
   * @returns Array of the most recent entries, ordered oldest-first
   */
  recent(n: number): LedgerEntry[] {
    const entries = readEntries(this.ledgerPath);
    if (n <= 0) return [];
    return entries.slice(-n);
  }

  /**
   * Find all entries matching a given event type.
   *
   * @param event - The event type to filter by
   * @returns Array of matching entries in chronological order
   */
  findByEvent(event: string): LedgerEntry[] {
    const entries = readEntries(this.ledgerPath);
    return entries.filter(e => e.event === event);
  }

  /**
   * Return the total number of entries in the ledger.
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
}
