import type { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { initProject, checkGate, advanceGate, loadState, computeHash, validateProjectRoot } from "../core/state-machine.js";
import { activateRole, getRoleStatus } from "../core/role-engine.js";
import { submitEvidence, verifyEvidence } from "../core/evidence.js";
import { createHandoff, getHandoffHistory } from "../core/handoff.js";
import { deriveEnforcementLevel, validateHostCapabilities, checkConstraint, getDegradationTable, HOST_PRESETS, EnforcementLevel } from "../core/enforcement.js";
import { HardConstraints } from "../core/hard_constraints.js";
import type { ConstraintContext } from "../core/hard_constraints.js";
import { VetoEscalation } from "../core/veto_escalation.js";
import type { VetoRecord } from "../core/veto_escalation.js";
import { AuditLedger } from "../core/audit_ledger.js";
import { join } from "node:path";
import { routeIntent, defaultProfile, LoopMode, RiskLevel } from "../core/router.js";
import { runChallengeForRole, runAllCertifications, buildCertStateAfterRun, ALL_ROLES } from "../core/certification.js";
import type { ProjectProfile } from "../core/router.js";
import type { RoleCertState } from "../core/certification.js";
import { runQualityGates } from "../../scripts/quality-gates.js";
import { runSecurityScan } from "../../scripts/security-scan.js";
import { runEvidenceChain } from "../../scripts/evidence-chain.js";
import { PhaseExecutor, PHASE_ROLES } from "../core/executor.js";
import { ExecutionLedger } from "../core/execution_ledger.js";
import { ContextLoader } from "../core/context_loader.js";
import { EnforcementHub } from "../core/enforcement_hub.js";
import { PacketBuilder, toMarkdown } from "../core/human_review_packet.js";
import type { HumanReviewPacket } from "../core/human_review_packet.js";

function resolveRoot(args: Record<string, unknown>): string {
  const raw = (args.project_root as string) || process.cwd();
  return validateProjectRoot(raw);
}

function textReply(text: string) {
  return { content: [{ type: "text" as const, text }] };
}

export function registerTools(server: Server): void {
  // ── List tools ──────────────────────────────────────
  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: [
      { name: "loop_init", description: "Initialize Loop governance for a project", inputSchema: { type: "object", properties: { project_root: { type: "string" }, project_name: { type: "string" } }, required: ["project_name"] } },
      { name: "loop_gate_check", description: "Check if a gate can advance", inputSchema: { type: "object", properties: { project_root: { type: "string" }, gate_id: { type: "string" } }, required: ["gate_id"] } },
      { name: "loop_gate_advance", description: "Advance a gate (blocks if conditions unmet)", inputSchema: { type: "object", properties: { project_root: { type: "string" }, gate_id: { type: "string" } }, required: ["gate_id"] } },
      { name: "loop_role_activate", description: "Activate a role", inputSchema: { type: "object", properties: { project_root: { type: "string" }, role_id: { type: "string" } }, required: ["role_id"] } },
      { name: "loop_role_status", description: "Query role status", inputSchema: { type: "object", properties: { project_root: { type: "string" }, role_id: { type: "string" } }, required: ["role_id"] } },
      { name: "loop_evidence_submit", description: "Submit evidence with hash binding", inputSchema: { type: "object", properties: { project_root: { type: "string" }, evidence_id: { type: "string" }, type: { type: "string" }, content: { type: "string" }, role_id: { type: "string" }, gate_id: { type: "string" }, ttl_seconds: { type: "number" } }, required: ["evidence_id", "type", "content"] } },
      { name: "loop_evidence_verify", description: "Verify evidence integrity and freshness", inputSchema: { type: "object", properties: { project_root: { type: "string" }, evidence_id: { type: "string" } }, required: ["evidence_id"] } },
      { name: "loop_handoff", description: "Create a handoff between roles", inputSchema: { type: "object", properties: { project_root: { type: "string" }, from_role: { type: "string" }, to_role: { type: "string" }, artifacts: { type: "array", items: { type: "object", properties: { path: { type: "string" }, version: { type: "string" } } } }, context_summary: { type: "string" } }, required: ["from_role", "to_role", "context_summary"] } },
      { name: "loop_state", description: "Query current project state", inputSchema: { type: "object", properties: { project_root: { type: "string" } } } },
      { name: "loop_enforcement_check", description: "Check host enforcement level and hard constraints", inputSchema: { type: "object", properties: { host_preset: { type: "string", description: "Known host: qoder|zcode|claude_code|standalone" }, constraint_id: { type: "string", description: "Specific constraint to check (optional)" } } } },
      { name: "loop_route_intent", description: "Classify project risk and determine Loop mode (LIGHTWEIGHT/STANDARD/FULL)", inputSchema: { type: "object", properties: { has_database: { type: "boolean" }, has_auth_permissions: { type: "boolean" }, has_payments: { type: "boolean" }, has_production_data: { type: "boolean" }, has_security_requirements: { type: "boolean" }, has_multiple_modules: { type: "boolean" }, has_external_api: { type: "boolean" }, has_concurrency_performance: { type: "boolean" }, requires_deployment: { type: "boolean" }, requires_monitoring_rollback: { type: "boolean" }, requires_ongoing_iteration: { type: "boolean" }, has_high_uncertainty: { type: "boolean" }, has_complex_business_logic: { type: "boolean" }, user_forced_mode: { type: "string", description: "LIGHTWEIGHT|STANDARD|FULL" } } } },
      { name: "loop_certify_role", description: "Run capability certification for a role", inputSchema: { type: "object", properties: { role_id: { type: "string", description: "Role to certify (or 'all')" }, current_state: { type: "string", description: "Current cert state (optional)" }, consecutive_failures: { type: "number", description: "Current consecutive failures (optional)" } } } },
      { name: "loop_quality_run", description: "Run quality gates (lint/typecheck/test/build/audit)", inputSchema: { type: "object", properties: { project_root: { type: "string" } } } },
      { name: "loop_security_scan", description: "Run security scan (secrets/injection/CVE)", inputSchema: { type: "object", properties: { project_root: { type: "string" }, scan_dir: { type: "string", description: "Directory to scan (default: src)" } } } },
      { name: "loop_evidence_chain", description: "Verify evidence chain integrity", inputSchema: { type: "object", properties: { project_root: { type: "string" }, strict: { type: "boolean", description: "Strict mode: any failure = BLOCKED" } } } },
      { name: "loop_constraint_check", description: "Run all 8 hard constraints (C1–C8) against the current context", inputSchema: { type: "object", properties: { project_root: { type: "string" }, current_phase: { type: "string", description: "Current phase (e.g. S1, S4)" }, target_phase: { type: "string", description: "Phase being entered" }, phase_gates: { type: "object", description: "gate_id → status map" }, tasks: { type: "array", description: "Task list", items: { type: "object", properties: { id: { type: "string" }, status: { type: "string" }, allowed_paths: { type: "array", items: { type: "string" } } } } }, target_path: { type: "string", description: "Intended write path" }, allowed_paths: { type: "array", description: "Permitted path prefixes", items: { type: "string" } }, quality_results: { type: "object", description: "test/lint/build → PASS/FAIL" }, review_status: { type: "object", description: "reviewer_role → verdict" }, gates: { type: "array", items: { type: "object", properties: { id: { type: "string" }, status: { type: "string" } } } }, evidence_list: { type: "array", description: "Evidence envelopes" }, current_hashes: { type: "object", description: "evidence_id → current content hash" } } } },
      { name: "loop_veto_escalate", description: "Analyse unresolved vetos and determine escalation level", inputSchema: { type: "object", properties: { vetos: { type: "array", description: "List of veto records", items: { type: "object", properties: { veto_id: { type: "string" }, role_id: { type: "string" }, severity: { type: "string" }, target: { type: "string" }, reason: { type: "string" }, created_at: { type: "string" }, resolved: { type: "boolean" } }, required: ["veto_id", "role_id", "severity", "target", "reason", "created_at"] } }, generate_summary: { type: "boolean", description: "Also generate human review summary (default: false)" } }, required: ["vetos"] } },
      { name: "loop_audit_log", description: "Append an entry to the chain-hashed audit ledger", inputSchema: { type: "object", properties: { project_root: { type: "string" }, event: { type: "string", description: "Event type (e.g. gate_advance, role_activate, veto, handoff)" }, actor: { type: "string", description: "Role or actor triggering the event" }, details: { type: "object", description: "Arbitrary structured details" } }, required: ["event", "actor"] } },
      { name: "loop_audit_verify", description: "Verify the integrity of the chain-hashed audit ledger", inputSchema: { type: "object", properties: { project_root: { type: "string" } } } },
      { name: "loop_host_status", description: "Report host integration capabilities and enforcement level", inputSchema: { type: "object", properties: {} } },
      { name: "loop_execute_phase", description: "Execute a complete phase (requirements/architecture/planning/implementation/review/delivery)", inputSchema: { type: "object", properties: { project_root: { type: "string" }, phase_id: { type: "string", description: "Phase to execute" } }, required: ["phase_id"] } },
      { name: "loop_execution_log", description: "Query execution ledger for a task or role", inputSchema: { type: "object", properties: { project_root: { type: "string" }, task_id: { type: "string" }, role_id: { type: "string" }, recent: { type: "number", description: "Number of recent entries (default: 10)" } } } },
      { name: "loop_execution_verify", description: "Verify execution ledger chain integrity", inputSchema: { type: "object", properties: { project_root: { type: "string" } } } },
      { name: "loop_governance_status", description: "Get full governance status summary (HEALTHY/DEGRADED/BLOCKED)", inputSchema: { type: "object", properties: { project_root: { type: "string" } } } },
      { name: "loop_load_context", description: "Load progressive role context based on task complexity", inputSchema: { type: "object", properties: { role_id: { type: "string" }, complexity: { type: "number", description: "Task complexity 0.0-1.0" } }, required: ["role_id"] } },
      { name: "loop_review_packet", description: "Generate a human-readable review packet for gate approval or veto escalation", inputSchema: { type: "object", properties: { project_root: { type: "string" }, packet_type: { type: "string", description: "GATE_APPROVAL | VETO_ESCALATION | CHANGE_REQUEST" }, phase: { type: "string", description: "Phase ID (for GATE_APPROVAL)" }, task_id: { type: "string" }, artifacts: { type: "array", items: { type: "string" } }, vetos: { type: "array", items: { type: "object" } }, description: { type: "string" } }, required: ["packet_type"] } },
    ],
  }));

  // ── Handle tool calls ───────────────────────────────
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    const root = resolveRoot(args ?? {});

    try {
      switch (name) {
        case "loop_init": {
          const state = await initProject(root, (args?.project_name as string) ?? "unnamed");
          return textReply(`Project initialized: ${state.project_name}\nPhase: ${state.current_phase}\nGate: ${state.current_gate_id}`);
        }

        case "loop_gate_check": {
          const result = await checkGate(root, args!.gate_id as string);
          if (result.status === "pass") {
            return textReply(`Gate ${result.gate_id}: PASS (${result.conditions_met}/${result.conditions_total} conditions met)`);
          }
          const missing = result.missing_conditions.map(m => `  - ${m.description}`).join("\n");
          return textReply(`Gate ${result.gate_id}: BLOCKED (${result.conditions_met}/${result.conditions_total})\nMissing:\n${missing}`);
        }

        case "loop_gate_advance": {
          const result = await advanceGate(root, args!.gate_id as string);
          if (result.success) {
            return textReply(`Gate advanced: ${result.previous_phase} → ${result.new_phase} at ${result.advanced_at}`);
          }
          return textReply(`Gate BLOCKED: ${result.error}`);
        }

        case "loop_role_activate": {
          const result = await activateRole(root, args!.role_id as string);
          if (result.success) {
            return textReply(`Role ${result.role_id} activated at ${result.activated_at}`);
          }
          return textReply(`Role activation failed: ${result.error}`);
        }

        case "loop_role_status": {
          const result = await getRoleStatus(root, args!.role_id as string);
          return textReply(JSON.stringify(result, null, 2));
        }

        case "loop_evidence_submit": {
          const result = await submitEvidence(root, {
            evidence_id: args!.evidence_id as string,
            type: args!.type as string,
            content: args!.content as string,
            role_id: args?.role_id as string | undefined,
            gate_id: args?.gate_id as string | undefined,
            ttl_seconds: args?.ttl_seconds as number | undefined,
          });
          return textReply(`Evidence submitted: ${result.evidence_id}\nHash: ${result.content_hash}\nStored: ${result.stored_at}`);
        }

        case "loop_evidence_verify": {
          const result = await verifyEvidence(root, args!.evidence_id as string);
          return textReply(JSON.stringify(result, null, 2));
        }

        case "loop_handoff": {
          const result = await createHandoff(
            root,
            args!.from_role as string,
            args!.to_role as string,
            (args?.artifacts as { path: string; version: string }[]) ?? [],
            args!.context_summary as string,
          );
          return textReply(`Handoff created: ${result.handoff_id}\nArtifacts: ${result.artifacts_count}`);
        }

        case "loop_state": {
          const state = await loadState(root);
          return textReply(JSON.stringify(state, null, 2));
        }

        case "loop_enforcement_check": {
          const preset = (args?.host_preset as string) || "qoder";
          const caps = HOST_PRESETS[preset];
          if (!caps) return textReply(`Unknown host preset: ${preset}. Available: ${Object.keys(HOST_PRESETS).join(", ")}`);
          const level = deriveEnforcementLevel(caps);
          const validation = validateHostCapabilities(caps, level);

          const constraintId = args?.constraint_id as string | undefined;
          if (constraintId) {
            const result = checkConstraint(constraintId, level, {});
            return textReply(JSON.stringify({ preset, enforcement_level: level, constraint: result }, null, 2));
          }

          const table = getDegradationTable(level);
          return textReply(JSON.stringify({
            preset,
            capabilities: caps,
            enforcement_level: level,
            honest: validation.is_honest,
            violations: validation.violations,
            constraints: table,
          }, null, 2));
        }

        case "loop_route_intent": {
          const profile: ProjectProfile = {
            has_database: Boolean(args?.has_database),
            has_auth_permissions: Boolean(args?.has_auth_permissions),
            has_payments: Boolean(args?.has_payments),
            has_production_data: Boolean(args?.has_production_data),
            has_security_requirements: Boolean(args?.has_security_requirements),
            has_multiple_modules: Boolean(args?.has_multiple_modules),
            has_external_api: Boolean(args?.has_external_api),
            has_concurrency_performance: Boolean(args?.has_concurrency_performance),
            requires_deployment: Boolean(args?.requires_deployment),
            requires_monitoring_rollback: Boolean(args?.requires_monitoring_rollback),
            requires_ongoing_iteration: Boolean(args?.requires_ongoing_iteration),
            has_high_uncertainty: Boolean(args?.has_high_uncertainty),
            has_complex_business_logic: Boolean(args?.has_complex_business_logic),
            user_forced_mode: args?.user_forced_mode ? (args.user_forced_mode as LoopMode) : null,
          };
          const result = routeIntent(profile);
          return textReply(JSON.stringify(result, null, 2));
        }

        case "loop_certify_role": {
          const roleId = (args?.role_id as string) || "all";
          const currentStateStr = args?.current_state as string | undefined;
          const consecutiveFailures = (args?.consecutive_failures as number) ?? 0;

          if (roleId === "all") {
            const run = runAllCertifications();
            const summary = ALL_ROLES.map(r => {
              const res = run.results[r];
              const tr = run.state_transitions[r];
              return `${res.passed ? "PASS" : "FAIL"} ${r.padEnd(25)} ${res.challenge_name.padEnd(45)} (${res.checks_passed}/${res.checks_total}) ${tr.previous_state}→${tr.next_state}`;
            }).join("\n");
            return textReply(`Certification: ${run.overall_pass ? "ALL PASS" : "SOME FAILED"}\n\n${summary}`);
          }

          const certState: Record<string, RoleCertState> = {
            [roleId]: {
              state: currentStateStr || "CERTIFIED",
              consecutive_failures: consecutiveFailures,
              last_run: "", last_challenge: "", last_score: 0, last_evidence_hash: "",
            },
          };
          const { result, transition } = runChallengeForRole(roleId, certState);
          return textReply(JSON.stringify({ result, transition }, null, 2));
        }

        case "loop_quality_run": {
          const report = runQualityGates(root);
          return textReply(JSON.stringify(report, null, 2));
        }

        case "loop_security_scan": {
          const scanDir = (args?.scan_dir as string) || "src";
          const report = runSecurityScan(root, scanDir);
          return textReply(JSON.stringify(report, null, 2));
        }

        case "loop_evidence_chain": {
          const strict = Boolean(args?.strict);
          const report = runEvidenceChain(root, strict);
          return textReply(JSON.stringify(report, null, 2));
        }

        case "loop_constraint_check": {
          const ctx: ConstraintContext = {
            current_phase: args?.current_phase as string | undefined,
            target_phase: args?.target_phase as string | undefined,
            phase_gates: args?.phase_gates as Record<string, string> | undefined,
            tasks: args?.tasks as Array<{ id: string; status: string; allowed_paths?: string[] }> | undefined,
            target_path: args?.target_path as string | undefined,
            allowed_paths: args?.allowed_paths as string[] | undefined,
            quality_results: args?.quality_results as Record<string, string> | undefined,
            review_status: args?.review_status as Record<string, string> | undefined,
            gates: args?.gates as Array<{ id: string; status: string }> | undefined,
            current_hashes: args?.current_hashes as Record<string, string> | undefined,
          };
          const checker = new HardConstraints();
          const result = checker.checkAll(ctx);
          const summary = result.passed
            ? `Constraint check: PASSED (${result.violations.length} warning(s))`
            : `Constraint check: BLOCKED (${result.violations.filter(v => v.severity === "BLOCKER").length} blocker(s), ${result.violations.filter(v => v.severity === "WARNING").length} warning(s))`;
          const details = result.violations.map(v =>
            `[${v.severity}] ${v.constraint_id}: ${v.message}\n  Remediation: ${v.remediation}`
          ).join("\n");
          return textReply(`${summary}\n${details || "No violations."}`);
        }

        case "loop_veto_escalate": {
          const vetos = (args?.vetos as VetoRecord[]) ?? [];
          const generateSummary = Boolean(args?.generate_summary);
          const escalation = new VetoEscalation();
          const decision = escalation.checkEscalation(vetos);
          let output = JSON.stringify(decision, null, 2);
          if (generateSummary) {
            output += "\n\n" + escalation.generateHumanReviewSummary(vetos);
          }
          return textReply(output);
        }

        case "loop_audit_log": {
          const ledgerPath = join(root, ".ai", "audit_ledger.jsonl");
          const ledger = new AuditLedger(ledgerPath);
          const event = args!.event as string;
          const actor = args!.actor as string;
          const details = (args?.details as Record<string, unknown>) ?? {};
          const entry = ledger.append(event, actor, details);
          return textReply(
            `Audit entry appended:\n` +
            `  seq:         ${entry.seq}\n` +
            `  timestamp:   ${entry.timestamp}\n` +
            `  event:       ${entry.event}\n` +
            `  actor:       ${entry.actor}\n` +
            `  chain_hash:  ${entry.chain_hash}`
          );
        }

        case "loop_audit_verify": {
          const ledgerPath = join(root, ".ai", "audit_ledger.jsonl");
          const ledger = new AuditLedger(ledgerPath);
          const integrity = ledger.verifyIntegrity();
          const totalEntries = ledger.length;
          if (integrity.valid) {
            return textReply(`Audit ledger: INTEGRITY OK (${totalEntries} entries verified)`);
          }
          return textReply(
            `Audit ledger: INTEGRITY FAILURE\n` +
            `First invalid entry seq: ${integrity.firstInvalidSeq}\n` +
            `Total entries: ${totalEntries}\n` +
            `The ledger may have been tampered with. Investigate immediately.`
          );
        }

        case "loop_host_status": {
          const preset = HOST_PRESETS["qoder"];
          return textReply(JSON.stringify({
            host: "qoder",
            enforcement_level: deriveEnforcementLevel(preset),
            capabilities: preset,
            hooks: [
              "gate-guard.js",
              "path-guard.js",
              "role-isolation.js",
              "ledger-guard.js",
              "auto-activate.js",
              "template-injector.js",
              "session-brief.js",
            ],
          }, null, 2));
        }

        case "loop_execute_phase": {
          const phaseId = args!.phase_id as string;
          const executor = new PhaseExecutor(root);
          const result = await executor.executePhase(phaseId);
          const summary = result.success
            ? `Phase ${result.phase_id}: COMPLETED (${result.steps_completed}/${result.steps_total} steps, ${result.duration_ms}ms)`
            : `Phase ${result.phase_id}: FAILED (${result.steps_failed} failed, ${result.errors.length} errors)`;
          const details = result.errors.length > 0 ? `\nErrors:\n${result.errors.map(e => `  - ${e}`).join("\n")}` : "";
          return textReply(summary + details);
        }

        case "loop_execution_log": {
          const ledgerPath = join(root, ".ai", "ledger", "executions.jsonl");
          const ledger = new ExecutionLedger(ledgerPath);
          const taskId = args?.task_id as string | undefined;
          const roleId = args?.role_id as string | undefined;
          const recentN = (args?.recent as number) ?? 10;

          let entries;
          if (taskId) {
            entries = ledger.findByTask(taskId);
          } else if (roleId) {
            entries = ledger.findByRole(roleId);
          } else {
            entries = ledger.recent(recentN);
          }
          return textReply(JSON.stringify(entries, null, 2));
        }

        case "loop_execution_verify": {
          const ledgerPath = join(root, ".ai", "ledger", "executions.jsonl");
          const ledger = new ExecutionLedger(ledgerPath);
          const integrity = ledger.verifyChain();
          if (integrity.valid) {
            return textReply(`Execution ledger: INTEGRITY OK (${integrity.totalEntries} entries verified)`);
          }
          return textReply(
            `Execution ledger: INTEGRITY FAILURE\n` +
            `First invalid entry seq: ${integrity.firstInvalidSeq}\n` +
            `Total entries: ${integrity.totalEntries}`
          );
        }

        case "loop_governance_status": {
          const hub = new EnforcementHub(root);
          const status = await hub.getGovernanceStatus();
          return textReply(JSON.stringify(status, null, 2));
        }

        case "loop_load_context": {
          const roleId = args!.role_id as string;
          const complexity = (args?.complexity as number) ?? 0.5;
          const loader = new ContextLoader();
          const loaded = loader.loadRoleContext(roleId, complexity);
          const summary = `Role: ${loaded.role_id}\nLevel: ${loaded.level}\nTokens: ~${loaded.estimated_tokens}\nSections: ${loaded.loaded_sections.join(", ")}`;
          return textReply(`${summary}\n\n--- System Prompt ---\n${loaded.system_prompt}`);
        }

        case "loop_review_packet": {
          const packetType = args!.packet_type as string;
          let packet: HumanReviewPacket;

          switch (packetType) {
            case "GATE_APPROVAL":
              packet = PacketBuilder.fromPhaseCompletion({
                phase: (args?.phase as string) ?? "unknown",
                taskId: (args?.task_id as string) ?? "",
                artifacts: (args?.artifacts as string[]) ?? [],
              });
              break;
            case "VETO_ESCALATION":
              packet = PacketBuilder.fromVetoEscalation({
                vetos: (args?.vetos as Array<{ role_id: string; reason: string; severity: string }>) ?? [],
                taskId: (args?.task_id as string) ?? "",
              });
              break;
            case "CHANGE_REQUEST":
              packet = PacketBuilder.fromChangeRequest({
                description: (args?.description as string) ?? "",
                impact: "",
                affectedModules: [],
              });
              break;
            default:
              return textReply(`Unknown packet type: ${packetType}. Available: GATE_APPROVAL, VETO_ESCALATION, CHANGE_REQUEST`);
          }

          const markdown = toMarkdown(packet);
          return textReply(markdown);
        }

        default:
          return textReply(`Unknown tool: ${name}`);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return textReply(`Error: ${msg}`);
    }
  });
}
