import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { AuditLedger } from "../src/core/audit_ledger.js";
import { mkdirSync, rmSync, existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const TEST_LEDGER = join(process.cwd(), ".test-audit-ledger-tmp", "audit.jsonl");
const TEST_DIR = join(process.cwd(), ".test-audit-ledger-tmp");

let ledger: AuditLedger;

beforeEach(() => {
  if (existsSync(TEST_DIR)) rmSync(TEST_DIR, { recursive: true });
  mkdirSync(TEST_DIR, { recursive: true });
  ledger = new AuditLedger(TEST_LEDGER);
});

afterEach(() => {
  if (existsSync(TEST_DIR)) rmSync(TEST_DIR, { recursive: true });
});

// ── append returns ordered entries ─────────────────────
describe("AuditLedger", () => {
  it("append returns ordered entries (seq increments)", () => {
    const e1 = ledger.append("event_a", "R06", { key: "val1" });
    const e2 = ledger.append("event_b", "R07", { key: "val2" });
    const e3 = ledger.append("event_c", "R08", { key: "val3" });

    expect(e1.seq).toBe(1);
    expect(e2.seq).toBe(2);
    expect(e3.seq).toBe(3);
    expect(ledger.length).toBe(3);
  });

  // ── chain_hash chain verification ──────────────────────
  it("chain_hash chain verification is correct", () => {
    ledger.append("first", "R06", { a: 1 });
    ledger.append("second", "R07", { b: 2 });

    const entries = ledger.recent(10);
    expect(entries[0].chain_hash).toBeTruthy();
    expect(entries[0].chain_hash).toHaveLength(64); // SHA-256 hex
    expect(entries[1].chain_hash).not.toBe(entries[0].chain_hash);
  });

  // ── verifyIntegrity on complete chain ──────────────────
  it("verifyIntegrity returns valid=true for intact chain", () => {
    ledger.append("event_1", "R06", { x: 1 });
    ledger.append("event_2", "R07", { x: 2 });
    ledger.append("event_3", "R08", { x: 3 });

    const result = ledger.verifyIntegrity();
    expect(result.valid).toBe(true);
    expect(result.firstInvalidSeq).toBeUndefined();
  });

  // ── Tampering detection ────────────────────────────────
  it("verifyIntegrity returns valid=false after tampering middle entry", () => {
    ledger.append("event_1", "R06", { x: 1 });
    ledger.append("event_2", "R07", { x: 2 });
    ledger.append("event_3", "R08", { x: 3 });

    // Read the JSONL file and tamper with the middle entry
    const raw = readFileSync(TEST_LEDGER, "utf-8");
    const lines = raw.trim().split("\n");
    const middleEntry = JSON.parse(lines[1]);
    middleEntry.details = { x: 999, tampered: true };
    lines[1] = JSON.stringify(middleEntry);
    writeFileSync(TEST_LEDGER, lines.join("\n") + "\n", "utf-8");

    const result = ledger.verifyIntegrity();
    expect(result.valid).toBe(false);
    expect(result.firstInvalidSeq).toBe(2);
  });

  // ── recent(N) ──────────────────────────────────────────
  it("recent(N) returns last N entries", () => {
    ledger.append("e1", "R01", {});
    ledger.append("e2", "R02", {});
    ledger.append("e3", "R03", {});
    ledger.append("e4", "R04", {});
    ledger.append("e5", "R05", {});

    const last3 = ledger.recent(3);
    expect(last3).toHaveLength(3);
    expect(last3[0].seq).toBe(3);
    expect(last3[1].seq).toBe(4);
    expect(last3[2].seq).toBe(5);
  });

  // ── findByEvent ────────────────────────────────────────
  it("findByEvent filters correctly", () => {
    ledger.append("gate_check", "R06", { gate: "g1" });
    ledger.append("role_activate", "R07", { role: "R06" });
    ledger.append("gate_check", "R08", { gate: "g2" });
    ledger.append("evidence_submit", "R06", { id: "ev1" });
    ledger.append("gate_check", "R09", { gate: "g3" });

    const gateChecks = ledger.findByEvent("gate_check");
    expect(gateChecks).toHaveLength(3);
    expect(gateChecks.every(e => e.event === "gate_check")).toBe(true);

    const roleActivates = ledger.findByEvent("role_activate");
    expect(roleActivates).toHaveLength(1);

    const empty = ledger.findByEvent("nonexistent");
    expect(empty).toHaveLength(0);
  });
});
