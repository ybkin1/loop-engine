/**
 * contracts.ts — Host Adapter Interface for Loop Engineering
 *
 * Defines the abstract boundary between Loop Core (host-agnostic) and
 * any AI coding host (Qoder, ZCode, Claude Code, etc.).
 *
 * Ported from ZCode loop_core/contracts.py.
 */

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { join } from "node:path";

import {
  EnforcementLevel,
  type HostCapabilities,
  deriveEnforcementLevel,
  HOST_PRESETS,
} from "./enforcement.js";
import { loadState, saveState, loadGates } from "./state-machine.js";
import type { ProjectState, GatesRegistry } from "../types/index.js";
import type { EvidenceEnvelope } from "./hard_constraints.js";

// ── Helper Interfaces ────────────────────────────────────────────────────────

export interface ExecResult {
  exit_code: number;
  stdout: string;
  stderr: string;
}

export interface TaskRecord {
  id: string;
  status: string;
  allowed_paths?: string[];
}

export interface GateDecision {
  decision: "APPROVED" | "REJECTED" | "TIMEOUT";
  actor: string;
  decided_at: string;
}

export interface EvidenceFreeze {
  evidence_id: string;
  content_hash: string;
  frozen_at: string;
}

export interface FreshnessCheck {
  evidence_id: string;
  is_fresh: boolean;
  expires_at: string;
  hash_stable: boolean;
}

// ── IHostAdapter Interface ───────────────────────────────────────────────────

export interface IHostAdapter {
  /** Host name identifier */
  readonly host_name: string;
  /** Host capability declaration */
  readonly capabilities: HostCapabilities;
  /** Derived enforcement level */
  readonly enforcement_level: EnforcementLevel;

  // File operations
  read_file(filePath: string): string | null;
  write_file(filePath: string, content: string): boolean;
  file_exists(filePath: string): boolean;

  // Command execution
  execute(command: string, cwd?: string): Promise<ExecResult>;

  // State management
  load_state(root: string): Promise<ProjectState | null>;
  save_state(root: string, state: ProjectState): Promise<void>;
  load_gates(root: string): Promise<GatesRegistry | null>;
  load_tasks(root: string): Promise<TaskRecord[]>;

  // User interaction (gate approval, questions)
  present_gate(gate_id: string, conditions: string[]): Promise<GateDecision>;
  ask_user(question: string, context?: string): Promise<string | null>;

  // Evidence
  freeze_evidence(evidence_id: string, content: string): EvidenceFreeze;
  check_evidence_freshness(envelopes: EvidenceEnvelope[]): FreshnessCheck[];
}

// ── HostAdapterQoder ─────────────────────────────────────────────────────────

export class HostAdapterQoder implements IHostAdapter {
  readonly host_name = "qoder";
  readonly capabilities: HostCapabilities = HOST_PRESETS["qoder"];
  readonly enforcement_level: EnforcementLevel = deriveEnforcementLevel(this.capabilities);

  // ── File operations ───────────────────────────────────────────────────

  read_file(filePath: string): string | null {
    try {
      return readFileSync(filePath, "utf-8");
    } catch {
      return null;
    }
  }

  write_file(filePath: string, content: string): boolean {
    try {
      writeFileSync(filePath, content, "utf-8");
      return true;
    } catch {
      return false;
    }
  }

  file_exists(filePath: string): boolean {
    return existsSync(filePath);
  }

  // ── Command execution ─────────────────────────────────────────────────

  async execute(command: string, cwd?: string): Promise<ExecResult> {
    try {
      const stdout = execFileSync("sh", ["-c", command], {
        cwd,
        encoding: "utf-8",
        timeout: 30_000,
      });
      return { exit_code: 0, stdout: stdout ?? "", stderr: "" };
    } catch (err: unknown) {
      const e = err as { status?: number; stdout?: string; stderr?: string };
      return {
        exit_code: e.status ?? -1,
        stdout: e.stdout ?? "",
        stderr: e.stderr ?? String(err),
      };
    }
  }

  // ── State management ──────────────────────────────────────────────────

  async load_state(root: string): Promise<ProjectState | null> {
    try {
      return await loadState(root);
    } catch {
      return null;
    }
  }

  async save_state(root: string, state: ProjectState): Promise<void> {
    await saveState(root, state);
  }

  async load_gates(root: string): Promise<GatesRegistry | null> {
    try {
      return await loadGates(root);
    } catch {
      return null;
    }
  }

  async load_tasks(root: string): Promise<TaskRecord[]> {
    try {
      const raw = readFileSync(join(root, ".ai", "task_graph.yaml"), "utf-8");
      const { parseDocument } = await import("yaml");
      const doc = parseDocument(raw).toJSON();
      if (!doc || !Array.isArray(doc.tasks)) return [];
      return doc.tasks.map((t: Record<string, unknown>) => ({
        id: String(t.id),
        status: String(t.status),
        allowed_paths: Array.isArray(t.allowed_paths)
          ? (t.allowed_paths as string[])
          : undefined,
      }));
    } catch {
      return [];
    }
  }

  // ── User interaction ──────────────────────────────────────────────────

  async present_gate(_gate_id: string, _conditions: string[]): Promise<GateDecision> {
    return { decision: "TIMEOUT", actor: "system", decided_at: new Date().toISOString() };
  }

  async ask_user(_question: string, _context?: string): Promise<string | null> {
    return null;
  }

  // ── Evidence ──────────────────────────────────────────────────────────

  freeze_evidence(evidence_id: string, content: string): EvidenceFreeze {
    return {
      evidence_id,
      content_hash: createHash("sha256").update(content, "utf-8").digest("hex"),
      frozen_at: new Date().toISOString(),
    };
  }

  check_evidence_freshness(envelopes: EvidenceEnvelope[]): FreshnessCheck[] {
    return envelopes.map((env) => ({
      evidence_id: env.evidence_id,
      is_fresh: env.is_fresh(),
      expires_at: env.expires_at,
      hash_stable: !env.has_hash_changed(env.content_hash),
    }));
  }
}

// ── HostAdapterStandalone ────────────────────────────────────────────────────

export class HostAdapterStandalone implements IHostAdapter {
  readonly host_name = "standalone";
  readonly capabilities: HostCapabilities = HOST_PRESETS["standalone"];
  readonly enforcement_level: EnforcementLevel = EnforcementLevel.ADVISORY;

  read_file(_filePath: string): string | null { return null; }
  write_file(_filePath: string, _content: string): boolean { return false; }
  file_exists(_filePath: string): boolean { return false; }

  async execute(_command: string, _cwd?: string): Promise<ExecResult> {
    return { exit_code: -1, stdout: "", stderr: "no host" };
  }

  async load_state(_root: string): Promise<ProjectState | null> { return null; }
  async save_state(_root: string, _state: ProjectState): Promise<void> { /* no-op */ }
  async load_gates(_root: string): Promise<GatesRegistry | null> { return null; }
  async load_tasks(_root: string): Promise<TaskRecord[]> { return []; }

  async present_gate(_gate_id: string, _conditions: string[]): Promise<GateDecision> {
    return { decision: "TIMEOUT", actor: "system", decided_at: new Date().toISOString() };
  }
  async ask_user(_question: string, _context?: string): Promise<string | null> { return null; }

  freeze_evidence(evidence_id: string, content: string): EvidenceFreeze {
    return {
      evidence_id,
      content_hash: createHash("sha256").update(content, "utf-8").digest("hex"),
      frozen_at: new Date().toISOString(),
    };
  }

  check_evidence_freshness(envelopes: EvidenceEnvelope[]): FreshnessCheck[] {
    return envelopes.map((env) => ({
      evidence_id: env.evidence_id,
      is_fresh: env.is_fresh(),
      expires_at: env.expires_at,
      hash_stable: !env.has_hash_changed(env.content_hash),
    }));
  }
}

// ── Factory ──────────────────────────────────────────────────────────────────

export function createHostAdapter(hostName: string): IHostAdapter {
  switch (hostName) {
    case "qoder":
      return new HostAdapterQoder();
    case "standalone":
      return new HostAdapterStandalone();
    default:
      return new HostAdapterStandalone(); // safe default
  }
}
