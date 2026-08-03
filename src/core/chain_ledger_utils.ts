/**
 * chain_ledger_utils.ts — Shared utilities for chain-hashed JSONL ledgers.
 *
 * Extracted from audit_ledger.ts, execution_ledger.ts, and knowledge_ledger.ts
 * to eliminate duplicated helper functions (sha256, ensureDir, readEntries,
 * maybeArchive, GENESIS_PREV_HASH).
 *
 * Each ledger has its own data shape and hash computation strategy, so they
 * remain as separate classes. This module provides the common building blocks.
 */

import { createHash } from "node:crypto";
import {
  readFileSync,
  existsSync,
  mkdirSync,
  renameSync,
} from "node:fs";
import { dirname } from "node:path";

// ── Constants ────────────────────────────────────────────────────────────────

/** The "genesis" previous-hash used for the very first entry (short form). */
export const GENESIS_HASH_SHORT = "0";

/** The "genesis" previous-hash used for the very first entry (64-char form). */
export const GENESIS_HASH_LONG = "0".repeat(64);

/** Default threshold for auto-archiving the ledger file. */
export const DEFAULT_ARCHIVE_THRESHOLD = 200;

// ── Crypto ───────────────────────────────────────────────────────────────────

/**
 * Compute the SHA-256 hex digest of the given string.
 */
export function sha256(input: string): string {
  return createHash("sha256").update(input, "utf-8").digest("hex");
}

/**
 * Compute a chain hash from concatenated fields.
 *
 * This is the most common pattern used by execution_ledger and knowledge_ledger:
 * chain_hash = SHA-256(prevHash + field1 + field2 + ... + fieldN)
 */
export function chainHashFields(prevHash: string, ...fields: (string | number)[]): string {
  const payload = prevHash + fields.join("");
  return sha256(payload);
}

/**
 * Compute a chain hash from a JSON-serialized entry (excluding the hash field).
 *
 * This is the pattern used by audit_ledger:
 * chain_hash = SHA-256(prevHash + JSON.stringify(entryWithoutHash))
 */
export function chainHashJson<T extends { chain_hash?: string }>(
  prevHash: string,
  entry: T,
): string {
  const { chain_hash: _, ...rest } = entry;
  return sha256(prevHash + JSON.stringify(rest));
}

// ── File System ──────────────────────────────────────────────────────────────

/**
 * Ensure the directory for the given file path exists.
 */
export function ensureDir(filePath: string): void {
  const dir = dirname(filePath);
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
}

/**
 * Read all entries from a JSONL ledger file.
 * Blank lines and malformed JSON lines are silently skipped.
 */
export function readJsonlEntries<T>(ledgerPath: string): T[] {
  if (!existsSync(ledgerPath)) return [];
  const raw = readFileSync(ledgerPath, "utf-8");
  const entries: T[] = [];
  for (const line of raw.split("\n")) {
    const trimmed = line.trim();
    if (trimmed.length === 0) continue;
    try {
      entries.push(JSON.parse(trimmed) as T);
    } catch {
      // Skip malformed lines
    }
  }
  return entries;
}

/**
 * Read all entries across the main ledger file and any archived files.
 * Archives are named as `<path>.1`, `<path>.2`, etc.
 */
export function readAllArchivedEntries<T>(ledgerPath: string): T[] {
  const entries: T[] = [];
  let archiveIdx = 1;
  while (existsSync(`${ledgerPath}.${archiveIdx}`)) {
    entries.push(...readJsonlEntries<T>(`${ledgerPath}.${archiveIdx}`));
    archiveIdx++;
  }
  entries.push(...readJsonlEntries<T>(ledgerPath));
  return entries;
}

/**
 * Archive the current ledger file if it exceeds the threshold.
 * Rotates existing archives upward (.jsonl.1 → .jsonl.2, etc.)
 *
 * @param ledgerPath - Path to the main ledger file
 * @param currentCount - Current number of entries in the file
 * @param threshold - Maximum entries before archiving (default: 200)
 */
export function maybeArchive(
  ledgerPath: string,
  currentCount: number,
  threshold: number = DEFAULT_ARCHIVE_THRESHOLD,
): void {
  if (currentCount <= threshold) return;

  let nextIdx = 1;
  while (existsSync(`${ledgerPath}.${nextIdx}`)) {
    nextIdx++;
  }

  for (let i = nextIdx - 1; i >= 1; i--) {
    renameSync(`${ledgerPath}.${i}`, `${ledgerPath}.${i + 1}`);
  }
  renameSync(ledgerPath, `${ledgerPath}.1`);
}
