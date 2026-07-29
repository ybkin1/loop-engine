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

/** Default timeout for command execution in milliseconds. */
const EXECUTE_TIMEOUT_MS = 30_000;

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

// ── Shared Evidence Helpers ─────────────────────────────────────────────────

/**
 * Freeze evidence content into a hash-bound envelope.
 * Shared by all host adapter implementations.
 */
function _freezeEvidence(evidence_id: string, content: string): EvidenceFreeze {
  return {
    evidence_id,
    content_hash: createHash("sha256").update(content, "utf-8").digest("hex"),
    frozen_at: new Date().toISOString(),
  };
}

/**
 * Check freshness of a list of evidence envelopes.
 * Shared by all host adapter implementations.
 */
function _checkEvidenceFreshness(envelopes: EvidenceEnvelope[]): FreshnessCheck[] {
  return envelopes.map((env) => ({
    evidence_id: env.evidence_id,
    is_fresh: env.is_fresh(),
    expires_at: env.expires_at,
    hash_stable: !env.has_hash_changed(env.content_hash),
  }));
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

  /**
   * Whitelist of commands permitted for execution via the adapter.
   * Only read-only or governance-related commands are allowed.
   * This prevents shell injection through the adapter interface.
   */
  private static readonly COMMAND_WHITELIST = new Set([
    /^npx\s+tsc\s+--noEmit\b/i,
    /^npx\s+vitest\s+(run|test)\b/i,
    /^npx\s+eslint\b/i,
    /^npm\s+(test|run\s+test|run\s+lint|run\s+build)\b/i,
    /^git\s+(status|log|diff|show)\b/i,
    /^node\s+-[ev]\b/i,
    /^python\d?\s+(-c|-m\s+compileall)\b/i,
    // Safe read-only commands
    /^echo\s+/i,
    /^dir\b/i,
    /^ls\b/i,
    /^cat\s+/i,
    /^type\s+/i,
    /^where\s+/i,
    /^which\s+/i,
    /^whoami\b/i,
    /^date\b/i,
    /^Get-ChildItem\b/i,
    /^Select-String\b/i,
  ]);

  async execute(command: string, cwd?: string): Promise<ExecResult> {
    const normalizedCmd = command.trim();

    // Reject commands with shell redirection or pipe operators (bypass attempt)
    if (/\||&|;|>>|>/.test(normalizedCmd) && !/^echo\s+\S+\s*$/.test(normalizedCmd)) {
      return { exit_code: -1, stdout: "", stderr: `Command rejected by whitelist: redirect/pipe detected in ${normalizedCmd.slice(0, 80)}` };
    }

    // Command validation — reject any command not matching whitelist patterns
    let allowed = false;
    for (const pattern of HostAdapterQoder.COMMAND_WHITELIST) {
      if (pattern.test(normalizedCmd)) { allowed = true; break; }
    }
    if (!allowed) {
      return { exit_code: -1, stdout: "", stderr: `Command rejected by whitelist: ${normalizedCmd.slice(0, 80)}` };
    }

    try {
      const isWindows = process.platform === "win32";
      const shell = isWindows ? "cmd.exe" : "sh";
      const shellArgs = isWindows ? ["/c", command] : ["-c", command];
      const stdout = execFileSync(shell, shellArgs, {
        cwd,
        encoding: "utf-8",
        timeout: EXECUTE_TIMEOUT_MS,
      });
      return { exit_code: 0, stdout: stdout ?? "", stderr: "" };
    } catch (err: unknown) {
      const e = err as NodeJS.ErrnoException & { status?: number; stdout?: string; stderr?: string };
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
    return _freezeEvidence(evidence_id, content);
  }

  check_evidence_freshness(envelopes: EvidenceEnvelope[]): FreshnessCheck[] {
    return _checkEvidenceFreshness(envelopes);
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
    return _freezeEvidence(evidence_id, content);
  }

  check_evidence_freshness(envelopes: EvidenceEnvelope[]): FreshnessCheck[] {
    return _checkEvidenceFreshness(envelopes);
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
