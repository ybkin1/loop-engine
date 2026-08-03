#!/usr/bin/env node
import { Command } from "commander";
import { initProject, checkGate, advanceGate, approveGate, loadState, loadGates } from "../core/state-machine.js";
import { activateRole, getRoleStatus } from "../core/role-engine.js";
import { submitEvidence, verifyEvidence } from "../core/evidence.js";
import { getHandoffHistory } from "../core/handoff.js";
import { generatePrompt } from "../core/prompt_engine.js";
import { HarnessAnalyzer } from "../core/harness_analyzer.js";
import { ConstraintEngine } from "../core/constraint_engine.js";
import type { PromptContext } from "../core/prompt_engine.js";

const program = new Command();
program.name("loop").description("Loop Engineering CLI").version("0.1.0");

// ── init ───────────────────────────────────────────────
program.command("init <project-name>")
  .description("Initialize Loop governance")
  .option("-r, --root <path>", "Project root", process.cwd())
  .action(async (name: string, opts: { root: string }) => {
    const state = await initProject(opts.root, name);
    console.log(`✅ Project "${state.project_name}" initialized`);
    console.log(`   Phase: ${state.current_phase}`);
    console.log(`   Gate:  ${state.current_gate_id}`);
  });

// ── gate ───────────────────────────────────────────────
const gate = program.command("gate").description("Gate operations");

gate.command("check <gate-id>")
  .option("-r, --root <path>", "Project root", process.cwd())
  .action(async (gateId: string, opts: { root: string }) => {
    const result = await checkGate(opts.root, gateId);
    if (result.status === "pass") {
      console.log(`✅ Gate ${gateId}: PASS (${result.conditions_met}/${result.conditions_total})`);
    } else {
      console.log(`❌ Gate ${gateId}: BLOCKED (${result.conditions_met}/${result.conditions_total})`);
      for (const m of result.missing_conditions) {
        console.log(`   - ${m.description}`);
      }
    }
  });

gate.command("advance <gate-id>")
  .option("-r, --root <path>", "Project root", process.cwd())
  .action(async (gateId: string, opts: { root: string }) => {
    const result = await advanceGate(opts.root, gateId);
    if (result.success) {
      console.log(`✅ Gate advanced: ${result.previous_phase} → ${result.new_phase}`);
    } else {
      console.log(`❌ Gate blocked: ${result.error}`);
    }
  });

gate.command("approve <gate-id>")
  .description("Record explicit user approval for a gate's manual_approval condition (user-only action)")
  .option("-r, --root <path>", "Project root", process.cwd())
  .option("-n, --note <text>", "Approval note")
  .action(async (gateId: string, opts: { root: string; note?: string }) => {
    const result = await approveGate(opts.root, gateId, opts.note);
    if (result.success) {
      console.log(`✅ User approval recorded for gate ${gateId} at ${result.approved_at}`);
      console.log(`   Run 'loop gate advance ${gateId}' once all conditions are met.`);
    } else {
      console.log(`❌ Approval failed: ${result.error}`);
      process.exitCode = 1;
    }
  });

// ── role ───────────────────────────────────────────────
const role = program.command("role").description("Role operations");

role.command("activate <role-id>")
  .option("-r, --root <path>", "Project root", process.cwd())
  .action(async (roleId: string, opts: { root: string }) => {
    const result = await activateRole(opts.root, roleId);
    if (result.success) {
      console.log(`✅ Role ${roleId} activated`);
    } else {
      console.log(`❌ Role activation failed: ${result.error}`);
    }
  });

role.command("status [role-id]")
  .option("-r, --root <path>", "Project root", process.cwd())
  .action(async (roleId: string | undefined, opts: { root: string }) => {
    if (!roleId) {
      const state = await loadState(opts.root);
      console.log(`Active role: ${state.active_role ?? "(none)"}`);
    } else {
      const result = await getRoleStatus(opts.root, roleId);
      console.log(JSON.stringify(result, null, 2));
    }
  });

// ── evidence ───────────────────────────────────────────
const evidence = program.command("evidence").description("Evidence operations");

evidence.command("submit")
  .requiredOption("--id <evidence-id>", "Evidence ID")
  .requiredOption("--type <type>", "Evidence type")
  .requiredOption("--content <text>", "Evidence content")
  .option("--role <role-id>", "Submitting role")
  .option("--gate <gate-id>", "Associated gate")
  .option("-r, --root <path>", "Project root", process.cwd())
  .action(async (opts: { id: string; type: string; content: string; role?: string; gate?: string; root: string }) => {
    const result = await submitEvidence(opts.root, {
      evidence_id: opts.id,
      type: opts.type,
      content: opts.content,
      role_id: opts.role,
      gate_id: opts.gate,
    });
    console.log(`✅ Evidence submitted: ${result.evidence_id}`);
    console.log(`   Hash: ${result.content_hash}`);
  });

evidence.command("verify <evidence-id>")
  .option("-r, --root <path>", "Project root", process.cwd())
  .action(async (evidenceId: string, opts: { root: string }) => {
    const result = await verifyEvidence(opts.root, evidenceId);
    console.log(JSON.stringify(result, null, 2));
  });

// ── state ──────────────────────────────────────────────
program.command("state")
  .option("-r, --root <path>", "Project root", process.cwd())
  .action(async (opts: { root: string }) => {
    const state = await loadState(opts.root);
    console.log(JSON.stringify(state, null, 2));
  });

// ── status ─────────────────────────────────────────────
program.command("status")
  .description("Show governance status")
  .option("-r, --root <path>", "Project root", process.cwd())
  .option("--full", "Show full status with Harness analysis and constraint check")
  .option("--json", "Machine-readable JSON output (parser-safe, no spinners/colors)")
  .option("--no-color", "Disable ANSI colors in human output")
  .action(async (opts: { root: string; full?: boolean; json?: boolean; color?: boolean }) => {
    const state = await loadState(opts.root);
    const gates = await loadGates(opts.root);

    const pendingGates = gates.gates.filter(g => g.status === "pending").map(g => g.gate_id);
    const blockedGates = gates.gates.filter(g => g.status === "blocked").map(g => g.gate_id);

    // Machine mode: emit a single parser-safe JSON document on stdout
    if (opts.json) {
      const payload: Record<string, unknown> = {
        project_name: state.project_name,
        current_phase: state.current_phase,
        current_gate: state.current_gate_id,
        active_role: state.active_role ?? null,
        pending_gates: pendingGates,
        blocked_gates: blockedGates,
      };

      if (opts.full) {
        const engine = new ConstraintEngine(opts.root);
        const govStatus = await engine.getGovernanceStatus();
        const analyzer = new HarnessAnalyzer(opts.root);
        const report = await analyzer.analyze();
        const freshness = await engine.checkEvidenceFreshness();
        const integrity = await engine.checkGovernanceFileIntegrity();

        payload.governance = {
          overall_status: govStatus.overall_status,
          constraint_violations: govStatus.constraint_violations,
          pending_gates: govStatus.pending_gates,
          blocked_gates: govStatus.blocked_gates,
        };
        payload.harness = {
          overall_score: report.overall_score,
          dimensions: report.dimensions.map(d => ({
            id: d.name,
            label: d.label,
            score: d.score,
            ceiling: d.ceiling,
            ceiling_state: d.ceiling_state,
            finding_count: d.findings.length,
          })),
          findings: report.findings.slice(0, 10).map(f => ({
            dimension: f.dimension,
            severity: f.severity,
            title: f.title,
            description: f.description,
          })),
          report_hash: report.report_hash,
        };
        payload.evidence = {
          freshness_ok: freshness.allowed,
          freshness_reason: freshness.reason,
        };
        payload.integrity = {
          verified: integrity.allowed,
          reason: integrity.reason,
        };
      }

      process.stdout.write(JSON.stringify(payload, null, 2) + "\n");
      return;
    }

    // Human mode (colors may be disabled via --no-color)
    const red = (s: string) => (opts.color === false ? s : `\x1b[31m${s}\x1b[0m`);
    const green = (s: string) => (opts.color === false ? s : `\x1b[32m${s}\x1b[0m`);
    const yellow = (s: string) => (opts.color === false ? s : `\x1b[33m${s}\x1b[0m`);
    const bold = (s: string) => (opts.color === false ? s : `\x1b[1m${s}\x1b[0m`);

    console.log(bold("=== Loop Status ==="));
    console.log(`Project:     ${state.project_name}`);
    console.log(`Phase:       ${state.current_phase}`);
    console.log(`Gate:        ${state.current_gate_id}`);
    console.log(`Active Role: ${state.active_role ?? "(none)"}`);

    console.log(`\nPending Gates: ${pendingGates.length > 0 ? yellow(pendingGates.join(", ")) : "(none)"}`);
    console.log(`Blocked Gates: ${blockedGates.length > 0 ? red(blockedGates.join(", ")) : green("(none)")}`);

    if (opts.full) {
      console.log(bold("\n=== Full Status ==="));

      // Constraint check
      const engine = new ConstraintEngine(opts.root);
      const govStatus = await engine.getGovernanceStatus();
      console.log(`\nGovernance Status: ${govStatus.overall_status === "HEALTHY" ? green(govStatus.overall_status) : govStatus.overall_status === "DEGRADED" ? yellow(govStatus.overall_status) : red(govStatus.overall_status)}`);
      console.log(`Constraint Violations: ${govStatus.constraint_violations}`);

      // Harness analysis
      const analyzer = new HarnessAnalyzer(opts.root);
      const report = await analyzer.analyze();
      console.log(`\nHarness Score: ${bold(String(report.overall_score))}/100`);
      console.log(`\nDimension Scores (ceiling: ${yellow("evidence state")}):`);
      for (const dim of report.dimensions) {
        const ceilingTag = `[上限${dim.ceiling} · ${dim.ceiling_state}]`;
        console.log(`  ${dim.label}: ${dim.score}/100 ${ceilingTag}`);
        for (const finding of dim.findings.slice(0, 3)) {
          console.log(`    - ${finding.title}: ${finding.description}`);
        }
      }

      // Evidence freshness
      const freshness = await engine.checkEvidenceFreshness();
      console.log(`\nEvidence Freshness: ${freshness.allowed ? green("OK") : red("Issues")}`);
      if (!freshness.allowed) {
        console.log(`  ${freshness.reason}`);
      }

      // Governance integrity
      const integrity = await engine.checkGovernanceFileIntegrity();
      console.log(`\nGovernance Integrity: ${integrity.allowed ? green("Verified") : red("Failed")}`);
      if (!integrity.allowed) {
        console.log(`  ${integrity.reason}`);
      }
    }
  });

// ── handoff ────────────────────────────────────────────
program.command("handoff")
  .description("Show handoff history")
  .option("-r, --root <path>", "Project root", process.cwd())
  .action(async (opts: { root: string }) => {
    const history = getHandoffHistory(opts.root);
    console.log(history || "(no handoffs recorded)");
  });

// ── prompt (Four-Quadrant Prompt Engine) ───────────────
program.command("prompt")
  .description("Generate a four-quadrant collaboration prompt automatically")
  .option("-t, --task <description>", "What you want to do")
  .option("--role <role-id>", "Role ID (R01-R11) for role-specific guidance")
  .option("--phase <phase-id>", "Current phase")
  .option("--known <info>", "What you already know")
  .option("--gaps <info>", "What you know you don't know")
  .option("--constraints <info>", "Time/resource/tech constraints")
  .option("--experience <level>", "Your experience level on this task")
  .option("-m, --mode <mode>", "Output mode: user | compact | subagent", "user")
  .action((opts: {
    task?: string; role?: string; phase?: string;
    known?: string; gaps?: string; constraints?: string;
    experience?: string; mode: string;
  }) => {
    const ctx: PromptContext = {
      task_description: opts.task,
      role_id: opts.role,
      phase_id: opts.phase,
      known_info: opts.known,
      known_gaps: opts.gaps,
      constraints: opts.constraints,
      experience_level: opts.experience,
      mode: opts.mode as PromptContext["mode"],
    };
    const result = generatePrompt(ctx);
    console.log(result.prompt);
  });

program.parse();
