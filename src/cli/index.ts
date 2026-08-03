#!/usr/bin/env node
import { Command } from "commander";
import { initProject, checkGate, advanceGate, approveGate, loadState } from "../core/state-machine.js";
import { activateRole, getRoleStatus } from "../core/role-engine.js";
import { submitEvidence, verifyEvidence } from "../core/evidence.js";
import { getHandoffHistory } from "../core/handoff.js";
import { generatePrompt } from "../core/prompt_engine.js";
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
